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

# Common WhatsApp and chat line regex patterns
# Matches timestamps in various regional and OS formats:
# e.g., "25/09/2026, 10:31 - Sender: Msg", "[25/09/2026, 10:31:00 AM] Sender: Msg", "[10:31] Sender: Msg", "Sender: Msg"
CHAT_PATTERNS = [
    # Format: [25/09/2026, 10:31:00 AM] Sender: Message or [25/09/26, 10:31 AM] Sender: Message
    re.compile(r"^\[(?P<timestamp>\d{1,4}[/-]\d{1,2}[/-]\d{2,4}[,\s]+\d{1,2}:\d{2}(?::\d{2})?(?:\s*[APap][Mm])?)\]\s*(?P<sender>[^:]+?):\s*(?P<message>.*)$"),

    # Format: [10:31, 25/09/2026] Sender: Message or [10:31:00] Sender: Message or [10:31] Sender: Message
    re.compile(r"^\[(?P<timestamp>\d{1,2}:\d{2}(?::\d{2})?(?:[,\s]+\d{1,4}[/-]\d{1,2}[/-]\d{2,4})?(?:\s*[APap][Mm])?)\]\s*(?P<sender>[^:]+?):\s*(?P<message>.*)$"),

    # Format: 25/09/2026, 10:31 - Sender: Message or 25/09/26, 10:31 AM - Sender: Message or 25/09/2026, 10:31:00 am - Sender: Message
    re.compile(r"^(?P<timestamp>\d{1,4}[/-]\d{1,2}[/-]\d{2,4}[,\s]+\d{1,2}:\d{2}(?::\d{2})?(?:\s*[APap][Mm])?)\s*[-–—]\s*(?P<sender>[^:]+?):\s*(?P<message>.*)$"),

    # Format: 10:31 - Sender: Message or 10:31 AM - Sender: Message
    re.compile(r"^(?P<timestamp>\d{1,2}:\d{2}(?::\d{2})?(?:\s*[APap][Mm])?)\s*[-–—]\s*(?P<sender>[^:]+?):\s*(?P<message>.*)$"),

    # Simple fallback: Sender: Message (no timestamp, e.g. "Suspect: Transfer the funds")
    re.compile(r"^(?P<sender>[A-Za-z0-9\+\s\-_\.]{2,40}):\s*(?P<message>.*)$")
]

# Patterns for extracting forensic indicators dynamically
PHONE_REGEX = re.compile(r'(?:\+?91[\s-]?)?[6-9]\d{4}[\s-]?\d{5}|\b\d{10}\b|\+\d{1,3}[\s-]?\d{4,5}[\s-]?\d{4,5}')
UPI_REGEX = re.compile(r'\b[a-zA-Z0-9.\-_]{2,256}@[a-zA-Z]{2,64}\b')
URL_REGEX = re.compile(r'https?://(?:www\.)?[-a-zA-Z0-9@:%._+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:[-a-zA-Z0-9()@:%_+.~#?&/=]*)')
EMAIL_REGEX = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b')
AMOUNT_REGEX = re.compile(r'(?:INR|Rs\.?|₹)\s*([\d,]+(?:\.\d{1,2})?)|(\b[\d,]+(?:\.\d{1,2})?\s*(?:rupees|lakhs?|crores?)\b)', re.IGNORECASE)
REMOTE_TOOL_REGEX = re.compile(r'\b(AnyDesk|TeamViewer|RustDesk|QuickSupport|AirDroid|\w+\.apk)\b', re.IGNORECASE)
ORG_REGEX = re.compile(r'\b(RBI|CBI|Cyber\s*Cell|Police|Crime\s*Branch|Customs|ED|Enforcement\s*Directorate|Supreme\s*Court|High\s*Court|Telecom|TRAI|FedEx|DHL|Blue\s*Dart|State\s*Bank|HDFC|ICICI|SBI|Axis|BESCOM|Electricity\s*Board)\b', re.IGNORECASE)

def clean_invisible_unicode(text: str) -> str:
    """Strip hidden Unicode directional formatting and zero-width characters common in WhatsApp exports."""
    # \u200e (LRM), \u200f (RLM), \u202a-\u202e (directional embeddings/overrides), \u202f (narrow no-break space), \ufeff (BOM), \u00a0 (NBSP)
    cleaned = re.sub(r'[\u200b-\u200f\u202a-\u202e\ufeff]', '', text)
    cleaned = cleaned.replace('\u202f', ' ').replace('\u00a0', ' ')
    return cleaned

class ChatProcessor(EvidenceProcessor):
    """
    Normalizes messy chat exports (WhatsApp, Telegram, SMS dialogues).
    Parses timestamps, senders, multi-line continuations, and extracts provenance.
    Strictly forbids inventing timestamps or senders when missing.
    """

    async def process(self, evidence: Any, file_bytes: Optional[bytes] = None) -> NormalizedEvidence:
        evidence_id = getattr(evidence, "id", "EV-UNKNOWN")
        case_id = getattr(evidence, "case_id", "CASE-UNKNOWN")
        filename = getattr(evidence, "filename", "chat_log.txt")
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
                    type="chat",
                    source={"filename": filename, "mime_type": mime_type, "file_size": file_size, "sha256_hash": sha256},
                    content={"text": "", "messages": []},
                    processing_status="failed",
                    error_message=f"Could not read chat file: {str(e)}",
                )

        # Clean hidden Unicode marks from chat text
        clean_raw = clean_invisible_unicode(raw_text)

        if not clean_raw.strip():
            return NormalizedEvidence(
                evidence_id=evidence_id,
                case_id=case_id,
                type="chat",
                source={"filename": filename, "mime_type": mime_type, "file_size": file_size, "sha256_hash": sha256},
                content={"text": "", "messages": []},
                processing_status="failed",
                error_message="Chat content is empty",
            )

        # Parse messages line by line with multi-line message stitching
        parsed_messages: List[Dict[str, Any]] = []
        segments: List[ContentSegment] = []
        provenance_items: List[ProvenanceItem] = []
        
        lines = clean_raw.splitlines()
        current_msg = None

        for line_num, line in enumerate(lines):
            clean_line = line.strip()
            if not clean_line:
                continue

            matched = False
            for pat in CHAT_PATTERNS:
                m = pat.match(clean_line)
                if m:
                    # Flush previous message if any
                    if current_msg:
                        parsed_messages.append(current_msg)

                    data = m.groupdict()
                    ts = data.get("timestamp")
                    sender = data.get("sender")
                    msg_body = data.get("message", "").strip()

                    current_msg = {
                        "index": len(parsed_messages) + 1,
                        "timestamp": ts.strip() if ts else None,
                        "sender": sender.strip() if sender else None,
                        "text": msg_body,
                        "line_number": line_num + 1,
                    }
                    matched = True
                    break

            if not matched:
                if current_msg:
                    # Multi-line continuation of current message
                    current_msg["text"] += f"\n{clean_line}"
                else:
                    # Line without header at start of text
                    current_msg = {
                        "index": len(parsed_messages) + 1,
                        "timestamp": None,
                        "sender": None,
                        "text": clean_line,
                        "line_number": line_num + 1,
                    }

        if current_msg:
            parsed_messages.append(current_msg)

        # Build normalized representation and content segments
        normalized_lines = []
        for msg in parsed_messages:
            idx = msg["index"]
            ts = msg["timestamp"]
            sender = msg["sender"]
            text = msg["text"]

            header_parts = [f"Message {idx}"]
            if ts:
                header_parts.append(f"Timestamp: {ts}")
            if sender:
                header_parts.append(f"Sender: {sender}")
            
            norm_block = f"{' | '.join(header_parts)}\nText: {text}"
            normalized_lines.append(norm_block)

            # Build ContentSegment for downstream agents
            seg_ref = f"Message {idx}" + (f" ({ts})" if ts else "") + (f" by {sender}" if sender else "")
            segments.append(
                ContentSegment(
                    segment_id=f"MSG-{idx:03d}",
                    sender=sender,
                    timestamp_str=ts,
                    text=text,
                    evidence_id=evidence_id,
                    confidence=1.0,
                )
            )

            # Dynamically extract all forensic provenance entities from this message
            # 1. Financial Amounts
            for amt_m in AMOUNT_REGEX.finditer(text):
                amt = amt_m.group(0).strip()
                provenance_items.append(
                    ProvenanceItem(
                        source_evidence_id=evidence_id,
                        source_reference=seg_ref,
                        extracted_value=amt,
                        confidence="high",
                        verification_status="supported",
                    )
                )

            # 2. UPI IDs (handles ending in @bank or @upi, filtering standard non-bank domains)
            for upi_m in UPI_REGEX.finditer(text):
                upi = upi_m.group(0).strip()
                if not upi.endswith((".com", ".org", ".net", ".edu", ".gov")) or upi.lower().endswith(("@upi", "@okhdfcbank", "@oksbi", "@paytm", "@icici")):
                    provenance_items.append(
                        ProvenanceItem(
                            source_evidence_id=evidence_id,
                            source_reference=seg_ref,
                            extracted_value=upi,
                            confidence="high",
                            verification_status="supported",
                        )
                    )

            # 3. Phone numbers
            for phone_m in PHONE_REGEX.finditer(text):
                phone = phone_m.group(0).strip()
                digits = re.sub(r'\D', '', phone)
                if "@" not in phone and len(digits) >= 10:
                    provenance_items.append(
                        ProvenanceItem(
                            source_evidence_id=evidence_id,
                            source_reference=seg_ref,
                            extracted_value=phone,
                            confidence="high",
                            verification_status="supported",
                        )
                    )

            # 4. URLs & Impersonation Portals
            for url_m in URL_REGEX.finditer(text):
                url_val = url_m.group(0).strip()
                provenance_items.append(
                    ProvenanceItem(
                        source_evidence_id=evidence_id,
                        source_reference=seg_ref,
                        extracted_value=url_val,
                        confidence="high",
                        verification_status="supported",
                    )
                )

            # 5. Email addresses
            for email_m in EMAIL_REGEX.finditer(text):
                email_val = email_m.group(0).strip()
                provenance_items.append(
                    ProvenanceItem(
                        source_evidence_id=evidence_id,
                        source_reference=seg_ref,
                        extracted_value=email_val,
                        confidence="high",
                        verification_status="supported",
                    )
                )

            # 6. Remote access tools / APKs mentioned
            for tool_m in REMOTE_TOOL_REGEX.finditer(text):
                tool = tool_m.group(0).strip()
                provenance_items.append(
                    ProvenanceItem(
                        source_evidence_id=evidence_id,
                        source_reference=seg_ref,
                        extracted_value=f"Remote Tool / APK: {tool}",
                        confidence="high",
                        verification_status="supported",
                    )
                )

            # 7. Claimed Authorities / Impersonated Organizations
            for org_m in ORG_REGEX.finditer(text):
                org = org_m.group(0).strip()
                provenance_items.append(
                    ProvenanceItem(
                        source_evidence_id=evidence_id,
                        source_reference=seg_ref,
                        extracted_value=f"Claimed Entity: {org}",
                        confidence="medium",
                        verification_status="supported",
                    )
                )

        full_normalized_text = "\n\n".join(normalized_lines)

        return NormalizedEvidence(
            evidence_id=evidence_id,
            case_id=case_id,
            type="chat",
            source={
                "filename": filename,
                "mime_type": mime_type,
                "file_size": file_size,
                "sha256_hash": sha256,
            },
            content={
                "text": full_normalized_text,
                "messages": parsed_messages,
                "segments": [s.model_dump() for s in segments],
                "message_count": len(parsed_messages),
            },
            metadata={
                "total_messages": len(parsed_messages),
                "has_timestamps": any(m["timestamp"] for m in parsed_messages),
                "has_senders": any(m["sender"] for m in parsed_messages),
                "platform": "whatsapp_or_chat",
            },
            provenance=provenance_items,
            processing_status="processed",
        )

