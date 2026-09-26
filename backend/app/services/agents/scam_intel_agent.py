from backend.app.services.agents.base import BaseAgent, CaseContext
from backend.app.services.ai.base import AIProvider
from backend.app.schemas.ai_output import ScamIntelligenceOutput

class ScamIntelligenceAgent(BaseAgent):
    """
    Analyzes conversational media (WhatsApp, SMS, transcript dialogues) to detect
    coercive tactics, psychological triggers, legal intimidation, and impersonation tokens.
    """

    @property
    def name(self) -> str:
        return "scam_intel_agent"

    @property
    def description(self) -> str:
        return "Extracts psychological triggers, coercive patterns, impersonation tokens, and fraud tactics from conversation logs."

    async def run(self, context: CaseContext, provider: AIProvider) -> ScamIntelligenceOutput:
        prompt = (
            f"CASE CONTEXT:\n"
            f"Case ID: {context.case_id}\n"
            f"Title: {context.title}\n"
            f"Description: {context.description or 'None provided'}\n\n"
            f"CONVERSATION LOGS & EVIDENCE:\n"
            f"{context.combined_evidence_text or '[No conversation text]'}\n\n"
            f"EXTERNAL TYPOLOGY GROUNDING (FOR REFERENCE ONLY):\n"
            f"{context.grounding.get('external_typologies', [])}\n\n"
            f"TASK:\n"
            f"Analyze the conversation for scam intelligence signals:\n"
            f"1. scam_type: e.g. Digital Arrest / Law Enforcement Impersonation, Fake KYC Scam, Part-Time Job Scam, etc.\n"
            f"2. impersonated_entities: List any specific authorities, departments, or companies the suspect claimed to represent.\n"
            f"3. tactics_observed: Extract specific tactics used (e.g. 'False Legal Deadline', 'Arrest Threat', 'Secret Holding Account', 'Screen Sharing Request').\n"
            f"4. psychological_triggers: Emotional levers exploited (e.g. Fear of criminal conviction, urgency/time pressure, trust in uniforms/badges, financial greed).\n"
            f"5. suspicious_indicators_found: List suspicious indicators (UPI, phone, domain, APK) with their conversational context.\n"
            f"6. threat_assessment: Comprehensive behavioral analysis of the scammer's modus operandi."
        )

        system_instruction = (
            "You are a Scam Intelligence & Behavioral Profiling Specialist. "
            "Examine conversational evidence for coercive patterns, social engineering, and fraudulent pretexts."
        )

        return await provider.complete_structured(
            prompt=prompt,
            schema=ScamIntelligenceOutput,
            system_instruction=system_instruction,
        )
