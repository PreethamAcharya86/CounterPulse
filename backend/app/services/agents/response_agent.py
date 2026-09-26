from backend.app.services.agents.base import BaseAgent, CaseContext
from backend.app.services.ai.base import AIProvider
from backend.app.schemas.ai_output import ResponsePackagesOutput

class ResponseAgent(BaseAgent):
    """
    Generates formal response draft packages (Bank Dispute Letter, NCRP 1930 Cybercrime Complaint,
    and Emergency Advisory).
    STRICT SAFETY RULE: These are strictly DRAFTS/RECOMMENDATIONS.
    The AI never executes external transmissions without human approval.
    """

    @property
    def name(self) -> str:
        return "response_agent"

    @property
    def description(self) -> str:
        return "Formulates formal bank dispute letters and NCRP cybercrime complaint drafts with statutory references."

    async def run(self, context: CaseContext, provider: AIProvider) -> ResponsePackagesOutput:
        prompt = (
            f"CASE CONTEXT:\n"
            f"Case ID: {context.case_id}\n"
            f"Title: {context.title}\n"
            f"Description: {context.description or 'None provided'}\n\n"
            f"FORENSIC EVIDENCE & RECONSTRUCTED DETAILS:\n"
            f"{context.combined_evidence_text or '[No evidence text]'}\n\n"
            f"REGULATORY GROUNDING (FOR REFERENCE ONLY):\n"
            f"- RBI Circular DBR.No.Leg.BC.78/09.07.005/2017-18 on Customer Protection — Limiting Liability of Customers in Unauthorized Electronic Banking Transactions.\n"
            f"- Indian Cyber Crime Coordination Centre (I4C) - 1930 National Cyber Crime Reporting Portal.\n\n"
            f"TASK:\n"
            f"Generate formal response package DRAFTS:\n"
            f"1. bank_dispute_subject: Clear subject line with loss amount and urgency indicator.\n"
            f"2. bank_dispute_body: Authoritative dispute letter citing the statutory RBI Circular on customer liability, the timeline of notification (golden hour), transaction IDs, and requesting immediate beneficiary account lien/freeze.\n"
            f"3. cybercrime_complaint_subject: Subject line tailored for 1930 / cybercrime.gov.in portal.\n"
            f"4. cybercrime_complaint_body: Forensic complaint text detailing the modus operandi, impersonated officers, fraudulent accounts/UPIs, and attached evidence records.\n"
            f"5. emergency_advisory: Bulleted immediate containment checklist for the victim.\n"
            f"6. is_draft_only: MUST be True.\n\n"
            f"SAFETY WARNING: This output is strictly a DRAFT for victim review. You will NOT send emails or initiate external actions."
        )

        system_instruction = (
            "You are a Banking Law & Cybercrime Regulatory Response Specialist. "
            "Draft authoritative, legally precise dispute and reporting documents adhering to statutory guidelines. "
            "Never execute external actions; generate structured draft recommendations only."
        )

        return await provider.complete_structured(
            prompt=prompt,
            schema=ResponsePackagesOutput,
            system_instruction=system_instruction,
        )
