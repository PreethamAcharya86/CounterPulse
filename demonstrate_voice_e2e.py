import asyncio
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
os.environ["TESTING"] = "true"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["TEST_DATABASE_URL"] = "sqlite:///:memory:"

from dotenv import load_dotenv
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.core.database import SessionLocal, Base, engine
from backend.app.models.case import Case
from backend.app.models.report import Report, ActionEvent
from backend.app.services.ai.mock import MockProvider
from backend.app.services.ai.factory import AIProviderFactory
from backend.app.services.email_service import MockEmailProvider, set_email_provider
from backend.app.api.deps import get_email_provider_dep

load_dotenv()

def run_e2e_demonstration():
    print("==================================================")
    print("COUNTERPULSE AI — GEMINI LIVE VOICE CONTROL E2E")
    print("==================================================")

    # Setup mock email provider for deterministic dispatch tracking
    mock_email = MockEmailProvider()
    set_email_provider(mock_email)
    app.dependency_overrides[get_email_provider_dep] = lambda: mock_email

    # Setup in-memory tables
    Base.metadata.create_all(bind=engine)

    # Setup client
    client = TestClient(app)

    # 1. Setup real case with evidence and intelligence
    print("\n--- STEP 1: INITIALIZE CASE WITH EVIDENCE & INTELLIGENCE ---")
    mock_ai = MockProvider()
    AIProviderFactory.set_override_provider(mock_ai)
    try:
        c_res = client.post(
            "/api/v1/cases",
            json={
                "title": "E2E Voice Demonstration Case",
                "description": "Victim subjected to coercive digital arrest scam impersonating CBI officers.",
            },
        )
        case_id = c_res.json()["id"]
        print(f"  Created Case ID: {case_id}")

        # Ingest text evidence
        client.post(
            f"/api/v1/cases/{case_id}/evidence/text",
            json={
                "text": "Call Transcript: CBI Officer Sharma ordered transfer of INR 95,000 to clearance.rbi@okhdfcbank under threat of detention.",
                "evidence_type": "chat",
            },
        )

        # Run AI Orchestrator pipeline
        client.post(f"/api/v1/cases/{case_id}/analyze")

        # Generate response reports
        client.get(f"/api/v1/cases/{case_id}/reports")
        print("  AI Orchestrator Pipeline completed. Reports generated.")
    finally:
        AIProviderFactory.set_override_provider(None)

    # 2. Voice Query: What happened?
    print("\n--- STEP 2: USER ASKS 'What happened?' ---")
    cmd1_res = client.post(
        f"/api/v1/cases/{case_id}/voice/command",
        json={"transcript": "What happened?", "session_id": "demo-voice-sess"},
    )
    assert cmd1_res.status_code == 200
    data1 = cmd1_res.json()
    print(f"  User Voice: 'What happened?'")
    print(f"  Parsed Intent: {data1['intent']}")
    print(f"  Voice State: {data1['voice_state']}")
    print(f"  Requires Confirmation: {data1['requires_confirmation']}")
    print(f"  Assistant Response: \"{data1['response_text']}\"")
    assert data1["intent"] == "WHAT_HAPPENED"
    assert data1["requires_confirmation"] is False

    # 3. Voice Query: Read the cybercrime complaint
    print("\n--- STEP 3: USER ASKS 'Read the cybercrime complaint.' ---")
    cmd2_res = client.post(
        f"/api/v1/cases/{case_id}/voice/command",
        json={"transcript": "Read the cybercrime complaint.", "session_id": "demo-voice-sess"},
    )
    assert cmd2_res.status_code == 200
    data2 = cmd2_res.json()
    print(f"  User Voice: 'Read the cybercrime complaint.'")
    print(f"  Parsed Intent: {data2['intent']}")
    print(f"  Assistant Response: \"{data2['response_text'][:150]}...\"")
    assert data2["intent"] == "READ_CYBERCRIME_COMPLAINT"
    assert data2["requires_confirmation"] is False

    # 4. Consequential Command: Send the complaint email
    print("\n--- STEP 4: USER ASKS 'Send the complaint email.' ---")
    print("  [CRITICAL SAFETY GATE ACTIVATED]")
    cmd3_res = client.post(
        f"/api/v1/cases/{case_id}/voice/command",
        json={"transcript": "Send the complaint email.", "session_id": "demo-voice-sess"},
    )
    assert cmd3_res.status_code == 200
    data3 = cmd3_res.json()
    print(f"  User Voice: 'Send the complaint email.'")
    print(f"  Parsed Intent: {data3['intent']}")
    print(f"  Requires Confirmation: {data3['requires_confirmation']}")
    print(f"  Pending Action Details: {data3['pending_action']}")
    print(f"  Assistant Prompt: \"{data3['response_text']}\"")
    assert data3["requires_confirmation"] is True
    assert data3["pending_action"]["action"] == "send_report"
    assert len(mock_email.sent_messages) == 0
    print("  [VERIFIED] 0 emails sent prior to explicit confirmation!")

    # 5. User Confirms: Yes
    print("\n--- STEP 5: USER CONFIRMS 'Yes, please send it.' ---")
    cmd4_res = client.post(
        f"/api/v1/cases/{case_id}/voice/command",
        json={"transcript": "Yes, please send it.", "session_id": "demo-voice-sess"},
    )
    assert cmd4_res.status_code == 200
    data4 = cmd4_res.json()
    print(f"  User Voice: 'Yes, please send it.'")
    print(f"  Parsed Intent: {data4['intent']}")
    print(f"  Action Executed: {data4['action_executed']}")
    print(f"  Assistant Response: \"{data4['response_text']}\"")
    assert data4["action_executed"] == "send_cybercrime_complaint"
    assert len(mock_email.sent_messages) == 1
    sent_msg = mock_email.sent_messages[0]
    print(f"  [VERIFIED] Dispatched to: {sent_msg['to']}")
    print(f"  [VERIFIED] Subject: {sent_msg['subject']}")
    print(f"  [VERIFIED] PDF Attached: {sent_msg['attachment']} ({sent_msg['attachment_size_bytes']} bytes)")

    # 6. Audit Trail Check
    print("\n--- STEP 6: VERIFY AUDIT TRAIL RECORDING ---")
    db = SessionLocal()
    try:
        events = db.query(ActionEvent).filter(ActionEvent.case_id == case_id).all()
        print(f"  Recorded Audit Events: {len(events)}")
        for ev in events:
            print(f"   - [{ev.action_type}] Status: {ev.status} | Details: {ev.details[:80] if ev.details else ''}")
        assert any(ev.action_type in ("approved", "sent", "send_attempted") for ev in events)
        print("  [SUCCESS] Immutable audit trail accurately recorded dispatch action.")
    finally:
        db.close()

    print("\n==================================================")
    print("ALL E2E VOICE CONTROL REQUIREMENTS VERIFIED!")
    print("==================================================")

if __name__ == "__main__":
    run_e2e_demonstration()
