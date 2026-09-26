import json
from backend.app.services.agents.base import BaseAgent, CaseContext
from backend.app.services.ai.base import AIProvider
from backend.app.schemas.ai_output import EvidenceIntelligenceOutput

class EvidenceIntelligenceAgent(BaseAgent):
    """
    Analyzes normalized evidence to extract verifiable entities, financial figures,
    identifiers, and timestamps while preserving exact evidence provenance.
    Strictly forbids fabricating unmentioned facts.
    """

    @property
    def name(self) -> str:
        return "evidence_intel_agent"

    @property
    def description(self) -> str:
        return "Extracts entities, financial amounts, handles, and dates directly from normalized evidence artifacts."

    async def run(self, context: CaseContext, provider: AIProvider) -> EvidenceIntelligenceOutput:
        prompt = (
            f"CASE CONTEXT:\n"
            f"Case ID: {context.case_id}\n"
            f"Title: {context.title}\n"
            f"Description: {context.description or 'None provided'}\n\n"
            f"NORMALIZED EVIDENCE ARTIFACTS:\n"
            f"{context.combined_evidence_text or '[No text content in evidence]'}\n\n"
            f"TASK:\n"
            f"Extract all verifiable forensic entities directly from the evidence above.\n"
            f"1. For extracted_indicators: extract UPI IDs, phone numbers, URLs, accounts, UTRs, and suspect names. Every indicator MUST specify source_evidence_id (e.g. EV-001) and source_reference citation.\n"
            f"2. For extracted_financials: extract all monetary losses or demanded amounts with exact numeric amount and currency (INR/USD).\n"
            f"3. For dates_mentioned: list all explicit calendar dates or timestamps.\n"
            f"4. For entities_mentioned: list government bodies, banks, or companies cited.\n"
            f"CRITICAL: Do NOT invent or hallucinate entities not present in the evidence."
        )

        system_instruction = (
            "You are an expert Evidence Intelligence Forensic Agent. "
            "You extract facts and indicators strictly from user-submitted forensic media. "
            "Never invent names, accounts, or values. Preserve exact provenance."
        )

        return await provider.complete_structured(
            prompt=prompt,
            schema=EvidenceIntelligenceOutput,
            system_instruction=system_instruction,
        )
