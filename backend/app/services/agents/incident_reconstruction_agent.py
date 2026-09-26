from backend.app.services.agents.base import BaseAgent, CaseContext
from backend.app.services.ai.base import AIProvider
from backend.app.schemas.ai_output import IncidentReconstructionOutput

class IncidentReconstructionAgent(BaseAgent):
    """
    Reconstructs the chronological incident timeline, step-by-step modus operandi,
    financial loss, and high-level categorization. Clearly distinguishes known from inferred events.
    """

    @property
    def name(self) -> str:
        return "incident_reconstruction_agent"

    @property
    def description(self) -> str:
        return "Reconstructs the incident narrative, chronological timeline, modus operandi, and financial loss."

    async def run(self, context: CaseContext, provider: AIProvider) -> IncidentReconstructionOutput:
        prompt = (
            f"CASE CONTEXT:\n"
            f"Case ID: {context.case_id}\n"
            f"Title: {context.title}\n"
            f"Description: {context.description or 'None provided'}\n\n"
            f"SUBMITTED FORENSIC EVIDENCE:\n"
            f"{context.combined_evidence_text or '[No evidence text available]'}\n\n"
            f"EXTERNAL GROUNDING (FOR REFERENCE ONLY):\n"
            f"{context.grounding.get('external_typologies', [])}\n\n"
            f"INSTRUCTIONS:\n"
            f"1. summary: Write a concise, objective executive incident summary.\n"
            f"2. incident_type: High-level classification (e.g., Financial Fraud, Extortion, Identity Theft).\n"
            f"3. scam_category: Specific typology (e.g. Digital Arrest / Law Enforcement Impersonation, UPI Phishing, Remote Access Scam, Part-Time Job Scam).\n"
            f"4. severity_level: Rate critical (if active remote access, credential leak, or high financial loss), high, medium, or low.\n"
            f"5. financial_loss: Total monetary amount lost or extorted (float or None if no loss detected). Do NOT guess; only state what is supported.\n"
            f"6. currency: INR (or other currency if explicitly shown).\n"
            f"7. modus_operandi: Step-by-step breakdown of how the attacker approached, coerced, and defrauded the victim.\n"
            f"8. timeline: Build chronological milestones. For each milestone, set is_inferred=True if inferred from context or False if explicitly recorded. Attach source_evidence_id.\n"
            f"9. indicators: Extract primary suspect handles (UPI, phone, URL) with confidence and provenance.\n"
            f"10. compromise: Provide risk assessment across banking, credentials, remote access, and identity.\n"
            f"11. recommended_immediate_actions: Actionable emergency containment steps for victim."
        )

        system_instruction = (
            "You are an expert Incident Reconstruction Forensic Investigator. "
            "Reconstruct the timeline accurately without fabricating milestones. "
            "Clearly distinguish known facts from inferred deductions."
        )

        return await provider.complete_structured(
            prompt=prompt,
            schema=IncidentReconstructionOutput,
            system_instruction=system_instruction,
        )
