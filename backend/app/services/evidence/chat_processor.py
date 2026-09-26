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
CHAT_PATTERNS = [
    # Format: [10:31, 25/09/2026] Sender: Message or [10:31] Sender: Message
    re.compile(r"^\[(?P<timestamp>\d{1,2}:\d{2}(?::\d{2})?(?:[,\s]+\d{1,2}[/-]\d{1,2}[/-]\d{2,4})?)\]\s*(?P<sender>[^:]+?):\s*(?P<message>.*)$"),
    
    # Format: [25/09/2026, 10:31:00 AM] Sender: Message
    re.compile(r"^\[(?P<timestamp>\d{1,2}[/-]\d{1,2}[/-]\d{2,4}[,\s]+\d{1,2}:\d{2}(?::\d{2})?(?:\s*[APap][Mm])?)\]\s*(?P<sender>[^:]+?):\s*(?P<message>.*)$"),

    # Format: 25/09/2026, 10:31 - Sender: Message or 25/09/26, 10:31 AM - Sender: Message
    re.compile(r"^(?P<timestamp>\d{1,2}[/-]\d{1,2}[/-]\d{2,4}[,\s]+\d{1,2}:\d{2}(?:\s*[APap][Mm])?)\s*-\s*(?P<sender>[^:]+?):\s*(?P<message>.*)$"),

    # Format: 10:31 - Sender: Message
    re.compile(r"^(?P<timestamp>\d{1,2}:\d{2}(?:\s*[APap][Mm])?)\s*-\s*(?P<sender>[^:]+?):\s*(?P<message>.*)$"),

    # Simple fallback: Sender: Message (no timestamp)
    re.compile(r"^(?P<sender>[A-Za-z0-9\+\s\-_]{2,30}):\s*(?P<message>.*)$")
]

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

        if not raw_text.strip():
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
        
        lines = raw_text.splitlines()
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

            # Build ContentSegment for Scam Intelligence Agent
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

            # Extract provenance entities from chat message
            # 1. Amounts
            amounts = re.findall(r"(?:₹|Rs\.?|INR)\s*[\d,]+(?:\.\d{2})?", text, re.IGNORECASE)
            for amt in amounts:
                provenance_items.append(
                    ProvenanceItem(
                        source_evidence_id=evidence_id,
                        source_reference=seg_ref,
                        extracted_value=amt,
                        confidence="high",
                        verification_status="supported",
                    )
                )

            # 2. UPI IDs
            upis = re.findall(r"[\w.-]+@(?:ok[a-z]+|okhdfcbank|oksbi|paytm|ybl|ibl|axl|apl)", text, re.IGNORECASE)
            for upi in upis:
                provenance_items.append(
                    ProvenanceItem(
                        source_evidence_id=evidence_id,
                        source_reference=seg_ref,
                        extracted_value=upi,
                        confidence="high",
                        verification_status="supported",
                    )
                )

            # 3. Remote access tools / APKs mentioned
            remote_tools = re.findall(r"\b(AnyDesk|TeamViewer|RustDesk|QuickSupport|AirDroid|\w+\.apk)\b", text, re.IGNORECASE)
            for tool in remote_tools:
                provenance_items.append(
                    ProvenanceItem(
                        source_evidence_id=evidence_id,
                        source_reference=seg_ref,
                        extracted_value=f"Remote Tool / APK: {tool}",
                        confidence="high",
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
