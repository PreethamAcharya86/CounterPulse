import io
import wave
import struct
import pytest
from PIL import Image, ImageDraw
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from backend.app.core.database import Base, get_db
from backend.app.main import app
from backend.app.models.case import Case
import backend.app.models  # Ensures all models are registered

# Test In-Memory Database with StaticPool so all connections share the same memory instance
TEST_DB_URL = "sqlite:///:memory:"
test_engine = create_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

@pytest.fixture(autouse=True)
def clean_db():
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    yield

@pytest.fixture
def client():
    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

@pytest.fixture
def sample_case() -> Case:
    db = TestingSessionLocal()
    case = Case(
        title="Test Phishing & Extortion Case",
        description="Victim received fake legal notice and coercive calls",
        status="intake",
    )
    db.add(case)
    db.commit()
    db.refresh(case)
    case_copy = Case(id=case.id, title=case.title, description=case.description, status=case.status)
    db.close()
    return case_copy

@pytest.fixture
def sample_image_bytes() -> bytes:
    """Generate a real PNG image containing clearly readable fraudulent text."""
    img = Image.new("RGB", (500, 150), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.text((20, 20), "ALERT: Transfer Rs 95,000 immediately to upi@okhdfcbank", fill=(0, 0, 0))
    draw.text((20, 50), "Call 9876543210 for verification", fill=(0, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

@pytest.fixture
def sample_pdf_bytes() -> bytes:
    """Generate a real 2-page PDF document using ReportLab."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    
    # Page 1
    c.drawString(100, 750, "NATIONAL CYBER CRIME COORDINATION CENTRE (I4C)")
    c.drawString(100, 720, "IMMEDIATE DIGITAL ARREST NOTICE")
    c.drawString(100, 690, "You are suspected of money laundering via Aadhaar.")
    c.showPage()
    
    # Page 2
    c.drawString(100, 750, "REF: UTR987654321098")
    c.drawString(100, 720, "Penalty amount assessed: INR 85,000")
    c.drawString(100, 690, "Deposit to clearing account within 2 hours.")
    c.showPage()
    
    c.save()
    return buf.getvalue()

@pytest.fixture
def sample_audio_bytes() -> bytes:
    """Generate a real valid WAV audio file with 1 second of audio."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wav_file:
        n_channels = 1
        sampwidth = 2
        framerate = 16000
        n_frames = 16000
        wav_file.setparams((n_channels, sampwidth, framerate, n_frames, "NONE", "not compressed"))
        # Generate simple sine/tone bytes
        raw_frames = struct.pack(f"<{n_frames}h", *([1000 if i % 2 == 0 else -1000 for i in range(n_frames)]))
        wav_file.writeframes(raw_frames)
    return buf.getvalue()
