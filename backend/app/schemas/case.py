from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel
from backend.app.schemas.evidence import EvidenceResponse

class CaseBase(BaseModel):
    title: str = "New Cyber-Fraud Incident"
    description: Optional[str] = None

class CaseCreate(CaseBase):
    pass

class CaseUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None

class IndicatorResponse(BaseModel):
    id: str
    case_id: str
    indicator_type: str
    value: str
    confidence: str
    verification_status: str
    source_evidence_id: Optional[str] = None
    source_reference: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class TimelineEventResponse(BaseModel):
    id: str
    case_id: str
    timestamp_str: str
    event_description: str
    source_evidence_id: Optional[str] = None
    order_index: int
    created_at: datetime

    class Config:
        from_attributes = True

class CompromiseAssessmentResponse(BaseModel):
    id: str
    case_id: str
    category: str
    risk_level: str
    details: str
    recommended_action: str
    source_evidence_id: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class ActionEventResponse(BaseModel):
    id: str
    case_id: str
    action_type: str
    status: str
    details: Optional[str] = None
    timestamp: datetime

    class Config:
        from_attributes = True

class ReportSummaryResponse(BaseModel):
    id: str
    case_id: str
    report_type: str
    title: str
    approval_status: str
    approved_at: Optional[datetime] = None
    pdf_path: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class CaseResponse(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    status: str
    scam_category: Optional[str] = None
    severity_level: str
    financial_loss: Optional[float] = None
    currency: str
    modus_operandi: Optional[str] = None
    summary: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

from backend.app.schemas.passport import FraudCasePassport

CasePassportResponse = FraudCasePassport

