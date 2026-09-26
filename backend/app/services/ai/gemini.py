import asyncio
import json
import logging
from typing import TypeVar, Type, Optional
from pydantic import BaseModel

from backend.app.core.config import settings
from backend.app.services.ai.base import (
    AIProvider,
    AIConfigurationError,
    AIQuotaExhaustedError,
    AIProviderUnavailableError,
    AIError,
)
from backend.app.services.ai.parser import RobustJSONParser

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

class GeminiProvider(AIProvider):
    """
    Google Gemini AI Provider implementing Gemini 2.0 Flash / 1.5.
    Uses official google-genai SDK.
    """

    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model_name = model_name or settings.GEMINI_MODEL
        self._client = None

    @property
    def provider_name(self) -> str:
        return "gemini"

    def _get_client(self):
        if not self.api_key:
            raise AIConfigurationError(
                "GEMINI_API_KEY is not configured. Please add GEMINI_API_KEY in .env or set environment variable."
            )
        if self._client is None:
            try:
                from google import genai
                self._client = genai.Client(api_key=self.api_key)
            except Exception as e:
                raise AIConfigurationError(f"Failed to initialize Google GenAI client: {str(e)}")
        return self._client

    async def complete_structured(
        self,
        prompt: str,
        schema: Type[T],
        system_instruction: Optional[str] = None,
    ) -> T:
        client = self._get_client()

        # Enforce JSON formatting and include JSON schema reference in prompt
        schema_json = json.dumps(schema.model_json_schema(), indent=2)
        augmented_prompt = (
            f"{prompt}\n\n"
            f"CRITICAL: Respond ONLY with a valid JSON object strictly conforming to this JSON Schema:\n"
            f"```json\n{schema_json}\n```\n"
            f"Do NOT include any commentary, explanations, or prose outside the JSON."
        )

        sys_inst = (system_instruction or "") + (
            "\nYou are an expert cyber-fraud forensic incident response agent. "
            "You MUST output valid, parseable JSON conforming strictly to the requested schema. "
            "Do not fabricate facts not present in the evidence."
        )

        try:
            from google.genai import types
            config = types.GenerateContentConfig(
                system_instruction=sys_inst.strip(),
                response_mime_type="application/json",
            )
            if hasattr(client, "aio") and hasattr(client.aio, "models") and hasattr(client.aio.models, "generate_content"):
                response = await client.aio.models.generate_content(
                    model=self.model_name,
                    contents=augmented_prompt,
                    config=config,
                )
            else:
                response = await asyncio.to_thread(
                    client.models.generate_content,
                    model=self.model_name,
                    contents=augmented_prompt,
                    config=config,
                )
            raw_text = response.text or ""
            return RobustJSONParser.parse_and_validate(raw_text, schema)
        except Exception as e:
            err_msg = str(e)
            if "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg:
                raise AIQuotaExhaustedError(f"Gemini API rate limit or quota exceeded: {err_msg}")
            elif "503" in err_msg or "UNAVAILABLE" in err_msg or "connection" in err_msg.lower():
                raise AIProviderUnavailableError(f"Gemini service temporarily unavailable: {err_msg}")
            elif "AISchemaValidationError" in err_msg:
                raise
            else:
                raise AIError(f"Gemini API invocation failed: {err_msg}")

    async def generate_text(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
    ) -> str:
        client = self._get_client()
        try:
            from google.genai import types
            config = types.GenerateContentConfig(
                system_instruction=system_instruction,
            ) if system_instruction else None

            if hasattr(client, "aio") and hasattr(client.aio, "models") and hasattr(client.aio.models, "generate_content"):
                response = await client.aio.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=config,
                )
            else:
                response = await asyncio.to_thread(
                    client.models.generate_content,
                    model=self.model_name,
                    contents=prompt,
                    config=config,
                )
            return response.text or ""
        except Exception as e:
            err_msg = str(e)
            if "429" in err_msg:
                raise AIQuotaExhaustedError(f"Gemini API rate limit: {err_msg}")
            raise AIError(f"Gemini generation failed: {err_msg}")

