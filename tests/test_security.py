import pytest
from backend.app.core.security import (
    sanitize_filename,
    validate_file_upload,
    compute_sha256,
    get_safe_storage_path,
    sanitize_path_for_response,
    MAX_FILE_SIZE_BYTES,
)

def test_filename_sanitization_directory_traversal():
    """Ensure directory traversal characters are completely stripped."""
    assert sanitize_filename("../../../etc/passwd.png") == "passwd.png"
    assert sanitize_filename("..\\..\\windows\\system32.jpg") == "system32.jpg"
    assert sanitize_filename("folder/subfolder/file.pdf") == "file.pdf"

def test_filename_sanitization_special_characters():
    """Ensure non-alphanumeric special characters are replaced with underscores."""
    cleaned = sanitize_filename("fake;notice <script>.png")
    assert "<" not in cleaned and ">" not in cleaned and ";" not in cleaned
    assert cleaned.endswith(".png")

def test_dangerous_extension_rejection():
    """Ensure dangerous executable extensions are rejected."""
    with pytest.raises(ValueError):
        sanitize_filename("exploit.exe")

    with pytest.raises(ValueError):
        sanitize_filename("script.sh")

    with pytest.raises(ValueError):
        sanitize_filename("batch.bat")

def test_file_validation_oversized():
    """Ensure files exceeding 25MB are rejected."""
    oversized = MAX_FILE_SIZE_BYTES + 1
    is_valid, msg = validate_file_upload("large.png", "image/png", oversized)
    assert not is_valid
    assert "exceeds maximum allowed limit" in msg

def test_file_validation_dangerous_mime():
    """Ensure executable or disallowed MIME types are rejected."""
    is_valid, msg = validate_file_upload("exploit.exe", "application/x-msdownload", 1024)
    assert not is_valid

def test_file_validation_valid():
    """Ensure supported MIME types pass validation."""
    is_valid, _ = validate_file_upload("screenshot.png", "image/png", 50000)
    assert is_valid

    is_valid, _ = validate_file_upload("notice.pdf", "application/pdf", 100000)
    assert is_valid

def test_safe_storage_path_generation(tmp_path):
    """Ensure storage path is strictly within designated storage directory."""
    storage_dir = str(tmp_path)
    safe_path = get_safe_storage_path(storage_dir, "EV-100", "screenshot.png")
    assert safe_path.startswith(storage_dir)
    assert "EV-100_screenshot.png" in safe_path

def test_sanitize_path_for_response():
    """Ensure internal filesystem paths like D:\\NITK\\... are never exposed."""
    raw_path = "D:\\NITK\\CounterPulse\\storage\\EV-100_screenshot.png"
    safe = sanitize_path_for_response(raw_path)
    assert "D:" not in safe
    assert "NITK" not in safe
    assert safe == "storage/EV-100_screenshot.png"

def test_compute_sha256():
    """Verify SHA-256 cryptographic hashing."""
    data = b"CounterPulse Forensics"
    h1 = compute_sha256(data)
    h2 = compute_sha256(data)
    assert h1 == h2
    assert len(h1) == 64
