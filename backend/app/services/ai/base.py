from abc import ABC, abstractmethod
from typing import TypeVar, Type, Optional, Any
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)

class AIError(Exception):
    """Base exception for all AI provider and orchestration errors."""
    pass

class AIConfigurationError(AIError):
    """Raised when an AI provider lacks required configuration (e.g. API keys)."""
    pass

class AIQuotaExhaustedError(AIError):
    """Raised when AI rate limits or quotas are exceeded (HTTP 429)."""
    pass

class AIProviderUnavailableError(AIError):
    """Raised when the AI provider service is down or unreachable (HTTP 503)."""
    pass

class AISchemaValidationError(AIError):
    """Raised when model completion cannot be parsed or validated against target Pydantic schema."""
    def __init__(self, message: str, raw_output: Optional[str] = None, validation_details: Optional[Any] = None):
        super().__init__(message)
        self.raw_output = raw_output
        self.validation_details = validation_details

class AIProvider(ABC):
    """
    Abstract Base Class for LLM providers in CounterPulse AI.
    Guarantees strict schema validation, provider abstraction, and fail-safe operation.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name of the provider (e.g. 'gemini', 'openai', 'mock')."""
        pass

    @abstractmethod
    async def complete_structured(
        self,
        prompt: str,
        schema: Type[T],
        system_instruction: Optional[str] = None,
    ) -> T:
        """
        Execute completion with guaranteed structured JSON output adhering to target Pydantic schema.
        Must never silently accept malformed output.
        """
        pass

    @abstractmethod
    async def complete_multimodal_structured(
        self,
        prompt: str,
        image_bytes: bytes,
        mime_type: str,
        schema: Type[T],
        system_instruction: Optional[str] = None,
    ) -> T:
        """
        Execute completion with multimodal image input (raw image bytes + MIME type)
        and guaranteed structured JSON output adhering to target Pydantic schema.
        """
        pass

    @abstractmethod
    async def generate_text(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
    ) -> str:
        """Execute standard text generation."""
        pass
