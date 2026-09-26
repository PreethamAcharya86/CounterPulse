import logging
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from backend.app.models.case import Case
from backend.app.models.evidence import Evidence
from backend.app.models.indicator import Indicator
from backend.app.models.timeline import TimelineEvent
from backend.app.models.compromise import CompromiseAssessment
from backend.app.models.report import Report
from backend.app.services.ai.base import AIProvider, AIError
from backend.app.services.ai.factory import AIProviderFactory
from backend.app.services.agents.base import CaseContext, BaseAgent
from backend.app.services.agents.evidence_intel_agent import EvidenceIntelligenceAgent
from backend.app.services.agents.incident_reconstruction_agent import IncidentReconstructionAgent
from backend.app.services.agents.triage_agent import TriageAgent
from backend.app.services.agents.scam_intel_agent import ScamIntelligenceAgent
from backend.app.services.agents.compromise_agent import CompromiseAssessmentAgent
from backend.app.services.agents.network_intel_agent import NetworkIntelligenceAgent
from backend.app.services.agents.response_agent import ResponseAgent
from backend.app.services.agents.followup_agent import FollowUpAgent
from backend.app.schemas.ai_output import (
    CaseIntelligence,
    ConflictingFinding,
    IncidentReconstructionOutput,
    TriageOutput,
    ScamIntelligenceOutput,
    CompromiseAssessmentOutput,
    NetworkIntelligenceOutput,
    EvidenceIntelligenceOutput,
    ResponsePackagesOutput,
    FollowUpAgentOutput,
)

logger = logging.getLogger(__name__)

class AIOrchestrator:
    """
    Coordinates multi-agent incident response intelligence.
    Determines agent execution schedules, manages context scoping,
    merges findings into unified CaseIntelligence, detects evidentiary conflicts,
    and updates database records with full provenance trails.
    """

    def __init__(self, provider: Optional[AIProvider] = None):
        self._provider = provider
        # Initialize specialized agent registry
        self.evidence_intel_agent = EvidenceIntelligenceAgent()
        self.incident_reconstruction_agent = IncidentReconstructionAgent()
        self.triage_agent = TriageAgent()
        self.scam_intel_agent = ScamIntelligenceAgent()
        self.compromise_agent = CompromiseAssessmentAgent()
        self.network_intel_agent = NetworkIntelligenceAgent()
        self.response_agent = ResponseAgent()
        self.followup_agent = FollowUpAgent()

    def get_provider(self) -> AIProvider:
        return self._provider or AIProviderFactory.get_provider()

    async def run_single_agent(
        self,
        agent_name: str,
        case_id: str,
        db: Session,
        provider_override: Optional[AIProvider] = None,
    ) -> Any:
        """Execute a single specialized agent against a case context."""
        case = db.query(Case).filter(Case.id == case_id).first()
        if not case:
            raise ValueError(f"Case '{case_id}' not found.")

        evidence_items = db.query(Evidence).filter(Evidence.case_id == case_id).all()
        context = CaseContext.from_case_and_evidence(
            case_id=case.id,
            title=case.title,
            description=case.description,
            evidence_list=evidence_items,
        )

        provider = provider_override or self.get_provider()
        agent_map: Dict[str, BaseAgent] = {
            "evidence_intel": self.evidence_intel_agent,
            "incident_reconstruction": self.incident_reconstruction_agent,
            "triage": self.triage_agent,
            "scam_intel": self.scam_intel_agent,
            "compromise": self.compromise_agent,
            "network_intel": self.network_intel_agent,
            "response": self.response_agent,
            "followup": self.followup_agent,
        }

        agent = agent_map.get(agent_name.lower().replace("-", "_"))
        if not agent:
            raise ValueError(f"Unknown agent '{agent_name}'. Available: {list(agent_map.keys())}")

        return await agent.run(context, provider)

    async def analyze_case(
        self,
        case_id: str,
        db: Session,
        provider_override: Optional[AIProvider] = None,
        persist_to_db: bool = True,
    ) -> CaseIntelligence:
        """
        Execute full multi-agent orchestration for a case:
        1. Context Building
        2. Specialized Agent Execution (Evidence, Incident, Triage, Scam, Compromise, Network, Response, Follow-up)
        3. Conflict Detection
        4. Case Intelligence Synthesis
        5. Database Persistence (Case metrics, Indicators, Timeline, Compromise, Reports)
        """
        case = db.query(Case).filter(Case.id == case_id).first()
        if not case:
            raise ValueError(f"Case '{case_id}' not found.")

        evidence_items = db.query(Evidence).filter(Evidence.case_id == case_id).all()
        context = CaseContext.from_case_and_evidence(
            case_id=case.id,
            title=case.title,
            description=case.description,
            evidence_list=evidence_items,
        )

        provider = provider_override or self.get_provider()
        executed_agents: List[str] = []

        # 1. Evidence Intelligence
        try:
            evidence_intel = await self.evidence_intel_agent.run(context, provider)
            executed_agents.append(self.evidence_intel_agent.name)
        except Exception as e:
            logger.error(f"Evidence Intel Agent error: {e}")
            evidence_intel = EvidenceIntelligenceOutput()

        # 2. Incident Reconstruction
        try:
            reconstruction = await self.incident_reconstruction_agent.run(context, provider)
            executed_agents.append(self.incident_reconstruction_agent.name)
        except Exception as e:
            logger.error(f"Incident Reconstruction Agent error: {e}")
            reconstruction = IncidentReconstructionOutput(
                summary="Automated reconstruction pending review.",
                incident_type="Financial Fraud",
                scam_category="Unclassified Incident",
                severity_level="medium",
                modus_operandi="Modus operandi analysis in progress.",
            )

        # 3. Triage Assessment
        try:
            triage = await self.triage_agent.run(context, provider)
            executed_agents.append(self.triage_agent.name)
        except Exception as e:
            logger.error(f"Triage Agent error: {e}")
            triage = TriageOutput(
                severity_level="medium",
                urgency_rating="active_monitoring",
                triage_summary="Triage assessment completed with defaults.",
            )

        # 4. Scam Intelligence
        try:
            scam_intel = await self.scam_intel_agent.run(context, provider)
            executed_agents.append(self.scam_intel_agent.name)
        except Exception as e:
            logger.error(f"Scam Intel Agent error: {e}")
            scam_intel = ScamIntelligenceOutput(
                scam_type="Financial Scam",
                threat_assessment="Scam intelligence analysis completed with fallback.",
            )

        # 5. Compromise Assessment
        try:
            compromise = await self.compromise_agent.run(context, provider)
            executed_agents.append(self.compromise_agent.name)
        except Exception as e:
            logger.error(f"Compromise Agent error: {e}")
            compromise = CompromiseAssessmentOutput(
                summary="Compromise assessment completed with fallback.",
            )

        # 6. Network Intelligence
        try:
            network_intel = await self.network_intel_agent.run(context, provider)
            executed_agents.append(self.network_intel_agent.name)
        except Exception as e:
            logger.error(f"Network Intel Agent error: {e}")
            network_intel = NetworkIntelligenceOutput()

        # 7. Response Agent (Drafts Only)
        try:
            response_packages = await self.response_agent.run(context, provider)
            executed_agents.append(self.response_agent.name)
        except Exception as e:
            logger.error(f"Response Agent error: {e}")
            response_packages = ResponsePackagesOutput(
                bank_dispute_subject="Formal Dispute of Fraudulent Transaction",
                bank_dispute_body="Draft dispute declaration pending victim review.",
                cybercrime_complaint_subject="Cybercrime Portal Complaint (1930)",
                cybercrime_complaint_body="Complaint draft narrative pending victim review.",
                emergency_advisory="Contact 1930 immediately to preserve dispute timelines.",
            )

        # 8. Follow-up Agent
        try:
            follow_up = await self.followup_agent.run(context, provider)
            executed_agents.append(self.followup_agent.name)
        except Exception as e:
            logger.error(f"Follow-up Agent error: {e}")
            follow_up = FollowUpAgentOutput()

        # 9. Conflict Detection
        conflicts = self._detect_conflicts(reconstruction, triage, follow_up, evidence_intel)

        # Build Master Intelligence object
        intelligence = CaseIntelligence(
            case_id=case.id,
            reconstruction=reconstruction,
            triage=triage,
            scam_intel=scam_intel,
            compromise=compromise,
            network_intel=network_intel,
            evidence_intel=evidence_intel,
            response_packages=response_packages,
            follow_up=follow_up,
            conflicting_findings=conflicts,
            agents_executed=executed_agents,
            provider_used=provider.provider_name,
        )

        # 10. Persist to Database
        if persist_to_db:
            self._persist_case_intelligence(case, intelligence, db)

        return intelligence

    def _detect_conflicts(
        self,
        reconstruction: IncidentReconstructionOutput,
        triage: TriageOutput,
        follow_up: FollowUpAgentOutput,
        evidence_intel: EvidenceIntelligenceOutput,
    ) -> List[ConflictingFinding]:
        """Detect evidentiary and cross-agent analytical contradictions."""
        conflicts: List[ConflictingFinding] = []

        # 1. Financial loss divergence between agents
        if (
            reconstruction.financial_loss is not None
            and triage.loss_amount is not None
            and abs(reconstruction.financial_loss - triage.loss_amount) > 1.0
        ):
            conflicts.append(
                ConflictingFinding(
                    field_name="financial_loss",
                    conflicting_values=[
                        f"Reconstruction: {reconstruction.financial_loss}",
                        f"Triage: {triage.loss_amount}"
                    ],
                    description="Discrepancy detected in assessed financial loss between Incident Reconstruction and Triage agents.",
                    resolution_status="flagged_for_human",
                )
            )

        # 2. Check explicitly reported contradictions from Follow-up agent
        for contradiction in follow_up.contradictions_detected:
            conflicts.append(
                ConflictingFinding(
                    field_name="evidence_consistency",
                    conflicting_values=[contradiction],
                    description=f"Evidence audit identified inconsistency: {contradiction}",
                    resolution_status="flagged_for_human",
                )
            )

        return conflicts

    def _persist_case_intelligence(
        self,
        case: Case,
        intel: CaseIntelligence,
        db: Session,
    ):
        """Update Case records, Indicators, Timeline, and Reports in SQLite."""
        # 1. Update Case high-level incident fields
        case.scam_category = intel.reconstruction.scam_category
        case.severity_level = intel.triage.severity_level
        case.financial_loss = intel.reconstruction.financial_loss or intel.triage.loss_amount
        case.currency = intel.reconstruction.currency
        case.modus_operandi = intel.reconstruction.modus_operandi
        case.summary = intel.reconstruction.summary
        case.intelligence_json = intel.model_dump_json()
        case.status = "passport_ready"

        # 2. Persist Indicators (merge from evidence_intel and reconstruction)
        all_inds = (
            intel.reconstruction.indicators
            + intel.evidence_intel.extracted_indicators
        )
        seen_indicators = set()
        for ind in all_inds:
            key = (ind.indicator_type, ind.value.strip().lower())
            if key in seen_indicators:
                continue
            seen_indicators.add(key)

            # Check if exists
            existing = (
                db.query(Indicator)
                .filter(
                    Indicator.case_id == case.id,
                    Indicator.indicator_type == ind.indicator_type,
                    Indicator.value == ind.value,
                )
                .first()
            )
            if not existing:
                db_ind = Indicator(
                    case_id=case.id,
                    indicator_type=ind.indicator_type,
                    value=ind.value,
                    confidence=ind.confidence,
                    verification_status=ind.verification_status,
                    source_evidence_id=ind.source_evidence_id,
                    source_reference=ind.source_reference,
                )
                db.add(db_ind)

        # 3. Persist Timeline Events
        # Clear previous timeline events to avoid duplication on re-analysis
        db.query(TimelineEvent).filter(TimelineEvent.case_id == case.id).delete()
        for idx, item in enumerate(intel.reconstruction.timeline):
            db_tl = TimelineEvent(
                case_id=case.id,
                timestamp_str=item.timestamp_str,
                event_description=item.event_description,
                source_evidence_id=item.source_evidence_id,
                order_index=idx,
            )
            db.add(db_tl)

        # 4. Persist Compromise Assessments
        db.query(CompromiseAssessment).filter(CompromiseAssessment.case_id == case.id).delete()
        for c in intel.compromise.assessments:
            db_comp = CompromiseAssessment(
                case_id=case.id,
                category=c.category,
                risk_level=c.status.lower(),
                details=c.details,
                recommended_action=c.recommended_action,
                source_evidence_id=c.source_evidence_id,
            )
            db.add(db_comp)

        # 5. Persist Draft Reports (Bank Dispute & Cybercrime Complaint)
        # Bank Dispute
        existing_bank_rep = (
            db.query(Report)
            .filter(Report.case_id == case.id, Report.report_type == "bank_dispute")
            .first()
        )
        if not existing_bank_rep:
            bank_rep = Report(
                case_id=case.id,
                report_type="bank_dispute",
                title=intel.response_packages.bank_dispute_subject,
                content_markdown=intel.response_packages.bank_dispute_body,
                approval_status="draft",
            )
            db.add(bank_rep)
        else:
            existing_bank_rep.title = intel.response_packages.bank_dispute_subject
            existing_bank_rep.content_markdown = intel.response_packages.bank_dispute_body

        # Cybercrime Complaint
        existing_cyber_rep = (
            db.query(Report)
            .filter(Report.case_id == case.id, Report.report_type == "cybercrime_complaint")
            .first()
        )
        if not existing_cyber_rep:
            cyber_rep = Report(
                case_id=case.id,
                report_type="cybercrime_complaint",
                title=intel.response_packages.cybercrime_complaint_subject,
                content_markdown=intel.response_packages.cybercrime_complaint_body,
                approval_status="draft",
            )
            db.add(cyber_rep)
        else:
            existing_cyber_rep.title = intel.response_packages.cybercrime_complaint_subject
            existing_cyber_rep.content_markdown = intel.response_packages.cybercrime_complaint_body

        db.commit()
        db.refresh(case)

# Singleton instance
ai_orchestrator = AIOrchestrator()
