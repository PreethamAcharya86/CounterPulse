import re
import logging
from typing import Optional, List, Dict, Any
from backend.app.services.evidence.base import (
    EvidenceProcessor,
    NormalizedEvidence,
    ContentSegment,
    ProvenanceItem,
)

logger = logging.getLogger(__name__)

class TextProcessor(EvidenceProcessor):
    """
    Normalizes arbitrary incident narratives, Bank SMS notifications, and emails.
    Preserves exact text and figures while structuring paragraphs and detecting financial markers.
    """

    async def process(self, evidence: Any, file_bytes: Optional[bytes] = None) -> NormalizedEvidence:
        evidence_id = getattr(evidence, "id", "EV-UNKNOWN")
        case_id = getattr(evidence, "case_id", "CASE-UNKNOWN")
        filename = getattr(evidence, "filename", "text_evidence.txt")
        mime_type = getattr(evidence, "mime_type", "text/plain")
        file_size = getattr(evidence, "file_size", 0)
        sha256 = getattr(evidence, "sha256_hash", "")

        raw_text = ""
        if file_bytes:
            try:
                raw_text = file_bytes.decode("utf-8", errors="replace")
            except Exception:
                raw_text = str(file_bytes)
        elif hasattr(evidence, "raw_content") and evidence.raw_content:
            raw_text = evidence.raw_content
        elif hasattr(evidence, "file_path") and evidence.file_path:
            try:
                with open(evidence.file_path, "r", encoding="utf-8", errors="replace") as f:
                    raw_text = f.read()
            except Exception as e:
                return NormalizedEvidence(
                    evidence_id=evidence_id,
                    case_id=case_id,
                    type="text",
                    source={"filename": filename, "mime_type": mime_type, "file_size": file_size, "sha256_hash": sha256},
                    content={"text": ""},
                    processing_status="failed",
                    error_message=f"Could not read text from disk: {str(e)}",
                )

        clean_text = raw_text.strip()
        if not clean_text:
            return NormalizedEvidence(
                evidence_id=evidence_id,
                case_id=case_id,
                type="text",
                source={"filename": filename, "mime_type": mime_type, "file_size": file_size, "sha256_hash": sha256},
                content={"text": ""},
                processing_status="failed",
                error_message="Text evidence is empty",
            )

        # Detect text subtype (e.g. Bank SMS, incident description, email)
        is_sms = bool(re.search(r"\b(?:debited|credited|INR|Rs\.?|A/c|account|OTP|bank|IMPS|UPI Ref)\b", clean_text, re.IGNORECASE))
        is_email = bool(re.search(r"^(?:From:|Subject:|Date:|To:)", clean_text, re.MULTILINE))

        # Split into logical paragraphs or sentences
        paragraphs = [p.strip() for p in clean_text.split("\n\n") if p.strip()]
        if not paragraphs:
            paragraphs = [clean_text]

        segments: List[ContentSegment] = []
        provenance_items: List[ProvenanceItem] = []

        for p_idx, para in enumerate(paragraphs):
            para_ref = f"Text Paragraph {p_idx+1}"
            segments.append(
                ContentSegment(
                    segment_id=f"TXT-{p_idx+1:03d}",
                    text=para,
                    evidence_id=evidence_id,
                    confidence=1.0,
                )
            )

            # Look for amounts
            amounts = re.findall(r"(?:₹|Rs\.?|INR)\s*[\d,]+(?:\.\d{2})?", para, re.IGNORECASE)
            for amt in amounts:
                provenance_items.append(
                    ProvenanceItem(
                        source_evidence_id=evidence_id,
                        source_reference=para_ref,
                        extracted_value=amt,
                        confidence="high",
                        verification_status="supported",
                    )
                )

            # Bank accounts / cards (e.g. A/c ending in 1234)
            acct_matches = re.findall(r"(?:A/c|account|card)\s*(?:no\.?)?\s*(?:ending\s*)?(?:in\s*)?([xX*]*\d{3,6})\b", para, re.IGNORECASE)
            for acct in acct_matches:
                provenance_items.append(
                    ProvenanceItem(
                        source_evidence_id=evidence_id,
                        source_reference=para_ref,
                        extracted_value=f"Account/Card: {acct}",
                        confidence="high",
                        verification_status="supported",
                    )
                )

            # UPI handles
            upis = re.findall(r"\b[a-zA-Z0-9.\-_]{2,256}@[a-zA-Z]{2,64}\b", para)
            for upi in upis:
                if not upi.endswith((".com", ".org", ".net", ".edu", ".gov")) or upi.lower().endswith(("@upi", "@okhdfcbank", "@oksbi", "@paytm", "@icici")):
                    provenance_items.append(
                        ProvenanceItem(
                            source_evidence_id=evidence_id,
                            source_reference=para_ref,
                            extracted_value=upi,
                            confidence="high",
                            verification_status="supported",
                        )
                    )

            # Phone numbers
            phones = re.findall(r'(?:\+?91[\s-]?)?[6-9]\d{4}[\s-]?\d{5}|\b\d{10}\b|\+\d{1,3}[\s-]?\d{4,5}[\s-]?\d{4,5}', para)
            for ph in phones:
                digits = re.sub(r'\D', '', ph)
                if "@" not in ph and len(digits) >= 10:
                    provenance_items.append(
                        ProvenanceItem(
                            source_evidence_id=evidence_id,
                            source_reference=para_ref,
                            extracted_value=ph,
                            confidence="high",
                            verification_status="supported",
                        )
                    )

            # URLs
            urls = re.findall(r'https?://(?:www\.)?[-a-zA-Z0-9@:%._+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:[-a-zA-Z0-9()@:%_+.~#?&/=]*)', para)
            for u in urls:
                provenance_items.append(
                    ProvenanceItem(
                        source_evidence_id=evidence_id,
                        source_reference=para_ref,
                        extracted_value=u,
                        confidence="high",
                        verification_status="supported",
                    )
                )

            # Reference / UTR
            utr_matches = re.findall(r"(?:UPI Ref(?:erence)?|Ref\s*No\.?|Txn\s*ID)[:\s]*([A-Z0-9]{8,22})", para, re.IGNORECASE)
            for utr in utr_matches:
                provenance_items.append(
                    ProvenanceItem(
                        source_evidence_id=evidence_id,
                        source_reference=para_ref,
                        extracted_value=f"Transaction Ref: {utr}",
                        confidence="high",
                        verification_status="supported",
                    )
                )

        return NormalizedEvidence(
            evidence_id=evidence_id,
            case_id=case_id,
            type="text",
            source={
                "filename": filename,
                "mime_type": mime_type,
                "file_size": file_size,
                "sha256_hash": sha256,
            },
            content={
                "text": clean_text,
                "segments": [s.model_dump() for s in segments],
                "char_count": len(clean_text),
                "paragraph_count": len(paragraphs),
            },
            metadata={
                "is_sms": is_sms,
                "is_email": is_email,
                "paragraph_count": len(paragraphs),
            },
            provenance=provenance_items,
            processing_status="processed",
        )
