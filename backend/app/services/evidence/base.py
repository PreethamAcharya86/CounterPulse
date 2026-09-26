from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class ContentSegment(BaseModel):
    segment_id: str = Field(..., description="Unique segment identifier (e.g. SEG-001)")
    start_time: Optional[float] = Field(None, description="Start offset in seconds (for audio)")
    end_time: Optional[float] = Field(None, description="End offset in seconds (for audio)")
    speaker: Optional[str] = Field(None, description="Speaker role: Victim, Impersonator, Unknown")
    sender: Optional[str] = Field(None, description="Sender name or phone number (for chats)")
    timestamp_str: Optional[str] = Field(None, description="Exact timestamp string if present in source")
    text: str = Field(..., description="Extracted content text")
    evidence_id: str = Field(..., description="Associated evidence ID")
    confidence: Optional[float] = Field(1.0, description="Extraction confidence (0.0 to 1.0)")

class ProvenanceItem(BaseModel):
    source_evidence_id: str = Field(..., description="Evidence ID (e.g. EV-001)")
    source_reference: str = Field(..., description="Specific citation e.g. 'Page 1, Para 2', 'OCR Box [10,20]', 'Audio 01:23-01:45'")
    extracted_value: str = Field(..., description="Extracted fact or entity (e.g. ₹95,000, 9876543210@paytm)")
    confidence: str = Field("high", description="high, medium, or low")
    verification_status: str = Field("supported", description="supported, possible, unverified, not_found")

class NormalizedEvidence(BaseModel):
    evidence_id: str
    case_id: str
    type: str  # image, pdf, text, chat, audio, url
    source: Dict[str, Any]  # filename, mime_type, file_size, sha256_hash
    content: Dict[str, Any]  # text: str, segments: List[dict], pages: List[dict]
    metadata: Dict[str, Any] = {}
    provenance: List[ProvenanceItem] = []
    processing_status: str = "processed"  # uploaded, processing, processed, failed
    error_message: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_db_content(self) -> str:
        """Return clean plain text content for database raw_content column."""
        return self.content.get("text", "") or ""

    def to_db_json(self) -> str:
        """Serialize full normalized data for database storage."""
        return self.model_dump_json()

class EvidenceProcessor(ABC):
    """
    Abstract Base Class for modular evidence processors.
    Enforces real processing, normalization, and provenance preservation.
    """
    @abstractmethod
    async def process(self, evidence: Any, file_bytes: Optional[bytes] = None) -> NormalizedEvidence:
        """
        Process the raw evidence into a standardized NormalizedEvidence model.
        Must NOT fabricate data. If extraction fails, must return valid error or review state.
        """
        pass
