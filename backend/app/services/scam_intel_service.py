import re
import json
import logging
from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy.orm import Session

from backend.app.models.case import Case
from backend.app.models.evidence import Evidence
from backend.app.models.indicator import Indicator
from backend.app.models.call_log import CallSession, CallMessage
from backend.app.schemas.scam_intel import (
    ScamIntelligenceItem,
    ScamIntelligenceAnalyzeRequest,
    ScamIntelligenceAnalysisResponse,
    AddIndicatorsToCaseRequest,
    AddIndicatorsToCaseResponse,
    DISCLAIMER_TEXT,
)
from backend.app.schemas.ai_output import ScamIntelligenceOutput
from backend.app.services.agents.base import CaseContext
from backend.app.services.agents.scam_intel_agent import ScamIntelligenceAgent
from backend.app.services.call_intelligence_service import (
    PHONE_REGEX,
    UPI_REGEX,
    URL_REGEX,
    EMAIL_REGEX,
    AMOUNT_REGEX,
    call_intelligence_service,
)
from backend.app.services.ai.factory import AIProviderFactory
from backend.app.services.ai.base import AIProvider

logger = logging.getLogger(__name__)

# Transaction reference pattern (UTR numbers, IMPS reference, banking transaction IDs)
TXN_REF_REGEX = re.compile(
    r'\b(?:UTR|Ref(?:erence)?|Txn(?:\s*ID)?|Transaction\s*ID)[:\s#-]*([A-Za-z0-9]{8,24})\b',
    re.IGNORECASE,
)

class ScamIntelligenceService:
    """
    Service for analyzing conversation transcripts, extracting forensic indicators with
    provenance, and integrating them into CaseIntelligence and the authoritative Case vault.
    """

    def __init__(self):
        self.scam_agent = ScamIntelligenceAgent()

    def extract_regex_indicators(
        self,
        text: str,
        message_index: Optional[int] = None,
        source_ref_prefix: str = "Message",
        source_evidence_id: Optional[str] = None,
    ) -> List[ScamIntelligenceItem]:
        """Extract high-precision pattern matches from a message or text chunk."""
        items: List[ScamIntelligenceItem] = []
        source_ref = (
            f"{source_ref_prefix} #{message_index}"
            if message_index is not None
            else source_ref_prefix
        )

        # 1. Phone numbers
        for m in PHONE_REGEX.finditer(text):
            val = m.group(0).strip()
            digits = re.sub(r'\D', '', val)
            if "@" not in val and len(digits) >= 10:
                items.append(
                    ScamIntelligenceItem(
                        indicator_type="phone_number",
                        value=val,
                        confidence="high",
                        verification_status="unverified",
                        source_message_index=message_index,
                        source_reference=source_ref,
                        source_evidence_id=source_evidence_id,
                        context=text,
                    )
                )

        # 2. UPI IDs
        for m in UPI_REGEX.finditer(text):
            val = m.group(0).strip()
            if not val.endswith((".com", ".org", ".net", ".edu", ".gov")):
                items.append(
                    ScamIntelligenceItem(
                        indicator_type="upi_id",
                        value=val,
                        confidence="high",
                        verification_status="unverified",
                        source_message_index=message_index,
                        source_reference=source_ref,
                        source_evidence_id=source_evidence_id,
                        context=text,
                    )
                )

        # 3. URLs
        for m in URL_REGEX.finditer(text):
            items.append(
                ScamIntelligenceItem(
                    indicator_type="url",
                    value=m.group(0).strip(),
                    confidence="high",
                    verification_status="unverified",
                    source_message_index=message_index,
                    source_reference=source_ref,
                    source_evidence_id=source_evidence_id,
                    context=text,
                )
            )

        # 4. Email addresses
        for m in EMAIL_REGEX.finditer(text):
            items.append(
                ScamIntelligenceItem(
                    indicator_type="email",
                    value=m.group(0).strip(),
                    confidence="high",
                    verification_status="unverified",
                    source_message_index=message_index,
                    source_reference=source_ref,
                    source_evidence_id=source_evidence_id,
                    context=text,
                )
            )

        # 5. Financial Amounts
        for m in AMOUNT_REGEX.finditer(text):
            items.append(
                ScamIntelligenceItem(
                    indicator_type="financial_amount",
                    value=m.group(0).strip(),
                    confidence="medium",
                    verification_status="unverified",
                    source_message_index=message_index,
                    source_reference=source_ref,
                    source_evidence_id=source_evidence_id,
                    context=text,
                )
            )

        # 6. Transaction Reference IDs (UTR, Txn ID)
        for m in TXN_REF_REGEX.finditer(text):
            items.append(
                ScamIntelligenceItem(
                    indicator_type="transaction_id",
                    value=m.group(1).strip(),
                    confidence="high",
                    verification_status="unverified",
                    source_message_index=message_index,
                    source_reference=source_ref,
                    source_evidence_id=source_evidence_id,
                    context=m.group(0).strip(),
                )
            )

        return items

    def _split_into_messages(self, raw_text: str) -> List[Tuple[int, str, str]]:
        """
        Split a conversation transcript into indexed message tuples:
        (message_index, speaker, content).
        """
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        messages: List[Tuple[int, str, str]] = []

        for idx, line in enumerate(lines, start=1):
            # Check for speaker formats: "Caller: ...", "Victim: ...", "[00:15] DCP Vikram: ..."
            match = re.match(r'^(?:\[.*?\]\s*)?([^:]+):\s*(.*)$', line)
            if match:
                speaker = match.group(1).strip()
                content = match.group(2).strip()
            else:
                speaker = "Participant"
                content = line
            messages.append((idx, speaker, content))

        return messages

    async def analyze_conversation(
        self,
        case_id: str,
        req: ScamIntelligenceAnalyzeRequest,
        db: Session,
        provider: Optional[AIProvider] = None,
    ) -> ScamIntelligenceAnalysisResponse:
        """
        Dynamically analyzes a conversation transcript or case evidence without hardcoding.
        Extracts regex indicators and AI behavioral intelligence with source provenance.
        """
        case = db.query(Case).filter(Case.id == case_id).first()
        if not case:
            raise ValueError(f"Case '{case_id}' was not found in the incident vault.")

        # 1. Resolve conversation text and source evidence ID
        conversation_text = req.conversation_text
        source_evidence_id = req.evidence_id

        if not conversation_text:
            if req.evidence_id:
                ev = (
                    db.query(Evidence)
                    .filter(Evidence.id == req.evidence_id, Evidence.case_id == case_id)
                    .first()
                )
                if not ev:
                    raise ValueError(f"Evidence '{req.evidence_id}' not found for case '{case_id}'.")
                conversation_text = ev.raw_content
            else:
                # Fallback to chat/text evidence or call sessions on the case
                chat_ev = (
                    db.query(Evidence)
                    .filter(
                        Evidence.case_id == case_id,
                        Evidence.evidence_type.in_(["chat", "text"]),
                        Evidence.raw_content.isnot(None),
                    )
                    .first()
                )
                if chat_ev and chat_ev.raw_content:
                    conversation_text = chat_ev.raw_content
                    source_evidence_id = chat_ev.id
                else:
                    # Check CallSession
                    cs = (
                        db.query(CallSession)
                        .filter(CallSession.case_id == case_id)
                        .order_by(CallSession.created_at.desc())
                        .first()
                    )
                    if cs and cs.raw_transcript:
                        conversation_text = cs.raw_transcript
                        source_evidence_id = cs.evidence_id

        if not conversation_text or conversation_text.strip() == "":
            raise ValueError(
                "No conversation text or evidence found to analyze. Please provide conversation text or select an evidence source."
            )

        # 2. Parse dialogue messages
        parsed_messages = self._split_into_messages(conversation_text)

        # 3. Focus if selected_message_index requested
        target_messages = parsed_messages
        if req.selected_message_index is not None:
            focused = [m for m in parsed_messages if m[0] == req.selected_message_index]
            if focused:
                target_messages = focused

        # 4. Extract regex indicators across selected messages
        regex_items: List[ScamIntelligenceItem] = []
        for idx, speaker, content in target_messages:
            ref_prefix = f"Message"
            items = self.extract_regex_indicators(
                text=content,
                message_index=idx,
                source_ref_prefix=ref_prefix,
                source_evidence_id=source_evidence_id,
            )
            regex_items.extend(items)

        # 5. Dynamic AI Intelligence Extraction
        ai_provider = provider
        if not ai_provider:
            try:
                ai_provider = AIProviderFactory.get_provider()
            except Exception as e:
                logger.warning("AI provider unavailable for scam intelligence: %s", e)

        scam_type = "Digital Extortion / Impersonation"
        threat_assessment = "Suspect executed psychological intimidation to coerce unauthorized financial transfer."
        tactics_observed: List[str] = []
        psychological_triggers: List[str] = []
        claimed_entities: List[ScamIntelligenceItem] = []
        scam_tactics: List[ScamIntelligenceItem] = []
        requested_actions: List[ScamIntelligenceItem] = []
        conversation_summary = f"Analyzed conversation consisting of {len(parsed_messages)} messages."

        if ai_provider:
            # A. Execute ScamIntelligenceAgent
            try:
                context = CaseContext(
                    case_id=case_id,
                    title=case.title,
                    description=case.description,
                    combined_evidence_text=conversation_text,
                )
                scam_out: ScamIntelligenceOutput = await self.scam_agent.run(context, ai_provider)
                scam_type = scam_out.scam_type
                threat_assessment = scam_out.threat_assessment
                tactics_observed = scam_out.tactics_observed
                psychological_triggers = scam_out.psychological_triggers

                # Convert suspicious indicators found by agent
                for ind in scam_out.suspicious_indicators_found:
                    # If a specific message was selected, only include if indicator is present in that message
                    if req.selected_message_index is not None:
                        target_text = " ".join([m[2] for m in target_messages])
                        digits_ind = re.sub(r'\D', '', ind.indicator)
                        digits_text = re.sub(r'\D', '', target_text)
                        if ind.indicator.lower() not in target_text.lower() and (not digits_ind or digits_ind not in digits_text):
                            continue
                        src_ref = f"Message #{req.selected_message_index}"
                        src_msg_idx = req.selected_message_index
                    else:
                        src_ref = "AI Agent Extraction"
                        src_msg_idx = None

                    regex_items.append(
                        ScamIntelligenceItem(
                            indicator_type=ind.type,
                            value=ind.indicator,
                            confidence="high",
                            verification_status="unverified",
                            source_message_index=src_msg_idx,
                            source_reference=src_ref,
                            source_evidence_id=source_evidence_id,
                            context=ind.context,
                        )
                    )

                # Convert impersonated entities
                for ent in scam_out.impersonated_entities:
                    claimed_entities.append(
                        ScamIntelligenceItem(
                            indicator_type="organization",
                            value=ent,
                            confidence="medium",
                            verification_status="unverified",
                            source_reference="AI Extraction - Impersonated Agency",
                            source_evidence_id=source_evidence_id,
                            context="Claimed authority identity",
                        )
                    )
            except Exception as e:
                logger.warning("ScamIntelligenceAgent run failed or unconfigured: %s", e)

            # B. Execute fine-grained entity & action extraction
            try:
                dummy_msgs: List[CallMessage] = []
                conv_data = await call_intelligence_service.extract_ai_conversation_intel(
                    full_transcript=conversation_text,
                    messages=dummy_msgs,
                    provider=ai_provider,
                )
                if conv_data.get("summary"):
                    conversation_summary = conv_data["summary"]

                for p in conv_data.get("claimed_persons", []):
                    if p.get("name"):
                        claimed_entities.append(
                            ScamIntelligenceItem(
                                indicator_type="suspect_name",
                                value=f"{p['name']} ({p.get('role', 'Suspect')})",
                                confidence="medium",
                                verification_status="unverified",
                                source_message_index=int(p.get("source_message_index") or 1),
                                source_reference=f"Message #{p.get('source_message_index', 1)}",
                                source_evidence_id=source_evidence_id,
                                context=p.get("role"),
                            )
                        )

                for o in conv_data.get("claimed_organizations", []):
                    if o.get("name") and not any(o["name"].lower() in e.value.lower() for e in claimed_entities):
                        claimed_entities.append(
                            ScamIntelligenceItem(
                                indicator_type="organization",
                                value=o["name"],
                                confidence="medium",
                                verification_status="unverified",
                                source_message_index=int(o.get("source_message_index") or 1),
                                source_reference=f"Message #{o.get('source_message_index', 1)}",
                                source_evidence_id=source_evidence_id,
                            )
                        )

                for t in conv_data.get("scam_tactics", []):
                    if t.get("tactic"):
                        scam_tactics.append(
                            ScamIntelligenceItem(
                                indicator_type="scam_tactic",
                                value=f"{t['tactic']}: {t.get('description', '')}",
                                confidence="high",
                                verification_status="flagged",
                                source_message_index=int(t.get("source_message_index") or 1),
                                source_reference=f"Message #{t.get('source_message_index', 1)}",
                                source_evidence_id=source_evidence_id,
                                context=t.get("severity", "medium"),
                            )
                        )

                for a in conv_data.get("requested_actions", []):
                    if a.get("action"):
                        requested_actions.append(
                            ScamIntelligenceItem(
                                indicator_type="requested_action",
                                value=f"{a['action']} (Urgency: {a.get('urgency', 'high')})",
                                confidence="high",
                                verification_status="flagged",
                                source_message_index=int(a.get("source_message_index") or 1),
                                source_reference=f"Message #{a.get('source_message_index', 1)}",
                                source_evidence_id=source_evidence_id,
                            )
                        )
            except Exception as e:
                logger.warning("Call intelligence entity extraction error: %s", e)

        # 6. Deduplicate items by (type, normalized value)
        seen_keys = set()
        deduped_regex: List[ScamIntelligenceItem] = []
        for it in regex_items:
            key = (it.indicator_type, it.value.strip().lower())
            if key not in seen_keys:
                seen_keys.add(key)
                deduped_regex.append(it)

        # 7. Split into categorized subsets
        phones = [i for i in deduped_regex if i.indicator_type == "phone_number"]
        upis = [i for i in deduped_regex if i.indicator_type == "upi_id"]
        urls = [i for i in deduped_regex if i.indicator_type == "url"]
        emails = [i for i in deduped_regex if i.indicator_type == "email"]
        amounts = [i for i in deduped_regex if i.indicator_type == "financial_amount"]
        txns = [i for i in deduped_regex if i.indicator_type == "transaction_id"]

        all_indicators = deduped_regex + claimed_entities + scam_tactics + requested_actions

        # 8. Add to Case if requested
        added_count = 0
        if req.add_to_case:
            add_res = self.add_indicators_to_case(
                case_id=case_id,
                indicators=all_indicators,
                evidence_id=source_evidence_id,
                db=db,
            )
            added_count = add_res.added_count

        return ScamIntelligenceAnalysisResponse(
            case_id=case_id,
            conversation_summary=conversation_summary,
            scam_type=scam_type,
            threat_assessment=threat_assessment,
            tactics_observed=tactics_observed,
            psychological_triggers=psychological_triggers,
            urgency_level="critical" if "arrest" in scam_type.lower() or amounts else "high",
            indicators=all_indicators,
            phone_numbers=phones,
            upi_ids=upis,
            urls=urls,
            emails=emails,
            claimed_entities=claimed_entities,
            financial_amounts=amounts,
            transaction_references=txns,
            scam_tactics=scam_tactics,
            requested_actions=requested_actions,
            disclaimer=DISCLAIMER_TEXT,
            added_to_case_count=added_count,
        )

    def add_indicators_to_case(
        self,
        case_id: str,
        indicators: List[ScamIntelligenceItem],
        evidence_id: Optional[str],
        db: Session,
    ) -> AddIndicatorsToCaseResponse:
        """
        Merges extracted indicators into the case's authoritative Indicator table.
        Avoids creating duplicates and preserves provenance references.
        """
        case = db.query(Case).filter(Case.id == case_id).first()
        if not case:
            raise ValueError(f"Case '{case_id}' was not found in the incident vault.")

        existing_indicators = db.query(Indicator).filter(Indicator.case_id == case_id).all()
        existing_lookup = {
            (ind.indicator_type.lower(), ind.value.strip().lower())
            for ind in existing_indicators
        }

        added_count = 0
        skipped_count = 0

        # Normalization mapping
        type_map = {
            "phone": "phone_number",
            "phone_number": "phone_number",
            "upi": "upi_id",
            "upi_id": "upi_id",
            "url": "url",
            "email": "email",
            "person": "suspect_name",
            "suspect_name": "suspect_name",
            "organization": "organization",
            "amount": "financial_amount",
            "financial_amount": "financial_amount",
            "transaction_ref": "transaction_id",
            "transaction_id": "transaction_id",
            "scam_tactic": "scam_tactic",
            "requested_action": "requested_action",
        }

        for item in indicators:
            norm_type = type_map.get(item.indicator_type, item.indicator_type)
            norm_val = item.value.strip()
            lookup_key = (norm_type.lower(), norm_val.lower())

            if lookup_key in existing_lookup:
                skipped_count += 1
                continue

            # Persist new Indicator with provenance
            new_ind = Indicator(
                case_id=case_id,
                indicator_type=norm_type,
                value=norm_val,
                confidence=item.confidence or "medium",
                verification_status="unverified",
                source_evidence_id=item.source_evidence_id or evidence_id,
                source_reference=item.source_reference,
            )
            db.add(new_ind)
            existing_lookup.add(lookup_key)
            added_count += 1

        db.commit()

        total_count = db.query(Indicator).filter(Indicator.case_id == case_id).count()

        return AddIndicatorsToCaseResponse(
            case_id=case_id,
            added_count=added_count,
            skipped_duplicates_count=skipped_count,
            total_case_indicators=total_count,
            message=f"Successfully integrated {added_count} new indicators into Case Intelligence ({skipped_count} existing duplicates skipped).",
        )

# Global singleton
scam_intel_service = ScamIntelligenceService()
