from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from pydantic import BaseModel, ConfigDict, Field

# Forensic Legal Disclaimer
DISCLAIMER_TEXT = (
    "Extracted indicators represent investigative artifacts from the conversation; "
    "does not automatically establish criminality of named individuals or entities."
)

class ScamIntelligenceItem(BaseModel):
    """Individual extracted forensic indicator or behavioral pattern with provenance."""
    model_config = ConfigDict(from_attributes=True)

    indicator_type: str = Field(
        ...,
        description="phone_number, upi_id, url, email, organization, suspect_name, financial_amount, transaction_id, scam_tactic, urgency_indicator, requested_action"
    )
    value: str = Field(..., description="Extracted value or text description")
    confidence: str = Field("medium", description="high, medium, low")
    verification_status: str = Field(
        "unverified",
        description="unverified, supported, possible, or flagged"
    )
    source_message_index: Optional[int] = Field(None, description="Sequence index of the message in the conversation")
    source_reference: str = Field(..., description="Citation e.g. 'Message #2' or 'Evidence EV-41F7A330'")
    source_evidence_id: Optional[str] = Field(None, description="Linked Evidence ID if promoted/associated with evidence")
    context: Optional[str] = Field(None, description="Conversational context or snippet")

class ScamIntelligenceAnalyzeRequest(BaseModel):
    """Request payload to analyze conversation text or existing case evidence."""
    conversation_text: Optional[str] = Field(
        None,
        description="Raw conversation dialogue / transcript to analyze dynamically"
    )
    evidence_id: Optional[str] = Field(
        None,
        description="ID of specific case Evidence to analyze"
    )
    selected_message_index: Optional[int] = Field(
        None,
        description="Optional 1-based index to focus analysis on a single selected message"
    )
    add_to_case: bool = Field(
        False,
        description="If True, automatically links extracted indicators into case.indicators"
    )

class ScamIntelligenceAnalysisResponse(BaseModel):
    """Structured response containing dynamically extracted intelligence across all categories."""
    case_id: str
    conversation_summary: str
    scam_type: str = Field(..., description="Identified scam typology (e.g. Digital Arrest / Law Enforcement Impersonation)")
    threat_assessment: str = Field(..., description="Behavioral analysis of threat vector")
    tactics_observed: List[str] = Field(default_factory=list)
    psychological_triggers: List[str] = Field(default_factory=list)
    urgency_level: str = Field("high", description="critical, high, medium, low")
    
    # All items unified
    indicators: List[ScamIntelligenceItem] = Field(default_factory=list)
    
    # Categorized subsets for targeted UI rendering
    phone_numbers: List[ScamIntelligenceItem] = Field(default_factory=list)
    upi_ids: List[ScamIntelligenceItem] = Field(default_factory=list)
    urls: List[ScamIntelligenceItem] = Field(default_factory=list)
    emails: List[ScamIntelligenceItem] = Field(default_factory=list)
    claimed_entities: List[ScamIntelligenceItem] = Field(default_factory=list)
    financial_amounts: List[ScamIntelligenceItem] = Field(default_factory=list)
    transaction_references: List[ScamIntelligenceItem] = Field(default_factory=list)
    scam_tactics: List[ScamIntelligenceItem] = Field(default_factory=list)
    requested_actions: List[ScamIntelligenceItem] = Field(default_factory=list)
    
    disclaimer: str = Field(default=DISCLAIMER_TEXT)
    added_to_case_count: int = Field(0, description="Count of indicators added to case if requested")
    analyzed_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class AddIndicatorsToCaseRequest(BaseModel):
    """Request payload to manually merge selected extracted indicators into the case vault."""
    indicators: List[ScamIntelligenceItem]
    evidence_id: Optional[str] = Field(None, description="Optional evidence ID to attach as source")

class AddIndicatorsToCaseResponse(BaseModel):
    """Confirmation of indicators added to case without duplicate creation."""
    case_id: str
    added_count: int
    skipped_duplicates_count: int
    total_case_indicators: int
    message: str
