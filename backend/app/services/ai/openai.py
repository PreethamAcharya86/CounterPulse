import json
import logging
from typing import TypeVar, Type, Optional
import httpx
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

class OpenAIProvider(AIProvider):
    """
    OpenAI-compatible AI Provider.
    Supports standard OpenAI chat models (gpt-4o, gpt-4o-mini) and custom endpoints.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.model_name = model_name or settings.OPENAI_MODEL
        self.base_url = (base_url or settings.OPENAI_BASE_URL or "https://api.openai.com/v1").rstrip("/")

    @property
    def provider_name(self) -> str:
        return "openai"

    def _check_config(self):
        if not self.api_key:
            raise AIConfigurationError(
                "OPENAI_API_KEY is not configured. Please add OPENAI_API_KEY in .env or set environment variable."
            )

    async def complete_multimodal_structured(
        self,
        prompt: str,
        image_bytes: bytes,
        mime_type: str,
        schema: Type[T],
        system_instruction: Optional[str] = None,
    ) -> T:
        self._check_config()
        import base64

        b64_img = base64.b64encode(image_bytes).decode("utf-8")
        data_uri = f"data:{mime_type};base64,{b64_img}"

        schema_json = json.dumps(schema.model_json_schema(), indent=2)
        sys_msg = (
            (system_instruction or "You are an expert digital forensics investigator analyzing mobile screenshots.")
            + f"\nCRITICAL: Respond ONLY with a valid JSON object strictly conforming to this JSON schema:\n{schema_json}"
        )

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": sys_msg},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": data_uri}},
                    ],
                },
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1,
        }

        url = f"{self.base_url}/chat/completions"

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(url, headers=headers, json=payload)
                if response.status_code == 429:
                    raise AIQuotaExhaustedError("OpenAI API rate limit exceeded.")
                elif response.status_code in (500, 502, 503, 504):
                    raise AIProviderUnavailableError(f"OpenAI service unavailable (HTTP {response.status_code}).")
                elif response.status_code != 200:
                    raise AIError(f"OpenAI API error {response.status_code}: {response.text}")

                data = response.json()
                content = data["choices"][0]["message"]["content"]
                return RobustJSONParser.parse_and_validate(content, schema)
            except (AIError, AIQuotaExhaustedError, AIProviderUnavailableError, AISchemaValidationError):
                raise
            except Exception as e:
                raise AIError(f"Failed OpenAI multimodal request: {str(e)}") from e

    async def complete_structured(
        self,
        prompt: str,
        schema: Type[T],
        system_instruction: Optional[str] = None,
    ) -> T:
        self._check_config()

        schema_json = json.dumps(schema.model_json_schema(), indent=2)
        sys_msg = (
            (system_instruction or "You are an expert cybersecurity fraud investigator.")
            + f"\nCRITICAL: Respond ONLY with a valid JSON object strictly conforming to this JSON schema:\n{schema_json}"
        )

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": sys_msg},
                {"role": "user", "content": prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1,
        }

        url = f"{self.base_url}/chat/completions"

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(url, headers=headers, json=payload)
            except httpx.NetworkError as ne:
                raise AIProviderUnavailableError(f"OpenAI network error: {str(ne)}")
            except Exception as e:
                raise AIError(f"OpenAI request failed: {str(e)}")

        if response.status_code == 429:
            raise AIQuotaExhaustedError(f"OpenAI quota/rate limit exceeded: {response.text}")
        elif response.status_code >= 500:
            raise AIProviderUnavailableError(f"OpenAI server error ({response.status_code}): {response.text}")
        elif response.status_code != 200:
            raise AIError(f"OpenAI error ({response.status_code}): {response.text}")

        res_json = response.json()
        raw_text = res_json["choices"][0]["message"]["content"]
        return RobustJSONParser.parse_and_validate(raw_text, schema)

    async def generate_text(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
    ) -> str:
        self._check_config()
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": 0.2,
        }
        url = f"{self.base_url}/chat/completions"

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(url, headers=headers, json=payload)
            except Exception as e:
                raise AIError(f"OpenAI request failed: {str(e)}")

        if response.status_code != 200:
            raise AIError(f"OpenAI error ({response.status_code}): {response.text}")

        res_json = response.json()
        return res_json["choices"][0]["message"]["content"]
