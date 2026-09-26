from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict, Field

class CallMessageCreate(BaseModel):
    speaker: str = Field(..., description="'caller', 'callee', or 'system'")
    content: str = Field(..., description="Message text or transcript snippet")
    timestamp_offset: Optional[str] = Field(None, description="e.g. '01:23'")

class CallMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    session_id: str
    speaker: str
    message_index: int
    content: str
    timestamp_offset: Optional[str] = None
    created_at: datetime

class CallSessionCreate(BaseModel):
    title: Optional[str] = "Live Scam Call Session"
    caller_label: Optional[str] = "Suspect / Impersonator"
    callee_label: Optional[str] = "Victim / Callee"

class ExtractedIndicatorItem(BaseModel):
    type: str = Field(..., description="phone, upi, url, email, person, organization, amount, tactic, action")
    value: str
    source_message_index: int = Field(0, description="1-indexed sequence number of the source message")
    source_reference: str = Field(..., description="Forensic source quote e.g. 'Message #3'")
    confidence: str = Field("medium", description="high, medium, low")
    status: str = Field("UNVERIFIED", description="UNVERIFIED, SUPPORTED, or FLAGGED")
    context: Optional[str] = None

class LiveExtractedIntelligence(BaseModel):
    indicators: List[ExtractedIndicatorItem] = Field(default_factory=list)
    phone_numbers: List[ExtractedIndicatorItem] = Field(default_factory=list)
    upi_ids: List[ExtractedIndicatorItem] = Field(default_factory=list)
    urls: List[ExtractedIndicatorItem] = Field(default_factory=list)
    emails: List[ExtractedIndicatorItem] = Field(default_factory=list)
    claimed_persons: List[ExtractedIndicatorItem] = Field(default_factory=list)
    claimed_organizations: List[ExtractedIndicatorItem] = Field(default_factory=list)
    financial_amounts: List[ExtractedIndicatorItem] = Field(default_factory=list)
    scam_tactics: List[ExtractedIndicatorItem] = Field(default_factory=list)
    requested_actions: List[ExtractedIndicatorItem] = Field(default_factory=list)
    summary: Optional[str] = None
    disclaimer: str = Field(
        "Extracted indicators represent investigative artifacts from the conversation; does not automatically establish criminality of named individuals or entities.",
        description="Legal / forensic disclaimer"
    )

class CallSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    case_id: str
    title: str
    caller_label: str
    callee_label: str
    status: str
    message_count: int = 0
    messages: List[CallMessageResponse] = Field(default_factory=list)
    intelligence: Optional[LiveExtractedIntelligence] = None
    evidence_id: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

class PromoteCallResponse(BaseModel):
    session_id: str
    evidence_id: str
    indicators_created_count: int
    message: str
