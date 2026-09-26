import pytest
from backend.app.services.evidence.image_processor import ImageProcessor
from backend.app.services.evidence.pdf_processor import PDFProcessor
from backend.app.services.evidence.chat_processor import ChatProcessor
from backend.app.services.evidence.text_processor import TextProcessor
from backend.app.services.evidence.audio_processor import AudioProcessor
from backend.app.services.evidence.url_processor import URLProcessor
from backend.app.services.evidence.live_processor import LiveWhatsAppProcessor

class DummyEvidence:
    def __init__(self, ev_id="EV-TEST-1", case_id="CASE-1", filename="test", mime_type="text/plain", raw_content=""):
        self.id = ev_id
        self.case_id = case_id
        self.filename = filename
        self.mime_type = mime_type
        self.file_size = len(raw_content)
        self.sha256_hash = "mockhash"
        self.raw_content = raw_content
        self.file_path = None

@pytest.mark.asyncio
async def test_image_processor_real_ocr(sample_image_bytes):
    """Test ImageProcessor running real RapidOCR on synthetic fixture."""
    processor = ImageProcessor()
    ev = DummyEvidence(ev_id="EV-IMG-1", filename="scam_notice.png", mime_type="image/png")
    
    normalized = await processor.process(ev, file_bytes=sample_image_bytes)
    assert normalized.processing_status == "processed"
    text = normalized.content["text"]
    assert "95,000" in text or "95000" in text
    assert len(normalized.content["segments"]) > 0
    
    # Check provenance item created for financial amount / UPI
    assert len(normalized.provenance) > 0
    assert any("OCR" in p.source_reference for p in normalized.provenance)

@pytest.mark.asyncio
async def test_pdf_processor_real_extraction(sample_pdf_bytes):
    """Test PDFProcessor extracting real text page-by-page from ReportLab PDF."""
    processor = PDFProcessor()
    ev = DummyEvidence(ev_id="EV-PDF-1", filename="arrest_notice.pdf", mime_type="application/pdf")

    normalized = await processor.process(ev, file_bytes=sample_pdf_bytes)
    assert normalized.processing_status == "processed"
    assert normalized.content["page_count"] == 2
    assert "Page 1" in normalized.content["text"]
    assert "I4C" in normalized.content["text"]
    assert "UTR987654321098" in normalized.content["text"]
    
    # Provenance links
    assert any("Page 2" in p.source_reference for p in normalized.provenance)

@pytest.mark.asyncio
async def test_chat_processor_whatsapp_normalization():
    """Test ChatProcessor parsing standard WhatsApp conversation with timestamps and senders."""
    chat_text = (
        "[10:31, 25/09/2026] Unknown: Your account has been flagged for illegal activity.\n"
        "[10:32, 25/09/2026] Unknown: Install AnyDesk immediately and transfer ₹95,000 to clear your name.\n"
        "[10:33, 25/09/2026] Victim: Why should I transfer this?\n"
        "I need a formal verification first."
    )
    processor = ChatProcessor()
    ev = DummyEvidence(ev_id="EV-CHAT-1", filename="chat.txt", raw_content=chat_text)

    normalized = await processor.process(ev)
    assert normalized.processing_status == "processed"
    assert normalized.content["message_count"] == 3
    messages = normalized.content["messages"]
    
    # Verify exact timestamps and senders
    assert messages[0]["sender"] == "Unknown"
    assert messages[0]["timestamp"] == "10:31, 25/09/2026"
    assert messages[2]["sender"] == "Victim"
    # Verify multi-line message continuation
    assert "formal verification first" in messages[2]["text"]

    # Verify provenance extraction for AnyDesk and amount
    prov_values = [p.extracted_value for p in normalized.provenance]
    assert any("₹95,000" in v for v in prov_values)
    assert any("AnyDesk" in v for v in prov_values)

@pytest.mark.asyncio
async def test_chat_processor_does_not_invent_missing_data():
    """Verify ChatProcessor STRICTLY DOES NOT fabricate missing timestamps or senders."""
    plain_text = "Transfer the money now or you will be arrested."
    processor = ChatProcessor()
    ev = DummyEvidence(ev_id="EV-CHAT-2", filename="chat.txt", raw_content=plain_text)

    normalized = await processor.process(ev)
    assert normalized.processing_status == "processed"
    messages = normalized.content["messages"]
    assert len(messages) == 1
    assert messages[0]["timestamp"] is None  # MUST NOT INVENT
    assert messages[0]["sender"] is None     # MUST NOT INVENT
    assert messages[0]["text"] == plain_text

@pytest.mark.asyncio
async def test_text_processor_bank_sms():
    """Test TextProcessor normalizing a Bank debit SMS."""
    sms_text = "INR 85,000.00 debited from A/c ending 5678 on 25-SEP-26 via UPI Ref 987654321098. If not you, report to 1930."
    processor = TextProcessor()
    ev = DummyEvidence(ev_id="EV-TXT-1", raw_content=sms_text)

    normalized = await processor.process(ev)
    assert normalized.processing_status == "processed"
    assert normalized.metadata["is_sms"] is True
    prov_values = [p.extracted_value for p in normalized.provenance]
    assert any("INR 85,000.00" in v for v in prov_values)
    assert any("Transaction Ref: 987654321098" in v for v in prov_values)

@pytest.mark.asyncio
async def test_audio_processor_unconfigured_honest_error(sample_audio_bytes):
    """Test AudioProcessor returns clear configuration error when STT is unconfigured, with NO fake output."""
    processor = AudioProcessor(provider=None)
    ev = DummyEvidence(ev_id="EV-AUD-1", filename="call.wav", mime_type="audio/wav")

    normalized = await processor.process(ev, file_bytes=sample_audio_bytes)
    assert normalized.processing_status == "failed"
    assert "Speech-to-Text provider not configured" in normalized.error_message
    assert normalized.content["text"] == ""  # Zero fake transcript

@pytest.mark.asyncio
async def test_url_processor_safe_analysis():
    """Test URLProcessor validates format, normalizes, marks UNVERIFIED, and checks threat patterns."""
    processor = URLProcessor()
    ev = DummyEvidence(ev_id="EV-URL-1", mime_type="text/uri-list", raw_content="http://192.168.1.100/sbi_fraud_alert.apk?user=test")

    normalized = await processor.process(ev)
    assert normalized.processing_status == "processed"
    assert normalized.metadata["verification_status"] == "UNVERIFIED"
    assert normalized.metadata["is_ip_address"] is True
    assert any("APK" in f for f in normalized.metadata["threat_flags"])

@pytest.mark.asyncio
async def test_live_whatsapp_processor_authorization():
    """Test LiveWhatsAppProcessor enforces explicit user authorization."""
    live_proc = LiveWhatsAppProcessor()
    
    # 1. Unauthorized must raise PermissionError
    with pytest.raises(PermissionError):
        await live_proc.process_chunk(
            case_id="CASE-1",
            chunk_text="Suspicious message",
            user_authorized=False
        )

    # 2. Authorized succeeds
    norm = await live_proc.process_chunk(
        case_id="CASE-1",
        chunk_text="Transfer funds now",
        user_authorized=True,
        sender="Suspect +919876543210"
    )
    assert norm.processing_status == "processed"
    assert norm.metadata["user_authorized"] is True
    assert "Suspect +919876543210" in norm.content["text"]
