import re
import json
import logging
from typing import TypeVar, Type, Optional, Any
from pydantic import BaseModel, ValidationError
from backend.app.services.ai.base import AISchemaValidationError

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

class RobustJSONParser:
    """
    Robust JSON parser for LLM outputs.
    Handles markdown fences, unescaped characters, trailing commas,
    truncated closing brackets, and Python literal formatting.
    Guarantees strict Pydantic validation.
    """

    @classmethod
    def extract_json_candidate(cls, text: str) -> str:
        """Extract the most plausible JSON substring from model output."""
        if not text:
            return ""

        clean = text.strip()

        # 1. Check for markdown code fences (```json ... ``` or ``` ...)
        fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", clean, re.IGNORECASE)
        if fence_match:
            candidate = fence_match.group(1).strip()
            if candidate.startswith("{") or candidate.startswith("["):
                return candidate

        # 2. Check for outer-most JSON object bounds
        first_brace = clean.find("{")
        last_brace = clean.rfind("}")
        if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
            return clean[first_brace : last_brace + 1]

        # 3. Check for outer-most JSON array bounds
        first_bracket = clean.find("[")
        last_bracket = clean.rfind("]")
        if first_bracket != -1 and last_bracket != -1 and last_bracket > first_bracket:
            return clean[first_bracket : last_bracket + 1]

        return clean

    @classmethod
    def repair_json_string(cls, json_str: str) -> str:
        """Apply defensive regex transformations to recover common LLM JSON defects."""
        candidate = json_str.strip()

        # Fix python booleans/nulls
        candidate = re.sub(r"\bTrue\b", "true", candidate)
        candidate = re.sub(r"\bFalse\b", "false", candidate)
        candidate = re.sub(r"\bNone\b", "null", candidate)

        # Remove trailing commas before closing braces/brackets
        candidate = re.sub(r",\s*([\}\]])", r"\1", candidate)

        # Balance unclosed brackets if truncated
        open_braces = candidate.count("{") - candidate.count("}")
        open_brackets = candidate.count("[") - candidate.count("]")

        if open_brackets > 0:
            candidate += "]" * open_brackets
        if open_braces > 0:
            candidate += "}" * open_braces

        return candidate

    @classmethod
    def parse_and_validate(cls, raw_text: str, schema: Type[T]) -> T:
        """
        Parse raw model text into target Pydantic schema.
        Raises AISchemaValidationError if parsing or validation fails after repair attempts.
        """
        if not raw_text or not raw_text.strip():
            raise AISchemaValidationError("Model returned empty output.", raw_output=raw_text)

        candidate = cls.extract_json_candidate(raw_text)

        # 1. Attempt standard direct parse
        parsed_dict: Optional[Any] = None
        try:
            parsed_dict = json.loads(candidate)
        except json.JSONDecodeError:
            # 2. Attempt repaired parse
            repaired = cls.repair_json_string(candidate)
            try:
                parsed_dict = json.loads(repaired)
            except json.JSONDecodeError as decode_err:
                logger.error(f"JSON decode failed after repair: {decode_err}\nRaw:\n{raw_text}")
                raise AISchemaValidationError(
                    f"Model output is not valid JSON: {str(decode_err)}",
                    raw_output=raw_text,
                    validation_details=str(decode_err),
                )

        # 3. Pydantic schema validation
        try:
            if isinstance(parsed_dict, dict):
                return schema.model_validate(parsed_dict)
            elif isinstance(parsed_dict, list) and hasattr(schema, "__root__"):
                return schema.model_validate(parsed_dict)
            else:
                return schema.model_validate(parsed_dict)
        except ValidationError as val_err:
            logger.error(f"Pydantic validation failed for {schema.__name__}: {val_err}\nData: {parsed_dict}")
            raise AISchemaValidationError(
                f"Model JSON failed validation against schema '{schema.__name__}': {str(val_err)}",
                raw_output=raw_text,
                validation_details=val_err.errors(),
            )
