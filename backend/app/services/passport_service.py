import logging
from typing import Optional, List, Dict, Any, Set, Tuple
from sqlalchemy.orm import Session

from backend.app.models.case import Case
from backend.app.models.evidence import Evidence
from backend.app.models.indicator import Indicator
from backend.app.models.timeline import TimelineEvent
from backend.app.models.compromise import CompromiseAssessment
from backend.app.schemas.ai_output import CaseIntelligence
from backend.app.schemas.passport import (
    FraudCasePassport,
    IncidentPassportInfo,
    FinancialPassportInfo,
    TimelinePassportItem,
    IndicatorPassportItem,
    CompromisePassportItem,
    EvidenceProvenanceItem,
)

logger = logging.getLogger(__name__)

class CaseNotFoundError(Exception):
    """Raised when the specified case ID is not found in the database."""
    pass

class AnalysisNotReadyError(Exception):
    """Raised when CaseIntelligence has not yet been generated for the requested case."""
    pass

class PassportService:
    """
    Presentation and aggregation service for Fraud Case Passports.
    Consumes real dynamically generated CaseIntelligence produced by the AI pipeline.
    Does NOT execute redundant AI model calls to construct or display the passport.
    Preserves strict forensic provenance from facts to source evidence items and references.
    """

    def get_passport(self, case_id: str, db: Session) -> FraudCasePassport:
        """
        Retrieve and assemble the FraudCasePassport for a given case ID.
        Raises CaseNotFoundError if case does not exist.
        Raises AnalysisNotReadyError if intelligence analysis has not yet been completed.
        """
        case = db.query(Case).filter(Case.id == case_id).first()
        if not case:
            raise CaseNotFoundError(f"Case '{case_id}' not found.")

        # Check whether analysis has completed
        has_intelligence_json = bool(case.intelligence_json)
        has_ready_status = case.status in ("passport_ready", "action_pending", "resolved")
        has_persisted_findings = bool(
            case.summary
            or (case.indicators and len(case.indicators) > 0)
            or (case.timeline_events and len(case.timeline_events) > 0)
        )

        if not (has_intelligence_json or has_ready_status or has_persisted_findings):
            raise AnalysisNotReadyError(
                f"Case analysis is not ready yet for case '{case_id}'. Please run incident analysis first."
            )

        # Build passport from CaseIntelligence JSON if available
        if has_intelligence_json:
            try:
                intel = CaseIntelligence.model_validate_json(case.intelligence_json)
                return self._build_from_intelligence(case, intel)
            except Exception as e:
                logger.warning(
                    f"Failed to deserialize intelligence_json for case {case_id}: {e}. "
                    f"Falling back to persisted relational tables."
                )

        # Fallback: assemble from persisted relational tables in SQLite
        return self._build_from_relational_tables(case)

    def _build_from_intelligence(self, case: Case, intel: CaseIntelligence) -> FraudCasePassport:
        """Assemble FraudCasePassport directly from master CaseIntelligence."""
        # 1. Incident Overview
        incident = IncidentPassportInfo(
            incident_type=intel.reconstruction.incident_type or "Financial Fraud",
            category=intel.reconstruction.scam_category or case.scam_category or "Unclassified Incident",
            severity=intel.reconstruction.severity_level or intel.triage.severity_level or case.severity_level or "medium",
            summary=intel.reconstruction.summary or case.summary or "Incident reconstruction completed.",
            modus_operandi=intel.reconstruction.modus_operandi or intel.scam_intel.threat_assessment or case.modus_operandi,
        )

        # 2. Financial Information
        loss = (
            intel.reconstruction.financial_loss
            if intel.reconstruction.financial_loss is not None
            else (intel.triage.loss_amount if intel.triage.loss_amount is not None else case.financial_loss)
        )
        currency = intel.reconstruction.currency or case.currency or "INR"
        transactions: List[Dict[str, Any]] = []
        if intel.evidence_intel and intel.evidence_intel.extracted_financials:
            for fin in intel.evidence_intel.extracted_financials:
                transactions.append({
                    "amount": fin.amount,
                    "currency": fin.currency,
                    "description": fin.description,
                    "source_evidence_id": fin.source_evidence_id,
                })

        financial = FinancialPassportInfo(
            loss=loss,
            currency=currency,
            transactions=transactions,
        )

        # 3. Timeline
        timeline: List[TimelinePassportItem] = []
        if intel.reconstruction and intel.reconstruction.timeline:
            for item in intel.reconstruction.timeline:
                timeline.append(
                    TimelinePassportItem(
                        timestamp=item.timestamp_str,
                        event_description=item.event_description,
                        source_evidence_id=item.source_evidence_id,
                        is_inferred=item.is_inferred,
                        confidence=item.confidence,
                    )
                )

        # 4. Indicators (merge reconstruction indicators and evidence_intel indicators, deduplicating)
        indicators: List[IndicatorPassportItem] = []
        seen_keys: Set[Tuple[str, str]] = set()

        raw_indicators = []
        if intel.reconstruction and intel.reconstruction.indicators:
            raw_indicators.extend(intel.reconstruction.indicators)
        if intel.evidence_intel and intel.evidence_intel.extracted_indicators:
            raw_indicators.extend(intel.evidence_intel.extracted_indicators)

        for ind in raw_indicators:
            key = (ind.indicator_type.lower(), ind.value.strip().lower())
            if key in seen_keys:
                continue
            seen_keys.add(key)
            indicators.append(
                IndicatorPassportItem(
                    indicator_type=ind.indicator_type,
                    value=ind.value,
                    confidence=ind.confidence,
                    verification_status=ind.verification_status,
                    source_evidence_id=ind.source_evidence_id,
                    source_reference=ind.source_reference,
                )
            )

        # 5. Compromise Assessments
        compromise: List[CompromisePassportItem] = []
        if intel.compromise and intel.compromise.assessments:
            for comp in intel.compromise.assessments:
                compromise.append(
                    CompromisePassportItem(
                        category=comp.category,
                        risk_level=comp.status,
                        details=comp.details,
                        recommended_action=comp.recommended_action,
                        source_evidence_id=comp.source_evidence_id,
                        source_reference=comp.source_reference,
                    )
                )
        elif intel.reconstruction and intel.reconstruction.compromise:
            for comp in intel.reconstruction.compromise:
                compromise.append(
                    CompromisePassportItem(
                        category=comp.category,
                        risk_level=comp.status,
                        details=comp.details,
                        recommended_action=comp.recommended_action,
                        source_evidence_id=comp.source_evidence_id,
                        source_reference=comp.source_reference,
                    )
                )

        # 6. Immediate Actions
        immediate_actions: List[str] = []
        if intel.reconstruction and intel.reconstruction.recommended_immediate_actions:
            immediate_actions.extend(intel.reconstruction.recommended_immediate_actions)
        elif intel.triage and intel.triage.immediate_containment_steps:
            immediate_actions.extend(intel.triage.immediate_containment_steps)
        elif intel.response_packages and intel.response_packages.emergency_advisory:
            immediate_actions.append(intel.response_packages.emergency_advisory)

        # 7. Evidence Provenance Items
        evidence_items = self._build_evidence_summary(case, timeline, indicators, compromise)

        return FraudCasePassport(
            case_id=case.id,
            title=case.title or "Untitled Incident",
            description=case.description,
            status=case.status,
            created_at=case.created_at,
            updated_at=case.updated_at,
            incident=incident,
            financial=financial,
            timeline=timeline,
            indicators=indicators,
            compromise=compromise,
            immediate_actions=immediate_actions,
            evidence_items=evidence_items,
            evidence_count=len(evidence_items),
        )

    def _build_from_relational_tables(self, case: Case) -> FraudCasePassport:
        """Assemble FraudCasePassport from existing relational SQLite tables."""
        incident = IncidentPassportInfo(
            incident_type="Financial Fraud",
            category=case.scam_category or "Unclassified Incident",
            severity=case.severity_level or "medium",
            summary=case.summary or "Incident reconstruction completed.",
            modus_operandi=case.modus_operandi,
        )

        financial = FinancialPassportInfo(
            loss=case.financial_loss,
            currency=case.currency or "INR",
            transactions=[],
        )

        timeline: List[TimelinePassportItem] = []
        for t in case.timeline_events:
            timeline.append(
                TimelinePassportItem(
                    timestamp=t.timestamp_str,
                    event_description=t.event_description,
                    source_evidence_id=t.source_evidence_id,
                )
            )

        indicators: List[IndicatorPassportItem] = []
        for ind in case.indicators:
            indicators.append(
                IndicatorPassportItem(
                    indicator_type=ind.indicator_type,
                    value=ind.value,
                    confidence=ind.confidence,
                    verification_status=ind.verification_status,
                    source_evidence_id=ind.source_evidence_id,
                    source_reference=ind.source_reference,
                )
            )

        compromise: List[CompromisePassportItem] = []
        immediate_actions: List[str] = []
        for comp in case.compromise_assessments:
            compromise.append(
                CompromisePassportItem(
                    category=comp.category,
                    risk_level=comp.risk_level.upper() if comp.risk_level else "UNVERIFIED",
                    details=comp.details,
                    recommended_action=comp.recommended_action,
                    source_evidence_id=comp.source_evidence_id,
                )
            )
            if comp.recommended_action and comp.recommended_action not in immediate_actions:
                immediate_actions.append(comp.recommended_action)

        evidence_items = self._build_evidence_summary(case, timeline, indicators, compromise)

        return FraudCasePassport(
            case_id=case.id,
            title=case.title or "Untitled Incident",
            description=case.description,
            status=case.status,
            created_at=case.created_at,
            updated_at=case.updated_at,
            incident=incident,
            financial=financial,
            timeline=timeline,
            indicators=indicators,
            compromise=compromise,
            immediate_actions=immediate_actions,
            evidence_items=evidence_items,
            evidence_count=len(evidence_items),
        )

    def _build_evidence_summary(
        self,
        case: Case,
        timeline: List[TimelinePassportItem],
        indicators: List[IndicatorPassportItem],
        compromise: List[CompromisePassportItem],
    ) -> List[EvidenceProvenanceItem]:
        """Summarize ingested evidence files and map how many facts derive from each."""
        # Count facts per evidence ID
        citation_counts: Dict[str, int] = {}
        for t in timeline:
            if t.source_evidence_id:
                citation_counts[t.source_evidence_id] = citation_counts.get(t.source_evidence_id, 0) + 1
        for i in indicators:
            if i.source_evidence_id:
                citation_counts[i.source_evidence_id] = citation_counts.get(i.source_evidence_id, 0) + 1
        for c in compromise:
            if c.source_evidence_id:
                citation_counts[c.source_evidence_id] = citation_counts.get(c.source_evidence_id, 0) + 1

        items: List[EvidenceProvenanceItem] = []
        for ev in case.evidence:
            items.append(
                EvidenceProvenanceItem(
                    evidence_id=ev.id,
                    evidence_type=ev.evidence_type,
                    filename=ev.filename,
                    processing_status=ev.processing_status,
                    created_at=ev.created_at,
                    facts_count=citation_counts.get(ev.id, 0),
                )
            )
        return items

passport_service = PassportService()
