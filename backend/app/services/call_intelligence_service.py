import re
import json
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session

from backend.app.models.case import Case
from backend.app.models.evidence import Evidence
from backend.app.models.indicator import Indicator
from backend.app.models.call_log import CallSession, CallMessage
from backend.app.schemas.call_log import (
    CallMessageCreate,
    CallSessionCreate,
    CallSessionResponse,
    CallMessageResponse,
    ExtractedIndicatorItem,
    LiveExtractedIntelligence,
    PromoteCallResponse,
)
from backend.app.services.ai.factory import AIProviderFactory
from backend.app.services.ai.base import AIProvider

logger = logging.getLogger(__name__)

# Strict forensic disclaimer
DISCLAIMER_TEXT = (
    "Extracted indicators represent investigative artifacts from the conversation; "
    "does not automatically establish criminality of named individuals or entities."
)

# Robust Pattern Matchers for Conversation Transcripts
PHONE_REGEX = re.compile(
    r'(?:\+?91[\s-]?)?[6-9]\d{4}[\s-]?\d{5}|\b\d{3}[-.\s]\d{3}[-.\s]\d{4}\b|\b\d{10}\b'
)
UPI_REGEX = re.compile(
    r'\b[a-zA-Z0-9.\-_]{2,256}@[a-zA-Z]{2,64}\b'
)
URL_REGEX = re.compile(
    r'https?://(?:www\.)?[-a-zA-Z0-9@:%._+~#=]{1,256}\.[a-zA-Z0-9()]{1,24}\b(?:[-a-zA-Z0-9()@:%_+.~#?&/=]*)'
)
EMAIL_REGEX = re.compile(
    r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b'
)
AMOUNT_REGEX = re.compile(
    r'(?:INR|Rs\.?|₹)\s*([\d,]+(?:\.\d{1,2})?)|(\b[\d,]+(?:\.\d{1,2})?\s*(?:rupees|lakhs?|crores?)\b)',
    re.IGNORECASE
)

class CallIntelligenceService:
    """
    Analyzes live or uploaded conversation transcripts.
    Dynamically extracts indicators, psychological tactics, and claimed entities
    with strict source provenance (Message #N) and UNVERIFIED status.
    """

    def create_session(
        self, case_id: str, session_in: CallSessionCreate, db: Session
    ) -> CallSession:
        """Create a new CallSession for a case."""
        case = db.query(Case).filter(Case.id == case_id).first()
        if not case:
            raise ValueError(f"Case '{case_id}' not found.")

        session = CallSession(
            case_id=case_id,
            title=session_in.title or "Live Scam Call Session",
            caller_label=session_in.caller_label or "Suspect / Impersonator",
            callee_label=session_in.callee_label or "Victim / Callee",
            status="active",
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        return session

    def get_session(self, case_id: str, session_id: str, db: Session) -> CallSession:
        """Retrieve a CallSession ensuring case match."""
        session = (
            db.query(CallSession)
            .filter(CallSession.id == session_id, CallSession.case_id == case_id)
            .first()
        )
        if not session:
            raise ValueError(f"Call session '{session_id}' not found for case '{case_id}'.")
        return session

    def list_sessions(self, case_id: str, db: Session) -> List[CallSession]:
        """List all CallSessions for a case."""
        return (
            db.query(CallSession)
            .filter(CallSession.case_id == case_id)
            .order_by(CallSession.created_at.desc())
            .all()
        )

    def extract_regex_indicators(
        self, text: str, message_index: int
    ) -> List[ExtractedIndicatorItem]:
        """Extract high-precision pattern matches from a message text."""
        items: List[ExtractedIndicatorItem] = []
        source_ref = f"Message #{message_index}"

        # Phone numbers
        for m in PHONE_REGEX.finditer(text):
            val = m.group(0).strip()
            # Avoid matching pure 10-digit numbers that are UPIs or amounts
            if "@" not in val and len(re.sub(r'\D', '', val)) >= 10:
                items.append(
                    ExtractedIndicatorItem(
                        type="phone",
                        value=val,
                        source_message_index=message_index,
                        source_reference=source_ref,
                        confidence="high",
                        status="UNVERIFIED",
                        context=text,
                    )
                )

        # UPI IDs
        for m in UPI_REGEX.finditer(text):
            val = m.group(0).strip()
            # Filter out standard email domains to isolate banking UPI handles
            if not val.endswith((".com", ".org", ".net", ".edu", ".gov")):
                items.append(
                    ExtractedIndicatorItem(
                        type="upi",
                        value=val,
                        source_message_index=message_index,
                        source_reference=source_ref,
                        confidence="high",
                        status="UNVERIFIED",
                        context=text,
                    )
                )

        # URLs
        for m in URL_REGEX.finditer(text):
            items.append(
                ExtractedIndicatorItem(
                    type="url",
                    value=m.group(0).strip(),
                    source_message_index=message_index,
                    source_reference=source_ref,
                    confidence="high",
                    status="UNVERIFIED",
                    context=text,
                )
            )

        # Emails
        for m in EMAIL_REGEX.finditer(text):
            val = m.group(0).strip()
            items.append(
                ExtractedIndicatorItem(
                    type="email",
                    value=val,
                    source_message_index=message_index,
                    source_reference=source_ref,
                    confidence="high",
                    status="UNVERIFIED",
                    context=text,
                )
            )

        # Financial Amounts
        for m in AMOUNT_REGEX.finditer(text):
            raw = m.group(0).strip()
            items.append(
                ExtractedIndicatorItem(
                    type="amount",
                    value=raw,
                    source_message_index=message_index,
                    source_reference=source_ref,
                    confidence="medium",
                    status="UNVERIFIED",
                    context=text,
                )
            )

        return items

    async def extract_ai_conversation_intel(
        self,
        full_transcript: str,
        messages: List[CallMessage],
        provider: Optional[AIProvider] = None,
    ) -> Dict[str, Any]:
        """
        Use dynamic AI provider to extract claimed persons, organizations,
        psychological tactics, and requested actions across the dialogue.
        """
        try:
            ai = provider or AIProviderFactory.get_provider()

            prompt = (
                f"DIALOGUE TRANSCRIPT:\n{full_transcript}\n\n"
                "TASK:\n"
                "Analyze this dialogue defensively. Extract forensic entities and psychological manipulation tactics.\n"
                "Output JSON with these fields:\n"
                "- claimed_persons: list of {name, role, source_message_index}\n"
                "- claimed_organizations: list of {name, source_message_index}\n"
                "- scam_tactics: list of {tactic, description, severity, source_message_index}\n"
                "- requested_actions: list of {action, urgency, source_message_index}\n"
                "- summary: concise 1-2 sentence executive summary of caller's objective\n\n"
                "CRITICAL LEGAL REQUIREMENT: Treat all names and entities as UNVERIFIED claims made by the speaker.\n"
                "Return valid JSON only."
            )

            system_instruction = (
                "You are a Forensic Cybercrime Intelligence Analyst. Extract entities, impersonated offices, "
                "and coercive tactics from conversation transcripts. Never invent facts unsupported by the text."
            )

            raw_text = await ai.generate_text(prompt=prompt, system_instruction=system_instruction)
            cleaned = raw_text.strip()
            if cleaned.startswith("```"):
                cleaned = re.sub(r"^```[a-zA-Z]*\n", "", cleaned)
                cleaned = re.sub(r"\n```$", "", cleaned)
            return json.loads(cleaned)
        except Exception as e:
            logger.warning("AI conversation extraction returned unparseable output or provider error: %s", e)
            # Graceful fallback: return empty structure rather than crashing
            return {
                "claimed_persons": [],
                "claimed_organizations": [],
                "scam_tactics": [],
                "requested_actions": [],
                "summary": "Transcript recorded. Awaiting full agentic reconstruction.",
            }

    async def process_message(
        self,
        case_id: str,
        session_id: str,
        msg_in: CallMessageCreate,
        db: Session,
        provider: Optional[AIProvider] = None,
    ) -> Tuple[CallMessage, LiveExtractedIntelligence]:
        """
        Append a message to the call session and dynamically extract live intelligence.
        """
        session = self.get_session(case_id, session_id, db)

        msg_count = len(session.messages)
        next_index = msg_count + 1

        message = CallMessage(
            session_id=session.id,
            speaker=msg_in.speaker,
            message_index=next_index,
            content=msg_in.content.strip(),
            timestamp_offset=msg_in.timestamp_offset or f"{next_index * 15 // 60:02d}:{next_index * 15 % 60:02d}",
        )
        db.add(message)
        db.commit()
        db.refresh(session)

        # Assemble full transcript
        transcript_lines = []
        for m in session.messages:
            speaker_label = session.caller_label if m.speaker == "caller" else session.callee_label if m.speaker == "callee" else "System"
            transcript_lines.append(f"[{m.timestamp_offset or '00:00'}] {speaker_label} (Message #{m.message_index}): {m.content}")

        full_transcript = "\n".join(transcript_lines)
        session.raw_transcript = full_transcript

        # 1. Regex Extraction across all messages
        all_regex_items: List[ExtractedIndicatorItem] = []
        for m in session.messages:
            all_regex_items.extend(self.extract_regex_indicators(m.content, m.message_index))

        # 2. AI Entity & Tactic Extraction
        ai_data = await self.extract_ai_conversation_intel(full_transcript, session.messages, provider=provider)

        # Group and build LiveExtractedIntelligence
        phones = [i for i in all_regex_items if i.type == "phone"]
        upis = [i for i in all_regex_items if i.type == "upi"]
        urls = [i for i in all_regex_items if i.type == "url"]
        emails = [i for i in all_regex_items if i.type == "email"]
        amounts = [i for i in all_regex_items if i.type == "amount"]

        persons = [
            ExtractedIndicatorItem(
                type="person",
                value=f"{p.get('name', 'Unknown')} ({p.get('role', 'Claimed Role')})",
                source_message_index=int(p.get("source_message_index", 0) or 0),
                source_reference=f"Message #{p.get('source_message_index', 0)}",
                confidence="medium",
                status="UNVERIFIED",
                context=p.get("role"),
            )
            for p in ai_data.get("claimed_persons", [])
            if p.get("name")
        ]

        orgs = [
            ExtractedIndicatorItem(
                type="organization",
                value=o.get("name", "Unknown"),
                source_message_index=int(o.get("source_message_index", 0) or 0),
                source_reference=f"Message #{o.get('source_message_index', 0)}",
                confidence="medium",
                status="UNVERIFIED",
            )
            for o in ai_data.get("claimed_organizations", [])
            if o.get("name")
        ]

        tactics = [
            ExtractedIndicatorItem(
                type="tactic",
                value=f"{t.get('tactic', 'Tactic')}: {t.get('description', '')}",
                source_message_index=int(t.get("source_message_index", 0) or 0),
                source_reference=f"Message #{t.get('source_message_index', 0)}",
                confidence="high",
                status="FLAGGED",
                context=t.get("severity", "medium"),
            )
            for t in ai_data.get("scam_tactics", [])
            if t.get("tactic")
        ]

        actions = [
            ExtractedIndicatorItem(
                type="action",
                value=f"{a.get('action', 'Action')} (Urgency: {a.get('urgency', 'high')})",
                source_message_index=int(a.get("source_message_index", 0) or 0),
                source_reference=f"Message #{a.get('source_message_index', 0)}",
                confidence="medium",
                status="FLAGGED",
            )
            for a in ai_data.get("requested_actions", [])
            if a.get("action")
        ]

        all_indicators = phones + upis + urls + emails + amounts + persons + orgs + tactics + actions

        intelligence = LiveExtractedIntelligence(
            indicators=all_indicators,
            phone_numbers=phones,
            upi_ids=upis,
            urls=urls,
            emails=emails,
            claimed_persons=persons,
            claimed_organizations=orgs,
            financial_amounts=amounts,
            scam_tactics=tactics,
            requested_actions=actions,
            summary=ai_data.get("summary"),
            disclaimer=DISCLAIMER_TEXT,
        )

        session.extracted_intelligence_json = intelligence.model_dump_json()
        db.commit()
        db.refresh(session)

        return message, intelligence

    def get_session_response(self, session: CallSession) -> CallSessionResponse:
        """Helper to format a CallSession into CallSessionResponse."""
        intel: Optional[LiveExtractedIntelligence] = None
        if session.extracted_intelligence_json:
            try:
                intel = LiveExtractedIntelligence.model_validate_json(session.extracted_intelligence_json)
            except Exception:
                pass

        return CallSessionResponse(
            id=session.id,
            case_id=session.case_id,
            title=session.title,
            caller_label=session.caller_label,
            callee_label=session.callee_label,
            status=session.status,
            message_count=len(session.messages),
            messages=[CallMessageResponse.model_validate(m) for m in session.messages],
            intelligence=intel,
            evidence_id=session.evidence_id,
            created_at=session.created_at,
            updated_at=session.updated_at,
        )

    def promote_to_case_evidence(
        self, case_id: str, session_id: str, db: Session
    ) -> PromoteCallResponse:
        """
        Promote this CallSession into the case's authoritative Evidence Vault.
        Creates an Evidence record (evidence_type='chat') and maps extracted indicators
        into case.indicators with source_evidence_id and UNVERIFIED status.
        """
        session = self.get_session(case_id, session_id, db)
        case = db.query(Case).filter(Case.id == case_id).first()

        if not session.raw_transcript or session.raw_transcript.strip() == "":
            raise ValueError("Call session contains no messages to promote.")

        # 1. Create Evidence record
        evidence = Evidence(
            case_id=case_id,
            evidence_type="chat",
            filename=f"Live_Call_{session.id}.txt",
            mime_type="text/plain",
            file_size=len(session.raw_transcript.encode("utf-8")),
            raw_content=session.raw_transcript,
            processing_status="processed",
        )
        db.add(evidence)
        db.flush()

        # 2. Extract indicators from stored intelligence and link to Evidence
        created_ind_count = 0
        if session.extracted_intelligence_json:
            try:
                intel = LiveExtractedIntelligence.model_validate_json(session.extracted_intelligence_json)
                for item in intel.indicators:
                    if item.type in ("phone", "upi", "url", "email", "person", "organization"):
                        ind_type = "upi_id" if item.type == "upi" else "phone_number" if item.type == "phone" else item.type
                        ind = Indicator(
                            case_id=case_id,
                            indicator_type=ind_type,
                            value=item.value,
                            confidence=item.confidence,
                            verification_status="unverified",
                            source_evidence_id=evidence.id,
                            source_reference=f"Call {session.id} - {item.source_reference}",
                        )
                        db.add(ind)
                        created_ind_count += 1
            except Exception as e:
                logger.error("Failed to map indicators during promotion: %s", e)

        session.status = "promoted"
        session.evidence_id = evidence.id
        db.commit()

        return PromoteCallResponse(
            session_id=session.id,
            evidence_id=evidence.id,
            indicators_created_count=created_ind_count,
            message="Call transcript promoted to Evidence Vault with linked indicators.",
        )

# Global singleton
call_intelligence_service = CallIntelligenceService()
