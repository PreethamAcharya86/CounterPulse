from typing import List, Optional, Literal
from pydantic import BaseModel, Field

class ExtractedIndicator(BaseModel):
    indicator_type: str = Field(
        ...,
        description="Type: upi_id, phone_number, url, email, suspect_name, organization, account_number, transaction_id, app_apk"
    )
    value: str = Field(..., description="The exact value extracted from evidence")
    confidence: Literal["high", "medium", "low"] = Field(
        "medium",
        description="Confidence level of this extraction"
    )
    verification_status: Literal["supported", "possible", "unverified", "not_found"] = Field(
        "unverified",
        description="Provenance status: supported (directly shown in evidence), possible (inferred), unverified (claimed by scammer), not_found"
    )
    source_evidence_id: Optional[str] = Field(
        None,
        description="ID of the evidence item from which this fact was extracted (e.g. EV-001)"
    )
    source_reference: Optional[str] = Field(
        None,
        description="Specific citation or excerpt from the evidence supporting this extraction"
    )

class TimelineItem(BaseModel):
    timestamp_str: str = Field(..., description="Date or time string of the event (e.g. 2026-09-25 14:30 IST or 'Initial contact')")
    event_description: str = Field(..., description="Detailed description of what occurred at this milestone")
    source_evidence_id: Optional[str] = Field(None, description="Originating evidence ID")

class CompromiseItem(BaseModel):
    category: Literal["banking", "credentials", "remote_access", "pii"] = Field(
        ...,
        description="Vulnerability category assessed"
    )
    risk_level: Literal["confirmed", "possible", "not_found", "unverified"] = Field(
        ...,
        description="Assessed risk level based strictly on available evidence"
    )
    details: str = Field(..., description="Detailed findings and forensic evidence justification")
    recommended_action: str = Field(..., description="Immediate containment step the victim should take")
    source_evidence_id: Optional[str] = Field(None, description="Evidence ID supporting this risk assessment")

class IncidentReconstructionOutput(BaseModel):
    summary: str = Field(..., description="Executive summary of the incident")
    incident_type: str = Field(..., description="High-level incident type (e.g., Financial Fraud, Identity Theft)")
    scam_category: str = Field(..., description="Specific scam category (e.g. Digital Arrest, Part-Time Job Scam, UPI Phishing, Remote Access Scam)")
    severity_level: Literal["critical", "high", "medium", "low"] = Field(
        ...,
        description="Severity score based on financial loss, active remote access, or credential exposure"
    )
    financial_loss: Optional[float] = Field(
        None,
        description="Total confirmed or claimed financial loss amount in the given currency. None if no loss detected."
    )
    currency: str = Field("INR", description="Currency code (e.g., INR, USD)")
    modus_operandi: str = Field(..., description="Step-by-step psychological tactics and attack vectors used")
    timeline: List[TimelineItem] = Field(default_factory=list, description="Chronological timeline of incident milestones")
    indicators: List[ExtractedIndicator] = Field(default_factory=list, description="Extracted forensic indicators with provenance")
    compromise: List[CompromiseItem] = Field(default_factory=list, description="Compromise assessment across vectors")
    recommended_immediate_actions: List[str] = Field(default_factory=list, description="Prioritized emergency containment steps")

class ResponsePackagesOutput(BaseModel):
    bank_dispute_subject: str = Field(..., description="Subject line for official bank dispute")
    bank_dispute_body: str = Field(..., description="Formal bank dispute declaration text adhering to standard banking guidelines")
    cybercrime_complaint_subject: str = Field(..., description="Subject line for 1930 / NCRP cybercrime portal")
    cybercrime_complaint_body: str = Field(..., description="Structured complaint narrative for National Cyber Crime Reporting Portal")
    emergency_advisory: str = Field(..., description="Victim emergency guidance and next steps")
