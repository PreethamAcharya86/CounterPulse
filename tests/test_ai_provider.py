import pytest
from pydantic import BaseModel, Field

from backend.app.services.ai.base import (
    AIProvider,
    AIError,
    AIConfigurationError,
    AIQuotaExhaustedError,
    AIProviderUnavailableError,
    AISchemaValidationError,
)
from backend.app.services.ai.parser import RobustJSONParser
from backend.app.services.ai.mock import MockProvider
from backend.app.services.ai.gemini import GeminiProvider
from backend.app.services.ai.openai import OpenAIProvider
from backend.app.services.ai.factory import AIProviderFactory
from backend.app.schemas.ai_output import IncidentReconstructionOutput

class DummySampleSchema(BaseModel):
    name: str
    amount: float
    is_active: bool

@pytest.mark.asyncio
async def test_mock_provider_deterministic_structured():
    """Verify MockProvider returns valid schema instance deterministically."""
    provider = MockProvider()
    result = await provider.complete_structured(
        prompt="Analyze Digital Arrest scam involving 95,000 INR",
        schema=IncidentReconstructionOutput,
    )
    assert isinstance(result, IncidentReconstructionOutput)
    assert result.financial_loss == 95000.0
    assert result.severity_level == "critical"
    assert len(result.timeline) > 0
    assert len(result.indicators) > 0

@pytest.mark.asyncio
async def test_mock_provider_custom_registration():
    """Verify MockProvider supports registering custom responses and handlers."""
    provider = MockProvider()
    custom_obj = DummySampleSchema(name="Test Case", amount=123.45, is_active=True)
    provider.register_response("dummysampleschema", custom_obj)

    res = await provider.complete_structured("give me sample", DummySampleSchema)
    assert res.name == "Test Case"
    assert res.amount == 123.45
    assert res.is_active is True

@pytest.mark.asyncio
async def test_mock_provider_simulated_failures():
    """Verify MockProvider accurately simulates various failure modes for testing."""
    # Quota exhaustion
    p_quota = MockProvider(simulate_quota=True)
    with pytest.raises(AIQuotaExhaustedError):
        await p_quota.complete_structured("prompt", IncidentReconstructionOutput)

    # Service unavailable (503)
    p_unavail = MockProvider(simulate_unavailable=True)
    with pytest.raises(AIProviderUnavailableError):
        await p_unavail.complete_structured("prompt", IncidentReconstructionOutput)

    # General provider failure
    p_fail = MockProvider(simulate_failure=True)
    with pytest.raises(AIError):
        await p_fail.complete_structured("prompt", IncidentReconstructionOutput)

    # Malformed output
    p_malformed = MockProvider(simulate_malformed=True)
    with pytest.raises(AISchemaValidationError):
        await p_malformed.complete_structured("prompt", IncidentReconstructionOutput)

def test_robust_json_parser_fences_and_literals():
    """Verify parser strips markdown code fences and fixes Python literals."""
    raw_markdown = """
    Here is your forensic analysis:
    ```json
    {
      "name": "Arrest Scam",
      "amount": 95000.0,
      "is_active": True,
    }
    ```
    Please review immediately.
    """
    parsed = RobustJSONParser.parse_and_validate(raw_markdown, DummySampleSchema)
    assert parsed.name == "Arrest Scam"
    assert parsed.amount == 95000.0
    assert parsed.is_active is True

def test_robust_json_parser_truncated_balance():
    """Verify parser balances unclosed braces when LLM output gets truncated."""
    truncated = '{"name": "Truncated Notice", "amount": 5000.0, "is_active": false'
    parsed = RobustJSONParser.parse_and_validate(truncated, DummySampleSchema)
    assert parsed.name == "Truncated Notice"
    assert parsed.is_active is False

def test_robust_json_parser_invalid_fails_cleanly():
    """Verify parser strictly raises AISchemaValidationError on hopeless gibberish."""
    with pytest.raises(AISchemaValidationError) as exc_info:
        RobustJSONParser.parse_and_validate("Totally invalid random text without braces", DummySampleSchema)
    assert exc_info.value.raw_output is not None

def test_ai_provider_factory_override():
    """Verify AIProviderFactory supports explicit mock override injection for testing."""
    mock = MockProvider()
    AIProviderFactory.set_override_provider(mock)
    resolved = AIProviderFactory.get_provider()
    assert resolved is mock
    assert resolved.provider_name == "mock"
    AIProviderFactory.set_override_provider(None)

def test_gemini_and_openai_unconfigured_error():
    """Verify Gemini and OpenAI providers raise AIConfigurationError if keys are missing."""
    gemini = GeminiProvider(api_key="")
    with pytest.raises(AIConfigurationError):
        gemini._get_client()

    openai = OpenAIProvider(api_key="")
    with pytest.raises(AIConfigurationError):
        openai._check_config()
