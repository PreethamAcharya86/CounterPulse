import json
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator

class ReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    case_id: str
    report_type: str
    title: str
    content_markdown: str
    content_html: Optional[str] = None
    approval_status: str = "draft"  # draft, reviewed, approved, sent, failed
    approved_at: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    recipient_email: Optional[str] = None
    error_message: Optional[str] = None
    pdf_path: Optional[str] = None
    evidence_references: List[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: Optional[datetime] = None

    @classmethod
    def from_orm_model(cls, report) -> "ReportResponse":
        ev_refs: List[str] = []
        if getattr(report, "evidence_references_json", None):
            try:
                ev_refs = json.loads(report.evidence_references_json)
                if not isinstance(ev_refs, list):
                    ev_refs = []
            except Exception:
                ev_refs = []

        return cls(
            id=report.id,
            case_id=report.case_id,
            report_type=report.report_type,
            title=report.title,
            content_markdown=report.content_markdown,
            content_html=report.content_html,
            approval_status=report.approval_status,
            approved_at=report.approved_at,
            sent_at=report.sent_at,
            recipient_email=report.recipient_email,
            error_message=report.error_message,
            pdf_path=report.pdf_path,
            evidence_references=ev_refs,
            created_at=report.created_at,
            updated_at=getattr(report, "updated_at", None),
        )

class ReportUpdate(BaseModel):
    title: Optional[str] = None
    content_markdown: Optional[str] = None
    recipient_email: Optional[str] = None
    approval_status: Optional[str] = None

class ReportApproveRequest(BaseModel):
    recipient_email: Optional[str] = None

class ReportSendRequest(BaseModel):
    recipient_email: Optional[str] = None
    attach_passport_pdf: bool = True

class ReportGenerateResponse(BaseModel):
    case_id: str
    count: int
    reports: List[ReportResponse]
