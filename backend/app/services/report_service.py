import json
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.models.case import Case
from backend.app.models.report import Report, ActionEvent
from backend.app.schemas.ai_output import CaseIntelligence
from backend.app.schemas.report import ReportUpdate
from backend.app.services.email_service import EmailProvider, get_email_provider, EmailDispatchError
from backend.app.services.passport_service import passport_service, PassportService
from backend.app.services.pdf_service import pdf_report_service, PDFReportService

logger = logging.getLogger(__name__)

class CaseNotFoundError(Exception):
    """Raised when the specified case ID is not found in the database."""
    pass

class AnalysisNotReadyError(Exception):
    """Raised when CaseIntelligence has not yet been generated for the requested case."""
    pass

class ReportNotFoundError(Exception):
    """Raised when the specified report ID is not found."""
    pass

class ReportAlreadySentError(Exception):
    """Raised when attempting to modify or re-approve a report that has already been dispatched."""
    pass

class ReportNotApprovedError(Exception):
    """Raised when attempting to dispatch an unapproved report."""
    pass

class ReportService:
    """
    Coordinates Report Generation, Human Review/Editing, Explicit Approval,
    and Email Dispatch with Audit Tracking.
    
    STRICT SAFETY RULE: A report MUST NEVER be sent without explicit human approval.
    """

    def __init__(
        self,
        passport_svc: Optional[PassportService] = None,
        pdf_svc: Optional[PDFReportService] = None,
    ):
        self.passport_svc = passport_svc or passport_service
        self.pdf_svc = pdf_svc or pdf_report_service

    def _record_audit_event(
        self,
        db: Session,
        case_id: str,
        action_type: str,
        status: str,
        details: Optional[str] = None,
    ) -> ActionEvent:
        """Helper to append an audit trail record to action_events."""
        event = ActionEvent(
            case_id=case_id,
            action_type=action_type,
            status=status,
            details=details,
            timestamp=datetime.now(timezone.utc),
        )
        db.add(event)
        return event

    def _get_case_or_raise(self, case_id: str, db: Session) -> Case:
        case = db.query(Case).filter(Case.id == case_id).first()
        if not case:
            raise CaseNotFoundError(f"Case '{case_id}' not found.")
        return case

    def _extract_evidence_references(self, case: Case, intel: Optional[CaseIntelligence] = None) -> List[str]:
        """Collect forensic evidence IDs or labels preserving provenance."""
        refs: List[str] = []
        if case.evidence:
            refs.extend([e.id for e in case.evidence])
        ev_intel = getattr(intel, "evidence_intel", None) or getattr(intel, "evidence_intelligence", None) if intel else None
        if ev_intel:
            for ind in getattr(ev_intel, "extracted_indicators", []):
                if ind.source_evidence_id and ind.source_evidence_id not in refs:
                    refs.append(ind.source_evidence_id)
            for fin in getattr(ev_intel, "extracted_financials", []):
                if fin.source_evidence_id and fin.source_evidence_id not in refs:
                    refs.append(fin.source_evidence_id)
        return refs

    def get_reports_for_case(self, case_id: str, db: Session) -> List[Report]:
        """
        Retrieve all reports for a case. If none exist yet but intelligence is ready,
        generate the initial draft reports so they are available for human review.
        """
        case = self._get_case_or_raise(case_id, db)
        reports = (
            db.query(Report)
            .filter(Report.case_id == case_id)
            .order_by(Report.created_at.asc())
            .all()
        )

        if reports and len(reports) > 0:
            return reports

        # If no reports exist yet, check if intelligence is available to generate them
        has_intelligence = bool(case.intelligence_json or case.summary)
        if not has_intelligence:
            raise AnalysisNotReadyError(
                f"Incident analysis is not ready yet for case '{case_id}'. Please run AI analysis first."
            )

        return self.generate_draft_reports(case_id=case_id, db=db, force_regenerate=False)

    def generate_draft_reports(
        self, case_id: str, db: Session, force_regenerate: bool = False
    ) -> List[Report]:
        """
        Generate or refresh draft reports from CaseIntelligence without redundant AI calls.
        Supports:
        1. Bank Dispute
        2. Cybercrime Complaint
        3. Emergency Security Advisory
        """
        case = self._get_case_or_raise(case_id, db)

        if not (case.intelligence_json or case.summary):
            raise AnalysisNotReadyError(
                f"Incident analysis is not ready yet for case '{case_id}'. Please run AI analysis first."
            )

        intel: Optional[CaseIntelligence] = None
        if case.intelligence_json:
            try:
                intel = CaseIntelligence.model_validate_json(case.intelligence_json)
            except Exception as e:
                logger.warning("Could not parse intelligence_json for case %s: %s", case_id, e)

        ev_refs = self._extract_evidence_references(case, intel)
        ev_refs_json = json.dumps(ev_refs) if ev_refs else None

        # Build content packages
        if intel and intel.response_packages:
            bank_subject = intel.response_packages.bank_dispute_subject
            bank_body = intel.response_packages.bank_dispute_body
            cyber_subject = intel.response_packages.cybercrime_complaint_subject
            cyber_body = intel.response_packages.cybercrime_complaint_body
            advisory_subject = "Emergency Security Containment & Incident Advisory"
            advisory_body = intel.response_packages.emergency_advisory
        else:
            loss_txt = f"{case.currency} {case.financial_loss:,.2f}" if case.financial_loss else "Undisclosed"
            bank_subject = f"URGENT: Dispute of Unauthorized Transactions — {loss_txt}"
            bank_body = (
                f"To: Nodal Fraud & Dispute Officer\n\n"
                f"Ref: Unauthorized Electronic Transaction Dispute\n"
                f"Incident: {case.title}\n"
                f"Summary: {case.summary or 'Unauthorized transaction reported.'}\n\n"
                f"In accordance with standard banking customer protection guidelines, I request an immediate "
                f"chargeback/dispute initiation and an urgent lien on the beneficiary account.\n\n"
                f"Evidence References: {', '.join(ev_refs) if ev_refs else 'Attached'}"
            )
            cyber_subject = f"Cyber Fraud Complaint: {case.scam_category or 'Financial Fraud'} — NCRP 1930"
            cyber_body = (
                f"National Cyber Crime Reporting Portal (1930) Complaint Draft\n"
                f"Incident Type: {case.scam_category or 'Online Financial Fraud'}\n"
                f"Total Claimed Loss: {loss_txt}\n\n"
                f"Narrative:\n{case.summary or case.description or 'Scam incident reported.'}\n\n"
                f"Forensic Indicators & Evidence Records: {', '.join(ev_refs) if ev_refs else 'Documented in Case Intelligence'}"
            )
            advisory_subject = "Emergency Security Containment & Incident Advisory"
            advisory_body = (
                "1. Immediately contact your bank to freeze net-banking access and block cards.\n"
                "2. Change all compromised passwords and enable multi-factor authentication (MFA).\n"
                "3. Terminate active sessions and uninstall any remote desktop tools (AnyDesk, TeamViewer).\n"
                "4. Preserve all original SMS, call logs, and transaction receipts for evidence.\n"
                "5. Report the incident promptly on the National Cyber Crime Reporting Portal (cybercrime.gov.in / 1930)."
            )

        report_defs = [
            ("bank_dispute", bank_subject, bank_body),
            ("cybercrime_complaint", cyber_subject, cyber_body),
            ("security_advisory", advisory_subject, advisory_body),
        ]

        generated_reports: List[Report] = []

        for r_type, title, body in report_defs:
            existing = (
                db.query(Report)
                .filter(Report.case_id == case_id, Report.report_type == r_type)
                .first()
            )

            if existing:
                # If report was already sent, never overwrite unless force_regenerate is explicitly True
                if existing.approval_status == "sent" and not force_regenerate:
                    generated_reports.append(existing)
                    continue

                # If force_regenerate or currently in draft/reviewed, refresh content
                if force_regenerate or existing.approval_status in ("draft", "reviewed"):
                    existing.title = title
                    existing.content_markdown = body
                    existing.evidence_references_json = ev_refs_json
                    existing.updated_at = datetime.now(timezone.utc)
                generated_reports.append(existing)
            else:
                new_rep = Report(
                    case_id=case_id,
                    report_type=r_type,
                    title=title,
                    content_markdown=body,
                    approval_status="draft",
                    evidence_references_json=ev_refs_json,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                )
                db.add(new_rep)
                generated_reports.append(new_rep)

        self._record_audit_event(
            db=db,
            case_id=case_id,
            action_type="draft_created" if not force_regenerate else "draft_regenerated",
            status="success",
            details=f"Generated {len(generated_reports)} draft reports for review",
        )

        db.commit()
        for r in generated_reports:
            db.refresh(r)

        return generated_reports

    def get_report(self, case_id: str, report_id: str, db: Session) -> Report:
        """Get single report by ID ensuring case matches."""
        self._get_case_or_raise(case_id, db)
        report = (
            db.query(Report)
            .filter(Report.id == report_id, Report.case_id == case_id)
            .first()
        )
        if not report:
            raise ReportNotFoundError(f"Report '{report_id}' not found for case '{case_id}'.")
        return report

    def update_draft_report(
        self, case_id: str, report_id: str, update_data: ReportUpdate, db: Session
    ) -> Report:
        """
        Update/edit a draft report.
        If a report was previously APPROVED and subject/body is modified,
        the approval is revoked back to DRAFT/REVIEWED to ensure no unapproved edits are sent.
        Modifying a SENT report is rejected.
        """
        report = self.get_report(case_id, report_id, db)

        if report.approval_status == "sent":
            raise ReportAlreadySentError(
                f"Cannot modify report '{report_id}' because it has already been sent."
            )

        content_modified = False
        if update_data.title is not None and update_data.title != report.title:
            report.title = update_data.title
            content_modified = True
        if update_data.content_markdown is not None and update_data.content_markdown != report.content_markdown:
            report.content_markdown = update_data.content_markdown
            content_modified = True
        if update_data.recipient_email is not None:
            report.recipient_email = update_data.recipient_email

        # If content changed and report was approved, revert approval to draft for human re-review
        if content_modified and report.approval_status == "approved":
            report.approval_status = "draft"
            report.approved_at = None
            self._record_audit_event(
                db=db,
                case_id=case_id,
                action_type="draft_edited",
                status="success",
                details=f"Report {report.report_type} edited after approval; approval status revoked to draft",
            )
        elif content_modified:
            self._record_audit_event(
                db=db,
                case_id=case_id,
                action_type="draft_edited",
                status="success",
                details=f"Report {report.report_type} draft updated",
            )

        if update_data.approval_status is not None:
            # Allow explicit transition to reviewed or draft
            if update_data.approval_status.lower() in ("draft", "reviewed"):
                report.approval_status = update_data.approval_status.lower()

        report.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(report)
        return report

    def approve_report(
        self,
        case_id: str,
        report_id: str,
        db: Session,
        recipient_email: Optional[str] = None,
    ) -> Report:
        """
        Explicitly mark report as APPROVED for dispatch.
        """
        report = self.get_report(case_id, report_id, db)

        if report.approval_status == "sent":
            raise ReportAlreadySentError(
                f"Report '{report_id}' has already been sent."
            )

        if recipient_email:
            report.recipient_email = recipient_email.strip()

        report.approval_status = "approved"
        report.approved_at = datetime.now(timezone.utc)
        report.updated_at = datetime.now(timezone.utc)

        self._record_audit_event(
            db=db,
            case_id=case_id,
            action_type="approved",
            status="success",
            details=f"Report {report.report_type} approved for dispatch (Recipient: {report.recipient_email or 'Default'})",
        )

        db.commit()
        db.refresh(report)
        return report

    def send_approved_report(
        self,
        case_id: str,
        report_id: str,
        db: Session,
        recipient_email: Optional[str] = None,
        attach_passport_pdf: bool = True,
        email_provider: Optional[EmailProvider] = None,
    ) -> Report:
        """
        Dispatch an approved report via the configured email provider.
        CRITICAL SAFETY RULE:
        Rejects immediately if report is not in 'approved' status.
        """
        report = self.get_report(case_id, report_id, db)

        # STRICT SAFETY GATE
        if report.approval_status != "approved":
            raise ReportNotApprovedError(
                f"Report '{report_id}' must be explicitly approved before sending. "
                f"Current status: '{report.approval_status}'."
            )

        # Determine target recipient
        target_to = (
            recipient_email.strip()
            if recipient_email and recipient_email.strip()
            else (report.recipient_email or settings.DEMO_RECIPIENT_EMAIL)
        )

        if not target_to or "@" not in target_to:
            raise ValueError(f"Invalid recipient email address: '{target_to}'")

        provider = email_provider or get_email_provider()

        # Audit attempt
        self._record_audit_event(
            db=db,
            case_id=case_id,
            action_type="send_attempted",
            status="pending",
            details=f"Attempting email dispatch for {report.report_type} to {target_to} (attach_pdf={attach_passport_pdf})",
        )
        db.commit()

        # Generate PDF attachment if requested
        attachment_bytes: Optional[bytes] = None
        attachment_filename: Optional[str] = None

        if attach_passport_pdf:
            try:
                passport = self.passport_svc.get_passport(case_id=case_id, db=db)
                attachment_bytes = self.pdf_svc.generate_passport_pdf(passport)
                attachment_filename = f"CounterPulse_Case_{case_id[:8]}.pdf"
            except Exception as e:
                logger.error("Failed to generate Case Passport PDF for attachment: %s", e)
                # If attachment generation fails, do not silently proceed without user knowledge
                report.approval_status = "failed"
                report.error_message = f"Failed to generate passport PDF attachment: {str(e)}"
                self._record_audit_event(
                    db=db,
                    case_id=case_id,
                    action_type="send_failed",
                    status="failed",
                    details=report.error_message,
                )
                db.commit()
                db.refresh(report)
                raise EmailDispatchError(report.error_message) from e

        # Execute email dispatch
        try:
            if attachment_bytes and attachment_filename:
                resp = provider.send_email_with_attachment(
                    to_email=target_to,
                    subject=report.title,
                    body=report.content_markdown,
                    attachment_bytes=attachment_bytes,
                    attachment_filename=attachment_filename,
                )
            else:
                resp = provider.send_email(
                    to_email=target_to,
                    subject=report.title,
                    body=report.content_markdown,
                )

            # Mark sent
            report.approval_status = "sent"
            report.sent_at = datetime.now(timezone.utc)
            report.recipient_email = target_to
            report.error_message = None
            report.updated_at = datetime.now(timezone.utc)

            self._record_audit_event(
                db=db,
                case_id=case_id,
                action_type="sent",
                status="success",
                details=f"Dispatched {report.report_type} via {resp.get('provider', 'provider')} to {target_to}",
            )
            db.commit()
            db.refresh(report)
            return report

        except Exception as e:
            logger.error("Email dispatch failed for report %s: %s", report_id, e)
            report.approval_status = "failed"
            report.error_message = str(e)
            report.updated_at = datetime.now(timezone.utc)

            self._record_audit_event(
                db=db,
                case_id=case_id,
                action_type="send_failed",
                status="failed",
                details=f"Dispatch failed to {target_to}: {str(e)}",
            )
            db.commit()
            db.refresh(report)
            raise EmailDispatchError(f"Email dispatch failed: {str(e)}") from e

# Global singleton
report_service = ReportService()
