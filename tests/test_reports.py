import pytest
from datetime import datetime
from fastapi.testclient import TestClient

from backend.app.services.ai.mock import MockProvider
from backend.app.services.ai.factory import AIProviderFactory
from backend.app.services.email_service import MockEmailProvider, set_email_provider, get_email_provider
from backend.app.api.deps import get_email_provider_dep
from backend.app.main import app

@pytest.fixture
def mock_email():
    """Provides a clean MockEmailProvider and injects it for tests."""
    mock = MockEmailProvider()
    set_email_provider(mock)
    app.dependency_overrides[get_email_provider_dep] = lambda: mock
    yield mock
    mock.clear()
    set_email_provider(None)
    app.dependency_overrides.pop(get_email_provider_dep, None)

@pytest.fixture
def analyzed_case_id(client: TestClient) -> str:
    """Creates a real case, uploads authentic evidence, and runs AI orchestration."""
    mock_ai = MockProvider()
    AIProviderFactory.set_override_provider(mock_ai)

    try:
        # Create Case
        create_res = client.post(
            "/api/v1/cases",
            json={
                "title": "Digital Arrest Cyber Extortion Case",
                "description": "Victim extorted under threat of fake arrest warrant.",
            },
        )
        assert create_res.status_code == 201
        case_id = create_res.json()["id"]

        # Upload Evidence 1
        sms_res = client.post(
            f"/api/v1/cases/{case_id}/evidence/text",
            json={
                "text": "INR 95,000.0 debited from A/c ending 4321 on 26-SEP-26 via UPI Ref 987654321012 to clearing95@okhdfcbank. Available balance: INR 4,210.50.",
                "evidence_type": "text",
            },
        )
        assert sms_res.status_code == 201

        # Upload Evidence 2
        chat_res = client.post(
            f"/api/v1/cases/{case_id}/evidence/text",
            json={
                "text": "Officer Sharma (CBI): You are under digital arrest. Transfer ₹95,000 to RBI clearing account or police will arrive.",
                "evidence_type": "chat",
            },
        )
        assert chat_res.status_code == 201

        # Run AI Pipeline
        analyze_res = client.post(f"/api/v1/cases/{case_id}/analyze")
        assert analyze_res.status_code == 200

        return case_id
    finally:
        AIProviderFactory.set_override_provider(None)

# 1. Test Generate Bank Dispute Draft
def test_generate_bank_dispute_draft(client: TestClient, analyzed_case_id: str):
    res = client.get(f"/api/v1/cases/{analyzed_case_id}/reports")
    assert res.status_code == 200
    reports = res.json()
    bank_rep = next((r for r in reports if r["report_type"] == "bank_dispute"), None)
    assert bank_rep is not None
    assert "dispute" in bank_rep["title"].lower() or "unauthorized" in bank_rep["title"].lower()
    assert len(bank_rep["content_markdown"]) > 50
    assert bank_rep["approval_status"] == "draft"
    assert bank_rep["approved_at"] is None

# 2. Test Generate Cybercrime Complaint Draft
def test_generate_cybercrime_complaint_draft(client: TestClient, analyzed_case_id: str):
    res = client.get(f"/api/v1/cases/{analyzed_case_id}/reports")
    assert res.status_code == 200
    reports = res.json()
    cyber_rep = next((r for r in reports if r["report_type"] == "cybercrime_complaint"), None)
    assert cyber_rep is not None
    assert "cyber" in cyber_rep["title"].lower() or "1930" in cyber_rep["title"].lower()
    assert len(cyber_rep["content_markdown"]) > 50
    assert cyber_rep["approval_status"] == "draft"

# 3. Test Generate Emergency Security Advisory
def test_generate_emergency_security_advisory(client: TestClient, analyzed_case_id: str):
    res = client.get(f"/api/v1/cases/{analyzed_case_id}/reports")
    assert res.status_code == 200
    reports = res.json()
    sec_rep = next((r for r in reports if r["report_type"] == "security_advisory"), None)
    assert sec_rep is not None
    assert "advisory" in sec_rep["title"].lower() or "containment" in sec_rep["title"].lower()
    assert len(sec_rep["content_markdown"]) > 30

# 4. Test Retrieve Reports
def test_retrieve_reports(client: TestClient, analyzed_case_id: str):
    res = client.get(f"/api/v1/cases/{analyzed_case_id}/reports")
    assert res.status_code == 200
    reports = res.json()
    assert len(reports) == 3
    types = {r["report_type"] for r in reports}
    assert types == {"bank_dispute", "cybercrime_complaint", "security_advisory"}

# 5. Test Edit a Draft
def test_edit_draft(client: TestClient, analyzed_case_id: str):
    res = client.get(f"/api/v1/cases/{analyzed_case_id}/reports")
    report = res.json()[0]
    report_id = report["id"]

    new_title = "UPDATED: Urgent Bank Chargeback Request — INR 95,000"
    new_body = "Formal dispute declaration with corrected transaction timestamp."
    new_email = "disputes-team@hdfcbank.com"

    patch_res = client.patch(
        f"/api/v1/cases/{analyzed_case_id}/reports/{report_id}",
        json={
            "title": new_title,
            "content_markdown": new_body,
            "recipient_email": new_email,
        },
    )
    assert patch_res.status_code == 200
    updated = patch_res.json()
    assert updated["title"] == new_title
    assert updated["content_markdown"] == new_body
    assert updated["recipient_email"] == new_email

# 6. Test Save Edited Draft
def test_save_edited_draft(client: TestClient, analyzed_case_id: str):
    res = client.get(f"/api/v1/cases/{analyzed_case_id}/reports")
    report = res.json()[0]
    report_id = report["id"]

    client.patch(
        f"/api/v1/cases/{analyzed_case_id}/reports/{report_id}",
        json={"title": "Custom Title Saved"},
    )

    get_single = client.get(f"/api/v1/cases/{analyzed_case_id}/reports/{report_id}")
    assert get_single.status_code == 200
    assert get_single.json()["title"] == "Custom Title Saved"

# 7. Test Approve a Report
def test_approve_report(client: TestClient, analyzed_case_id: str):
    res = client.get(f"/api/v1/cases/{analyzed_case_id}/reports")
    report = res.json()[0]
    report_id = report["id"]

    approve_res = client.post(
        f"/api/v1/cases/{analyzed_case_id}/reports/{report_id}/approve",
        json={"recipient_email": "fraud-nodal@bank.com"},
    )
    assert approve_res.status_code == 200
    approved = approve_res.json()
    assert approved["approval_status"] == "approved"
    assert approved["approved_at"] is not None
    assert approved["recipient_email"] == "fraud-nodal@bank.com"

# 8. Test Cannot Send an Unapproved Report (Strict Safety Rule)
def test_cannot_send_unapproved_report(client: TestClient, analyzed_case_id: str, mock_email: MockEmailProvider):
    res = client.get(f"/api/v1/cases/{analyzed_case_id}/reports")
    report = res.json()[0]
    assert report["approval_status"] == "draft"

    send_res = client.post(
        f"/api/v1/cases/{analyzed_case_id}/reports/{report['id']}/send",
        json={"recipient_email": "nodal@bank.com"},
    )
    # STRICT SAFETY CHECK: Must reject with 400
    assert send_res.status_code == 400
    assert "must be explicitly approved before sending" in send_res.json()["detail"].lower()
    assert len(mock_email.sent_messages) == 0

# 9. Test Can Send an Approved Report
def test_can_send_approved_report(client: TestClient, analyzed_case_id: str, mock_email: MockEmailProvider):
    res = client.get(f"/api/v1/cases/{analyzed_case_id}/reports")
    report = res.json()[0]
    report_id = report["id"]

    # 1. Approve
    app_res = client.post(f"/api/v1/cases/{analyzed_case_id}/reports/{report_id}/approve")
    assert app_res.status_code == 200

    # 2. Send
    send_res = client.post(
        f"/api/v1/cases/{analyzed_case_id}/reports/{report_id}/send",
        json={"recipient_email": "recovery-officer@bank.com", "attach_passport_pdf": False},
    )
    assert send_res.status_code == 200
    sent_data = send_res.json()
    assert sent_data["approval_status"] == "sent"
    assert sent_data["sent_at"] is not None
    assert len(mock_email.sent_messages) == 1
    assert mock_email.sent_messages[0]["to"] == "recovery-officer@bank.com"

# 10. Test Email Provider Success
def test_email_provider_success(client: TestClient, analyzed_case_id: str, mock_email: MockEmailProvider):
    res = client.get(f"/api/v1/cases/{analyzed_case_id}/reports")
    report = res.json()[1]

    client.post(f"/api/v1/cases/{analyzed_case_id}/reports/{report['id']}/approve")
    send_res = client.post(
        f"/api/v1/cases/{analyzed_case_id}/reports/{report['id']}/send",
        json={"recipient_email": "complaints@cybercrime.gov.in"},
    )
    assert send_res.status_code == 200
    assert len(mock_email.sent_messages) == 1
    assert mock_email.sent_messages[0]["to"] == "complaints@cybercrime.gov.in"

# 11. Test Email Provider Failure
def test_email_provider_failure(client: TestClient, analyzed_case_id: str, mock_email: MockEmailProvider):
    res = client.get(f"/api/v1/cases/{analyzed_case_id}/reports")
    report = res.json()[0]
    client.post(f"/api/v1/cases/{analyzed_case_id}/reports/{report['id']}/approve")

    # Simulate provider failure
    mock_email.simulate_failure = True
    mock_email.failure_message = "SMTP Connection Timed Out"

    send_res = client.post(
        f"/api/v1/cases/{analyzed_case_id}/reports/{report['id']}/send",
        json={"recipient_email": "victim@bank.com"},
    )
    assert send_res.status_code == 502
    assert "SMTP Connection Timed Out" in send_res.json()["detail"]

    # Verify report status transitioned to failed
    get_rep = client.get(f"/api/v1/cases/{analyzed_case_id}/reports/{report['id']}")
    assert get_rep.json()["approval_status"] == "failed"
    assert "SMTP Connection Timed Out" in get_rep.json()["error_message"]

# 12. Test Correct Status Transitions
def test_correct_status_transitions(client: TestClient, analyzed_case_id: str, mock_email: MockEmailProvider):
    res = client.get(f"/api/v1/cases/{analyzed_case_id}/reports")
    report = res.json()[0]
    report_id = report["id"]

    # Initial: draft
    assert report["approval_status"] == "draft"

    # Transition to reviewed
    rev_res = client.patch(
        f"/api/v1/cases/{analyzed_case_id}/reports/{report_id}",
        json={"approval_status": "reviewed"},
    )
    assert rev_res.json()["approval_status"] == "reviewed"

    # Transition to approved
    app_res = client.post(f"/api/v1/cases/{analyzed_case_id}/reports/{report_id}/approve")
    assert app_res.json()["approval_status"] == "approved"

    # Edit approved report -> must reset status to draft to prevent silent modifications
    edit_res = client.patch(
        f"/api/v1/cases/{analyzed_case_id}/reports/{report_id}",
        json={"title": "Modified after approval"},
    )
    assert edit_res.json()["approval_status"] == "draft"
    assert edit_res.json()["approved_at"] is None

    # Re-approve and send
    client.post(f"/api/v1/cases/{analyzed_case_id}/reports/{report_id}/approve")
    send_res = client.post(
        f"/api/v1/cases/{analyzed_case_id}/reports/{report_id}/send",
        json={"recipient_email": "test@demo.com"},
    )
    assert send_res.json()["approval_status"] == "sent"

# 13. Test Case Not Found
def test_case_not_found(client: TestClient):
    res = client.get("/api/v1/cases/non-existent-uuid/reports")
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()

# 14. Test Analysis Not Ready
def test_analysis_not_ready(client: TestClient):
    # Create empty case without running analysis
    create_res = client.post("/api/v1/cases", json={"title": "Unanalyzed Case"})
    case_id = create_res.json()["id"]

    res = client.get(f"/api/v1/cases/{case_id}/reports")
    assert res.status_code == 400
    assert "analysis is not ready" in res.json()["detail"].lower()

# 15. Test Invalid Report ID
def test_invalid_report_id(client: TestClient, analyzed_case_id: str):
    res = client.get(f"/api/v1/cases/{analyzed_case_id}/reports/invalid-uuid-1234")
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()

# 16. Test Cannot Modify a SENT Report
def test_cannot_modify_sent_report(client: TestClient, analyzed_case_id: str, mock_email: MockEmailProvider):
    res = client.get(f"/api/v1/cases/{analyzed_case_id}/reports")
    report = res.json()[0]
    report_id = report["id"]

    # Approve and send
    client.post(f"/api/v1/cases/{analyzed_case_id}/reports/{report_id}/approve")
    client.post(
        f"/api/v1/cases/{analyzed_case_id}/reports/{report_id}/send",
        json={"recipient_email": "dispatched@bank.com"},
    )

    # Attempting to PATCH a sent report must be rejected
    patch_res = client.patch(
        f"/api/v1/cases/{analyzed_case_id}/reports/{report_id}",
        json={"title": "Sneaky edit after sending"},
    )
    assert patch_res.status_code == 400
    assert "already been sent" in patch_res.json()["detail"].lower()

    # Attempting to re-approve a sent report must also be rejected
    app_res = client.post(f"/api/v1/cases/{analyzed_case_id}/reports/{report_id}/approve")
    assert app_res.status_code == 400
    assert "already been sent" in app_res.json()["detail"].lower()

# 17. Test API Keys are Not Returned
def test_api_keys_not_returned(client: TestClient, analyzed_case_id: str):
    res = client.get(f"/api/v1/cases/{analyzed_case_id}/reports")
    assert res.status_code == 200
    content_str = res.text
    assert "RESEND_API_KEY" not in content_str
    assert "GEMINI_API_KEY" not in content_str
    assert "OPENAI_API_KEY" not in content_str

# 18. Test PDF Attachment Works if Enabled
def test_pdf_attachment_works(client: TestClient, analyzed_case_id: str, mock_email: MockEmailProvider):
    res = client.get(f"/api/v1/cases/{analyzed_case_id}/reports")
    report = res.json()[0]
    client.post(f"/api/v1/cases/{analyzed_case_id}/reports/{report['id']}/approve")

    send_res = client.post(
        f"/api/v1/cases/{analyzed_case_id}/reports/{report['id']}/send",
        json={"recipient_email": "dossier@bank.com", "attach_passport_pdf": True},
    )
    assert send_res.status_code == 200
    assert len(mock_email.sent_messages) == 1
    sent_msg = mock_email.sent_messages[0]
    assert sent_msg["attachment"] is not None
    assert sent_msg["attachment"].endswith(".pdf")
    assert sent_msg["attachment_size_bytes"] > 1000

# 19. Test Provenance Remains Intact
def test_provenance_remains_intact(client: TestClient, analyzed_case_id: str):
    res = client.get(f"/api/v1/cases/{analyzed_case_id}/reports")
    report = res.json()[0]
    report_id = report["id"]

    # Provenance citations exist initially
    initial_refs = report["evidence_references"]
    assert len(initial_refs) > 0

    # Edit the report
    client.patch(
        f"/api/v1/cases/{analyzed_case_id}/reports/{report_id}",
        json={"title": "Edited subject"},
    )

    # Provenance citations must still be intact
    get_res = client.get(f"/api/v1/cases/{analyzed_case_id}/reports/{report_id}")
    assert get_res.json()["evidence_references"] == initial_refs
