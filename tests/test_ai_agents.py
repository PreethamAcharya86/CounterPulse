import pytest
from backend.app.services.ai.mock import MockProvider
from backend.app.services.ai.base import AIError, AISchemaValidationError
from backend.app.knowledge.grounding import GroundingService
from backend.app.services.agents import (
    BaseAgent,
    CaseContext,
    EvidenceIntelligenceAgent,
    IncidentReconstructionAgent,
    TriageAgent,
    ScamIntelligenceAgent,
    CompromiseAssessmentAgent,
    NetworkIntelligenceAgent,
    ResponseAgent,
    FollowUpAgent,
)

from backend.app.schemas.ai_output import (
    EvidenceIntelligenceOutput,
    IncidentReconstructionOutput,
    TriageOutput,
    ScamIntelligenceOutput,
    CompromiseAssessmentOutput,
    NetworkIntelligenceOutput,
    ResponsePackagesOutput,
    FollowUpAgentOutput,
)


# -------------------------------------------------------------
# 1. Knowledge Grounding Tests
# -------------------------------------------------------------
def test_grounding_service_digital_arrest_detection():
    text = "The suspect called claiming to be from Supreme Court and issued a CBI warrant for digital arrest."
    grounding = GroundingService.get_grounding_context(text)
    
    assert "external_typologies" in grounding
    typology_names = [t["name"] for t in grounding["external_typologies"]]
    assert any("Digital Arrest" in name for name in typology_names)
    assert len(grounding["external_typologies"]) > 0


def test_grounding_service_remote_tools_detection():
    text = "Please download AnyDesk APK and share the 9-digit code with our technician."
    grounding = GroundingService.get_grounding_context(text)
    
    assert "detected_tool_grounding" in grounding
    tools = [t["tool"] for t in grounding["detected_tool_grounding"]]
    assert "anydesk" in tools


# -------------------------------------------------------------
# 2. CaseContext Construction Tests
# -------------------------------------------------------------
def test_case_context_creation():
    class DummyEvidence:
        id = "EV-100"
        evidence_type = "chat"
        filename = "whatsapp_chat.txt"
        raw_content = "Fraudster sent UPI QR code for clearing95@okhdfcbank."
        normalized_json = '{"sender": "Unknown", "message": "Pay 95000"}'

    ctx = CaseContext.from_case_and_evidence(
        case_id="case-123",
        title="UPI Extortion",
        description="Victim coerced into payment",
        evidence_list=[DummyEvidence()],
    )

    assert ctx.case_id == "case-123"
    assert len(ctx.evidence_items) == 1
    assert "clearing95@okhdfcbank" in ctx.combined_evidence_text
    assert "external_typologies" in ctx.grounding


# -------------------------------------------------------------
# 3. Individual Specialized Agent Tests (Mock Provider)
# -------------------------------------------------------------
@pytest.fixture
def sample_context():
    return CaseContext(
        case_id="case-test-001",
        title="Digital Arrest Extortion Incident",
        description="Caller impersonating CBI officer demanded payment via UPI.",
        combined_evidence_text=(
            "Caller claiming to be DCP Rajesh from CBI demanded INR 95,000 security deposit "
            "to clear fake money laundering charges. UPI ID: clearing95@okhdfcbank. "
            "Caller asked victim to install AnyDesk to verify phone."
        ),
        grounding=GroundingService.get_grounding_context("Digital arrest CBI AnyDesk 95000"),
    )


@pytest.mark.asyncio
async def test_evidence_intel_agent(sample_context):
    provider = MockProvider()
    agent = EvidenceIntelligenceAgent()
    assert agent.name == "evidence_intel_agent"

    output = await agent.run(sample_context, provider)
    assert isinstance(output, EvidenceIntelligenceOutput)
    assert len(output.extracted_indicators) > 0
    assert any(i.value == "clearing95@okhdfcbank" for i in output.extracted_indicators)
    assert len(output.extracted_financials) > 0
    assert output.extracted_financials[0].amount == 95000.0


@pytest.mark.asyncio
async def test_incident_reconstruction_agent(sample_context):
    provider = MockProvider()
    agent = IncidentReconstructionAgent()
    assert agent.name == "incident_reconstruction_agent"

    output = await agent.run(sample_context, provider)
    assert isinstance(output, IncidentReconstructionOutput)
    assert output.financial_loss == 95000.0
    assert output.severity_level == "critical"
    assert len(output.timeline) >= 2
    assert output.currency == "INR"


@pytest.mark.asyncio
async def test_triage_agent(sample_context):
    provider = MockProvider()
    agent = TriageAgent()
    assert agent.name == "triage_agent"

    output = await agent.run(sample_context, provider)
    assert isinstance(output, TriageOutput)
    assert output.severity_level == "critical"
    assert output.urgency_rating == "immediate_containment"
    assert output.financial_loss_detected is True
    assert output.loss_amount == 95000.0
    assert len(output.immediate_containment_steps) > 0


@pytest.mark.asyncio
async def test_scam_intel_agent(sample_context):
    provider = MockProvider()
    agent = ScamIntelligenceAgent()
    assert agent.name == "scam_intel_agent"

    output = await agent.run(sample_context, provider)
    assert isinstance(output, ScamIntelligenceOutput)
    assert "Digital Arrest" in output.scam_type
    assert len(output.impersonated_entities) > 0
    assert len(output.tactics_observed) > 0


@pytest.mark.asyncio
async def test_compromise_agent_four_tier_model(sample_context):
    """Verify strictly: REQUESTED != DISCLOSED != INSTALLED != CONFIRMED."""
    provider = MockProvider()
    agent = CompromiseAssessmentAgent()
    assert agent.name == "compromise_agent"

    output = await agent.run(sample_context, provider)
    assert isinstance(output, CompromiseAssessmentOutput)
    
    statuses = {item.category: item.status for item in output.assessments}
    
    # Credentials were requested by attacker, NOT confirmed compromised
    assert statuses.get("credentials") == "REQUESTED"
    # Remote access requested
    assert statuses.get("remote_access") == "REQUESTED"
    # Financial transfer was confirmed
    assert statuses.get("financial_information") == "CONFIRMED"
    # Identity verified
    assert statuses.get("identity_information") == "DISCLOSED"


@pytest.mark.asyncio
async def test_network_intel_agent(sample_context):
    provider = MockProvider()
    agent = NetworkIntelligenceAgent()
    assert agent.name == "network_intel_agent"

    output = await agent.run(sample_context, provider)
    assert isinstance(output, NetworkIntelligenceOutput)
    assert len(output.nodes) > 0
    assert "criminality" in output.disclaimer.lower()


@pytest.mark.asyncio
async def test_response_agent_enforces_draft_and_guidelines(sample_context):
    provider = MockProvider()
    agent = ResponseAgent()
    assert agent.name == "response_agent"

    output = await agent.run(sample_context, provider)
    assert isinstance(output, ResponsePackagesOutput)
    assert output.is_draft_only is True
    # Verify statutory RBI circular reference in dispute body
    assert "DBR.No.Leg.BC.78/09.07.005/2017-18" in output.bank_dispute_body
    # Verify National Cybercrime reference
    assert "1930" in output.cybercrime_complaint_body


@pytest.mark.asyncio
async def test_followup_agent(sample_context):
    provider = MockProvider()
    agent = FollowUpAgent()
    assert agent.name == "followup_agent"

    output = await agent.run(sample_context, provider)
    assert isinstance(output, FollowUpAgentOutput)
    assert len(output.missing_information) > 0
    assert len(output.unanswered_questions) > 0


# -------------------------------------------------------------
# 4. Agent Error & Robustness Tests
# -------------------------------------------------------------
@pytest.mark.asyncio
async def test_agent_provider_failure_handling(sample_context):
    failing_provider = MockProvider(simulate_failure=True)
    agent = TriageAgent()
    
    with pytest.raises(AIError):
        await agent.run(sample_context, failing_provider)


@pytest.mark.asyncio
async def test_agent_malformed_json_handling(sample_context):
    malformed_provider = MockProvider(simulate_malformed=True)
    agent = ScamIntelligenceAgent()
    
    with pytest.raises(AISchemaValidationError):
        await agent.run(sample_context, malformed_provider)
