import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from backend.app.services.evidence.base import (
    NormalizedEvidence,
    ContentSegment,
    ProvenanceItem,
)
from backend.app.services.evidence.chat_processor import ChatProcessor

logger = logging.getLogger(__name__)

class LiveWhatsAppProcessor:
    """
    Handles live, user-authorized text chunks sent by the Laptop 5 companion/UI.
    Processes incremental chunks without covert monitoring or account interaction.
    """

    def __init__(self):
        self.chat_processor = ChatProcessor()

    async def process_chunk(
        self,
        case_id: str,
        chunk_text: str,
        user_authorized: bool,
        sender: Optional[str] = None,
        timestamp: Optional[str] = None,
        source_device: Optional[str] = "Companion App",
        existing_evidence: Optional[Any] = None,
    ) -> NormalizedEvidence:
        if not user_authorized:
            raise PermissionError("Live text ingestion requires explicit user authorization.")

        if not chunk_text or not chunk_text.strip():
            raise ValueError("Live text chunk is empty.")

        now_str = timestamp or datetime.now(timezone.utc).strftime("%H:%M")
        
        # If chunk is a raw message, format with timestamp and sender if available
        if sender and not (chunk_text.startswith("[") or " - " in chunk_text[:20]):
            formatted_chunk = f"[{now_str}] {sender}: {chunk_text.strip()}"
        else:
            formatted_chunk = chunk_text.strip()

        evidence_id = getattr(existing_evidence, "id", None) or f"EV-LIVE-{int(datetime.now(timezone.utc).timestamp())}"

        # Combine with existing content if appending to a live stream evidence item
        if existing_evidence and getattr(existing_evidence, "raw_content", None):
            combined_text = f"{existing_evidence.raw_content}\n{formatted_chunk}"
        else:
            combined_text = formatted_chunk

        # Process through ChatProcessor to get clean messages, segments, and provenance
        dummy_evidence = type("DummyEvidence", (), {
            "id": evidence_id,
            "case_id": case_id,
            "filename": "live_whatsapp_stream.txt",
            "mime_type": "text/plain",
            "file_size": len(combined_text.encode("utf-8")),
            "sha256_hash": "",
            "raw_content": combined_text,
        })()

        normalized = await self.chat_processor.process(dummy_evidence)
        normalized.metadata["live_stream"] = True
        normalized.metadata["user_authorized"] = True
        normalized.metadata["source_device"] = source_device
        normalized.metadata["last_chunk_received_at"] = datetime.now(timezone.utc).isoformat()

        return normalized
