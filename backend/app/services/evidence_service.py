import os
import re
import json
import logging
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from fastapi import UploadFile, HTTPException

from backend.app.models.evidence import Evidence
from backend.app.models.case import Case
from backend.app.models.indicator import Indicator
from backend.app.core.config import settings
from backend.app.core.security import (
    sanitize_filename,
    validate_file_upload,
    compute_sha256,
    get_safe_storage_path,
    sanitize_path_for_response,
)
from backend.app.services.evidence.factory import EvidenceProcessorFactory
from backend.app.services.evidence.live_processor import LiveWhatsAppProcessor
from backend.app.services.evidence.base import NormalizedEvidence

logger = logging.getLogger(__name__)

class EvidenceService:
    """
    Evidence Intake and Lifecycle Management Service.
    Handles file intake, validation, cryptographic hashing, modular processing,
    normalized persistence, and provenance extraction.
    """

    def __init__(self):
        self.live_processor = LiveWhatsAppProcessor()

    async def ingest_file(
        self,
        case_id: str,
        file: UploadFile,
        db: Session,
        evidence_type_override: Optional[str] = None,
        auto_process: bool = True,
    ) -> Tuple[Evidence, Optional[NormalizedEvidence]]:
        """
        Validate, store, and optionally process an uploaded evidence file.
        """
        # 1. Verify case exists
        case = db.query(Case).filter(Case.id == case_id).first()
        if not case:
            raise HTTPException(status_code=404, detail=f"Case with ID '{case_id}' not found.")

        # 2. Read bytes and validate
        original_filename = file.filename or "uploaded_file"
        mime_type = file.content_type or "application/octet-stream"

        try:
            file_bytes = await file.read()
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to read uploaded file: {str(e)}")

        file_size = len(file_bytes)

        is_valid, error_msg = validate_file_upload(original_filename, mime_type, file_size)
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_msg)

        # 3. Cryptographic hash
        sha256 = compute_sha256(file_bytes)

        # 4. Determine evidence type
        if evidence_type_override:
            ev_type = evidence_type_override.lower()
        else:
            if mime_type.startswith("image/"):
                ev_type = "image"
            elif mime_type == "application/pdf":
                ev_type = "pdf"
            elif mime_type.startswith("audio/"):
                ev_type = "audio"
            else:
                # Auto-detect if text file contains WhatsApp or chat log structure
                text_sample = ""
                try:
                    text_sample = file_bytes[:4096].decode("utf-8", errors="replace")
                except Exception:
                    pass
                fn_lower = original_filename.lower()
                is_chat_name = "chat" in fn_lower or "whatsapp" in fn_lower or fn_lower.endswith(".chat")
                is_chat_content = bool(re.search(r'(?:^\[?\d{1,4}[/-]\d{1,2}[/-]\d{2,4}[,\s]+\d{1,2}:\d{2}|^\d{1,2}:\d{2}\s*[-–—]|^\[\d{1,2}:\d{2})', text_sample, re.MULTILINE))
                if is_chat_name or is_chat_content:
                    ev_type = "chat"
                else:
                    ev_type = "text"

        # 5. Create DB record first to obtain evidence_id
        safe_orig_name = sanitize_filename(original_filename)
        raw_content_str = None
        if ev_type in ("text", "chat"):
            try:
                raw_content_str = file_bytes.decode("utf-8", errors="replace")
            except Exception:
                pass

        evidence = Evidence(
            case_id=case_id,
            evidence_type=ev_type,
            filename=safe_orig_name,
            mime_type=mime_type,
            file_size=file_size,
            raw_content=raw_content_str,
            sha256_hash=sha256,
            processing_status="uploaded",
        )
        db.add(evidence)
        db.flush()  # Populates evidence.id

        # 6. Save file safely
        try:
            target_storage_path = get_safe_storage_path(
                settings.STORAGE_DIR, evidence.id, safe_orig_name
            )
            with open(target_storage_path, "wb") as f:
                f.write(file_bytes)
            evidence.file_path = target_storage_path
            db.commit()
            db.refresh(evidence)
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to persist file for {evidence.id}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to store evidence file: {str(e)}")

        # 7. Execute processing if requested
        normalized = None
        if auto_process:
            normalized = await self.process_evidence_record(evidence.id, db, file_bytes=file_bytes)

        return evidence, normalized

    async def ingest_text(
        self,
        case_id: str,
        text: str,
        db: Session,
        evidence_type: str = "text",
        description: Optional[str] = None,
    ) -> Tuple[Evidence, NormalizedEvidence]:
        """
        Ingest text/SMS/chat evidence directly.
        """
        case = db.query(Case).filter(Case.id == case_id).first()
        if not case:
            raise HTTPException(status_code=404, detail=f"Case with ID '{case_id}' not found.")

        clean_text = text.strip()
        if not clean_text:
            raise HTTPException(status_code=400, detail="Evidence text cannot be empty.")

        # Auto-detect if raw text matches WhatsApp or chat structure
        resolved_ev_type = evidence_type
        if resolved_ev_type == "text":
            is_chat = bool(re.search(r'(?:^\[?\d{1,4}[/-]\d{1,2}[/-]\d{2,4}[,\s]+\d{1,2}:\d{2}|^\d{1,2}:\d{2}\s*[-–—]|^\[\d{1,2}:\d{2})', clean_text[:4096], re.MULTILINE))
            if is_chat:
                resolved_ev_type = "chat"

        text_bytes = clean_text.encode("utf-8")
        sha256 = compute_sha256(text_bytes)

        filename = f"{resolved_ev_type}_evidence.txt"
        evidence = Evidence(
            case_id=case_id,
            evidence_type=resolved_ev_type,
            filename=filename,
            mime_type="text/plain",
            file_size=len(text_bytes),
            raw_content=clean_text,
            sha256_hash=sha256,
            processing_status="uploaded",
        )
        db.add(evidence)
        db.commit()
        db.refresh(evidence)

        normalized = await self.process_evidence_record(evidence.id, db, file_bytes=text_bytes)
        return evidence, normalized

    async def ingest_url(
        self,
        case_id: str,
        url: str,
        db: Session,
        description: Optional[str] = None,
    ) -> Tuple[Evidence, NormalizedEvidence]:
        """
        Ingest a suspicious URL as forensic evidence.
        """
        case = db.query(Case).filter(Case.id == case_id).first()
        if not case:
            raise HTTPException(status_code=404, detail=f"Case with ID '{case_id}' not found.")

        clean_url = url.strip()
        if not clean_url:
            raise HTTPException(status_code=400, detail="URL cannot be empty.")

        url_bytes = clean_url.encode("utf-8")
        sha256 = compute_sha256(url_bytes)

        evidence = Evidence(
            case_id=case_id,
            evidence_type="url",
            filename="url_evidence.txt",
            mime_type="text/uri-list",
            file_size=len(url_bytes),
            raw_content=clean_url,
            sha256_hash=sha256,
            processing_status="uploaded",
        )
        db.add(evidence)
        db.commit()
        db.refresh(evidence)

        normalized = await self.process_evidence_record(evidence.id, db, file_bytes=url_bytes)
        return evidence, normalized

    async def process_evidence_record(
        self,
        evidence_id: str,
        db: Session,
        file_bytes: Optional[bytes] = None,
    ) -> NormalizedEvidence:
        """
        Run the designated modular processor on an evidence record.
        Updates processing_status, normalized_json, raw_content, and error_message.
        """
        evidence = db.query(Evidence).filter(Evidence.id == evidence_id).first()
        if not evidence:
            raise HTTPException(status_code=404, detail=f"Evidence with ID '{evidence_id}' not found.")

        # Update status to processing
        evidence.processing_status = "processing"
        evidence.error_message = None
        db.commit()

        # Select modular processor
        processor = EvidenceProcessorFactory.get_processor(
            evidence_type=evidence.evidence_type,
            mime_type=evidence.mime_type,
        )

        try:
            normalized = await processor.process(evidence, file_bytes=file_bytes)
            
            # Check processor output status
            if normalized.processing_status == "failed":
                evidence.processing_status = "failed"
                evidence.error_message = normalized.error_message or "Processing failed without specific error message"
            else:
                evidence.processing_status = "processed"
                evidence.raw_content = normalized.to_db_content()
                evidence.normalized_json = normalized.to_db_json()
                evidence.error_message = None

                db.commit()
                db.refresh(evidence)

                # Persist extracted indicators and financial impact to case
                self._persist_evidence_indicators(evidence, normalized, db)

                return normalized

        except Exception as e:
            logger.exception(f"Unexpected error processing evidence {evidence_id}: {e}")
            evidence.processing_status = "failed"
            evidence.error_message = str(e)
            db.commit()
            db.refresh(evidence)
            
            return NormalizedEvidence(
                evidence_id=evidence.id,
                case_id=evidence.case_id,
                type=evidence.evidence_type,
                source={
                    "filename": evidence.filename,
                    "mime_type": evidence.mime_type,
                    "file_size": evidence.file_size,
                    "sha256_hash": evidence.sha256_hash or "",
                },
                content={"text": ""},
                processing_status="failed",
                error_message=str(e),
            )

    async def ingest_live_chunk(
        self,
        case_id: str,
        chunk_text: str,
        user_authorized: bool,
        db: Session,
        sender: Optional[str] = None,
        timestamp: Optional[str] = None,
        source_device: Optional[str] = "Companion App",
    ) -> Tuple[Evidence, NormalizedEvidence]:
        """
        Ingest an authorized live WhatsApp text chunk from Laptop 5 companion.
        """
        case = db.query(Case).filter(Case.id == case_id).first()
        if not case:
            raise HTTPException(status_code=404, detail=f"Case with ID '{case_id}' not found.")

        # Look for existing active live-stream evidence for this case
        existing_evidence = (
            db.query(Evidence)
            .filter(Evidence.case_id == case_id, Evidence.evidence_type == "chat", Evidence.filename == "live_whatsapp_stream.txt")
            .first()
        )

        if not existing_evidence:
            existing_evidence = Evidence(
                case_id=case_id,
                evidence_type="chat",
                filename="live_whatsapp_stream.txt",
                mime_type="text/plain",
                file_size=0,
                processing_status="processing",
            )
            db.add(existing_evidence)
            db.flush()

        normalized = await self.live_processor.process_chunk(
            case_id=case_id,
            chunk_text=chunk_text,
            user_authorized=user_authorized,
            sender=sender,
            timestamp=timestamp,
            source_device=source_device,
            existing_evidence=existing_evidence,
        )

        existing_evidence.raw_content = normalized.to_db_content()
        existing_evidence.normalized_json = normalized.to_db_json()
        existing_evidence.file_size = len(existing_evidence.raw_content.encode("utf-8"))
        existing_evidence.sha256_hash = compute_sha256(existing_evidence.raw_content.encode("utf-8"))
        existing_evidence.processing_status = "processed"
        existing_evidence.error_message = None

        db.commit()
        db.refresh(existing_evidence)
        return existing_evidence, normalized

    def _persist_evidence_indicators(
        self,
        evidence: Evidence,
        normalized: NormalizedEvidence,
        db: Session,
    ) -> None:
        """
        Extract and persist indicators directly from normalized evidence into the case Indicator table.
        Avoids duplicates and updates financial loss if present.
        """
        try:
            case = db.query(Case).filter(Case.id == evidence.case_id).first()
            if not case:
                return

            existing = db.query(Indicator).filter(Indicator.case_id == evidence.case_id).all()
            existing_keys = {(i.indicator_type.lower(), i.value.strip().lower()) for i in existing}

            # 1. Gather items from normalized.provenance (from OCR + Gemini Multimodal)
            items_to_add: List[Tuple[str, str, str, str, str]] = []

            for p in getattr(normalized, "provenance", []):
                val = p.extracted_value.strip()
                if not val:
                    continue
                ind_type = "suspicious_entity"
                if "@" in val and "." not in val.split("@")[0]:
                    ind_type = "upi_id"
                elif re.search(r'^(?:\+?91[\s-]?)?[6-9]\d{4}[\s-]?\d{5}$', val) or (len(re.sub(r'\D', '', val)) == 10 and "@" not in val):
                    ind_type = "phone_number"
                elif val.startswith("http://") or val.startswith("https://"):
                    ind_type = "url"
                elif "@" in val and "." in val.split("@")[1]:
                    ind_type = "email"
                elif any(c in val for c in ("₹", "Rs", "INR")):
                    ind_type = "financial_amount"
                elif "Vision (" in p.source_reference:
                    m = re.search(r'Vision \((\w+)\)', p.source_reference)
                    if m:
                        ind_type = m.group(1)

                items_to_add.append((
                    ind_type,
                    val,
                    p.confidence or "high",
                    p.verification_status or "supported",
                    p.source_reference or f"Evidence {evidence.id[:8]}",
                ))

            # 2. Also extract regex indicators from plain text / raw_content
            content_text = normalized.to_db_content()
            if content_text:
                from backend.app.services.call_intelligence_service import PHONE_REGEX, UPI_REGEX, URL_REGEX, EMAIL_REGEX, AMOUNT_REGEX
                for m in PHONE_REGEX.finditer(content_text):
                    pv = m.group(0).strip()
                    if "@" not in pv and len(re.sub(r'\D', '', pv)) >= 10:
                        items_to_add.append(("phone_number", pv, "high", "supported", f"Evidence OCR ({evidence.id[:8]})"))
                for m in UPI_REGEX.finditer(content_text):
                    uv = m.group(0).strip()
                    if not uv.endswith((".com", ".org", ".net", ".edu", ".gov")):
                        items_to_add.append(("upi_id", uv, "high", "supported", f"Evidence OCR ({evidence.id[:8]})"))
                for m in URL_REGEX.finditer(content_text):
                    items_to_add.append(("url", m.group(0).strip(), "high", "supported", f"Evidence OCR ({evidence.id[:8]})"))
                for m in EMAIL_REGEX.finditer(content_text):
                    items_to_add.append(("email", m.group(0).strip(), "high", "supported", f"Evidence OCR ({evidence.id[:8]})"))
                for m in AMOUNT_REGEX.finditer(content_text):
                    items_to_add.append(("financial_amount", m.group(0).strip(), "medium", "supported", f"Evidence OCR ({evidence.id[:8]})"))

            # 3. Insert non-duplicate indicators
            for ind_type, val, conf, v_status, ref in items_to_add:
                k = (ind_type.lower(), val.strip().lower())
                if k not in existing_keys:
                    new_ind = Indicator(
                        case_id=evidence.case_id,
                        indicator_type=ind_type,
                        value=val.strip(),
                        confidence=conf,
                        verification_status=v_status,
                        source_evidence_id=evidence.id,
                        source_reference=ref,
                    )
                    db.add(new_ind)
                    existing_keys.add(k)

                    # Update case financial_loss if amount found and not yet set
                    if ind_type == "financial_amount" and (case.financial_loss is None or case.financial_loss == 0):
                        num_str = re.sub(r'[^\d.]', '', val)
                        try:
                            if num_str:
                                case.financial_loss = float(num_str)
                        except Exception:
                            pass

            db.commit()
        except Exception as e:
            logger.warning(f"Failed to persist evidence indicators for {evidence.id}: {e}")

# Singleton instance
evidence_service = EvidenceService()
