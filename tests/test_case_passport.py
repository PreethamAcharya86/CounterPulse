import io
import pytest
from pypdf import PdfReader
from sqlalchemy.orm import Session

from backend.app.models.case import Case
from backend.app.models.evidence import Evidence
from backend.app.schemas.passport import (
    FraudCasePassport,
    IncidentPassportInfo,
    FinancialPassportInfo,
    TimelinePassportItem,
    IndicatorPassportItem,
    CompromisePassportItem,
)
from backend.app.services.ai.mock import MockProvider
from backend.app.services.orchestrator import AIOrchestrator
from backend.app.services.passport_service import (
    PassportService,
    CaseNotFoundError,
    AnalysisNotReadyError,
    passport_service,
)
from backend.app.services.pdf_service import pdf_report_service


@pytest.fixture
def analyzed_case(client) -> str:
    """
    Creates a real case, uploads authentic demo evidence text,
    runs full AI orchestration with deterministic mock provider,
    and returns the case ID in passport_ready state.
    """
    mock = MockProvider()
    from backend.app.services.ai.factory import AIProviderFactory
    AIProviderFactory.set_override_provider(mock)

    try:
        # 1. Create Case
        create_res = client.post(
            "/api/v1/cases",
            json={
                "title": "Digital Arrest Cyber Extortion Case",
                "description": "Victim extorted under threat of fake CBI digital arrest warrant.",
            },
        )
        assert create_res.status_code == 201
        case_id = create_res.json()["id"]

        # 2. Upload Bank SMS Evidence
        sms_res = client.post(
            f"/api/v1/cases/{case_id}/evidence/text",
            json={
                "text": "INR 95,000.0 debited from A/c ending 4321 on 26-SEP-26 via UPI Ref 987654321012 to clearing95@okhdfcbank. Available balance: INR 4,210.50.",
                "evidence_type": "text",
            },
        )
        assert sms_res.status_code == 201

        # 3. Upload WhatsApp Chat Evidence
        chat_res = client.post(
            f"/api/v1/cases/{case_id}/evidence/chat",
            json={
                "chat_text": (
                    "[10:00] Inspector Sharma: You are under digital arrest by CBI order.\n"
                    "[10:05] Inspector Sharma: Transfer penalty to clearing95@okhdfcbank or face immediate arrest.\n"
                    "[10:15] Victim: I have transferred ₹95,000.\n"
                    "[10:20] Inspector Sharma: Download AnyDesk APK from https://cbi-clearing-portal.gov.in/verify"
                ),
                "platform": "whatsapp",
            },
        )
        assert chat_res.status_code == 201

        # 4. Trigger Real AI Incident Analysis
        analyze_res = client.post(f"/api/v1/cases/{case_id}/analyze")
        assert analyze_res.status_code == 200

        yield case_id
    finally:
        AIProviderFactory.set_override_provider(None)



# -------------------------------------------------------------
# 1. Passport Generation with Valid CaseIntelligence
# -------------------------------------------------------------
def test_passport_generation_with_valid_case_intelligence(client, analyzed_case):
    """Verify passport generation against real dynamic CaseIntelligence."""
    res = client.get(f"/api/v1/cases/{analyzed_case}/passport")
    assert res.status_code == 200
    data = res.json()

    assert data["case_id"] == analyzed_case
    assert data["status"] in ("passport_ready", "action_pending", "resolved")
    assert "incident" in data
    assert "financial" in data
    assert "timeline" in data
    assert "indicators" in data
    assert "compromise" in data
    assert "immediate_actions" in data
    assert len(data["immediate_actions"]) > 0


# -------------------------------------------------------------
# 2. Passport Preserves Case ID
# -------------------------------------------------------------
def test_passport_preserves_case_id(client, analyzed_case):
    """Verify passport strictly preserves the case ID."""
    res = client.get(f"/api/v1/cases/{analyzed_case}/passport")
    assert res.status_code == 200
    assert res.json()["case_id"] == analyzed_case


# -------------------------------------------------------------
# 3. Passport Preserves Incident Classification
# -------------------------------------------------------------
def test_passport_preserves_incident_classification(client, analyzed_case):
    """Verify scam category, severity, loss, and summary are preserved."""
    res = client.get(f"/api/v1/cases/{analyzed_case}/passport")
    assert res.status_code == 200
    data = res.json()

    incident = data["incident"]
    assert incident["incident_type"]
    assert incident["category"]
    assert incident["severity"] in ("critical", "high", "medium", "low")
    assert incident["summary"]
    assert len(incident["summary"]) > 20

    financial = data["financial"]
    assert financial["currency"] == "INR"
    assert financial["loss"] is not None
    assert financial["loss"] > 0


# -------------------------------------------------------------
# 4. Passport Preserves Timeline
# -------------------------------------------------------------
def test_passport_preserves_timeline(client, analyzed_case):
    """Verify chronological milestones are preserved in the timeline."""
    res = client.get(f"/api/v1/cases/{analyzed_case}/passport")
    assert res.status_code == 200
    timeline = res.json()["timeline"]

    assert len(timeline) >= 2
    for event in timeline:
        assert event["timestamp"]
        assert event["event_description"]
        assert "confidence" in event


# -------------------------------------------------------------
# 5. Passport Preserves Indicators
# -------------------------------------------------------------
def test_passport_preserves_indicators(client, analyzed_case):
    """Verify extracted indicators contain value, type, and verification status."""
    res = client.get(f"/api/v1/cases/{analyzed_case}/passport")
    assert res.status_code == 200
    indicators = res.json()["indicators"]

    assert len(indicators) > 0
    indicator_types = {ind["indicator_type"] for ind in indicators}
    assert any(t in indicator_types for t in ("upi_id", "phone_number", "url", "transaction_id", "suspect_name"))

    for ind in indicators:
        assert ind["value"]
        assert ind["confidence"] in ("high", "medium", "low")
        assert ind["verification_status"] in ("supported", "possible", "unverified", "not_found")


# -------------------------------------------------------------
# 6. Passport Preserves Evidence Provenance
# -------------------------------------------------------------
def test_passport_preserves_evidence_provenance(client, analyzed_case):
    """Verify provenance linking each indicator and timeline fact back to source evidence."""
    res = client.get(f"/api/v1/cases/{analyzed_case}/passport")
    assert res.status_code == 200
    data = res.json()

    # Timeline provenance
    timeline = data["timeline"]
    provenance_found = any(t.get("source_evidence_id") is not None for t in timeline)
    assert provenance_found, "Expected at least one timeline event with source_evidence_id"

    # Indicators provenance
    indicators = data["indicators"]
    ind_provenance_found = any(i.get("source_evidence_id") is not None for i in indicators)
    assert ind_provenance_found, "Expected at least one indicator with source_evidence_id"

    # Evidence items summary
    evidence_items = data.get("evidence_items", [])
    assert len(evidence_items) >= 2
    for ev in evidence_items:
        assert ev["evidence_id"].startswith("EV-")
        assert ev["processing_status"] == "processed"


# -------------------------------------------------------------
# 7. Passport Preserves Compromise Assessment
# -------------------------------------------------------------
def test_passport_preserves_compromise_assessment(client, analyzed_case):
    """Verify compromise assessments maintain category, risk level, details, and action."""
    res = client.get(f"/api/v1/cases/{analyzed_case}/passport")
    assert res.status_code == 200
    compromise = res.json()["compromise"]

    assert len(compromise) > 0
    for comp in compromise:
        assert comp["category"]
        assert comp["risk_level"]
        assert comp["details"]
        assert comp["recommended_action"]


# -------------------------------------------------------------
# 8. Missing Case Returns Appropriate Error (404)
# -------------------------------------------------------------
def test_missing_case_returns_appropriate_error(client):
    """Verify requesting passport or PDF for a non-existent case returns 404."""
    fake_id = "non-existent-case-uuid-99999"

    # Passport JSON endpoint
    res_json = client.get(f"/api/v1/cases/{fake_id}/passport")
    assert res_json.status_code == 404
    assert f"'{fake_id}' not found" in res_json.json()["detail"]

    # PDF endpoint
    res_pdf = client.get(f"/api/v1/cases/{fake_id}/passport/pdf")
    assert res_pdf.status_code == 404
    assert f"'{fake_id}' not found" in res_pdf.json()["detail"]


# -------------------------------------------------------------
# 9. Case Without Completed Analysis Handled Correctly (400)
# -------------------------------------------------------------
def test_case_without_completed_analysis_handled_correctly(client):
    """Verify a case in 'intake' status without intelligence returns clean 400 error."""
    create_res = client.post(
        "/api/v1/cases",
        json={"title": "Unanalyzed Case", "description": "Fresh intake"},
    )
    assert create_res.status_code == 201
    case_id = create_res.json()["id"]

    res = client.get(f"/api/v1/cases/{case_id}/passport")
    assert res.status_code == 400
    assert "not ready" in res.json()["detail"].lower()

    pdf_res = client.get(f"/api/v1/cases/{case_id}/passport/pdf")
    assert pdf_res.status_code == 400
    assert "not ready" in pdf_res.json()["detail"].lower()


# -------------------------------------------------------------
# 10. PDF Generation Succeeds
# -------------------------------------------------------------
def test_pdf_generation_succeeds():
    """Verify ReportLab PDF generation builds valid PDF binary bytes."""
    passport = FraudCasePassport(
        case_id="case-unit-test-01",
        title="Unit Test Phishing Incident",
        status="passport_ready",
        incident=IncidentPassportInfo(
            incident_type="Financial Fraud",
            category="UPI Phishing",
            severity="high",
            summary="Victim received a malicious payment collection request.",
            modus_operandi="Attacker masqueraded as electricity department agent.",
        ),
        financial=FinancialPassportInfo(loss=45000.0, currency="INR"),
        timeline=[
            TimelinePassportItem(timestamp="2026-09-26 10:00", event_description="Received SMS notice"),
            TimelinePassportItem(timestamp="2026-09-26 10:15", event_description="Transferred money via UPI"),
        ],
        indicators=[
            IndicatorPassportItem(indicator_type="upi_id", value="fraud@paytm", confidence="high", verification_status="supported"),
        ],
        compromise=[
            CompromisePassportItem(
                category="banking",
                risk_level="CONFIRMED",
                details="Debit transaction executed.",
                recommended_action="Block UPI handle immediately.",
            )
        ],
        immediate_actions=["Call 1930 within the Golden Hour window.", "Dispute transaction with bank."],
    )

    pdf_bytes = pdf_report_service.generate_passport_pdf(passport)
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 1000
    assert pdf_bytes.startswith(b"%PDF")


# -------------------------------------------------------------
# 11. PDF Endpoint Returns Correct Content Type & Headers
# -------------------------------------------------------------
def test_pdf_endpoint_returns_correct_content_type(client, analyzed_case):
    """Verify GET /cases/{id}/passport/pdf returns application/pdf and proper filename."""
    res = client.get(f"/api/v1/cases/{analyzed_case}/passport/pdf")
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/pdf"
    assert f'filename="CounterPulse_Case_{analyzed_case}.pdf"' in res.headers["content-disposition"]
    assert res.content.startswith(b"%PDF")


# -------------------------------------------------------------
# 12. PDF Contains Actual Case Information
# -------------------------------------------------------------
def test_pdf_contains_actual_case_information(client, analyzed_case):
    """Verify that extracted text from generated PDF includes actual case information."""
    res = client.get(f"/api/v1/cases/{analyzed_case}/passport/pdf")
    assert res.status_code == 200

    reader = PdfReader(io.BytesIO(res.content))
    assert len(reader.pages) >= 1

    full_text = " ".join([page.extract_text() for page in reader.pages])

    # Check for actual case ID
    assert analyzed_case in full_text
    # Check for platform title
    assert "COUNTERPULSE AI" in full_text
    # Check for disclaimer
    assert "human review required" in full_text.lower() or "disclaimer" in full_text.lower()


# -------------------------------------------------------------
# 13. Multiple Timeline Entries Work
# -------------------------------------------------------------
def test_multiple_timeline_entries_work():
    """Verify PDF generates cleanly with 15+ timeline milestones."""
    timeline = [
        TimelinePassportItem(
            timestamp=f"2026-09-26 10:{i:02d}",
            event_description=f"Sequential investigation event milestone #{i} detailing scam progression.",
            source_evidence_id=f"EV-{i:03d}",
        )
        for i in range(15)
    ]

    passport = FraudCasePassport(
        case_id="case-multi-timeline",
        title="Multi Timeline Test Case",
        status="passport_ready",
        incident=IncidentPassportInfo(category="Multi Milestone Scam", summary="Extensive chronological sequence."),
        financial=FinancialPassportInfo(loss=100000.0, currency="INR"),
        timeline=timeline,
    )

    pdf_bytes = pdf_report_service.generate_passport_pdf(passport)
    assert len(pdf_bytes) > 2000
    reader = PdfReader(io.BytesIO(pdf_bytes))
    assert len(reader.pages) >= 1


# -------------------------------------------------------------
# 14. Multiple Indicators Work
# -------------------------------------------------------------
def test_multiple_indicators_work():
    """Verify PDF handles 20+ diverse indicators cleanly."""
    indicators = [
        IndicatorPassportItem(
            indicator_type="phone_number" if i % 2 == 0 else "upi_id",
            value=f"+919876543{i:03d}" if i % 2 == 0 else f"target{i}@okhdfcbank",
            confidence="high",
            verification_status="supported",
            source_evidence_id="EV-001",
        )
        for i in range(20)
    ]

    passport = FraudCasePassport(
        case_id="case-multi-indicators",
        title="Multi Indicators Test Case",
        status="passport_ready",
        incident=IncidentPassportInfo(category="High Volume Indicators", summary="Syndicate indicator mapping."),
        financial=FinancialPassportInfo(loss=50000.0, currency="INR"),
        indicators=indicators,
    )

    pdf_bytes = pdf_report_service.generate_passport_pdf(passport)
    assert len(pdf_bytes) > 2000
    reader = PdfReader(io.BytesIO(pdf_bytes))
    assert len(reader.pages) >= 1


# -------------------------------------------------------------
# 15. Long Text Does Not Crash PDF Generation
# -------------------------------------------------------------
def test_long_text_does_not_crash_pdf_generation():
    """Verify PDF generator handles very long text and unwrapped URLs without crashing or overflowing."""
    very_long_summary = " ".join([
        "On September 26, the victim was subjected to an aggressive multi-hour coercive impersonation campaign."
        "The perpetrators claimed affiliation with the Supreme Court, CBI, and TRAI, asserting that a money-laundering"
        "investigation had linked the victim's Aadhaar credentials to unlawful syndicate accounts."
    ] * 20)

    very_long_url = "https://very-long-fraudulent-phishing-domain-name-with-deep-nested-path.org/verification/portal/subfolder/token?id=1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef&session=xyz987654321"

    passport = FraudCasePassport(
        case_id="case-long-text-overflow-test",
        title="Extreme Text Volume Stress Test Incident",
        status="passport_ready",
        incident=IncidentPassportInfo(
            category="Stress Test Typology",
            summary=very_long_summary,
            modus_operandi=very_long_summary,
        ),
        financial=FinancialPassportInfo(loss=2500000.0, currency="INR"),
        timeline=[
            TimelinePassportItem(
                timestamp="2026-09-26 09:00 IST",
                event_description=very_long_summary[:300],
                source_evidence_id="EV-EXTREME-01",
            )
        ],
        indicators=[
            IndicatorPassportItem(
                indicator_type="url",
                value=very_long_url,
                confidence="high",
                verification_status="supported",
                source_evidence_id="EV-EXTREME-01",
            )
        ],
        compromise=[
            CompromisePassportItem(
                category="credentials",
                risk_level="CONFIRMED",
                details=very_long_summary[:400],
                recommended_action=very_long_summary[:200],
                source_evidence_id="EV-EXTREME-01",
            )
        ],
        immediate_actions=[
            f"Step {i}: " + very_long_summary[:150] for i in range(1, 10)
        ],
    )

    pdf_bytes = pdf_report_service.generate_passport_pdf(passport)
    assert len(pdf_bytes) > 3000
    reader = PdfReader(io.BytesIO(pdf_bytes))
    # Document should cleanly break across multiple pages
    assert len(reader.pages) >= 2
