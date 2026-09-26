from backend.app.services.agents.base import BaseAgent, CaseContext
from backend.app.services.ai.base import AIProvider
from backend.app.schemas.ai_output import CompromiseAssessmentOutput

class CompromiseAssessmentAgent(BaseAgent):
    """
    Evaluates vulnerability exposure across banking, credentials, identity, and remote access.
    Strictly applies the project's 4-tier compromise taxonomy:
    REQUESTED -> DISCLOSED -> INSTALLED -> CONFIRMED.
    Never marks a category as compromised solely because the attacker requested it.
    """

    @property
    def name(self) -> str:
        return "compromise_agent"

    @property
    def description(self) -> str:
        return "Applies the REQUESTED/DISCLOSED/INSTALLED/CONFIRMED compromise model to evaluate device, credential, and financial exposure."

    async def run(self, context: CaseContext, provider: AIProvider) -> CompromiseAssessmentOutput:
        prompt = (
            f"CASE CONTEXT:\n"
            f"Case ID: {context.case_id}\n"
            f"Title: {context.title}\n"
            f"Description: {context.description or 'None provided'}\n\n"
            f"EVIDENCE CONTENT:\n"
            f"{context.combined_evidence_text or '[No evidence text]'}\n\n"
            f"KNOWN REMOTE TOOLS GROUNDING (FOR REFERENCE ONLY):\n"
            f"{context.grounding.get('detected_tool_grounding', [])}\n\n"
            f"CRITICAL TAXONOMY RULES:\n"
            f"Assess compromise across categories: 'credentials', 'financial_information', 'identity_information', 'otp_authentication', 'remote_access', 'device'.\n"
            f"For each category, determine status:\n"
            f"- 'REQUESTED': The attacker asked the victim for this item (e.g. asked for OTP, PIN, password, or AnyDesk download).\n"
            f"- 'DISCLOSED': The victim willingly shared or typed the information into a message or untrusted page.\n"
            f"- 'INSTALLED': An unauthorized application, APK, or remote management tool was downloaded/installed on victim device.\n"
            f"- 'CONFIRMED': There is verifiable forensic proof of active exploitation or financial loss (e.g. bank debit SMS confirmation, funds withdrawn, remote session established).\n\n"
            f"CRITICAL INSTRUCTION: Do NOT claim compromise merely because something was requested! Differentiate what the attacker requested from what the victim actually disclosed or installed and what is forensically confirmed.\n"
            f"Provide actionable recommended_action for each assessed vector."
        )

        system_instruction = (
            "You are a Cybersecurity Compromise Assessment Specialist. "
            "Differentiate requested vulnerabilities from actual confirmed exposure. "
            "Strictly adhere to the REQUESTED -> DISCLOSED -> INSTALLED -> CONFIRMED progression."
        )

        return await provider.complete_structured(
            prompt=prompt,
            schema=CompromiseAssessmentOutput,
            system_instruction=system_instruction,
        )
