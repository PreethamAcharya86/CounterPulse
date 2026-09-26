import io
import re
import logging
from typing import Optional, List, Dict, Any
import numpy as np
from PIL import Image

from backend.app.services.evidence.base import (
    EvidenceProcessor,
    NormalizedEvidence,
    ContentSegment,
    ProvenanceItem,
)
from backend.app.core.config import settings

logger = logging.getLogger(__name__)

# Singleton OCR engine to avoid reloading on every request
_ocr_engine = None

def get_ocr_engine():
    global _ocr_engine
    if _ocr_engine is None:
        try:
            from rapidocr_onnxruntime import RapidOCR
            _ocr_engine = RapidOCR()
            logger.info("RapidOCR engine initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize RapidOCR engine: {e}")
            raise RuntimeError(f"OCR Engine initialization failed: {e}")
    return _ocr_engine

class ImageProcessor(EvidenceProcessor):
    """
    Real Optical Character Recognition (OCR) and vision processor.
    Extracts text, bounding boxes, confidence scores, and provenance from images.
    Supports PNG, JPG, JPEG, WEBP.
    """

    async def process(self, evidence: Any, file_bytes: Optional[bytes] = None) -> NormalizedEvidence:
        evidence_id = getattr(evidence, "id", "EV-UNKNOWN")
        case_id = getattr(evidence, "case_id", "CASE-UNKNOWN")
        filename = getattr(evidence, "filename", "unnamed.png")
        mime_type = getattr(evidence, "mime_type", "image/png")
        file_size = getattr(evidence, "file_size", len(file_bytes) if file_bytes else 0)
        sha256 = getattr(evidence, "sha256_hash", "")

        if not file_bytes:
            # Try reading from file_path if available
            file_path = getattr(evidence, "file_path", None)
            if file_path:
                try:
                    with open(file_path, "rb") as f:
                        file_bytes = f.read()
                except Exception as e:
                    return NormalizedEvidence(
                        evidence_id=evidence_id,
                        case_id=case_id,
                        type="image",
                        source={"filename": filename, "mime_type": mime_type, "file_size": file_size, "sha256_hash": sha256},
                        content={"text": "", "segments": []},
                        processing_status="failed",
                        error_message=f"Could not read image file from disk: {str(e)}",
                    )
            else:
                return NormalizedEvidence(
                    evidence_id=evidence_id,
                    case_id=case_id,
                    type="image",
                    source={"filename": filename, "mime_type": mime_type, "file_size": file_size, "sha256_hash": sha256},
                    content={"text": "", "segments": []},
                    processing_status="failed",
                    error_message="No image data provided for processing",
                )

        # 1. Validate image format & dimensions using PIL
        try:
            pil_image = Image.open(io.BytesIO(file_bytes))
            width, height = pil_image.size
            img_format = pil_image.format or "UNKNOWN"
            # Convert to RGB if necessary (e.g. RGBA or palette images)
            if pil_image.mode not in ("RGB", "L"):
                pil_image = pil_image.convert("RGB")
            img_np = np.array(pil_image)
        except Exception as e:
            logger.error(f"Image decode error for {evidence_id}: {e}")
            return NormalizedEvidence(
                evidence_id=evidence_id,
                case_id=case_id,
                type="image",
                source={"filename": filename, "mime_type": mime_type, "file_size": file_size, "sha256_hash": sha256},
                content={"text": "", "segments": []},
                metadata={"error": "corrupt_image"},
                processing_status="failed",
                error_message=f"Failed to decode image: {str(e)}",
            )

        # 2. Perform Real Local OCR via RapidOCR
        segments: List[ContentSegment] = []
        provenance_items: List[ProvenanceItem] = []
        extracted_lines: List[str] = []

        try:
            engine = get_ocr_engine()
            ocr_results, _ = engine(img_np)
        except Exception as e:
            logger.error(f"OCR execution error for {evidence_id}: {e}")
            return NormalizedEvidence(
                evidence_id=evidence_id,
                case_id=case_id,
                type="image",
                source={"filename": filename, "mime_type": mime_type, "file_size": file_size, "sha256_hash": sha256},
                content={"text": "", "segments": []},
                processing_status="failed",
                error_message=f"OCR execution failed: {str(e)}",
            )

        if ocr_results:
            for idx, item in enumerate(ocr_results):
                box, text, score = item
                text = str(text).strip()
                if not text:
                    continue
                extracted_lines.append(text)

                try:
                    score_val = float(score)
                except (ValueError, TypeError):
                    score_val = 0.8

                # Bounding box coordinates summary: [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
                box_summary = f"[{int(box[0][0])},{int(box[0][1])} to {int(box[2][0])},{int(box[2][1])}]"
                conf_level = "high" if score_val >= 0.85 else ("medium" if score_val >= 0.60 else "low")

                segments.append(
                    ContentSegment(
                        segment_id=f"OCR-{idx+1:03d}",
                        text=text,
                        evidence_id=evidence_id,
                        confidence=round(score_val, 3),
                        timestamp_str=None,
                        speaker=None,
                    )
                )

                # Search for forensic entities to create immediate provenance records
                # e.g., currency amounts (₹, Rs, INR)
                amount_match = re.search(r"(?:₹|Rs\.?|INR)\s*[\d,]+(?:\.\d{2})?", text, re.IGNORECASE)
                if amount_match:
                    provenance_items.append(
                        ProvenanceItem(
                            source_evidence_id=evidence_id,
                            source_reference=f"Screenshot OCR {box_summary}",
                            extracted_value=amount_match.group(0),
                            confidence=conf_level,
                            verification_status="supported",
                        )
                    )
                # UPI handles
                upi_match = re.search(r"[\w.-]+@(?:ok[a-z]+|okhdfcbank|oksbi|paytm|ybl|ibl|axl|apl)", text, re.IGNORECASE)
                if upi_match:
                    provenance_items.append(
                        ProvenanceItem(
                            source_evidence_id=evidence_id,
                            source_reference=f"Screenshot OCR {box_summary}",
                            extracted_value=upi_match.group(0),
                            confidence=conf_level,
                            verification_status="supported",
                        )
                    )
                # Phone numbers
                phone_match = re.search(r"(?:\+91[\-\s]?)?[6-9]\d{9}\b", text)
                if phone_match:
                    provenance_items.append(
                        ProvenanceItem(
                            source_evidence_id=evidence_id,
                            source_reference=f"Screenshot OCR {box_summary}",
                            extracted_value=phone_match.group(0),
                            confidence=conf_level,
                            verification_status="supported",
                        )
                    )

        full_extracted_text = "\n".join(extracted_lines)
        if not full_extracted_text:
            full_extracted_text = "[No readable text detected in image]"

        return NormalizedEvidence(
            evidence_id=evidence_id,
            case_id=case_id,
            type="image",
            source={
                "filename": filename,
                "mime_type": mime_type,
                "file_size": file_size,
                "sha256_hash": sha256,
            },
            content={
                "text": full_extracted_text,
                "segments": [s.model_dump() for s in segments],
                "line_count": len(extracted_lines),
            },
            metadata={
                "image_width": width,
                "image_height": height,
                "format": img_format,
                "ocr_engine": "RapidOCR-ONNX",
                "detected_blocks": len(segments),
            },
            provenance=provenance_items,
            processing_status="processed",
        )
