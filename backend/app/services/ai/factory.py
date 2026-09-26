import logging
from typing import Optional, Dict, Type
from backend.app.core.config import settings
from backend.app.services.ai.base import AIProvider, AIConfigurationError
from backend.app.services.ai.gemini import GeminiProvider
from backend.app.services.ai.openai import OpenAIProvider
from backend.app.services.ai.mock import MockProvider

logger = logging.getLogger(__name__)

class AIProviderFactory:
    """
    Factory for instantiating and selecting AI providers.
    Supports Gemini, OpenAI, and deterministic MockProvider.
    """

    _override_provider: Optional[AIProvider] = None

    @classmethod
    def set_override_provider(cls, provider: Optional[AIProvider]):
        """Inject an explicit provider instance (useful for unit tests and deterministic mocks)."""
        cls._override_provider = provider

    @classmethod
    def get_provider(cls, provider_type: Optional[str] = None) -> AIProvider:
        """
        Resolve and instantiate the appropriate AIProvider based on configuration or override.
        """
        if cls._override_provider is not None:
            return cls._override_provider

        ptype = (provider_type or settings.AI_PROVIDER or "gemini").lower().strip()

        if ptype == "gemini":
            if not settings.GEMINI_API_KEY:
                logger.warning("GEMINI_API_KEY not set. Using MockProvider as safe fallback.")
                return MockProvider()
            return GeminiProvider()

        elif ptype == "openai":
            if not settings.OPENAI_API_KEY:
                logger.warning("OPENAI_API_KEY not set. Using MockProvider as safe fallback.")
                return MockProvider()
            return OpenAIProvider()

        elif ptype == "mock":
            return MockProvider()

        else:
            logger.warning(f"Unknown AI provider '{ptype}', defaulting to MockProvider.")
            return MockProvider()
