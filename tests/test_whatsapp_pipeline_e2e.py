import os
import pytest
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

def generate_chat_screenshot(lines: list) -> bytes:
    img = Image.new("RGB", (800, 600), color=(18, 24, 38))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 20)
    except Exception:
        font = ImageFont.load_default(size=20)
    draw.text((40, 20), "WHATSAPP SECURE MESSAGE", fill=(37, 211, 102), font=font)
    y = 75
    for line in lines:
        draw.text((40, y), line, fill=(240, 240, 240), font=font)
        y += 50
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

def test_whatsapp_capture_e2e_isolation_and_scam_intel(client):
    """
    Requirement 10 & 13:
    Full End-to-End Pipeline Verification with Unique Data:
    NEW CASE -> CAPTURE SCREENSHOT -> EVIDENCE -> OCR -> GEMINI MULTIMODAL -> PERSIST -> SCAM INTEL -> VOICE -> ISOLATION
    """
    # =========================================================================
    # 1. CREATE CASE A
    # =========================================================================
    case_a_resp = client.post("/api/v1/cases", json={
        "title": "Fresh Investigation Case 8472",
        "description": "WhatsApp extortion verification case",
    })
    assert case_a_resp.status_code == 201
    case_a = case_a_resp.json()
    case_a_id = case_a["id"]
    assert case_a_id

    # Generate unique screenshot for Case A
    # Unique values requested by user:
    # Amount: ₹7,321
    # UPI: counterpulse8472@upi
    # Phone: +91 9000012345
    # URL: https://case8472.example
    img_bytes_a = generate_chat_screenshot([
        "[11:15] Unknown Officer: Pay urgent verification fee INR 7,321 (₹7,321) immediately.",
        "[11:16] Officer: Send payment to UPI ID: counterpulse8472@upi to unblock account.",
        "[11:17] Officer: Call official helpline +91 9000012345 right now.",
        "[11:18] Officer: Check status online at https://case8472.example",
    ])

    # Upload evidence to Case A
    upload_a_resp = client.post(
        f"/api/v1/cases/{case_a_id}/evidence",
        files={"file": ("whatsapp_evidence_a.png", img_bytes_a, "image/png")},
        data={"evidence_type": "image"},
    )
    assert upload_a_resp.status_code == 201
    ev_a = upload_a_resp.json()
    assert ev_a["case_id"] == case_a_id

    # =========================================================================
    # 2. VERIFY SCAM INTELLIGENCE RETRIEVAL FOR CASE A
    # =========================================================================
    intel_a_resp = client.get(f"/api/v1/cases/{case_a_id}/scam-intelligence")
    assert intel_a_resp.status_code == 200
    intel_a = intel_a_resp.json()
    assert intel_a["case_id"] == case_a_id

    # Verify extracted indicators contain the unique values
    inds_a = intel_a.get("indicators", [])
    ind_values_a = [i["value"].lower() for i in inds_a]
    
    assert any("counterpulse8472@upi" in val for val in ind_values_a), f"UPI not found in {ind_values_a}"
    assert any("9000012345" in val for val in ind_values_a), f"Phone not found in {ind_values_a}"
    assert any("case8472.example" in val for val in ind_values_a), f"URL not found in {ind_values_a}"
    
    # Verify financial loss
    financial_amounts_a = [i["value"] for i in intel_a.get("financial_amounts", [])]
    loss_a = intel_a.get("financial_loss")
    assert loss_a == 7321.0 or any("7,321" in str(v) or "7321" in str(v) for v in financial_amounts_a)

    # =========================================================================
    # 3. VERIFY VOICE COMMAND FOR CASE A
    # =========================================================================
    voice_resp = client.post(
        f"/api/v1/cases/{case_a_id}/voice/command",
        json={"transcript": "What's the UPI ID?", "synthesize": False},
    )
    assert voice_resp.status_code == 200
    voice_data = voice_resp.json()
    assert "counterpulse8472@upi" in voice_data["response_text"].lower()

    # =========================================================================
    # 4. CREATE CASE B WITH COMPLETELY DIFFERENT UNIQUE VALUES
    # =========================================================================
    case_b_resp = client.post("/api/v1/cases", json={
        "title": "Fresh Investigation Case 9999",
        "description": "Electricity fraud case",
    })
    assert case_b_resp.status_code == 201
    case_b = case_b_resp.json()
    case_b_id = case_b["id"]
    assert case_b_id != case_a_id

    img_bytes_b = generate_chat_screenshot([
        "[14:00] BESCOM Officer: Electricity bill pending payment of INR 4,567 (₹4,567).",
        "[14:01] BESCOM: Transfer immediately to UPI: bescom9999@oksbi.",
        "[14:02] BESCOM: Call support desk at +91 9845199999.",
        "[14:03] BESCOM: Download receipt at https://portal9999.test",
    ])

    upload_b_resp = client.post(
        f"/api/v1/cases/{case_b_id}/evidence",
        files={"file": ("whatsapp_evidence_b.png", img_bytes_b, "image/png")},
        data={"evidence_type": "image"},
    )
    assert upload_b_resp.status_code == 201

    # Verify Case B intelligence
    intel_b_resp = client.get(f"/api/v1/cases/{case_b_id}/scam-intelligence")
    assert intel_b_resp.status_code == 200
    intel_b = intel_b_resp.json()
    assert intel_b["case_id"] == case_b_id

    inds_b = intel_b.get("indicators", [])
    ind_values_b = [i["value"].lower() for i in inds_b]

    assert any("bescom9999@oksbi" in val for val in ind_values_b), f"UPI not found in {ind_values_b}"
    assert any("9845199999" in val for val in ind_values_b), f"Phone not found in {ind_values_b}"
    assert any("portal9999.test" in val for val in ind_values_b), f"URL not found in {ind_values_b}"

    # Verify Case B financial loss
    financial_amounts_b = [i["value"] for i in intel_b.get("financial_amounts", [])]
    loss_b = intel_b.get("financial_loss")
    assert loss_b == 4567.0 or any("4,567" in str(v) or "4567" in str(v) for v in financial_amounts_b)

    # =========================================================================
    # 5. STRICT CASE ISOLATION VERIFICATION: NO CROSS-CASE CONTAMINATION
    # =========================================================================
    # Case B MUST NOT contain any Case A indicators
    for val in ind_values_b:
        assert "counterpulse8472" not in val
        assert "9000012345" not in val
        assert "case8472.example" not in val

    # Case A MUST NOT contain any Case B indicators
    for val in ind_values_a:
        assert "bescom9999" not in val
        assert "9845199999" not in val
        assert "portal9999.test" not in val
