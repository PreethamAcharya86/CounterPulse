import re
import logging
from typing import Optional, List, Dict, Any
from urllib.parse import urlparse, parse_qs
from backend.app.services.evidence.base import (
    EvidenceProcessor,
    NormalizedEvidence,
    ProvenanceItem,
    ContentSegment,
)

logger = logging.getLogger(__name__)

# List of suspicious TLDs frequently observed in phishing / fraud campaigns
SUSPICIOUS_TLDS = {".top", ".xyz", ".club", ".icu", ".vip", ".work", ".site", ".online", ".link", ".click"}

class URLProcessor(EvidenceProcessor):
    """
    Safely processes URLs as forensic evidence.
    Validates syntax, normalizes, detects suspicious domain patterns.
    STRICTLY NEVER executes JavaScript or auto-downloads untrusted files.
    """

    async def process(self, evidence: Any, file_bytes: Optional[bytes] = None) -> NormalizedEvidence:
        evidence_id = getattr(evidence, "id", "EV-UNKNOWN")
        case_id = getattr(evidence, "case_id", "CASE-UNKNOWN")
        filename = getattr(evidence, "filename", "url_evidence.txt")
        mime_type = getattr(evidence, "mime_type", "text/uri-list")
        file_size = getattr(evidence, "file_size", 0)
        sha256 = getattr(evidence, "sha256_hash", "")

        raw_url = ""
        if hasattr(evidence, "raw_content") and evidence.raw_content:
            raw_url = evidence.raw_content.strip()
        elif file_bytes:
            raw_url = file_bytes.decode("utf-8", errors="replace").strip()

        if not raw_url:
            return NormalizedEvidence(
                evidence_id=evidence_id,
                case_id=case_id,
                type="url",
                source={"filename": filename, "mime_type": mime_type, "file_size": file_size, "sha256_hash": sha256},
                content={"text": ""},
                processing_status="failed",
                error_message="No URL provided",
            )

        # 1. Syntax Validation
        # Prepend https:// if user submitted domain without scheme
        if not re.match(r"^https?://", raw_url, re.IGNORECASE):
            candidate_url = f"https://{raw_url}"
        else:
            candidate_url = raw_url

        parsed = urlparse(candidate_url)
        if not parsed.netloc:
            return NormalizedEvidence(
                evidence_id=evidence_id,
                case_id=case_id,
                type="url",
                source={"filename": filename, "mime_type": mime_type, "file_size": file_size, "sha256_hash": sha256},
                content={"text": raw_url},
                processing_status="failed",
                error_message=f"Malformed URL: '{raw_url}' has invalid domain structure.",
            )

        # 2. Normalization
        normalized_scheme = parsed.scheme.lower()
        normalized_host = parsed.netloc.lower()
        normalized_path = parsed.path or "/"
        canonical_url = f"{normalized_scheme}://{normalized_host}{normalized_path}"
        if parsed.query:
            canonical_url += f"?{parsed.query}"

        # 3. Static Threat Pattern Analysis (Safe / Offline)
        threat_flags: List[str] = []
        is_ip_address = bool(re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}(?::\d+)?$", normalized_host))
        if is_ip_address:
            threat_flags.append("Raw IP address used instead of domain name")

        # Check for lookalike brands in domain
        brands = ["sbi", "hdfc", "icici", "paytm", "phonepe", "gpay", "google", "amazon", "police", "cbi", "trai", "rbi"]
        for b in brands:
            if b in normalized_host and not normalized_host.endswith(f".{b}.com") and not normalized_host.endswith(f".{b}.co.in"):
                threat_flags.append(f"Potential brand spoofing of '{b}' in hostname '{normalized_host}'")

        # Check for APK download link in path
        if re.search(r"\.apk(?:\?|$)", normalized_path, re.IGNORECASE):
            threat_flags.append("Direct Android APK installer download path detected")

        # Check suspicious TLD
        for tld in SUSPICIOUS_TLDS:
            if normalized_host.endswith(tld):
                threat_flags.append(f"Domain registered on high-risk TLD: {tld}")
                break

        query_params = parse_qs(parsed.query)
        # Redact potentially sensitive tokens in query params for logging
        sanitized_params = {k: v[0] if len(v) == 1 else v for k, v in query_params.items()}

        full_text = (
            f"Submitted URL: {canonical_url}\n"
            f"Host: {normalized_host}\n"
            f"Verification Status: UNVERIFIED\n"
            f"Threat Flags: {', '.join(threat_flags) if threat_flags else 'None detected by heuristic'}"
        )

        provenance_items = [
            ProvenanceItem(
                source_evidence_id=evidence_id,
                source_reference="Submitted URL Record",
                extracted_value=canonical_url,
                confidence="high",
                verification_status="unverified",
            ),
            ProvenanceItem(
                source_evidence_id=evidence_id,
                source_reference=f"URL Host ({normalized_host})",
                extracted_value=normalized_host,
                confidence="high",
                verification_status="unverified",
            )
        ]

        segments = [
            ContentSegment(
                segment_id="URL-001",
                text=canonical_url,
                evidence_id=evidence_id,
                confidence=1.0,
            )
        ]

        return NormalizedEvidence(
            evidence_id=evidence_id,
            case_id=case_id,
            type="url",
            source={
                "filename": filename,
                "mime_type": mime_type,
                "file_size": file_size,
                "sha256_hash": sha256,
            },
            content={
                "text": full_text,
                "canonical_url": canonical_url,
                "segments": [s.model_dump() for s in segments],
            },
            metadata={
                "scheme": normalized_scheme,
                "host": normalized_host,
                "path": normalized_path,
                "query_parameters": sanitized_params,
                "threat_flags": threat_flags,
                "is_ip_address": is_ip_address,
                "verification_status": "UNVERIFIED",
            },
            provenance=provenance_items,
            processing_status="processed",
        )
