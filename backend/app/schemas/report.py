from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr

class ReportResponse(BaseModel):
    id: str
    case_id: str
    report_type: str
    title: str
    content_markdown: str
    content_html: Optional[str] = None
    approval_status: str
    approved_at: Optional[datetime] = None
    pdf_path: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class ReportUpdateRequest(BaseModel):
    title: Optional[str] = None
    content_markdown: str

class ReportApproveRequest(BaseModel):
    confirmed_by_victim: bool
    notes: Optional[str] = None

class EmailSendRequest(BaseModel):
    recipient_email: str
    subject_override: Optional[str] = None
    attach_pdf: bool = True

class EmailSendResponse(BaseModel):
    success: bool
    message: str
    email_event_id: str
    recipient: str
    timestamp: datetime
