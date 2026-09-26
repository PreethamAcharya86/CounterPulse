import pytest
import json
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.ai.mock import MockProvider
from backend.app.services.ai.factory import AIProviderFactory
from backend.app.services.email_service import MockEmailProvider, set_email_provider
from backend.app.api.deps import get_email_provider_dep
from backend.app.services.voice_service import voice_service, VoiceControlService
from backend.app.schemas.voice import VoiceCommandRequest
from backend.app.core.config import settings

@pytest.fixture
def mock_email():
    mock = MockEmailProvider()
    set_email_provider(mock)
    app.dependency_overrides[get_email_provider_dep] = lambda: mock
    yield mock
    mock.clear()
    set_email_provider(None)
    app.dependency_overrides.pop(get_email_provider_dep, None)

@pytest.fixture
def test_case(client: TestClient) -> str:
    mock_ai = MockProvider()
    AIProviderFactory.set_override_provider(mock_ai)
    try:
        c_res = client.post(
            "/api/v1/cases",
            json={
                "title": "Gemini Live Voice Test Incident",
                "description": "Victim received coercive calls and fraudulent courier notices.",
            },
        )
        assert c_res.status_code == 201
        cid = c_res.json()["id"]

        # Ingest text evidence
        client.post(
            f"/api/v1/cases/{cid}/evidence/text",
            json={
                "text": "Transfer INR 75,000 to customs.clearance@icici or face warrant.",
                "evidence_type": "chat",
            },
        )

        # Run AI analysis
        client.post(f"/api/v1/cases/{cid}/analyze")

        # Generate report drafts
        client.get(f"/api/v1/cases/{cid}/reports")

        return cid
    finally:
        AIProviderFactory.set_override_provider(None)

# 1. Voice Command Parsing
def test_voice_command_parsing():
    assert voice_service.parse_intent("Analyze this case.") == "ANALYZE_CASE"
    assert voice_service.parse_intent("What happened?") == "WHAT_HAPPENED"
    assert voice_service.parse_intent("What accounts are compromised?") == "WHAT_COMPROMISED"
    assert voice_service.parse_intent("Show me the evidence.") == "SHOW_EVIDENCE"
    assert voice_service.parse_intent("Read the cybercrime complaint.") == "READ_CYBERCRIME_COMPLAINT"
    assert voice_service.parse_intent("Generate a bank dispute.") == "GENERATE_BANK_DISPUTE"
    assert voice_service.parse_intent("Read the security advisory.") == "READ_SECURITY_ADVISORY"
    assert voice_service.parse_intent("Send the complaint email.") == "SEND_CYBERCRIME_COMPLAINT"
    assert voice_service.parse_intent("Yes, proceed.") == "CONFIRM_ACTION"
    assert voice_service.parse_intent("No, cancel.") == "CANCEL_ACTION"
    assert voice_service.parse_intent("What is the weather in Delhi?") == "UNKNOWN"

# 2. Informational Command Routing
def test_informational_command_routing(client: TestClient, test_case: str):
    res = client.post(
        f"/api/v1/cases/{test_case}/voice/command",
        json={"transcript": "Show me the evidence."},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["intent"] == "SHOW_EVIDENCE"
    assert "vault contains" in data["response_text"].lower() or "forensic" in data["response_text"].lower()
    assert data["requires_confirmation"] is False

# 3. Case Summary Voice Command
def test_case_summary_voice_command(client: TestClient, test_case: str):
    res = client.post(
        f"/api/v1/cases/{test_case}/voice/command",
        json={"transcript": "What happened?"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["intent"] == "WHAT_HAPPENED"
    assert len(data["response_text"]) > 20
    assert "happened" in data["response_text"].lower()

# 4. Report Reading Command
def test_report_reading_command(client: TestClient, test_case: str):
    # Read Cybercrime Complaint
    res1 = client.post(
        f"/api/v1/cases/{test_case}/voice/command",
        json={"transcript": "Read the cybercrime complaint."},
    )
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["intent"] == "READ_CYBERCRIME_COMPLAINT"
    assert len(data1["response_text"]) > 20

    # Read Security Advisory
    res2 = client.post(
        f"/api/v1/cases/{test_case}/voice/command",
        json={"transcript": "Read the security advisory."},
    )
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["intent"] == "READ_SECURITY_ADVISORY"
    assert len(data2["response_text"]) > 20

# 5. Consequential Action Detection
def test_consequential_action_detection(client: TestClient, test_case: str):
    res = client.post(
        f"/api/v1/cases/{test_case}/voice/command",
        json={"transcript": "Send the complaint email."},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["intent"] == "SEND_CYBERCRIME_COMPLAINT"
    assert data["requires_confirmation"] is True
    assert data["pending_action"] is not None
    assert data["pending_action"]["action"] == "send_report"

# 6. Explicit Confirmation Requirement
def test_explicit_confirmation_requirement(client: TestClient, test_case: str):
    sid = "sess-explicit-confirm-1"
    res = client.post(
        f"/api/v1/cases/{test_case}/voice/command",
        json={"transcript": "Send the complaint email.", "session_id": sid},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["requires_confirmation"] is True
    assert "do you want me to send it" in data["response_text"].lower()
    assert "yes" in data["response_text"].lower()
    assert "no" in data["response_text"].lower()

# 7. Unconfirmed Send Blocked
def test_unconfirmed_send_blocked(client: TestClient, test_case: str, mock_email: MockEmailProvider):
    sid = "sess-unconfirmed-block"
    # Initiate
    client.post(
        f"/api/v1/cases/{test_case}/voice/command",
        json={"transcript": "Send the complaint email.", "session_id": sid},
    )

    # User says ambiguous statement
    ambig_res = client.post(
        f"/api/v1/cases/{test_case}/voice/command",
        json={"transcript": "I am not really sure.", "session_id": sid},
    )
    assert ambig_res.status_code == 200
    assert len(mock_email.sent_messages) == 0

    # User says No
    cancel_res = client.post(
        f"/api/v1/cases/{test_case}/voice/command",
        json={"transcript": "No, do not send it.", "session_id": sid},
    )
    assert cancel_res.status_code == 200
    assert "cancelled" in cancel_res.json()["response_text"].lower()
    assert len(mock_email.sent_messages) == 0

# 8. Confirmed Send Uses Existing HITL Workflow
def test_confirmed_send_uses_hitl_workflow(client: TestClient, test_case: str, mock_email: MockEmailProvider):
    sid = "sess-hitl-flow"
    # Initiate
    client.post(
        f"/api/v1/cases/{test_case}/voice/command",
        json={"transcript": "Send the complaint email.", "session_id": sid},
    )

    # Explicit Affirmative Confirmation
    confirm_res = client.post(
        f"/api/v1/cases/{test_case}/voice/command",
        json={"transcript": "Yes, approve and send.", "session_id": sid},
    )
    assert confirm_res.status_code == 200
    data = confirm_res.json()
    assert data["action_executed"] == "send_cybercrime_complaint"
    assert "dispatched" in data["response_text"].lower() or "approved" in data["response_text"].lower()
    assert len(mock_email.sent_messages) == 1
    assert mock_email.sent_messages[0]["attachment"] is not None

# 9. Unsupported Command Rejection
def test_unsupported_command_rejection(client: TestClient, test_case: str):
    res = client.post(
        f"/api/v1/cases/{test_case}/voice/command",
        json={"transcript": "Order a pizza for the investigator."},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["intent"] == "UNKNOWN"
    assert "supported" in data["response_text"].lower() or "commands" in data["response_text"].lower()

# 10. Missing GEMINI_API_KEY Handling
def test_missing_gemini_api_key_handling(client: TestClient, test_case: str):
    # With GEMINI_API_KEY empty (the fixture default), commands still work deterministically
    res = client.post(
        f"/api/v1/cases/{test_case}/voice/command",
        json={"transcript": "What happened?", "synthesize": True},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["intent"] == "WHAT_HAPPENED"
    # Audio is None because key is absent in test environment, but execution never crashes
    assert data["audio_base64"] is None

# 11. Invalid Gemini Configuration
@pytest.mark.asyncio
async def test_invalid_gemini_configuration():
    # Calling synthesize_live_audio when API key is missing or invalid gracefully returns None
    result = await voice_service.synthesize_live_audio("Test audio synthesis")
    assert result is None

# 12. Live Session Failure & Error State
def test_live_session_failure(client: TestClient):
    res = client.post(
        "/api/v1/cases/NON_EXISTENT_CASE/voice/command",
        json={"transcript": "What happened?"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["voice_state"] == "ERROR"
    assert "not found" in data["response_text"].lower()

# 13. Session Termination & Status
def test_session_termination_and_status(client: TestClient, test_case: str):
    sid = "sess-term-test"
    # Check initial status
    status_res = client.get(f"/api/v1/cases/{test_case}/voice/session?session_id={sid}")
    assert status_res.status_code == 200
    data = status_res.json()
    assert data["case_id"] == test_case
    assert data["voice_state"] in ("IDLE", "LISTENING")

    # Cancel action resets session
    client.post(
        f"/api/v1/cases/{test_case}/voice/command",
        json={"transcript": "Cancel", "session_id": sid},
    )
    status_after = client.get(f"/api/v1/cases/{test_case}/voice/session?session_id={sid}")
    assert status_after.json()["voice_state"] == "IDLE"

# 14. API Key Non-Exposure
def test_api_key_non_exposure(client: TestClient, test_case: str):
    res = client.post(
        f"/api/v1/cases/{test_case}/voice/command",
        json={"transcript": "What happened?"},
    )
    assert "GEMINI_API_KEY" not in res.text
    assert "sk-" not in res.text
    assert "AIza" not in res.text

# 15. Security Validation: Tool Calling Security
def test_security_validation_safe_tools():
    # Check declarations only expose approved functions
    tools = voice_service.get_safe_tool_declarations()
    names = [t["name"] for t in tools]
    assert "get_case_summary" in names
    assert "get_compromise_summary" in names
    assert "get_report" in names
    assert "request_report_send_confirmation" in names

    # Unsafe tools MUST NOT be exposed
    assert "execute_command" not in names
    assert "send_email" not in names
    assert "arbitrary_http_request" not in names
    assert "arbitrary_database_query" not in names

    # Execution of unapproved tools is strictly rejected
    db_mock = MagicMock()
    rejected = voice_service.execute_safe_tool("arbitrary_exec", {"case_id": "c1"}, db=db_mock)
    assert "not permitted" in rejected["error"]

# 16. Voice State Transitions
def test_voice_state_transitions(client: TestClient, test_case: str):
    sid = "sess-state-trans"
    sess = voice_service.get_or_create_session(sid, test_case)
    assert sess.voice_state == "IDLE"

    # Consequential trigger moves session into confirmation listening
    res = client.post(
        f"/api/v1/cases/{test_case}/voice/command",
        json={"transcript": "Send the complaint email.", "session_id": sid},
    )
    assert res.json()["voice_state"] == "LISTENING"

    # Cancel moves it back to IDLE
    res2 = client.post(
        f"/api/v1/cases/{test_case}/voice/command",
        json={"transcript": "No", "session_id": sid},
    )
    assert res2.json()["voice_state"] == "IDLE"

# 17. WebSocket Live Bidirectional Streaming
def test_websocket_live_bidirectional(client: TestClient, test_case: str):
    with client.websocket_connect(f"/api/v1/cases/{test_case}/voice/live") as ws:
        # Initial greeting
        init_msg = ws.receive_json()
        assert init_msg["type"] == "state_change"
        assert init_msg["voice_state"] == "LISTENING"

        # Ping-Pong
        ws.send_json({"type": "ping"})
        pong = ws.receive_json()
        assert pong["type"] == "pong"

        # Voice command
        ws.send_json({"type": "voice_command", "transcript": "What happened?"})

        # Processing state change
        proc_msg = ws.receive_json()
        assert proc_msg["type"] == "state_change"
        assert proc_msg["voice_state"] == "PROCESSING"

        # Voice response
        resp_msg = ws.receive_json()
        assert resp_msg["type"] == "voice_response"
        assert resp_msg["intent"] == "WHAT_HAPPENED"

        # Post response state change
        post_msg = ws.receive_json()
        assert post_msg["type"] == "state_change"
        assert post_msg["voice_state"] == "IDLE"

# 18. Multilingual Voice Command Parsing (Hindi & Kannada)
def test_multilingual_voice_command_parsing():
    # Hindi Commands
    assert voice_service.parse_intent("क्या हुआ?") == "WHAT_HAPPENED"
    assert voice_service.parse_intent("kya hua yahan?") == "WHAT_HAPPENED"
    assert voice_service.parse_intent("शिकायत पढ़ो") == "READ_CYBERCRIME_COMPLAINT"
    assert voice_service.parse_intent("shikayat padho") == "READ_CYBERCRIME_COMPLAINT"
    assert voice_service.parse_intent("शिकायत ईमेल भेजो") == "SEND_CYBERCRIME_COMPLAINT"
    assert voice_service.parse_intent("shikayat email bhejo") == "SEND_CYBERCRIME_COMPLAINT"
    assert voice_service.parse_intent("हाँ, भेजो") == "CONFIRM_ACTION"
    assert voice_service.parse_intent("जी हाँ") == "CONFIRM_ACTION"
    assert voice_service.parse_intent("नहीं, मत भेजो") == "CANCEL_ACTION"
    assert voice_service.parse_intent("mat bhejo") == "CANCEL_ACTION"

    # Kannada Commands
    assert voice_service.parse_intent("ಏನಾಯಿತು?") == "WHAT_HAPPENED"
    assert voice_service.parse_intent("enaitu illi?") == "WHAT_HAPPENED"
    assert voice_service.parse_intent("ದೂರು ಓದಿ") == "READ_CYBERCRIME_COMPLAINT"
    assert voice_service.parse_intent("duru odi") == "READ_CYBERCRIME_COMPLAINT"
    assert voice_service.parse_intent("ದೂರು ಇಮೇಲ್ ಕಳುಹಿಸಿ") == "SEND_CYBERCRIME_COMPLAINT"
    assert voice_service.parse_intent("duru email kaluhisi") == "SEND_CYBERCRIME_COMPLAINT"
    assert voice_service.parse_intent("ಹೌದು, ಕಳುಹಿಸಿ") == "CONFIRM_ACTION"
    assert voice_service.parse_intent("haudu") == "CONFIRM_ACTION"
    assert voice_service.parse_intent("ಬೇಡ, ರದ್ದುಮಾಡು") == "CANCEL_ACTION"
    assert voice_service.parse_intent("beda") == "CANCEL_ACTION"

    # Strict safety: negation must take precedence over confirmation verbs
    assert voice_service.parse_intent("nahi bhejo") == "CANCEL_ACTION"
    assert voice_service.parse_intent("beda kaluhisabedi") == "CANCEL_ACTION"

# 19. Multilingual Voice Confirmation Flow (Hindi & Kannada Safety)
def test_multilingual_voice_confirmation_flow(client: TestClient, test_case: str, mock_email: MockEmailProvider):
    sid = "sess-multi-safety-1"
    # Step 1: Speak Hindi command to send complaint
    res1 = client.post(
        f"/api/v1/cases/{test_case}/voice/command",
        json={"transcript": "शिकायत ईमेल भेजो", "session_id": sid},
    )
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["intent"] == "SEND_CYBERCRIME_COMPLAINT"
    assert data1["requires_confirmation"] is True

    # Step 2: Cancel in Kannada ("ಬೇಡ") -> must cancel and NOT dispatch
    res2 = client.post(
        f"/api/v1/cases/{test_case}/voice/command",
        json={"transcript": "ಬೇಡ", "session_id": sid},
    )
    assert res2.status_code == 200
    assert res2.json()["intent"] == "CANCEL_ACTION"
    assert len(mock_email.sent_messages) == 0

    # Step 3: Trigger send again in Kannada
    sid3 = "sess-multi-safety-2"
    res3 = client.post(
        f"/api/v1/cases/{test_case}/voice/command",
        json={"transcript": "ದೂರು ಇಮೇಲ್ ಕಳುಹಿಸಿ", "session_id": sid3},
    )
    assert res3.status_code == 200
    assert res3.json()["requires_confirmation"] is True

    # Step 4: Confirm in Hindi ("हाँ, भेजो") -> must confirm and dispatch
    res4 = client.post(
        f"/api/v1/cases/{test_case}/voice/command",
        json={"transcript": "हाँ, भेजो", "session_id": sid3},
    )
    assert res4.status_code == 200
    assert res4.json()["intent"] == "CONFIRM_ACTION"
    assert len(mock_email.sent_messages) == 1

# 20. Synthetic Demo Case Creation with Dynamic AI Orchestration
def test_demo_case_creation_endpoint(client: TestClient):
    mock_ai = MockProvider()
    AIProviderFactory.set_override_provider(mock_ai)
    try:
        res = client.post("/api/v1/cases/demo", json={"scenario": "digital_arrest"})
        assert res.status_code == 201
        data = res.json()
        assert "id" in data
        cid = data["id"]
        assert "Synthetic Demo" in data["title"]
        assert data["severity_level"].upper() in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]

        # Verify evidence was ingested
        ev_res = client.get(f"/api/v1/cases/{cid}/evidence")
        assert ev_res.status_code == 200
        ev_items = ev_res.json()
        assert len(ev_items) >= 2  # Chat, SMS, and URL

        # Verify passport is ready
        pass_res = client.get(f"/api/v1/cases/{cid}/passport")
        assert pass_res.status_code == 200

        # Verify reports are ready
        rep_res = client.get(f"/api/v1/cases/{cid}/reports")
        assert rep_res.status_code == 200
        reports = rep_res.json()
        assert len(reports) == 3
    finally:
        AIProviderFactory.set_override_provider(None)

