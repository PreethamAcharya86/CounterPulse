import json
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from backend.app.services.ai.base import AIProvider
from backend.app.knowledge.grounding import GroundingService

class CaseContext(BaseModel):
    """
    Standard input context passed to specialized intelligence agents.
    Isolates case evidence, user statements, and external knowledge grounding.
    """
    case_id: str
    title: str = "Cyber-Fraud Incident"
    description: Optional[str] = None
    evidence_items: List[Dict[str, Any]] = Field(default_factory=list)
    combined_evidence_text: str = ""
    grounding: Dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_case_and_evidence(
        cls,
        case_id: str,
        title: str,
        description: Optional[str],
        evidence_list: List[Any],
    ) -> "CaseContext":
        items = []
        text_parts = []

        for ev in evidence_list:
            ev_id = getattr(ev, "id", "")
            ev_type = getattr(ev, "evidence_type", "")
            fname = getattr(ev, "filename", "")
            raw = getattr(ev, "raw_content", "") or ""
            norm_json = getattr(ev, "normalized_json", None)
            norm_data = None
            if norm_json:
                try:
                    norm_data = json.loads(norm_json)
                except Exception:
                    norm_data = None

            items.append({
                "id": ev_id,
                "evidence_type": ev_type,
                "filename": fname,
                "raw_content": raw,
                "normalized_data": norm_data,
            })

            if raw:
                text_parts.append(f"[{ev_id} | {ev_type} | {fname}]:\n{raw}")

        full_text = "\n\n".join(text_parts)
        grounding_data = GroundingService.get_grounding_context(full_text)

        return cls(
            case_id=case_id,
            title=title,
            description=description,
            evidence_items=items,
            combined_evidence_text=full_text,
            grounding=grounding_data,
        )

class BaseAgent(ABC):
    """Abstract Base Class for all specialized intelligence agents."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Agent identifier (e.g. 'triage_agent', 'scam_intel_agent')."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Brief human-readable description of agent mandate."""
        pass

    @abstractmethod
    async def run(self, context: CaseContext, provider: AIProvider) -> Any:
        """
        Execute agent reasoning over case context using provided AIProvider.
        Returns validated Pydantic model for this agent's domain.
        """
        pass
