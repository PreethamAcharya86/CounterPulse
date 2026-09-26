from typing import List, Optional, Literal, Dict, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field

# -------------------------------------------------------------
# Provenance & Source Reference
# -------------------------------------------------------------
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
    is_inferred: bool = Field(False, description="True if inferred by AI; False if directly recorded in evidence")
    confidence: Literal["high", "medium", "low"] = Field("high", description="Confidence in this timeline event")

# -------------------------------------------------------------
# Compromise Model: REQUESTED, DISCLOSED, INSTALLED, CONFIRMED
# -------------------------------------------------------------
CompromiseStatus = Literal["REQUESTED", "DISCLOSED", "INSTALLED", "CONFIRMED"]

class CompromiseAssessmentItem(BaseModel):
    category: Literal[
        "credentials",
        "financial_information",
        "identity_information",
        "otp_authentication",
        "remote_access",
        "device"
    ] = Field(..., description="Compromise category")
    status: CompromiseStatus = Field(
        ...,
        description="Compromise level: REQUESTED (demanded by attacker), DISCLOSED (shared by victim), INSTALLED (downloaded/setup on device), CONFIRMED (forensically proven compromise)"
    )
    details: str = Field(..., description="Forensic details and reasoning based strictly on available evidence")
    recommended_action: str = Field(..., description="Immediate containment action victim must execute")
    source_evidence_id: Optional[str] = Field(None, description="Evidence ID supporting this finding")
    source_reference: Optional[str] = Field(None, description="Citation from evidence")

# Compatibility alias for existing models
CompromiseItem = CompromiseAssessmentItem

class CompromiseAssessmentOutput(BaseModel):
    assessments: List[CompromiseAssessmentItem] = Field(default_factory=list)
    overall_device_compromise: bool = Field(False, description="Whether remote access or malicious APK compromised device")
    summary: str = Field(..., description="Executive summary of compromise exposure")

# -------------------------------------------------------------
# Specialized Agent Outputs
# -------------------------------------------------------------

class TriageOutput(BaseModel):
    severity_level: Literal["critical", "high", "medium", "low"] = Field(
        ...,
        description="Severity score based on financial loss, active remote access, or credential exposure"
    )
    urgency_rating: Literal["immediate_containment", "active_monitoring", "standard_followup"] = Field(
        "immediate_containment",
        description="Urgency for 1930 / bank golden-hour containment"
    )
    financial_loss_detected: bool = Field(False)
    loss_amount: Optional[float] = Field(None)
    currency: str = Field("INR")
    authority_impersonation: bool = Field(False)
    remote_access_risk: bool = Field(False)
    credential_risk: bool = Field(False)
    identity_exposure: bool = Field(False)
    triage_summary: str = Field(..., description="Triage assessment justification")
    immediate_containment_steps: List[str] = Field(default_factory=list)

class ScamIndicatorFinding(BaseModel):
    indicator: str
    type: str
    context: str

class ScamIntelligenceOutput(BaseModel):
    scam_type: str = Field(..., description="Specific scam category (e.g. Digital Arrest, Part-Time Job Scam, UPI Phishing, Remote Access)")
    impersonated_entities: List[str] = Field(default_factory=list, description="Agencies or organizations impersonated (e.g. CBI, TRAI, Supreme Court, SBI)")
    tactics_observed: List[str] = Field(default_factory=list, description="Tactics: e.g. Urgency Pressure, Legal Intimidation, Fake KYC, Remote Access Request")
    psychological_triggers: List[str] = Field(default_factory=list, description="Emotional and cognitive manipulation triggers")
    suspicious_indicators_found: List[ScamIndicatorFinding] = Field(default_factory=list)
    threat_assessment: str = Field(..., description="Comprehensive modus operandi analysis")

class NetworkNode(BaseModel):
    entity_type: str
    value: str
    threat_score: float = Field(0.5, ge=0.0, le=1.0)
    notes: Optional[str] = None

class NetworkIntelligenceOutput(BaseModel):
    nodes: List[NetworkNode] = Field(default_factory=list)
    correlations: List[str] = Field(default_factory=list)
    external_knowledge_matches: List[str] = Field(default_factory=list)
    disclaimer: str = Field(
        "Indicators represent suspicious investigative artifacts; does not establish criminality of named individuals.",
        description="Strict legal disclaimer"
    )

class ExtractedFinancialItem(BaseModel):
    amount: float
    currency: str = "INR"
    description: str
    source_evidence_id: Optional[str] = None

class EvidenceIntelligenceOutput(BaseModel):
    extracted_indicators: List[ExtractedIndicator] = Field(default_factory=list)
    extracted_financials: List[ExtractedFinancialItem] = Field(default_factory=list)
    dates_mentioned: List[str] = Field(default_factory=list)
    entities_mentioned: List[str] = Field(default_factory=list)

class ResponsePackagesOutput(BaseModel):
    bank_dispute_subject: str = Field(..., description="Subject line for official bank dispute")
    bank_dispute_body: str = Field(..., description="Formal bank dispute declaration text adhering to standard banking guidelines")
    cybercrime_complaint_subject: str = Field(..., description="Subject line for 1930 / NCRP cybercrime portal")
    cybercrime_complaint_body: str = Field(..., description="Structured complaint narrative for National Cyber Crime Reporting Portal")
    emergency_advisory: str = Field(..., description="Victim emergency guidance and next steps")
    is_draft_only: bool = Field(True, description="Safety flag: strictly draft recommendations pending explicit human approval")

class FollowUpAgentOutput(BaseModel):
    missing_information: List[str] = Field(default_factory=list, description="Critical facts missing from current case")
    unanswered_questions: List[str] = Field(default_factory=list, description="Questions victim or bank should clarify")
    evidence_gaps: List[str] = Field(default_factory=list, description="Missing evidence files (e.g. bank statement PDF, transaction receipt)")
    contradictions_detected: List[str] = Field(default_factory=list, description="Conflicting claims detected across evidence")
    recommended_additional_evidence: List[str] = Field(default_factory=list, description="Files to upload that would materially improve dispute success")

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
    compromise: List[CompromiseAssessmentItem] = Field(default_factory=list, description="Compromise assessment across vectors")
    recommended_immediate_actions: List[str] = Field(default_factory=list, description="Prioritized emergency containment steps")

# -------------------------------------------------------------
# Unified Master Case Intelligence (Orchestration Output)
# -------------------------------------------------------------
class ConflictingFinding(BaseModel):
    field_name: str
    conflicting_values: List[str]
    description: str
    resolution_status: Literal["unresolved", "inferred", "flagged_for_human"] = "flagged_for_human"

class CaseIntelligence(BaseModel):
    case_id: str
    reconstruction: IncidentReconstructionOutput
    triage: TriageOutput
    scam_intel: ScamIntelligenceOutput
    compromise: CompromiseAssessmentOutput
    network_intel: NetworkIntelligenceOutput
    evidence_intel: EvidenceIntelligenceOutput
    response_packages: ResponsePackagesOutput
    follow_up: FollowUpAgentOutput
    conflicting_findings: List[ConflictingFinding] = Field(default_factory=list)
    agents_executed: List[str] = Field(default_factory=list)
    provider_used: str = "mock"
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    human_approval_required: bool = Field(True, description="Strict safety gate: all consequential actions require victim approval")
