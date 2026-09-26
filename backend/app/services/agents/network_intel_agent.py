from backend.app.services.agents.base import BaseAgent, CaseContext
from backend.app.services.ai.base import AIProvider
from backend.app.schemas.ai_output import NetworkIntelligenceOutput

class NetworkIntelligenceAgent(BaseAgent):
    """
    Correlates suspect network indicators (domains, IP addresses, UPI handles, phone numbers)
    with threat patterns and external grounding. Strictly maintains legal disclaimers.
    """

    @property
    def name(self) -> str:
        return "network_intel_agent"

    @property
    def description(self) -> str:
        return "Extracts and correlates network indicators, domains, handles, and phone numbers with external threat signals."

    async def run(self, context: CaseContext, provider: AIProvider) -> NetworkIntelligenceOutput:
        prompt = (
            f"CASE CONTEXT:\n"
            f"Case ID: {context.case_id}\n"
            f"Title: {context.title}\n"
            f"Description: {context.description or 'None provided'}\n\n"
            f"FORENSIC EVIDENCE CONTENT:\n"
            f"{context.combined_evidence_text or '[No evidence content]'}\n\n"
            f"EXTERNAL KNOWLEDGE GROUNDING:\n"
            f"{context.grounding}\n\n"
            f"TASK:\n"
            f"1. Extract nodes: Identify all distinct network entities (UPI IDs, phone numbers, URLs, domains, APKs). For each, estimate a threat_score (0.0 to 1.0) and descriptive notes.\n"
            f"2. correlations: Describe observed infrastructure connections (e.g. UPI handle linked to telecom provider SMS, disposable domain registration, IP hosting).\n"
            f"3. external_knowledge_matches: Note any matches against known typologies or threat patterns.\n"
            f"4. disclaimer: You MUST include this strict disclaimer: 'Indicators represent suspicious investigative artifacts; does not establish criminality of named individuals.'\n\n"
            f"CRITICAL LEGAL RULE: NEVER state or conclude that an individual is definitely a criminal merely because an indicator appears suspicious or was used in the transaction."
        )

        system_instruction = (
            "You are a Cyber Threat Intelligence Network Analyst. "
            "Correlate indicators objectively. Never label an individual as a convicted criminal based on unverified artifacts."
        )

        return await provider.complete_structured(
            prompt=prompt,
            schema=NetworkIntelligenceOutput,
            system_instruction=system_instruction,
        )
