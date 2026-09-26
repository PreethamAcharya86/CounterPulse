import logging
from typing import Dict, Type, Optional
from backend.app.services.evidence.base import EvidenceProcessor
from backend.app.services.evidence.image_processor import ImageProcessor
from backend.app.services.evidence.pdf_processor import PDFProcessor
from backend.app.services.evidence.text_processor import TextProcessor
from backend.app.services.evidence.chat_processor import ChatProcessor
from backend.app.services.evidence.audio_processor import AudioProcessor
from backend.app.services.evidence.url_processor import URLProcessor

logger = logging.getLogger(__name__)

class EvidenceProcessorFactory:
    """
    Factory for selecting and instantiating modular EvidenceProcessors.
    Allows easy extension with new evidence types without coupling.
    """

    _processors: Dict[str, Type[EvidenceProcessor]] = {
        "image": ImageProcessor,
        "pdf": PDFProcessor,
        "text": TextProcessor,
        "chat": ChatProcessor,
        "audio": AudioProcessor,
        "url": URLProcessor,
    }

    _mime_map: Dict[str, str] = {
        "image/jpeg": "image",
        "image/png": "image",
        "image/webp": "image",
        "application/pdf": "pdf",
        "text/plain": "text",
        "text/csv": "text",
        "application/json": "text",
        "audio/mpeg": "audio",
        "audio/wav": "audio",
        "audio/x-wav": "audio",
        "audio/mp3": "audio",
        "audio/mp4": "audio",
        "audio/x-m4a": "audio",
        "audio/m4a": "audio",
        "audio/ogg": "audio",
        "audio/aac": "audio",
        "audio/webm": "audio",
        "text/uri-list": "url",
    }

    @classmethod
    def register_processor(cls, type_name: str, processor_cls: Type[EvidenceProcessor]):
        """Register a new processor for an evidence type."""
        cls._processors[type_name.lower()] = processor_cls
        logger.info(f"Registered processor '{processor_cls.__name__}' for type '{type_name}'")

    @classmethod
    def get_processor(cls, evidence_type: str, mime_type: Optional[str] = None) -> EvidenceProcessor:
        """
        Resolve and instantiate the appropriate EvidenceProcessor.
        Checks explicit evidence_type first, then falls back to MIME-type mapping.
        """
        normalized_type = (evidence_type or "").lower().strip()
        
        # 1. Exact type match
        if normalized_type in cls._processors:
            return cls._processors[normalized_type]()

        # 2. Match via MIME type
        if mime_type:
            clean_mime = mime_type.lower().split(";")[0].strip()
            if clean_mime in cls._mime_map:
                mapped_type = cls._mime_map[clean_mime]
                return cls._processors[mapped_type]()
            elif clean_mime.startswith("image/"):
                return cls._processors["image"]()
            elif clean_mime.startswith("audio/"):
                return cls._processors["audio"]()

        # 3. Default fallback to TextProcessor
        logger.warning(f"No specific processor found for type='{evidence_type}', mime='{mime_type}'. Defaulting to TextProcessor.")
        return cls._processors["text"]()
