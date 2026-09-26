from backend.app.services.agents.base import BaseAgent, CaseContext
from backend.app.services.ai.base import AIProvider
from backend.app.schemas.ai_output import TriageOutput

class TriageAgent(BaseAgent):
    """
    Evaluates incident urgency, threat vectors, and golden-hour response requirements.
    Assesses structured risk signals rather than emitting generic scam labels.
    """

    @property
    def name(self) -> str:
        return "triage_agent"

    @property
    def description(self) -> str:
        return "Assesses incident urgency, threat vectors, authority impersonation, and immediate containment needs."

    async def run(self, context: CaseContext, provider: AIProvider) -> TriageOutput:
        prompt = (
            f"CASE CONTEXT:\n"
            f"Case ID: {context.case_id}\n"
            f"Title: {context.title}\n"
            f"Description: {context.description or 'None provided'}\n\n"
            f"FORENSIC EVIDENCE CONTENT:\n"
            f"{context.combined_evidence_text or '[No evidence text]'}\n\n"
            f"TASK:\n"
            f"Perform an emergency triage evaluation of this cybersecurity fraud incident.\n"
            f"Analyze structured signals:\n"
            f"- financial_loss_detected (boolean) and loss_amount (float or null)\n"
            f"- authority_impersonation (boolean): Did attacker pose as police, CBI, TRAI, judge, or bank officer?\n"
            f"- remote_access_risk (boolean): Did attacker demand or attempt installation of AnyDesk, TeamViewer, etc.?\n"
            f"- credential_risk (boolean): Were OTPs, passwords, or PINs demanded or exposed?\n"
            f"- identity_exposure (boolean): Was Aadhaar, PAN, passport, or identity information compromised?\n"
            f"- severity_level: 'critical' if active remote access or confirmed loss > ₹50,000; 'high' if extortion/impersonation; 'medium' if suspicious links; 'low' otherwise.\n"
            f"- urgency_rating: 'immediate_containment' (golden hour: within 24h), 'active_monitoring', or 'standard_followup'.\n"
            f"- triage_summary: Technical justification of the severity rating based strictly on structured signals.\n"
            f"- immediate_containment_steps: Concrete first-response actions (e.g. 1930 helpline, bank freeze, device isolation)."
        )

        system_instruction = (
            "You are a Cybersecurity Incident Triage Officer. "
            "Evaluate operational urgency strictly using forensic evidence signals. "
            "Do not emit generic scam warnings; provide structured tactical triage."
        )

        return await provider.complete_structured(
            prompt=prompt,
            schema=TriageOutput,
            system_instruction=system_instruction,
        )
