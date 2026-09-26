import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.ai.mock import MockProvider
from backend.app.services.ai.factory import AIProviderFactory
from backend.app.services.email_service import MockEmailProvider, set_email_provider
from backend.app.api.deps import get_email_provider_dep
from backend.app.services.voice_service import voice_service

@pytest.fixture
def mock_email():
    """Provides a clean MockEmailProvider for tests."""
    mock = MockEmailProvider()
    set_email_provider(mock)
    app.dependency_overrides[get_email_provider_dep] = lambda: mock
    yield mock
    mock.clear()
    set_email_provider(None)
    app.dependency_overrides.pop(get_email_provider_dep, None)

@pytest.fixture
def analyzed_case_id(client: TestClient) -> str:
    """Creates a real case with evidence and completes AI analysis."""
    mock_ai = MockProvider()
    AIProviderFactory.set_override_provider(mock_ai)

    try:
        c_res = client.post(
            "/api/v1/cases",
            json={
                "title": "Voice & Call Log Test Incident",
                "description": "Victim received fraudulent calls impersonating police.",
            },
        )
        assert c_res.status_code == 201
        case_id = c_res.json()["id"]

        # Ingest Evidence
        e_res = client.post(
            f"/api/v1/cases/{case_id}/evidence/text",
            json={
                "text": "Call Transcript: Transfer INR 95,000 to upi@okhdfcbank or face digital arrest.",
                "evidence_type": "chat",
            },
        )
        assert e_res.status_code == 201

        # Run AI Pipeline
        a_res = client.post(f"/api/v1/cases/{case_id}/analyze")
        assert a_res.status_code == 200

        # Generate Reports
        client.get(f"/api/v1/cases/{case_id}/reports")

        return case_id
    finally:
        AIProviderFactory.set_override_provider(None)

# 1. Voice Command Parsing
def test_voice_command_parsing():
    assert voice_service.parse_intent("Analyze this case") == "ANALYZE_CASE"
    assert voice_service.parse_intent("What happened?") == "WHAT_HAPPENED"
    assert voice_service.parse_intent("What accounts are compromised?") == "WHAT_COMPROMISED"
    assert voice_service.parse_intent("Show me the evidence") == "SHOW_EVIDENCE"
    assert voice_service.parse_intent("Read the cybercrime complaint") == "READ_CYBERCRIME_COMPLAINT"
    assert voice_service.parse_intent("Generate a bank dispute") == "GENERATE_BANK_DISPUTE"
    assert voice_service.parse_intent("Read the security advisory") == "READ_SECURITY_ADVISORY"
    assert voice_service.parse_intent("Send the complaint email") == "SEND_CYBERCRIME_COMPLAINT"
    assert voice_service.parse_intent("Yes, proceed") == "CONFIRM_ACTION"
    assert voice_service.parse_intent("No, cancel that") == "CANCEL_ACTION"
    assert voice_service.parse_intent("Tell me a random joke") == "UNKNOWN"

# 2. Informational Voice Commands
def test_informational_voice_commands(client: TestClient, analyzed_case_id: str):
    # What happened
    res1 = client.post(
        f"/api/v1/cases/{analyzed_case_id}/voice/command",
        json={"transcript": "What happened?"},
    )
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["intent"] == "WHAT_HAPPENED"
    assert len(data1["response_text"]) > 20
    assert not data1["requires_confirmation"]

    # What is compromised
    res2 = client.post(
        f"/api/v1/cases/{analyzed_case_id}/voice/command",
        json={"transcript": "What accounts are compromised?"},
    )
    assert res2.status_code == 200
    assert "compromise" in res2.json()["intent"].lower() or "what_compromised" in res2.json()["intent"].lower()

    # Show evidence
    res3 = client.post(
        f"/api/v1/cases/{analyzed_case_id}/voice/command",
        json={"transcript": "Show me the evidence."},
    )
    assert res3.status_code == 200
    assert "vault contains" in res3.json()["response_text"].lower() or "forensic" in res3.json()["response_text"].lower()

# 3. Consequential Command Requires Confirmation
def test_consequential_command_requires_confirmation(client: TestClient, analyzed_case_id: str):
    res = client.post(
        f"/api/v1/cases/{analyzed_case_id}/voice/command",
        json={"transcript": "Send the complaint email", "session_id": "sess-test-confirm"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["requires_confirmation"] is True
    assert data["pending_action"] is not None
    assert "do you want me to send it" in data["response_text"].lower()
    assert "yes" in data["response_text"].lower()

# 4. Unconfirmed Send is Blocked
def test_unconfirmed_send_is_blocked(client: TestClient, analyzed_case_id: str, mock_email: MockEmailProvider):
    # Initiate consequential send
    client.post(
        f"/api/v1/cases/{analyzed_case_id}/voice/command",
        json={"transcript": "Send the complaint email", "session_id": "sess-test-block"},
    )

    # Cancel action
    cancel_res = client.post(
        f"/api/v1/cases/{analyzed_case_id}/voice/command",
        json={"transcript": "No, cancel that", "session_id": "sess-test-block"},
    )
    assert cancel_res.status_code == 200
    assert "cancelled" in cancel_res.json()["response_text"].lower()

    # Zero emails must be sent
    assert len(mock_email.sent_messages) == 0

# 5. Confirmed Action Reaches Existing HITL Workflow
def test_confirmed_action_reaches_hitl_workflow(client: TestClient, analyzed_case_id: str, mock_email: MockEmailProvider):
    # Initiate consequential send
    client.post(
        f"/api/v1/cases/{analyzed_case_id}/voice/command",
        json={"transcript": "Send the complaint email", "session_id": "sess-test-exec"},
    )

    # Confirm action
    confirm_res = client.post(
        f"/api/v1/cases/{analyzed_case_id}/voice/command",
        json={"transcript": "Yes, send it now", "session_id": "sess-test-exec"},
    )
    assert confirm_res.status_code == 200
    data = confirm_res.json()
    assert "dispatched" in data["response_text"].lower() or "approved" in data["response_text"].lower()
    assert len(mock_email.sent_messages) == 1
    assert mock_email.sent_messages[0]["attachment"] is not None

# 6. Live Intelligence Extraction
def test_live_intelligence_extraction(client: TestClient, analyzed_case_id: str):
    # 1. Create Call Session
    sess_res = client.post(
        f"/api/v1/cases/{analyzed_case_id}/calls",
        json={"title": "Test Call Extraction Session"},
    )
    assert sess_res.status_code == 201
    call_id = sess_res.json()["id"]

    # 2. Add message with indicators
    msg_res = client.post(
        f"/api/v1/cases/{analyzed_case_id}/calls/{call_id}/messages",
        json={
            "speaker": "caller",
            "content": "Transfer ₹1,50,000 to fraudulent.desk@okhdfcbank or call 9876543210 immediately.",
        },
    )
    assert msg_res.status_code == 200
    data = msg_res.json()
    assert data["message_count"] == 1
    assert data["intelligence"] is not None

    upis = [u["value"] for u in data["intelligence"]["upi_ids"]]
    assert "fraudulent.desk@okhdfcbank" in upis

    phones = [p["value"] for p in data["intelligence"]["phone_numbers"]]
    assert any("9876543210" in p for p in phones)

# 7. Indicator Provenance
def test_indicator_provenance(client: TestClient, analyzed_case_id: str):
    sess_res = client.post(
        f"/api/v1/cases/{analyzed_case_id}/calls",
        json={"title": "Provenance Test Call"},
    )
    call_id = sess_res.json()["id"]

    # Message 1
    client.post(
        f"/api/v1/cases/{analyzed_case_id}/calls/{call_id}/messages",
        json={"speaker": "caller", "content": "Hello, this is Cyber Cell."},
    )

    # Message 2 containing specific URL
    msg2_res = client.post(
        f"/api/v1/cases/{analyzed_case_id}/calls/{call_id}/messages",
        json={"speaker": "caller", "content": "Visit https://fraud-portal.org/clearance now."},
    )
    data = msg2_res.json()
    url_item = next((u for u in data["intelligence"]["urls"] if "fraud-portal.org" in u["value"]), None)
    assert url_item is not None
    assert url_item["source_message_index"] == 2
    assert "Message #2" in url_item["source_reference"]

# 8. Unverified Indicator Handling & Disclaimer
def test_unverified_indicator_handling(client: TestClient, analyzed_case_id: str):
    sess_res = client.post(
        f"/api/v1/cases/{analyzed_case_id}/calls",
        json={"title": "Unverified Indicator Test"},
    )
    call_id = sess_res.json()["id"]

    msg_res = client.post(
        f"/api/v1/cases/{analyzed_case_id}/calls/{call_id}/messages",
        json={"speaker": "caller", "content": "Send funds to officer@icici"},
    )
    intel = msg_res.json()["intelligence"]
    assert "does not automatically establish criminality" in intel["disclaimer"].lower()
    for ind in intel["upi_ids"]:
        assert ind["status"] == "UNVERIFIED"

# 9. Malformed AI Output Handling
@pytest.mark.asyncio
async def test_malformed_ai_output_handling():
    from backend.app.services.call_intelligence_service import call_intelligence_service

    class BrokenAIProvider:
        async def complete(self, prompt: str, system_instruction: str = "") -> str:
            return "NOT JSON AT ALL {{{ broken"

    res = await call_intelligence_service.extract_ai_conversation_intel(
        "Some transcript", [], provider=BrokenAIProvider()
    )
    assert isinstance(res, dict)
    assert "claimed_persons" in res
    assert "summary" in res

# 10. Missing Gemini Configuration
@pytest.mark.asyncio
async def test_missing_gemini_configuration(client: TestClient, analyzed_case_id: str):
    # Voice command works deterministically even if Gemini is not configured
    res = client.post(
        f"/api/v1/cases/{analyzed_case_id}/voice/command",
        json={"transcript": "What happened?"},
    )
    assert res.status_code == 200
    assert res.json()["intent"] == "WHAT_HAPPENED"

# 11. Voice Session Status
def test_voice_session_status(client: TestClient, analyzed_case_id: str):
    status_res = client.get(f"/api/v1/cases/{analyzed_case_id}/voice/session?session_id=sess-status-test")
    assert status_res.status_code == 200
    data = status_res.json()
    assert data["case_id"] == analyzed_case_id
    assert "voice_state" in data

# 12. Voice State & Error Handling
def test_voice_state_error_handling(client: TestClient):
    res = client.post(
        "/api/v1/cases/non-existent-case-id/voice/command",
        json={"transcript": "Analyze this case"},
    )
    assert res.status_code == 200
    assert res.json()["voice_state"] == "ERROR"

# 13. Invalid Conversation Input
def test_invalid_conversation_input(client: TestClient):
    # Non existent case
    res = client.post(
        "/api/v1/cases/invalid-case-id/calls",
        json={"title": "Invalid Call"},
    )
    assert res.status_code == 404

# 14. Promote Call to Case Evidence
def test_promote_call_to_evidence(client: TestClient, analyzed_case_id: str):
    # Create call session
    sess_res = client.post(
        f"/api/v1/cases/{analyzed_case_id}/calls",
        json={"title": "Call To Promote"},
    )
    call_id = sess_res.json()["id"]

    # Add message
    client.post(
        f"/api/v1/cases/{analyzed_case_id}/calls/{call_id}/messages",
        json={"speaker": "caller", "content": "Transfer INR 50,000 to refund@okhdfcbank"},
    )

    # Promote
    prom_res = client.post(f"/api/v1/cases/{analyzed_case_id}/calls/{call_id}/promote")
    assert prom_res.status_code == 200
    prom_data = prom_res.json()
    assert prom_data["evidence_id"].startswith("EV-")
    assert prom_data["indicators_created_count"] >= 1

    # Verify evidence exists in case evidence vault
    ev_list = client.get(f"/api/v1/cases/{analyzed_case_id}/evidence")
    assert any(e["id"] == prom_data["evidence_id"] for e in ev_list.json())

# 15. Security Validation: No Secrets or API Keys in Responses
def test_security_validation(client: TestClient, analyzed_case_id: str):
    call_res = client.get(f"/api/v1/cases/{analyzed_case_id}/calls")
    assert "GEMINI_API_KEY" not in call_res.text
    assert "RESEND_API_KEY" not in call_res.text

    voice_res = client.post(
        f"/api/v1/cases/{analyzed_case_id}/voice/command",
        json={"transcript": "What happened?"},
    )
    assert "GEMINI_API_KEY" not in voice_res.text
    assert "RESEND_API_KEY" not in voice_res.text
