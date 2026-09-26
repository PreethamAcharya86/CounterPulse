import io
import pytest

def test_api_upload_image(client, sample_case, sample_image_bytes):
    """Test uploading real PNG image via multipart/form-data."""
    response = client.post(
        f"/api/v1/cases/{sample_case.id}/evidence",
        files={"file": ("screenshot.png", sample_image_bytes, "image/png")},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["case_id"] == sample_case.id
    assert data["evidence_type"] == "image"
    assert data["processing_status"] == "processed"
    assert data["file_path"].startswith("storage/")  # Safe path
    assert "95,000" in data["raw_content"] or "95000" in data["raw_content"]

def test_api_upload_pdf(client, sample_case, sample_pdf_bytes):
    """Test uploading real 2-page PDF via multipart/form-data."""
    response = client.post(
        f"/api/v1/cases/{sample_case.id}/evidence",
        files={"file": ("arrest_warrant.pdf", sample_pdf_bytes, "application/pdf")},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["evidence_type"] == "pdf"
    assert data["processing_status"] == "processed"
    assert "Page 1" in data["raw_content"]
    assert "UTR987654321098" in data["raw_content"]

def test_api_upload_text_json(client, sample_case):
    """Test uploading Bank SMS via JSON endpoint."""
    sms = "INR 85,000 debited from A/c ending 1234 on 25-SEP-26 via UPI Ref 987654321012."
    response = client.post(
        f"/api/v1/cases/{sample_case.id}/evidence/text",
        json={"text": sms, "evidence_type": "text"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["evidence_type"] == "text"
    assert data["processing_status"] == "processed"
    assert "INR 85,000" in data["raw_content"]

def test_api_upload_chat_json(client, sample_case):
    """Test uploading WhatsApp conversation export via JSON endpoint."""
    chat = (
        "[10:31] Scammer: Your phone will be disconnected.\n"
        "[10:32] Scammer: Pay ₹50,000 to keep it active."
    )
    response = client.post(
        f"/api/v1/cases/{sample_case.id}/evidence/chat",
        json={"chat_text": chat, "platform": "whatsapp"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["evidence_type"] == "chat"
    assert data["processing_status"] == "processed"
    assert "Message 1" in data["raw_content"]
    assert "Scammer" in data["raw_content"]

def test_api_upload_url_json(client, sample_case):
    """Test uploading suspicious phishing URL."""
    url = "https://trai-verification-portal.xyz/kyc"
    response = client.post(
        f"/api/v1/cases/{sample_case.id}/evidence/url",
        json={"url": url},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["evidence_type"] == "url"
    assert data["processing_status"] == "processed"
    assert "UNVERIFIED" in data["raw_content"]

def test_api_upload_audio(client, sample_case, sample_audio_bytes):
    """Test uploading audio recording. When unconfigured, it fails gracefully without fake data."""
    response = client.post(
        f"/api/v1/cases/{sample_case.id}/evidence",
        files={"file": ("call_recording.wav", sample_audio_bytes, "audio/wav")},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["evidence_type"] == "audio"
    # Status should be failed since no API key is in test environment, but not crashing!
    assert data["processing_status"] in ("failed", "processed")
    if data["processing_status"] == "failed":
        assert "Speech-to-Text provider not configured" in (data["error_message"] or "")

def test_api_reject_unsupported_file(client, sample_case):
    """Ensure executable files are rejected with 400 Bad Request."""
    response = client.post(
        f"/api/v1/cases/{sample_case.id}/evidence",
        files={"file": ("malware.exe", b"MZ...", "application/x-msdownload")},
    )
    assert response.status_code == 400
    assert "prohibited" in response.json()["detail"].lower() or "disallowed" in response.json()["detail"].lower()

def test_api_reject_oversized_file(client, sample_case):
    """Ensure files exceeding 25MB are rejected."""
    # 26MB buffer
    big_buffer = b"0" * (26 * 1024 * 1024)
    response = client.post(
        f"/api/v1/cases/{sample_case.id}/evidence",
        files={"file": ("huge.png", big_buffer, "image/png")},
    )
    assert response.status_code == 400
    assert "exceeds maximum allowed limit" in response.json()["detail"]

def test_api_list_and_get_evidence(client, sample_case, sample_image_bytes):
    """Test listing evidence for a case and fetching details by evidence ID."""
    # Create evidence
    up_res = client.post(
        f"/api/v1/cases/{sample_case.id}/evidence",
        files={"file": ("doc.png", sample_image_bytes, "image/png")},
    )
    ev_id = up_res.json()["id"]

    # List
    list_res = client.get(f"/api/v1/cases/{sample_case.id}/evidence")
    assert list_res.status_code == 200
    items = list_res.json()
    assert len(items) >= 1
    assert any(i["id"] == ev_id for i in items)

    # Get single
    get_res = client.get(f"/api/v1/evidence/{ev_id}")
    assert get_res.status_code == 200
    single = get_res.json()
    assert single["id"] == ev_id
    assert single["processing_status"] == "processed"
    assert single["normalized_data"] is not None

def test_api_process_retry(client, sample_case, sample_image_bytes):
    """Test re-triggering processing on existing evidence."""
    up_res = client.post(
        f"/api/v1/cases/{sample_case.id}/evidence",
        files={"file": ("retry_test.png", sample_image_bytes, "image/png")},
    )
    ev_id = up_res.json()["id"]

    # Call /process
    proc_res = client.post(f"/api/v1/evidence/{ev_id}/process")
    assert proc_res.status_code == 200
    pdata = proc_res.json()
    assert pdata["evidence_id"] == ev_id
    assert pdata["processing_status"] == "processed"
    assert pdata["character_count"] > 0

def test_api_live_whatsapp_streaming(client, sample_case):
    """Test live WhatsApp text ingestion endpoint from Laptop 5 companion."""
    # 1. Unauthorized chunk rejected with 403 Forbidden
    unauth_res = client.post(
        "/api/v1/live/text",
        json={
            "case_id": sample_case.id,
            "chunk_text": "Transfer money now",
            "user_authorized": False,
        }
    )
    assert unauth_res.status_code == 403

    # 2. Authorized chunk accepted
    auth_res = client.post(
        "/api/v1/live/text",
        json={
            "case_id": sample_case.id,
            "chunk_text": "Transfer ₹95,000 to fraud@upi immediately",
            "user_authorized": True,
            "sender": "+919876543210",
        }
    )
    assert auth_res.status_code == 200
    live_ev = auth_res.json()
    assert live_ev["evidence_type"] == "chat"
    assert live_ev["processing_status"] == "processed"
    assert "+919876543210" in live_ev["raw_content"]
