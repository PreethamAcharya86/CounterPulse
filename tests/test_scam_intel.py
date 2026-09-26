import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.ai.mock import MockProvider
from backend.app.services.ai.factory import AIProviderFactory
from backend.app.models.case import Case
from backend.app.models.indicator import Indicator

@pytest.fixture
def mock_ai():
    mock = MockProvider()
    AIProviderFactory.set_override_provider(mock)
    yield mock
    AIProviderFactory.set_override_provider(None)

@pytest.fixture
def test_case_id(client: TestClient) -> str:
    res = client.post(
        "/api/v1/cases",
        json={
            "title": "Scam Intelligence Investigation",
            "description": "Suspects impersonated cyber police demanding immediate deposit.",
        },
    )
    assert res.status_code == 201
    return res.json()["id"]

SAMPLE_CONVERSATION = """
[10:01] Suspect: This is DCP Vikram from Delhi Cyber Cell. You are under immediate digital arrest.
[10:02] Suspect: Call our verification line immediately at +91 98765 43210.
[10:03] Victim: Sir what is this about? I have not committed any crime.
[10:04] Suspect: Your Aadhaar was used in illegal narcotics shipping. Transfer INR 85,000 security deposit to clearance.vault@icici now.
[10:05] Suspect: Verification portal is https://narcotics-clearance-desk.gov-fraud.in/verify with UTR: UTR98273645120.
[10:06] Suspect: Contact officer directly at investigator.cyber@cell-notice.org.
"""

# 1. Valid conversation analysis
def test_valid_conversation_analysis(client: TestClient, test_case_id: str, mock_ai: MockProvider):
    res = client.post(
        f"/api/v1/cases/{test_case_id}/scam-intelligence/analyze",
        json={"conversation_text": SAMPLE_CONVERSATION},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["case_id"] == test_case_id
    assert len(data["indicators"]) > 0
    assert data["scam_type"] is not None
    assert data["threat_assessment"] is not None
    assert "investigative artifacts" in data["disclaimer"].lower()

# 2. Extracted indicators and categorization
def test_extracted_indicators_and_categories(client: TestClient, test_case_id: str, mock_ai: MockProvider):
    res = client.post(
        f"/api/v1/cases/{test_case_id}/scam-intelligence/analyze",
        json={"conversation_text": SAMPLE_CONVERSATION},
    )
    assert res.status_code == 200
    data = res.json()

    # Phone number
    assert any("+91 98765 43210" in p["value"] for p in data["phone_numbers"])
    # UPI ID
    assert any("clearance.vault@icici" in u["value"] for u in data["upi_ids"])
    # URL
    assert any("narcotics-clearance-desk" in u["value"] for u in data["urls"])
    # Email
    assert any("investigator.cyber@cell-notice.org" in e["value"] for e in data["emails"])
    # Amount
    assert any("85,000" in a["value"] for a in data["financial_amounts"])
    # Transaction ref
    assert any("UTR98273645120" in t["value"] for t in data["transaction_references"])

# 3. Provenance preservation
def test_provenance_preservation(client: TestClient, test_case_id: str, mock_ai: MockProvider):
    res = client.post(
        f"/api/v1/cases/{test_case_id}/scam-intelligence/analyze",
        json={"conversation_text": SAMPLE_CONVERSATION},
    )
    assert res.status_code == 200
    data = res.json()

    for item in data["indicators"]:
        assert item["source_reference"] is not None
        assert "Message" in item["source_reference"] or "Extraction" in item["source_reference"]
        assert item["confidence"] in ("high", "medium", "low")

# 4. Unverified indicator status (No criminal accusation)
def test_unverified_indicator_status(client: TestClient, test_case_id: str, mock_ai: MockProvider):
    res = client.post(
        f"/api/v1/cases/{test_case_id}/scam-intelligence/analyze",
        json={"conversation_text": SAMPLE_CONVERSATION},
    )
    assert res.status_code == 200
    data = res.json()

    # Phone, UPI, URL, email MUST be unverified
    for p in data["phone_numbers"]:
        assert p["verification_status"].lower() == "unverified"
    for u in data["upi_ids"]:
        assert u["verification_status"].lower() == "unverified"

# 5. Analyze selected message focus
def test_analyze_selected_message(client: TestClient, test_case_id: str, mock_ai: MockProvider):
    # Only analyze Message #2 (Phone number message)
    res = client.post(
        f"/api/v1/cases/{test_case_id}/scam-intelligence/analyze",
        json={
            "conversation_text": SAMPLE_CONVERSATION,
            "selected_message_index": 2,
        },
    )
    assert res.status_code == 200
    data = res.json()
    # Message #2 has phone number but NOT the UPI from Message #4
    assert any("+91 98765 43210" in p["value"] for p in data["phone_numbers"])
    assert not any("clearance.vault@icici" in u["value"] for u in data["upi_ids"])
    for p in data["phone_numbers"]:
        assert p["source_reference"] == "Message #2"

# 6. Missing case handling
def test_missing_case_handling(client: TestClient, mock_ai: MockProvider):
    res = client.post(
        "/api/v1/cases/00000000-0000-0000-0000-000000000000/scam-intelligence/analyze",
        json={"conversation_text": SAMPLE_CONVERSATION},
    )
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()

# 7. Missing evidence and empty conversation
def test_missing_evidence_and_empty_conversation(client: TestClient, test_case_id: str):
    res = client.post(
        f"/api/v1/cases/{test_case_id}/scam-intelligence/analyze",
        json={},
    )
    assert res.status_code == 400
    assert "no conversation text" in res.json()["detail"].lower()

# 8. Invalid evidence ID
def test_invalid_evidence_id(client: TestClient, test_case_id: str):
    res = client.post(
        f"/api/v1/cases/{test_case_id}/scam-intelligence/analyze",
        json={"evidence_id": "EV-NONEXISTENT"},
    )
    assert res.status_code == 404

# 9. Case Integration: Add indicators to case
def test_add_indicators_to_case(client: TestClient, test_case_id: str, mock_ai: MockProvider):
    # Analyze conversation
    an_res = client.post(
        f"/api/v1/cases/{test_case_id}/scam-intelligence/analyze",
        json={"conversation_text": SAMPLE_CONVERSATION},
    )
    assert an_res.status_code == 200
    indicators = an_res.json()["indicators"]
    assert len(indicators) > 0

    # Add to case
    add_res = client.post(
        f"/api/v1/cases/{test_case_id}/scam-intelligence/add-to-case",
        json={"indicators": indicators},
    )
    assert add_res.status_code == 200
    add_data = add_res.json()
    assert add_data["added_count"] > 0
    assert add_data["total_case_indicators"] >= add_data["added_count"]

    # Verify indicators are now part of the case
    case_res = client.get(f"/api/v1/cases/{test_case_id}/scam-intelligence")
    assert case_res.status_code == 200
    c_data = case_res.json()
    assert c_data["total_indicators"] == add_data["total_case_indicators"]
    assert any("+91 98765 43210" in p["value"] for p in c_data["phone_numbers"])

# 10. Duplicate prevention on add-to-case
def test_duplicate_prevention_on_add_to_case(client: TestClient, test_case_id: str, mock_ai: MockProvider):
    an_res = client.post(
        f"/api/v1/cases/{test_case_id}/scam-intelligence/analyze",
        json={"conversation_text": SAMPLE_CONVERSATION},
    )
    indicators = an_res.json()["indicators"]

    # First add
    add1 = client.post(
        f"/api/v1/cases/{test_case_id}/scam-intelligence/add-to-case",
        json={"indicators": indicators},
    )
    added_first = add1.json()["added_count"]
    assert added_first > 0

    # Second add with identical indicators
    add2 = client.post(
        f"/api/v1/cases/{test_case_id}/scam-intelligence/add-to-case",
        json={"indicators": indicators},
    )
    assert add2.status_code == 200
    # Must skip all duplicates
    assert add2.json()["added_count"] == 0
    assert add2.json()["skipped_duplicates_count"] == len(indicators)

# 11. No hardcoded output mapping: Different conversation yields different intelligence
def test_no_hardcoded_output_mapping(client: TestClient, test_case_id: str, mock_ai: MockProvider):
    custom_conv = """
    [01:00] Caller: SBI Card Services. Your card ending in 4920 is blocked.
    [01:01] Caller: Call supervisor Priya Sharma at 9123456789.
    [01:02] Caller: Send unblock processing fee of ₹12,500 to sbi.unblock@paytm.
    [01:03] Caller: Check portal https://sbi-card-reactivate.cc/secure
    """
    res = client.post(
        f"/api/v1/cases/{test_case_id}/scam-intelligence/analyze",
        json={"conversation_text": custom_conv},
    )
    assert res.status_code == 200
    data = res.json()

    # Dynamic extraction must match custom conversation, NOT the previous sample!
    assert any("9123456789" in p["value"] for p in data["phone_numbers"])
    assert any("sbi.unblock@paytm" in u["value"] for u in data["upi_ids"])
    assert any("sbi-card-reactivate.cc" in u["value"] for u in data["urls"])
    assert any("12,500" in a["value"] for a in data["financial_amounts"])
    # Must NOT have values from the other conversation
    assert not any("clearance.vault@icici" in u["value"] for u in data["upi_ids"])

# 12. AI provider failure graceful fallback
def test_ai_provider_failure_graceful_fallback(client: TestClient, test_case_id: str):
    failing_ai = MockProvider(simulate_failure=True)
    AIProviderFactory.set_override_provider(failing_ai)

    try:
        res = client.post(
            f"/api/v1/cases/{test_case_id}/scam-intelligence/analyze",
            json={"conversation_text": SAMPLE_CONVERSATION},
        )
        assert res.status_code == 200
        data = res.json()
        # Even with AI failure, regex indicators MUST be preserved!
        assert len(data["phone_numbers"]) > 0
        assert len(data["upi_ids"]) > 0
        assert len(data["urls"]) > 0
    finally:
        AIProviderFactory.set_override_provider(None)

# 13. Analyze with add_to_case=True
def test_analyze_with_add_to_case_flag(client: TestClient, test_case_id: str, mock_ai: MockProvider):
    res = client.post(
        f"/api/v1/cases/{test_case_id}/scam-intelligence/analyze",
        json={
            "conversation_text": SAMPLE_CONVERSATION,
            "add_to_case": True,
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["added_to_case_count"] > 0

    # Verify directly in case indicators endpoint
    case_res = client.get(f"/api/v1/cases/{test_case_id}/scam-intelligence")
    assert case_res.status_code == 200
    assert case_res.json()["total_indicators"] >= data["added_to_case_count"]
