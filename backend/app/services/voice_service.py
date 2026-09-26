import logging
import uuid
import re
import asyncio
from typing import Dict, Any, Optional, Tuple, List
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.models.case import Case
from backend.app.models.report import Report
from backend.app.schemas.ai_output import CaseIntelligence
from backend.app.schemas.voice import VoiceCommandRequest, VoiceCommandResponse, VoiceSessionStatus
from backend.app.services.ai.factory import AIProviderFactory
from backend.app.services.ai.base import AIProvider
from backend.app.services.orchestrator import ai_orchestrator, AIOrchestrator
from backend.app.services.report_service import report_service, ReportService
from backend.app.services.email_service import get_email_provider, EmailProvider

logger = logging.getLogger(__name__)

class VoiceSessionState:
    """Stores per-session voice control state and pending consequential confirmations."""
    def __init__(self, session_id: str, case_id: str):
        self.session_id = session_id
        self.case_id = case_id
        self.voice_state: str = "IDLE"  # IDLE, LISTENING, PROCESSING, RESPONDING, ERROR
        self.pending_action: Optional[Dict[str, Any]] = None
        self.history: list = []

class VoiceControlService:
    """
    Control layer for voice interaction and Gemini Live bidirectional integration.
    Operates strictly over existing CounterPulse cases, reports, and AI orchestrator.
    
    CRITICAL SAFETY REQUIREMENT:
    Voice MUST NEVER bypass the backend HITL approval system.
    Consequential operations (such as email dispatch) require explicit user confirmation.
    """

    def __init__(
        self,
        orchestrator_svc: Optional[AIOrchestrator] = None,
        report_svc: Optional[ReportService] = None,
    ):
        self.orchestrator = orchestrator_svc or ai_orchestrator
        self.report_svc = report_svc or report_service
        self._sessions: Dict[str, VoiceSessionState] = {}

    def get_or_create_session(self, session_id: Optional[str], case_id: str) -> VoiceSessionState:
        sid = session_id or f"vsession-{case_id}"
        if sid not in self._sessions:
            self._sessions[sid] = VoiceSessionState(sid, case_id)
        return self._sessions[sid]

    def get_session_status(self, case_id: str, session_id: Optional[str] = None) -> VoiceSessionStatus:
        sess = self.get_or_create_session(session_id, case_id)
        return VoiceSessionStatus(
            session_id=sess.session_id,
            case_id=sess.case_id,
            voice_state=sess.voice_state,
            has_pending_action=sess.pending_action is not None,
            pending_action=sess.pending_action,
        )

    def get_safe_tool_declarations(self) -> List[Dict[str, Any]]:
        """
        Strict, minimal function declarations for Gemini Live tool calling.
        CRITICAL HITL SAFETY REQUIREMENT:
        - Exposes ONLY approved, safe CounterPulse case inspection functions.
        - NEVER exposes arbitrary command execution, arbitrary HTTP requests, or raw email dispatch.
        - Report dispatching MUST pass through explicit confirmation gate.
        """
        return [
            {
                "name": "get_case_summary",
                "description": "Retrieve incident reconstruction summary, scam category, and financial loss for the case.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "case_id": {"type": "STRING", "description": "The case ID to query"}
                    },
                    "required": ["case_id"],
                },
            },
            {
                "name": "get_case_intelligence",
                "description": "Retrieve deep intelligence including modus operandi, psychological tactics, and attacker indicators.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "case_id": {"type": "STRING", "description": "The case ID to query"}
                    },
                    "required": ["case_id"],
                },
            },
            {
                "name": "get_compromise_summary",
                "description": "Retrieve compromise assessments for bank accounts, cards, credentials, and devices.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "case_id": {"type": "STRING", "description": "The case ID to query"}
                    },
                    "required": ["case_id"],
                },
            },
            {
                "name": "get_report",
                "description": "Retrieve an existing generated report draft (e.g. cybercrime_complaint, bank_dispute, security_advisory).",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "case_id": {"type": "STRING", "description": "The case ID"},
                        "report_type": {"type": "STRING", "description": "Type of report: cybercrime_complaint, bank_dispute, security_advisory"}
                    },
                    "required": ["case_id", "report_type"],
                },
            },
            {
                "name": "generate_report",
                "description": "Generate or retrieve response report for the case.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "case_id": {"type": "STRING", "description": "The case ID"},
                        "report_type": {"type": "STRING", "description": "Type of report: cybercrime_complaint, bank_dispute, security_advisory"}
                    },
                    "required": ["case_id", "report_type"],
                },
            },
            {
                "name": "request_report_send_confirmation",
                "description": "Request explicit human confirmation before dispatching a report. NEVER sends email directly.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "case_id": {"type": "STRING", "description": "The case ID"},
                        "report_type": {"type": "STRING", "description": "Type of report to request confirmation for"}
                    },
                    "required": ["case_id", "report_type"],
                },
            },
        ]

    def get_case_summary(self, case_id: str, db: Session) -> Dict[str, Any]:
        case = db.query(Case).filter(Case.id == case_id).first()
        if not case:
            return {"error": f"Case '{case_id}' not found"}
        loss_str = f"INR {case.financial_loss:,.2f}" if case.financial_loss else "undisclosed amounts"
        return {
            "case_id": case.id,
            "title": case.title,
            "scam_category": case.scam_category or "Unclassified Fraud",
            "severity_level": case.severity_level or "medium",
            "financial_loss": loss_str,
            "summary": case.summary or case.description or "No incident summary recorded.",
            "status": case.status.value if hasattr(case.status, "value") else str(case.status),
        }

    def get_compromise_summary(self, case_id: str, db: Session) -> Dict[str, Any]:
        case = db.query(Case).filter(Case.id == case_id).first()
        if not case:
            return {"error": f"Case '{case_id}' not found"}
        comps = [
            {
                "category": c.category,
                "risk_level": c.risk_level,
                "details": c.details,
                "recommended_action": c.recommended_action,
            }
            for c in (case.compromise_assessments or [])
        ]
        return {"case_id": case_id, "compromise_count": len(comps), "assessments": comps}

    def get_case_intelligence(self, case_id: str, db: Session) -> Dict[str, Any]:
        case = db.query(Case).filter(Case.id == case_id).first()
        if not case:
            return {"error": f"Case '{case_id}' not found"}
        return {
            "case_id": case_id,
            "summary": case.summary,
            "scam_category": case.scam_category,
            "modus_operandi": case.modus_operandi,
            "ai_analysis": case.ai_analysis or {},
        }

    def get_report(self, case_id: str, report_type: str, db: Session) -> Dict[str, Any]:
        reports = self.report_svc.get_reports_for_case(case_id=case_id, db=db)
        r = next((x for x in reports if x.report_type == report_type), None)
        if not r:
            return {"error": f"Report of type '{report_type}' not found for case {case_id}."}
        return {
            "report_id": r.id,
            "report_type": r.report_type,
            "title": r.title,
            "status": r.status.value if hasattr(r.status, "value") else str(r.status),
            "recipient": r.recipient_email,
            "summary": r.content_markdown[:400] if r.content_markdown else "",
        }

    def generate_report(self, case_id: str, report_type: str, db: Session) -> Dict[str, Any]:
        return self.get_report(case_id=case_id, report_type=report_type, db=db)

    def request_report_send_confirmation(
        self, case_id: str, report_type: str, db: Session, session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        reports = self.report_svc.get_reports_for_case(case_id=case_id, db=db)
        r = next((x for x in reports if x.report_type == report_type), None)
        if not r:
            return {"error": f"No {report_type} report found to send. Run analysis first."}
        recipient = r.recipient_email or settings.DEMO_RECIPIENT_EMAIL
        sess = self.get_or_create_session(session_id, case_id)
        sess.pending_action = {
            "action": "send_report",
            "report_id": r.id,
            "report_type": report_type,
            "recipient": recipient,
        }
        sess.voice_state = "RESPONDING"
        label = report_type.replace("_", " ").title()
        return {
            "status": "confirmation_required",
            "pending_action": sess.pending_action,
            "confirmation_prompt": (
                f"The {label} is ready for {recipient}. Do you want me to send it? "
                "Please say 'yes' to confirm or 'no' to cancel."
            ),
        }

    def execute_safe_tool(
        self, name: str, args: Dict[str, Any], db: Session, session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute an approved safe tool by name with arguments.
        Rejects any unrecognized or unapproved function calls.
        """
        ALLOWED_TOOLS = {
            "get_case_summary",
            "get_case_intelligence",
            "get_compromise_summary",
            "get_report",
            "generate_report",
            "request_report_send_confirmation",
        }
        if name not in ALLOWED_TOOLS:
            logger.warning("Rejected unapproved tool call: %s", name)
            return {"error": f"Tool '{name}' is not permitted by CounterPulse security policy."}

        case_id = args.get("case_id")
        if not case_id:
            return {"error": "Missing required argument 'case_id'."}

        if name == "get_case_summary":
            return self.get_case_summary(case_id=case_id, db=db)
        elif name == "get_case_intelligence":
            return self.get_case_intelligence(case_id=case_id, db=db)
        elif name == "get_compromise_summary":
            return self.get_compromise_summary(case_id=case_id, db=db)
        elif name == "get_report":
            return self.get_report(case_id=case_id, report_type=args.get("report_type", ""), db=db)
        elif name == "generate_report":
            return self.generate_report(case_id=case_id, report_type=args.get("report_type", ""), db=db)
        elif name == "request_report_send_confirmation":
            return self.request_report_send_confirmation(
                case_id=case_id,
                report_type=args.get("report_type", ""),
                db=db,
                session_id=session_id,
            )
        return {"error": f"Unhandled tool '{name}'"}

    def parse_intent(self, transcript: str) -> str:
        """
        Identify voice intent using pattern matching with high precision across:
        - English
        - Hindi (हिंदी / Romanized)
        - Kannada (ಕನ್ನಡ / Romanized)

        CRITICAL SAFETY:
        Cancellation and negative intents are ALWAYS evaluated first before confirmation.
        """
        t = transcript.lower().strip()

        # 1. Cancellation & Negative Intents (Checked first for strict safety)
        # English: no, cancel, stop, don't, do not, nevermind, abort
        # Hindi: नहीं, मत भेजो, रोको, रद्द करो, रुको, nahi, mat bhejo, roko, radd
        # Kannada: ಬೇಡ, ಕಳುಹಿಸಬೇಡಿ, ನಿಲ್ಲಿಸಿ, ರದ್ದುಮಾಡಿ, beda, kaluhisabedi, nillisi, raddu
        if re.search(
            r'\b(no|cancel|stop|don\'t|dont|do not|nevermind|wait|abort|reject|nahi|nahin|mat bhejo|roko|radd|beda|kaluhisabedi|nillisi|raddu)\b'
            r'|नहीं|मत भेजो|रोको|रद्द|रुको|ಬೇಡ|ಕಳುಹಿಸಬೇಡಿ|ನಿಲ್ಲಿಸಿ|ರದ್ದು',
            t
        ):
            return "CANCEL_ACTION"

        # 2. Consequential Dispatches (Checked before generic confirmation words like 'send'/'भेजो')
        # Cybercrime Complaint:
        if (
            any(w in t for w in ["send", "dispatch", "email", "bhejo", "kaluhisi", "भेजो", "ಕಳುಹಿಸಿ"])
            and any(w in t for w in ["complaint", "cybercrime", "ncrp", "police", "shikayat", "duru", "शिकायत", "ದೂರು", "ಸೈಬರ್"])
        ):
            return "SEND_CYBERCRIME_COMPLAINT"
        # Bank Dispute:
        if (
            any(w in t for w in ["send", "dispatch", "email", "bhejo", "kaluhisi", "भेजो", "ಕಳುಹಿಸಿ"])
            and any(w in t for w in ["bank", "dispute", "vivad", "vivada", "बैंक", "ಬ್ಯಾಂಕ್", "ವಿವಾದ"])
        ):
            return "SEND_BANK_DISPUTE"
        # Security Advisory:
        if (
            any(w in t for w in ["send", "dispatch", "bhejo", "kaluhisi", "भेजो", "ಕಳುಹಿಸಿ"])
            and any(w in t for w in ["advisory", "security", "suraksha", "bhadrata", "सलाह", "ಸಲಹೆ"])
        ):
            return "SEND_SECURITY_ADVISORY"
        if ("send" in t or "email" in t or "भेजो" in t or "ಕಳುಹಿಸಿ" in t) and ("email" in t or "ईमेल" in t or "ಇಮೇಲ್" in t):
            return "SEND_CYBERCRIME_COMPLAINT"

        # 3. Confirmation & Proceed
        # English: yes, confirm, proceed, send it, approve, do it, yes please
        # Hindi: हाँ, भेज दो, पुष्टि, haan, bhej do, theek hai, kardo
        # Kannada: ಹೌದು, ಮುಂದುವರಿಸಿ, ದೃಢೀಕರಿಸಿ, haudu, munduvarisi, kalsu
        if re.search(
            r'\b(yes|confirm|proceed|send it|approve and send|do it|haan|bhejo|bhej do|theek hai|kardo|haudu|kaluhisi|munduvarisi|kalsu|yes please)\b'
            r'|हाँ|भेजो|भेज दो|पुष्टि|स्वीकृत|ಹೌದು|ಕಳುಹಿಸಿ|ಮುಂದುವರಿಸಿ|ದೃಢೀಕರಿಸಿ',
            t
        ):
            return "CONFIRM_ACTION"

        # 4. Report Generation & Retrieval
        if "cybercrime" in t or "cyber complaint" in t or (("read" in t or "padho" in t or "odi" in t or "पढ़ो" in t or "ಓದಿ" in t) and ("complaint" in t or "shikayat" in t or "duru" in t or "शिकायत" in t or "ದೂರು" in t)):
            return "READ_CYBERCRIME_COMPLAINT"
        if "bank dispute" in t or "dispute letter" in t or "bank letter" in t or "बैंक विवाद" in t or "ಬ್ಯಾಂಕ್ ವಿವಾದ" in t or "bank vivad" in t:
            return "GENERATE_BANK_DISPUTE"
        if "security advisory" in t or "safety steps" in t or "सुरक्षा सलाह" in t or "ಭದ್ರತಾ ಸಲಹೆ" in t or "suraksha salah" in t:
            return "READ_SECURITY_ADVISORY"

        # 5. Intelligence Queries
        if (
            re.search(r'\b(what happened|summarize|tell me what happened|summary|incident|kya hua|yenayithu|enayithu|enaitu|yenaitu)\b', t)
            or "क्या हुआ" in t
            or "ಏನಾಯಿತು" in t
            or "ಏನಾಯ್ತು" in t
        ):
            return "WHAT_HAPPENED"

        if (
            re.search(r'\b(compromised|accounts?|credentials?|devices?|compromise assessment|khate|khategalu)\b', t)
            or "खाते" in t
            or "क्या चोरी हुआ" in t
            or "ಖಾತೆಗಳು" in t
            or "ಏನು ಕಳವಾಗಿದೆ" in t
        ):
            return "WHAT_COMPROMISED"

        if (
            re.search(r'\b(evidence|vault|files|screenshots?|documents?|show me the evidence|saboot|purave)\b', t)
            or "सबूत दिखाओ" in t
            or "साक्ष्य दिखाओ" in t
            or "ಪುರಾವೆ ತೋರಿಸಿ" in t
            or "ಸಾಕ್ಷ್ಯ ತೋರಿಸಿ" in t
        ):
            return "SHOW_EVIDENCE"

        if (
            re.search(r'\b(analyze|investigate|run analysis|ai pipeline|orchestrate|vishleshan|thanihe)\b', t)
            or "विश्लेषण" in t
            or "जांच करो" in t
            or "ವಿಶ್ಲೇಷಿಸಿ" in t
            or "ತನಿಖೆ" in t
        ):
            return "ANALYZE_CASE"

        return "UNKNOWN"

    async def execute_command(
        self,
        case_id: str,
        cmd: VoiceCommandRequest,
        db: Session,
        email_provider: Optional[EmailProvider] = None,
        ai_provider: Optional[AIProvider] = None,
    ) -> VoiceCommandResponse:
        """
        Public entrypoint for executing voice commands.
        Wraps dispatch with optional Gemini Live 24kHz speech synthesis.
        """
        resp = await self._dispatch_command(
            case_id=case_id,
            cmd=cmd,
            db=db,
            email_provider=email_provider,
            ai_provider=ai_provider,
        )
        if cmd.synthesize or (cmd.audio_base64 and settings.GEMINI_API_KEY):
            resp.audio_base64 = await self.synthesize_live_audio(resp.response_text)
        return resp

    async def synthesize_live_audio(self, text: str) -> Optional[str]:
        """
        Synthesize natural 24kHz linear PCM audio speech for response text via Gemini Live.
        Returns base64-encoded audio string, or None if unconfigured or in offline test mode.
        """
        if not settings.GEMINI_API_KEY or AIProviderFactory.get_override_provider() is not None:
            return None

        async def _connect_and_synthesize() -> Optional[str]:
            from google import genai
            from google.genai import types
            import base64

            client = genai.Client(api_key=settings.GEMINI_API_KEY)
            config = types.LiveConnectConfig(
                response_modalities=["AUDIO"],
                system_instruction="You are CounterPulse Voice Layer. Read the text aloud clearly, concisely, and professionally in the target language (English, Hindi, or Kannada)."
            )
            audio_chunks = bytearray()
            async with client.aio.live.connect(model=settings.GEMINI_LIVE_MODEL, config=config) as session:
                await session.send_client_content(
                    turns=[types.Content(role="user", parts=[types.Part.from_text(text=f"Read this text clearly: {text}")])],
                    turn_complete=True
                )
                async for response in session.receive():
                    sc = response.server_content
                    if sc and sc.model_turn:
                        for part in sc.model_turn.parts:
                            if part.inline_data and part.inline_data.data:
                                audio_chunks.extend(part.inline_data.data)
                    if sc and sc.turn_complete:
                        break
            if audio_chunks:
                return base64.b64encode(audio_chunks).decode("ascii")
            return None

        try:
            return await asyncio.wait_for(_connect_and_synthesize(), timeout=12.0)
        except Exception as e:
            logger.warning("Gemini Live speech synthesis skipped or failed: %s", e)
            return None

    async def _dispatch_command(
        self,
        case_id: str,
        cmd: VoiceCommandRequest,
        db: Session,
        email_provider: Optional[EmailProvider] = None,
        ai_provider: Optional[AIProvider] = None,
    ) -> VoiceCommandResponse:
        """
        Processes voice command, applies confirmation gates for consequential actions,
        and returns structured response with vocalized response_text.
        """
        case = db.query(Case).filter(Case.id == case_id).first()
        if not case:
            return VoiceCommandResponse(
                intent="ERROR",
                response_text=f"Case '{case_id}' was not found in the incident vault.",
                voice_state="ERROR",
            )

        sess = self.get_or_create_session(cmd.session_id, case_id)
        sess.voice_state = "PROCESSING"

        transcript = cmd.transcript.strip()
        intent = self.parse_intent(transcript)

        # 1. HANDLE CONFIRMATION OF PENDING CONSEQUENTIAL ACTION
        if intent == "CONFIRM_ACTION":
            if not sess.pending_action:
                sess.voice_state = "IDLE"
                return VoiceCommandResponse(
                    intent="NO_PENDING_ACTION",
                    response_text="There is no pending consequential action requiring confirmation. How else can I assist with this investigation?",
                    voice_state="IDLE",
                )

            pending = sess.pending_action
            action_type = pending.get("action")

            if action_type == "send_report":
                report_id = pending["report_id"]
                report_type = pending["report_type"]
                recipient = pending.get("recipient") or settings.DEMO_RECIPIENT_EMAIL

                try:
                    # 1. Authoritative backend approval
                    self.report_svc.approve_report(
                        case_id=case_id,
                        report_id=report_id,
                        db=db,
                        recipient_email=recipient,
                    )

                    # 2. Authoritative backend dispatch
                    dispatched = self.report_svc.send_approved_report(
                        case_id=case_id,
                        report_id=report_id,
                        db=db,
                        recipient_email=recipient,
                        attach_passport_pdf=True,
                        email_provider=email_provider,
                    )

                    sess.pending_action = None
                    sess.voice_state = "RESPONDING"
                    label = report_type.replace("_", " ").title()

                    return VoiceCommandResponse(
                        intent="CONFIRM_ACTION",
                        response_text=f"Confirmed. The {label} has been approved and dispatched to {recipient}. An official audit event has been recorded.",
                        voice_state="IDLE",
                        action_executed=f"send_{report_type}",
                        details={"report_id": report_id, "recipient": recipient, "sent_at": dispatched.sent_at.isoformat() if dispatched.sent_at else None},
                    )

                except Exception as e:
                    logger.error("Error executing confirmed voice dispatch: %s", e)
                    sess.voice_state = "ERROR"
                    return VoiceCommandResponse(
                        intent="ERROR",
                        response_text=f"Failed to dispatch report: {str(e)}. Please review the Response Center.",
                        voice_state="ERROR",
                    )

            # Unknown pending action
            sess.pending_action = None
            sess.voice_state = "IDLE"
            return VoiceCommandResponse(
                intent="CONFIRM_ACTION",
                response_text="Pending action resolved.",
                voice_state="IDLE",
            )

        # 2. HANDLE CANCELLATION
        if intent == "CANCEL_ACTION":
            if sess.pending_action:
                p_type = sess.pending_action.get("report_type", "report")
                sess.pending_action = None
                sess.voice_state = "IDLE"
                return VoiceCommandResponse(
                    intent="CANCEL_ACTION",
                    response_text=f"Dispatch cancelled. The {p_type.replace('_', ' ')} draft remains safe in draft state and was not transmitted.",
                    voice_state="IDLE",
                )
            sess.voice_state = "IDLE"
            return VoiceCommandResponse(
                intent="CANCEL_ACTION",
                response_text="Action cancelled. Standing by for your next command.",
                voice_state="IDLE",
            )

        # 3. CONSEQUENTIAL ACTION TRIGGERS (Require Confirmation)
        if intent in ("SEND_CYBERCRIME_COMPLAINT", "SEND_BANK_DISPUTE", "SEND_SECURITY_ADVISORY"):
            target_type = (
                "cybercrime_complaint" if intent == "SEND_CYBERCRIME_COMPLAINT"
                else "bank_dispute" if intent == "SEND_BANK_DISPUTE"
                else "security_advisory"
            )

            # Ensure reports exist or generate drafts
            try:
                reports = self.report_svc.get_reports_for_case(case_id=case_id, db=db)
                target_report = next((r for r in reports if r.report_type == target_type), None)
            except Exception:
                target_report = None

            if not target_report:
                sess.voice_state = "ERROR"
                return VoiceCommandResponse(
                    intent="ERROR",
                    response_text="The draft report is not ready yet because incident analysis has not been performed. Say 'Analyze this case' first.",
                    voice_state="ERROR",
                )

            recipient = target_report.recipient_email or settings.DEMO_RECIPIENT_EMAIL
            label = target_type.replace("_", " ").title()

            # Store pending action and ask for confirmation
            sess.pending_action = {
                "action": "send_report",
                "report_id": target_report.id,
                "report_type": target_type,
                "recipient": recipient,
            }
            sess.voice_state = "RESPONDING"

            confirm_prompt = (
                f"The {label} draft is ready for recipient {recipient}. "
                f"Do you want me to send it? Please say 'yes' to confirm or 'no' to cancel."
            )

            return VoiceCommandResponse(
                intent=intent,
                response_text=confirm_prompt,
                voice_state="LISTENING",
                requires_confirmation=True,
                pending_action=sess.pending_action,
                details={"report_id": target_report.id, "recipient": recipient},
            )

        # 4. INFORMATIONAL & INVESTIGATION COMMANDS (No Consequential External Send)

        # A. Analyze Case
        if intent == "ANALYZE_CASE":
            if not case.evidence or len(case.evidence) == 0:
                sess.voice_state = "IDLE"
                return VoiceCommandResponse(
                    intent="ANALYZE_CASE",
                    response_text="Cannot analyze yet because no evidence has been uploaded to this case vault. Please upload an image, audio file, or chat transcript first.",
                    voice_state="IDLE",
                )

            try:
                intel = await self.orchestrator.analyze_case(
                    case_id=case_id, db=db, provider_override=ai_provider, persist_to_db=True
                )
                loss_str = f"₹{case.financial_loss:,.2f}" if case.financial_loss else "undisclosed amounts"
                resp = (
                    f"Incident analysis complete. CounterPulse reconstructed this incident as a "
                    f"{intel.reconstruction.scam_category} of {intel.reconstruction.severity_level} severity, "
                    f"with total estimated loss of {loss_str}. Draft bank dispute and cybercrime packages are generated."
                )
                sess.voice_state = "IDLE"
                return VoiceCommandResponse(
                    intent="ANALYZE_CASE",
                    response_text=resp,
                    voice_state="IDLE",
                    details={"scam_category": intel.reconstruction.scam_category, "severity": intel.reconstruction.severity_level},
                )
            except Exception as e:
                logger.error("Error executing voice analysis: %s", e)
                sess.voice_state = "ERROR"
                return VoiceCommandResponse(
                    intent="ERROR",
                    response_text=f"Analysis pipeline encountered an error: {str(e)}.",
                    voice_state="ERROR",
                )

        # B. What Happened
        if intent == "WHAT_HAPPENED":
            summary = case.summary or case.description
            if not summary:
                resp = "This incident has not been analyzed yet. Say 'Analyze this case' to initiate full agentic reconstruction."
            else:
                cat = case.scam_category or "Financial Fraud"
                loss = f"₹{case.financial_loss:,.2f}" if case.financial_loss else "an unconfirmed amount"
                resp = f"Here is what happened: This is a {cat} involving {loss}. {summary}"
                if case.modus_operandi:
                    resp += f" Psychological tactics: {case.modus_operandi[:200]}..."

            sess.voice_state = "IDLE"
            return VoiceCommandResponse(
                intent="WHAT_HAPPENED",
                response_text=resp,
                voice_state="IDLE",
                details={"summary": case.summary, "category": case.scam_category},
            )

        # C. What Accounts are Compromised
        if intent == "WHAT_COMPROMISED":
            comps = case.compromise_assessments
            if not comps or len(comps) == 0:
                resp = "No compromise assessments have been recorded yet. Run analysis to assess exposed bank accounts and credentials."
            else:
                findings = []
                for c in comps:
                    cat_label = (c.category or "asset").replace("_", " ").title()
                    findings.append(f"{cat_label}: risk level {c.risk_level.upper()} - {c.details or c.recommended_action}")
                resp = f"Compromise assessment report: {'. '.join(findings)}."

            sess.voice_state = "IDLE"
            return VoiceCommandResponse(
                intent="WHAT_COMPROMISED",
                response_text=resp,
                voice_state="IDLE",
                details={"compromises_count": len(comps) if comps else 0},
            )

        # D. Show Evidence
        if intent == "SHOW_EVIDENCE":
            ev_list = case.evidence
            if not ev_list or len(ev_list) == 0:
                resp = "The evidence vault for this case is currently empty. You can upload transaction screenshots, PDF notices, or call logs."
            else:
                types = {}
                for e in ev_list:
                    types[e.evidence_type] = types.get(e.evidence_type, 0) + 1
                type_summary = ", ".join([f"{count} {k} files" for k, count in types.items()])
                resp = f"The vault contains {len(ev_list)} forensic items: {type_summary}. All evidence hashes and provenance links are preserved."

            sess.voice_state = "IDLE"
            return VoiceCommandResponse(
                intent="SHOW_EVIDENCE",
                response_text=resp,
                voice_state="IDLE",
                details={"evidence_count": len(ev_list) if ev_list else 0},
            )

        # E. Read Cybercrime Complaint
        if intent == "READ_CYBERCRIME_COMPLAINT":
            try:
                reports = self.report_svc.get_reports_for_case(case_id=case_id, db=db)
                c_rep = next((r for r in reports if r.report_type == "cybercrime_complaint"), None)
            except Exception:
                c_rep = None

            if not c_rep:
                resp = "The cybercrime complaint draft is not available. Please run case analysis first."
            else:
                first_paragraph = c_rep.content_markdown.split("\n\n")[0] if "\n\n" in c_rep.content_markdown else c_rep.content_markdown[:250]
                resp = f"Subject: {c_rep.title}. Complaint Summary: {first_paragraph}. To send this report, say 'Send the complaint email'."

            sess.voice_state = "IDLE"
            return VoiceCommandResponse(
                intent="READ_CYBERCRIME_COMPLAINT",
                response_text=resp,
                voice_state="IDLE",
                details={"report_id": c_rep.id if c_rep else None},
            )

        # F. Generate / Read Bank Dispute
        if intent == "GENERATE_BANK_DISPUTE":
            try:
                reports = self.report_svc.get_reports_for_case(case_id=case_id, db=db)
                b_rep = next((r for r in reports if r.report_type == "bank_dispute"), None)
            except Exception:
                b_rep = None

            if not b_rep:
                resp = "Bank dispute draft is not available. Please run incident analysis first."
            else:
                first_lines = b_rep.content_markdown[:300]
                resp = f"Bank Dispute Package: {b_rep.title}. Narrative: {first_lines}... Grounded in RBI customer protection circular. Say 'Send bank dispute' if you wish to dispatch."

            sess.voice_state = "IDLE"
            return VoiceCommandResponse(
                intent="GENERATE_BANK_DISPUTE",
                response_text=resp,
                voice_state="IDLE",
                details={"report_id": b_rep.id if b_rep else None},
            )

        # G. Read Security Advisory
        if intent == "READ_SECURITY_ADVISORY":
            try:
                reports = self.report_svc.get_reports_for_case(case_id=case_id, db=db)
                s_rep = next((r for r in reports if r.report_type == "security_advisory"), None)
            except Exception:
                s_rep = None

            if not s_rep:
                resp = "Emergency security advisory is not generated yet. Say 'Analyze this case' first."
            else:
                resp = f"Emergency Security Advisory: {s_rep.content_markdown[:350]}..."

            sess.voice_state = "IDLE"
            return VoiceCommandResponse(
                intent="READ_SECURITY_ADVISORY",
                response_text=resp,
                voice_state="IDLE",
                details={"report_id": s_rep.id if s_rep else None},
            )

        # UNKNOWN COMMAND FALLBACK
        sess.voice_state = "IDLE"
        return VoiceCommandResponse(
            intent="UNKNOWN",
            response_text=(
                "I am the CounterPulse voice control assistant. You can speak commands such as: "
                "'Analyze this case', 'What happened?', 'What accounts are compromised?', 'Show me the evidence', "
                "'Read the cybercrime complaint', 'Generate a bank dispute', 'Read the security advisory', "
                "or 'Send the complaint email'."
            ),
            voice_state="IDLE",
        )

# Global singleton
voice_service = VoiceControlService()
