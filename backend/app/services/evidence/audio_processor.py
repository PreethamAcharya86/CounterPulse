import re
import logging
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, Tuple
from backend.app.services.evidence.base import (
    EvidenceProcessor,
    NormalizedEvidence,
    ContentSegment,
    ProvenanceItem,
)
from backend.app.core.config import settings

logger = logging.getLogger(__name__)

class SpeechToTextProvider(ABC):
    """Abstract base class for audio transcription providers."""
    @abstractmethod
    async def transcribe(self, audio_bytes: bytes, mime_type: str) -> Tuple[str, List[ContentSegment]]:
        """Return (full_transcript_text, list_of_timestamped_segments)."""
        pass

class GeminiAudioSTTProvider(SpeechToTextProvider):
    """
    Speech-to-Text implementation using Google Gemini 2.0 Flash Multimodal Audio.
    Extracts timestamped speech segments with speaker role classification.
    """
    def __init__(self, api_key: str, model_name: str = "gemini-2.0-flash"):
        self.api_key = api_key
        self.model_name = model_name

    async def transcribe(self, audio_bytes: bytes, mime_type: str) -> Tuple[str, List[ContentSegment]]:
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is not configured.")

        from google import genai
        from google.genai import types

        client = genai.Client(api_key=self.api_key)

        prompt = (
            "Transcribe this scam/fraud audio recording accurately. "
            "For every spoken utterance, provide the timestamp range, identified speaker role (e.g. 'Victim', 'Caller', or 'Impersonator'), and exact transcript. "
            "Use this exact format on each line:\n"
            "[MM:SS - MM:SS] Speaker: Transcript text\n"
            "Example:\n"
            "[00:12 - 00:18] Caller: I am calling from the Cyber Crime Department.\n"
            "[00:19 - 00:23] Victim: Why are you calling me?\n"
            "Do not invent words. Transcribe what is actually spoken."
        )

        audio_part = types.Part.from_bytes(data=audio_bytes, mime_type=mime_type)
        response = client.models.generate_content(
            model=self.model_name,
            contents=[audio_part, prompt],
        )

        raw_output = response.text or ""
        segments: List[ContentSegment] = []
        
        # Regex to parse [MM:SS - MM:SS] or [SS.S - SS.S] Speaker: text
        line_pat = re.compile(
            r"^\[(?P<start>\d{1,2}:\d{2}(?:\.\d+)?|\d+(?:\.\d+)?)\s*-\s*(?P<end>\d{1,2}:\d{2}(?:\.\d+)?|\d+(?:\.\d+)?)\]\s*(?P<speaker>[^:]+?):\s*(?P<text>.*)$"
        )

        def to_seconds(t_str: str) -> float:
            try:
                if ":" in t_str:
                    parts = t_str.split(":")
                    return float(parts[0]) * 60 + float(parts[1])
                return float(t_str)
            except Exception:
                return 0.0

        lines = raw_output.splitlines()
        for idx, line in enumerate(lines):
            clean = line.strip()
            if not clean:
                continue
            m = line_pat.match(clean)
            if m:
                s_str = m.group("start")
                e_str = m.group("end")
                spk = m.group("speaker").strip()
                txt = m.group("text").strip()

                start_sec = to_seconds(s_str)
                end_sec = to_seconds(e_str)

                segments.append(
                    ContentSegment(
                        segment_id=f"SEG-{idx+1:03d}",
                        start_time=round(start_sec, 2),
                        end_time=round(end_sec, 2),
                        speaker=spk,
                        text=txt,
                        evidence_id="AUDIO-EXTRACT",
                        confidence=0.95,
                    )
                )

        return raw_output, segments

class AudioProcessor(EvidenceProcessor):
    """
    Audio / Call recording processor.
    Uses SpeechToTextProvider abstraction.
    Does NOT invent transcripts; fails gracefully with clear configuration guidance if provider is unconfigured.
    """

    def __init__(self, provider: Optional[SpeechToTextProvider] = None):
        self.provider = provider
        if not self.provider and settings.GEMINI_API_KEY:
            self.provider = GeminiAudioSTTProvider(
                api_key=settings.GEMINI_API_KEY,
                model_name=settings.GEMINI_MODEL
            )

    async def process(self, evidence: Any, file_bytes: Optional[bytes] = None) -> NormalizedEvidence:
        evidence_id = getattr(evidence, "id", "EV-UNKNOWN")
        case_id = getattr(evidence, "case_id", "CASE-UNKNOWN")
        filename = getattr(evidence, "filename", "recording.mp3")
        mime_type = getattr(evidence, "mime_type", "audio/mpeg")
        file_size = getattr(evidence, "file_size", len(file_bytes) if file_bytes else 0)
        sha256 = getattr(evidence, "sha256_hash", "")

        if not file_bytes:
            file_path = getattr(evidence, "file_path", None)
            if file_path:
                try:
                    with open(file_path, "rb") as f:
                        file_bytes = f.read()
                except Exception as e:
                    return NormalizedEvidence(
                        evidence_id=evidence_id,
                        case_id=case_id,
                        type="audio",
                        source={"filename": filename, "mime_type": mime_type, "file_size": file_size, "sha256_hash": sha256},
                        content={"text": "", "segments": []},
                        processing_status="failed",
                        error_message=f"Could not read audio file: {str(e)}",
                    )
            else:
                return NormalizedEvidence(
                    evidence_id=evidence_id,
                    case_id=case_id,
                    type="audio",
                    source={"filename": filename, "mime_type": mime_type, "file_size": file_size, "sha256_hash": sha256},
                    content={"text": "", "segments": []},
                    processing_status="failed",
                    error_message="No audio data provided",
                )

        # Provider check
        if not self.provider:
            return NormalizedEvidence(
                evidence_id=evidence_id,
                case_id=case_id,
                type="audio",
                source={"filename": filename, "mime_type": mime_type, "file_size": file_size, "sha256_hash": sha256},
                content={"text": "", "segments": []},
                metadata={"provider_configured": False},
                processing_status="failed",
                error_message="Speech-to-Text provider not configured. Please set GEMINI_API_KEY in .env to enable call transcription.",
            )

        try:
            full_transcript, segments = await self.provider.transcribe(file_bytes, mime_type)
        except Exception as e:
            logger.error(f"Audio transcription error for {evidence_id}: {e}")
            return NormalizedEvidence(
                evidence_id=evidence_id,
                case_id=case_id,
                type="audio",
                source={"filename": filename, "mime_type": mime_type, "file_size": file_size, "sha256_hash": sha256},
                content={"text": "", "segments": []},
                processing_status="failed",
                error_message=f"Transcription failed: {str(e)}",
            )

        # Attach evidence_id to segments
        for s in segments:
            s.evidence_id = evidence_id

        # Build provenance items from transcript
        provenance_items: List[ProvenanceItem] = []
        for s in segments:
            # Check for coercive or remote app commands
            remote_match = re.search(r"\b(AnyDesk|TeamViewer|RustDesk|QuickSupport|screen share|install)\b", s.text, re.IGNORECASE)
            if remote_match:
                ts_label = f"{s.start_time}s - {s.end_time}s" if s.start_time is not None else "audio"
                provenance_items.append(
                    ProvenanceItem(
                        source_evidence_id=evidence_id,
                        source_reference=f"Call Recording ({ts_label})",
                        extracted_value=f"Coercive instruction: '{s.text}'",
                        confidence="high",
                        verification_status="supported",
                    )
                )

        return NormalizedEvidence(
            evidence_id=evidence_id,
            case_id=case_id,
            type="audio",
            source={
                "filename": filename,
                "mime_type": mime_type,
                "file_size": file_size,
                "sha256_hash": sha256,
            },
            content={
                "text": full_transcript,
                "segments": [s.model_dump() for s in segments],
                "segment_count": len(segments),
            },
            metadata={
                "provider": self.provider.__class__.__name__,
                "segment_count": len(segments),
            },
            provenance=provenance_items,
            processing_status="processed",
        )
