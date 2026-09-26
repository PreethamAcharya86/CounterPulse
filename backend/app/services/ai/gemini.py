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

    async def _execute_with_retry(self, fn, *args, **kwargs):
        """Execute an async Gemini client call with backoff for transient 503/429 spikes."""
        max_attempts = 4
        last_exception = None
        for attempt in range(max_attempts):
            try:
                return await fn(*args, **kwargs)
            except Exception as e:
                last_exception = e
                err_msg = str(e)
                is_transient = (
                    "503" in err_msg
                    or "UNAVAILABLE" in err_msg
                    or "RESOURCE_EXHAUSTED" in err_msg
                    or "429" in err_msg
                )
                if is_transient and attempt < max_attempts - 1:
                    wait_time = 1.5 * (attempt + 1)
                    logger.warning(
                        "Gemini API transient spike. Retrying in %.1fs (attempt %d/%d)...",
                        wait_time,
                        attempt + 1,
                        max_attempts,
                    )
                    await asyncio.sleep(wait_time)
                else:
                    raise
        raise last_exception

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
            async def _call():
                if hasattr(client, "aio") and hasattr(client.aio, "models") and hasattr(client.aio.models, "generate_content"):
                    return await client.aio.models.generate_content(
                        model=self.model_name,
                        contents=augmented_prompt,
                        config=config,
                    )
                else:
                    return await asyncio.to_thread(
                        client.models.generate_content,
                        model=self.model_name,
                        contents=augmented_prompt,
                        config=config,
                    )

            response = await self._execute_with_retry(_call)
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

    async def complete_multimodal_structured(
        self,
        prompt: str,
        image_bytes: bytes,
        mime_type: str,
        schema: Type[T],
        system_instruction: Optional[str] = None,
    ) -> T:
        client = self._get_client()

        schema_json = json.dumps(schema.model_json_schema(), indent=2)
        augmented_prompt = (
            f"{prompt}\n\n"
            f"CRITICAL: Respond ONLY with a valid JSON object strictly conforming to this JSON Schema:\n"
            f"```json\n{schema_json}\n```\n"
            f"Do NOT include any commentary, explanations, or prose outside the JSON."
        )

        sys_inst = (system_instruction or "") + (
            "\nYou are an expert digital forensics investigator analyzing mobile screenshots and evidentiary images. "
            "You MUST output valid, parseable JSON conforming strictly to the requested schema. "
            "Examine the actual image pixels. Transcribe visible messages, timestamps, contact headers, and forensic indicators. "
            "Do NOT fabricate facts or indicators not visible in the image."
        )

        try:
            from google.genai import types
            config = types.GenerateContentConfig(
                system_instruction=sys_inst.strip(),
                response_mime_type="application/json",
            )
            image_part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
            contents = [augmented_prompt, image_part]

            async def _call():
                if hasattr(client, "aio") and hasattr(client.aio, "models") and hasattr(client.aio.models, "generate_content"):
                    return await client.aio.models.generate_content(
                        model=self.model_name,
                        contents=contents,
                        config=config,
                    )
                else:
                    return await asyncio.to_thread(
                        client.models.generate_content,
                        model=self.model_name,
                        contents=contents,
                        config=config,
                    )

            response = await self._execute_with_retry(_call)
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
                raise AIError(f"Gemini multimodal API invocation failed: {err_msg}")

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

