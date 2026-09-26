from backend.app.services.agents.base import BaseAgent, CaseContext
from backend.app.services.ai.base import AIProvider
from backend.app.schemas.ai_output import FollowUpAgentOutput

class FollowUpAgent(BaseAgent):
    """
    Identifies evidence gaps, missing documentation, unanswered forensic questions,
    and conflicting claims to guide the victim in strengthening their dispute.
    """

    @property
    def name(self) -> str:
        return "followup_agent"

    @property
    def description(self) -> str:
        return "Identifies missing documentation, evidentiary gaps, and recommended follow-up actions to improve recovery odds."

    async def run(self, context: CaseContext, provider: AIProvider) -> FollowUpAgentOutput:
        prompt = (
            f"CASE CONTEXT:\n"
            f"Case ID: {context.case_id}\n"
            f"Title: {context.title}\n"
            f"Description: {context.description or 'None provided'}\n\n"
            f"CURRENT CASE EVIDENCE:\n"
            f"{context.combined_evidence_text or '[No evidence text]'}\n\n"
            f"TASK:\n"
            f"Audit the case evidence for gaps and recovery impediments:\n"
            f"1. missing_information: List crucial factual details not yet known (e.g. 12-digit bank UTR, debit timestamp, beneficiary bank name).\n"
            f"2. unanswered_questions: Questions the victim or investigator needs answered to establish liability.\n"
            f"3. evidence_gaps: Specific files or documents missing (e.g. bank passbook statement, APK download log, call duration screenshot).\n"
            f"4. contradictions_detected: Note any conflicting statements, timestamps, or amounts found across the evidence.\n"
            f"5. recommended_additional_evidence: Prioritized list of tangible documents the victim should upload next to maximize bank dispute success."
        )

        system_instruction = (
            "You are a Forensic Audit & Quality Assurance Specialist. "
            "Critically analyze case evidence to spot evidentiary gaps, missing proof, and inconsistencies."
        )

        return await provider.complete_structured(
            prompt=prompt,
            schema=FollowUpAgentOutput,
            system_instruction=system_instruction,
        )
