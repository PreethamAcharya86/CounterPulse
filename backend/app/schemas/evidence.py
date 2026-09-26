from datetime import datetime
from typing import Optional
from pydantic import BaseModel

class EvidenceBase(BaseModel):
    evidence_type: str
    filename: str
    mime_type: str
    raw_content: Optional[str] = None

class EvidenceCreate(EvidenceBase):
    pass

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
    created_at: datetime

    class Config:
        from_attributes = True

class TextEvidenceUpload(BaseModel):
    text: str
    description: Optional[str] = "Pasted text / chat log"
    evidence_type: Optional[str] = "text"
