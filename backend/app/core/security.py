import os
import re
import hashlib
from pathlib import Path
from typing import Tuple, Set

# Maximum file size: 25MB (as per PROJECT_SPEC.md)
MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024

# Allowed MIME types and corresponding canonical extensions
ALLOWED_MIME_TYPES: Set[str] = {
    # Images
    "image/jpeg",
    "image/png",
    "image/webp",
    # Documents
    "application/pdf",
    # Text
    "text/plain",
    "text/csv",
    "application/json",
    # Audio
    "audio/mpeg",
    "audio/wav",
    "audio/x-wav",
    "audio/mp3",
    "audio/mp4",
    "audio/x-m4a",
    "audio/m4a",
    "audio/ogg",
    "audio/aac",
    "audio/webm",
}

# Dangerous executable extensions that MUST NEVER be allowed
DANGEROUS_EXTENSIONS: Set[str] = {
    ".exe", ".bat", ".cmd", ".sh", ".bash", ".ps1", ".vbs", ".dll",
    ".so", ".bin", ".scr", ".pif", ".msi", ".jar", ".py", ".pyw",
    ".js", ".vbe", ".jse", ".wsf", ".wsh", ".msc"
}

ALLOWED_EXTENSIONS: Set[str] = {
    ".jpg", ".jpeg", ".png", ".webp",
    ".pdf",
    ".txt", ".log", ".json", ".csv",
    ".mp3", ".wav", ".m4a", ".ogg", ".aac", ".mp4", ".webm"
}

def sanitize_filename(filename: str) -> str:
    """
    Sanitize user-provided filename by:
    1. Extracting base name (prevent directory traversal)
    2. Replacing non-whitelisted characters with '_'
    3. Trimming to safe length
    """
    if not filename:
        return "unnamed_file"
    
    # Strip paths
    basename = Path(filename).name
    # Handle Windows backslashes if present
    basename = basename.split("\\")[-1].split("/")[-1]
    
    # Split stem and suffix
    p = Path(basename)
    suffix = p.suffix.lower()
    stem = p.stem
    
    # Check for dangerous extensions
    if suffix in DANGEROUS_EXTENSIONS:
        raise ValueError(f"Dangerous file extension rejected: {suffix}")
    
    # Sanitize characters: allow only a-z, A-Z, 0-9, _, -, .
    clean_stem = re.sub(r"[^a-zA-Z0-9_-]", "_", stem)
    clean_stem = clean_stem[:100] if clean_stem else "evidence"
    
    clean_suffix = re.sub(r"[^a-zA-Z0-9.]", "", suffix)[:10]
    return f"{clean_stem}{clean_suffix}"

def validate_file_upload(filename: str, mime_type: str, file_size: int) -> Tuple[bool, str]:
    """
    Validate uploaded file before persistence.
    Returns (is_valid, error_message).
    """
    if file_size > MAX_FILE_SIZE_BYTES:
        mb = file_size / (1024 * 1024)
        return False, f"File size ({mb:.1f} MB) exceeds maximum allowed limit of 25 MB"
    
    if file_size <= 0:
        return False, "File is empty (0 bytes)"
    
    # Check extension
    ext = Path(filename).suffix.lower()
    if ext in DANGEROUS_EXTENSIONS:
        return False, f"Executable or dangerous file types ({ext}) are strictly prohibited"
    
    # Normalize mime_type
    clean_mime = mime_type.lower().split(";")[0].strip()
    
    # Allow fallback if mime is generic octet-stream but extension is strictly whitelisted
    if clean_mime == "application/octet-stream":
        if ext not in ALLOWED_EXTENSIONS:
            return False, f"Disallowed file format: extension {ext} with generic stream"
    elif clean_mime not in ALLOWED_MIME_TYPES:
        return False, f"Disallowed MIME type '{clean_mime}'. Supported types: Images, PDFs, Audio, Text"
    
    return True, ""

def compute_sha256(data: bytes) -> str:
    """Compute SHA-256 cryptographic hash of file bytes for tamper-evidence."""
    return hashlib.sha256(data).hexdigest()

def get_safe_storage_path(storage_dir: str, evidence_id: str, original_filename: str) -> str:
    """
    Generate unique, tamper-evident storage path within storage_dir.
    Guarantees no directory traversal out of storage_dir.
    """
    safe_name = sanitize_filename(original_filename)
    unique_filename = f"{evidence_id}_{safe_name}"
    
    base_dir = Path(storage_dir).resolve()
    target_path = (base_dir / unique_filename).resolve()
    
    # Path traversal check
    if not str(target_path).startswith(str(base_dir)):
        raise ValueError("Invalid storage path: directory traversal attempt detected")
    
    return str(target_path)

def sanitize_path_for_response(file_path: str) -> str:
    """
    Ensure internal server disk paths are NEVER exposed to client.
    Converts absolute path to safe relative reference.
    """
    if not file_path:
        return ""
    # Return only basename or safe storage relative reference
    return f"storage/{Path(file_path).name}"
