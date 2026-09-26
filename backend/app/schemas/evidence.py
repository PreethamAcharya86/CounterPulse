from datetime import datetime
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field

class EvidenceBase(BaseModel):
    evidence_type: str
    filename: str
    mime_type: str
    raw_content: Optional[str] = None

class EvidenceCreate(EvidenceBase):
    pass

class ContentSegmentSchema(BaseModel):
    segment_id: str
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    speaker: Optional[str] = None
    sender: Optional[str] = None
    timestamp_str: Optional[str] = None
    text: str
    evidence_id: str
    confidence: Optional[float] = 1.0

class ProvenanceItemSchema(BaseModel):
    source_evidence_id: str
    source_reference: str
    extracted_value: str
    confidence: str = "high"
    verification_status: str = "supported"

class EvidenceResponse(BaseModel):
    id: str
    case_id: str
    evidence_type: str
    filename: str
    mime_type: str
    file_size: int
    file_path: Optional[str] = None
    raw_content: Optional[str] = None
    sha256_hash: Optional[str] = None
    processing_status: str
    normalized_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class TextEvidenceUpload(BaseModel):
    text: str = Field(..., min_length=1, description="Raw text, SMS, or incident description")
    description: Optional[str] = "Pasted text / SMS log"
    evidence_type: Optional[str] = "text"

class ChatEvidenceUpload(BaseModel):
    chat_text: str = Field(..., min_length=1, description="Exported or pasted chat conversation")
    platform: Optional[str] = "whatsapp"
    description: Optional[str] = "WhatsApp conversation log"

class URLEvidenceUpload(BaseModel):
    url: str = Field(..., min_length=4, description="Suspicious URL or phishing link")
    description: Optional[str] = "Suspicious URL evidence"

class LiveTextChunkUpload(BaseModel):
    case_id: Optional[str] = None
    chunk_text: str = Field(..., min_length=1, description="Live text message chunk")
    user_authorized: bool = Field(..., description="Explicit user authorization for live monitoring")
    sender: Optional[str] = None
    timestamp: Optional[str] = None
    source_device: Optional[str] = "Companion App"

class EvidenceProcessResponse(BaseModel):
    evidence_id: str
    processing_status: str
    evidence_type: str
    character_count: int = 0
    segment_count: int = 0
    normalized_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
