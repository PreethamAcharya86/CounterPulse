import io
import re
import logging
from typing import Optional, List, Dict, Any
from pypdf import PdfReader
from PIL import Image
import numpy as np

from backend.app.services.evidence.base import (
    EvidenceProcessor,
    NormalizedEvidence,
    ContentSegment,
    ProvenanceItem,
)
from backend.app.services.evidence.image_processor import get_ocr_engine

logger = logging.getLogger(__name__)

class PDFProcessor(EvidenceProcessor):
    """
    Real PDF text extractor supporting multi-page documents.
    Preserves exact per-page structure and falls back to OCR for scanned pages.
    """

    async def process(self, evidence: Any, file_bytes: Optional[bytes] = None) -> NormalizedEvidence:
        evidence_id = getattr(evidence, "id", "EV-UNKNOWN")
        case_id = getattr(evidence, "case_id", "CASE-UNKNOWN")
        filename = getattr(evidence, "filename", "document.pdf")
        mime_type = getattr(evidence, "mime_type", "application/pdf")
        file_size = getattr(evidence, "file_size", len(file_bytes) if file_bytes else 0)
        sha256 = getattr(evidence, "sha256_hash", "")

        if not file_bytes:
            file_path = getattr(evidence, "file_path", None)
            if file_path:
                try:
                    with open(file_path, "rb") as f:
                        file_bytes = f.read()
                except Exception as e:
                    return NormalizedEvidence(
                        evidence_id=evidence_id,
                        case_id=case_id,
                        type="pdf",
                        source={"filename": filename, "mime_type": mime_type, "file_size": file_size, "sha256_hash": sha256},
                        content={"text": "", "pages": []},
                        processing_status="failed",
                        error_message=f"Could not read PDF from disk: {str(e)}",
                    )
            else:
                return NormalizedEvidence(
                    evidence_id=evidence_id,
                    case_id=case_id,
                    type="pdf",
                    source={"filename": filename, "mime_type": mime_type, "file_size": file_size, "sha256_hash": sha256},
                    content={"text": "", "pages": []},
                    processing_status="failed",
                    error_message="No PDF bytes provided for processing",
                )

        try:
            reader = PdfReader(io.BytesIO(file_bytes))
            total_pages = len(reader.pages)
        except Exception as e:
            logger.error(f"Failed to parse PDF {evidence_id}: {e}")
            return NormalizedEvidence(
                evidence_id=evidence_id,
                case_id=case_id,
                type="pdf",
                source={"filename": filename, "mime_type": mime_type, "file_size": file_size, "sha256_hash": sha256},
                content={"text": "", "pages": []},
                processing_status="failed",
                error_message=f"Corrupt or unreadable PDF: {str(e)}",
            )

        pages_data: List[Dict[str, Any]] = []
        segments: List[ContentSegment] = []
        provenance_items: List[ProvenanceItem] = []
        full_text_blocks: List[str] = []
        scanned_page_count = 0

        for page_idx, page in enumerate(reader.pages):
            page_num = page_idx + 1
            extracted_text = ""
            is_ocr = False

            try:
                # 1. Direct text extraction
                raw_page_text = page.extract_text() or ""
                extracted_text = raw_page_text.strip()
            except Exception as e:
                logger.warning(f"Error extracting text from page {page_num}: {e}")

            # 2. Check if page appears scanned / image-only (less than 20 characters)
            if len(extracted_text) < 20 and hasattr(page, "images") and len(page.images) > 0:
                logger.info(f"Page {page_num} of {evidence_id} appears to be scanned. Running OCR fallback...")
                ocr_page_lines = []
                try:
                    engine = get_ocr_engine()
                    for img_file in page.images:
                        img_pil = Image.open(io.BytesIO(img_file.data))
                        if img_pil.mode not in ("RGB", "L"):
                            img_pil = img_pil.convert("RGB")
                        ocr_res, _ = engine(np.array(img_pil))
                        if ocr_res:
                            for item in ocr_res:
                                ocr_page_lines.append(item[1])
                    if ocr_page_lines:
                        extracted_text = "\n".join(ocr_page_lines)
                        is_ocr = True
                        scanned_page_count += 1
                except Exception as ocr_err:
                    logger.warning(f"OCR fallback failed on page {page_num}: {ocr_err}")

            if not extracted_text:
                extracted_text = f"[Page {page_num}: Empty or image without recognizable text]"

            formatted_page_header = f"--- Page {page_num} ---\n{extracted_text}"
            full_text_blocks.append(formatted_page_header)

            pages_data.append({
                "page_number": page_num,
                "text": extracted_text,
                "char_count": len(extracted_text),
                "is_ocr_fallback": is_ocr,
            })

            # Create a content segment per page
            segments.append(
                ContentSegment(
                    segment_id=f"PAGE-{page_num:03d}",
                    text=extracted_text[:1000],  # preview
                    evidence_id=evidence_id,
                    confidence=0.85 if is_ocr else 1.0,
                    timestamp_str=None,
                    speaker=None,
                )
            )

            # Look for critical financial/case indicators on this page
            amounts = re.findall(r"(?:₹|Rs\.?|INR)\s*[\d,]+(?:\.\d{2})?", extracted_text, re.IGNORECASE)
            for amt in amounts[:3]:
                provenance_items.append(
                    ProvenanceItem(
                        source_evidence_id=evidence_id,
                        source_reference=f"PDF Page {page_num}",
                        extracted_value=amt,
                        confidence="high",
                        verification_status="supported",
                    )
                )

            # Bank account / UTR / Reference numbers
            utr_matches = re.findall(r"\b(?:UTR|Ref|Txn|Reference)\s*(?:No\.?)?[:\s]*([A-Z0-9]{8,22})\b", extracted_text, re.IGNORECASE)
            for utr in utr_matches[:3]:
                provenance_items.append(
                    ProvenanceItem(
                        source_evidence_id=evidence_id,
                        source_reference=f"PDF Page {page_num}",
                        extracted_value=f"Ref: {utr}",
                        confidence="high",
                        verification_status="supported",
                    )
                )

        normalized_full_text = "\n\n".join(full_text_blocks)

        return NormalizedEvidence(
            evidence_id=evidence_id,
            case_id=case_id,
            type="pdf",
            source={
                "filename": filename,
                "mime_type": mime_type,
                "file_size": file_size,
                "sha256_hash": sha256,
            },
            content={
                "text": normalized_full_text,
                "pages": pages_data,
                "segments": [s.model_dump() for s in segments],
                "page_count": total_pages,
            },
            metadata={
                "total_pages": total_pages,
                "scanned_pages_detected": scanned_page_count,
                "ocr_fallback_used": scanned_page_count > 0,
            },
            provenance=provenance_items,
            processing_status="processed",
        )
