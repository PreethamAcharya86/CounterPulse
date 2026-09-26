import React, { useState, useEffect, useCallback } from "react";
import {
  FileText,
  Landmark,
  ShieldAlert,
  ShieldCheck,
  Send,
  CheckCircle2,
  AlertTriangle,
  Clock,
  RefreshCw,
  Save,
  Check,
  Mail,
  Paperclip,
  X,
  FileCheck,
  Sparkles,
  Info,
  ChevronRight,
} from "lucide-react";

export interface ReportItem {
  id: string;
  case_id: string;
  report_type: string;
  title: string;
  content_markdown: string;
  content_html?: string | null;
  approval_status: string; // draft, reviewed, approved, sent, failed
  approved_at?: string | null;
  sent_at?: string | null;
  recipient_email?: string | null;
  error_message?: string | null;
  pdf_path?: string | null;
  evidence_references: string[];
  created_at: string;
  updated_at?: string | null;
}

interface Props {
  caseId: string;
  onNavigateToEvidence?: () => void;
  onNavigateToPassport?: () => void;
}

export const ReportsView: React.FC<Props> = ({
  caseId,
  onNavigateToEvidence,
  onNavigateToPassport,
}) => {
  const [reports, setReports] = useState<ReportItem[]>([]);
  const [activeType, setActiveType] = useState<string>("bank_dispute");
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isSaving, setIsSaving] = useState<boolean>(false);
  const [isApproving, setIsApproving] = useState<boolean>(false);
  const [isSending, setIsSending] = useState<boolean>(false);
  const [isGenerating, setIsGenerating] = useState<boolean>(false);

  const [errorStatus, setErrorStatus] = useState<"NOT_FOUND" | "NOT_READY" | "NETWORK_ERROR" | null>(null);
  const [errorMessage, setErrorMessage] = useState<string>("");
  const [successBanner, setSuccessBanner] = useState<string | null>(null);

  // Editable fields for active report
  const [editTitle, setEditTitle] = useState<string>("");
  const [editBody, setEditBody] = useState<string>("");
  const [editRecipient, setEditRecipient] = useState<string>("");
  const [isDirty, setIsDirty] = useState<boolean>(false);

  // Send Confirmation Modal
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);
  const [modalRecipient, setModalRecipient] = useState<string>("");
  const [modalAttachPdf, setModalAttachPdf] = useState<boolean>(true);
  const [modalError, setModalError] = useState<string | null>(null);

  const activeReport = reports.find((r) => r.report_type === activeType) || reports[0];

  // Sync edit form with active report
  useEffect(() => {
    if (activeReport) {
      setEditTitle(activeReport.title);
      setEditBody(activeReport.content_markdown);
      setEditRecipient(activeReport.recipient_email || "");
      setIsDirty(false);
    }
  }, [activeReport?.id, activeType]);

  const fetchReports = useCallback(async () => {
    if (!caseId) return;
    setIsLoading(true);
    setErrorStatus(null);
    setErrorMessage("");

    try {
      const res = await fetch(`/api/v1/cases/${caseId}/reports`);
      if (res.ok) {
        const data: ReportItem[] = await res.json();
        setReports(data);
        if (data.length > 0 && !data.some((r) => r.report_type === activeType)) {
          setActiveType(data[0].report_type);
        }
      } else if (res.status === 400) {
        const err = await res.json().catch(() => ({}));
        setErrorStatus("NOT_READY");
        setErrorMessage(err.detail || "Case analysis is not ready yet. Please run AI analysis first.");
      } else if (res.status === 404) {
        const err = await res.json().catch(() => ({}));
        setErrorStatus("NOT_FOUND");
        setErrorMessage(err.detail || `Case '${caseId}' not found.`);
      } else {
        const err = await res.json().catch(() => ({}));
        setErrorStatus("NETWORK_ERROR");
        setErrorMessage(err.detail || "Failed to load reports from server.");
      }
    } catch (err: any) {
      setErrorStatus("NETWORK_ERROR");
      setErrorMessage(err.message || "Failed to connect to backend service.");
    } finally {
      setIsLoading(false);
    }
  }, [caseId, activeType]);

  useEffect(() => {
    fetchReports();
  }, [fetchReports]);

  // Regenerate/Refresh AI drafts
  const handleRegenerate = async (force: boolean = false) => {
    if (!caseId) return;
    setIsGenerating(true);
    setErrorStatus(null);
    setSuccessBanner(null);

    try {
      const res = await fetch(`/api/v1/cases/${caseId}/reports/generate?force=${force}`, {
        method: "POST",
      });
      if (res.ok) {
        const data = await res.json();
        setReports(data.reports || []);
        setSuccessBanner("Draft reports refreshed from CaseIntelligence.");
        setTimeout(() => setSuccessBanner(null), 4000);
      } else {
        const err = await res.json().catch(() => ({}));
        setErrorMessage(err.detail || "Failed to regenerate reports.");
      }
    } catch (err: any) {
      setErrorMessage(err.message || "Network error while regenerating reports.");
    } finally {
      setIsGenerating(false);
    }
  };

  // Save changes to draft
  const handleSaveDraft = async () => {
    if (!activeReport) return;
    setIsSaving(true);
    setErrorMessage("");
    setSuccessBanner(null);

    try {
      const res = await fetch(`/api/v1/cases/${caseId}/reports/${activeReport.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: editTitle,
          content_markdown: editBody,
          recipient_email: editRecipient.trim() || null,
        }),
      });

      if (res.ok) {
        const updated: ReportItem = await res.json();
        setReports((prev) => prev.map((r) => (r.id === updated.id ? updated : r)));
        setIsDirty(false);
        setSuccessBanner("Draft changes saved successfully.");
        setTimeout(() => setSuccessBanner(null), 3000);
      } else {
        const err = await res.json().catch(() => ({}));
        setErrorMessage(err.detail || "Failed to save draft changes.");
      }
    } catch (err: any) {
      setErrorMessage(err.message || "Network error while saving draft.");
    } finally {
      setIsSaving(false);
    }
  };

  // Explicit approval
  const handleApprove = async () => {
    if (!activeReport) return;
    setIsApproving(true);
    setErrorMessage("");
    setSuccessBanner(null);

    try {
      // First save any unsaved edits if dirty
      if (isDirty) {
        await fetch(`/api/v1/cases/${caseId}/reports/${activeReport.id}`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            title: editTitle,
            content_markdown: editBody,
            recipient_email: editRecipient.trim() || null,
          }),
        });
      }

      const res = await fetch(`/api/v1/cases/${caseId}/reports/${activeReport.id}/approve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          recipient_email: editRecipient.trim() || null,
        }),
      });

      if (res.ok) {
        const updated: ReportItem = await res.json();
        setReports((prev) => prev.map((r) => (r.id === updated.id ? updated : r)));
        setIsDirty(false);
        setSuccessBanner(`Report approved! Ready for dispatch.`);
        setTimeout(() => setSuccessBanner(null), 4000);
      } else {
        const err = await res.json().catch(() => ({}));
        setErrorMessage(err.detail || "Approval failed.");
      }
    } catch (err: any) {
      setErrorMessage(err.message || "Network error during approval.");
    } finally {
      setIsApproving(false);
    }
  };

  // Open confirmation modal
  const handleOpenSendModal = () => {
    if (!activeReport) return;
    setModalRecipient(editRecipient.trim() || activeReport.recipient_email || "");
    setModalAttachPdf(true);
    setModalError(null);
    setIsModalOpen(true);
  };

  // Execute actual dispatch inside confirmation modal
  const handleConfirmSend = async () => {
    if (!activeReport) return;
    setIsSending(true);
    setModalError(null);

    try {
      // If not yet approved, approve it first as part of the explicit user action flow
      if (activeReport.approval_status !== "approved") {
        const appRes = await fetch(`/api/v1/cases/${caseId}/reports/${activeReport.id}/approve`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ recipient_email: modalRecipient.trim() || null }),
        });
        if (!appRes.ok) {
          const appErr = await appRes.json().catch(() => ({}));
          throw new Error(appErr.detail || "Approval failed prior to sending.");
        }
      }

      const res = await fetch(`/api/v1/cases/${caseId}/reports/${activeReport.id}/send`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          recipient_email: modalRecipient.trim() || null,
          attach_passport_pdf: modalAttachPdf,
        }),
      });

      if (res.ok) {
        const sentReport: ReportItem = await res.json();
        setReports((prev) => prev.map((r) => (r.id === sentReport.id ? sentReport : r)));
        setIsModalOpen(false);
        setSuccessBanner(
          `Report dispatched successfully via email to ${sentReport.recipient_email}!`
        );
        setTimeout(() => setSuccessBanner(null), 6000);
      } else {
        const err = await res.json().catch(() => ({}));
        setModalError(err.detail || "Dispatch failed. Please verify provider settings.");
      }
    } catch (err: any) {
      setModalError(err.message || "Network error during email dispatch.");
    } finally {
      setIsSending(false);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status.toLowerCase()) {
      case "approved":
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
            <CheckCircle2 className="w-3.5 h-3.5" />
            Approved for dispatch
          </span>
        );
      case "sent":
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-cyan-500/15 text-cyan-300 border border-cyan-500/30">
            <Send className="w-3.5 h-3.5" />
            Sent successfully
          </span>
        );
      case "failed":
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-rose-500/15 text-rose-400 border border-rose-500/30">
            <AlertTriangle className="w-3.5 h-3.5" />
            Dispatch failed — retry available
          </span>
        );
      case "reviewed":
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-blue-500/15 text-blue-400 border border-blue-500/30">
            <FileCheck className="w-3.5 h-3.5" />
            Ready for approval
          </span>
        );
      case "draft":
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-amber-500/15 text-amber-400 border border-amber-500/30">
            <Sparkles className="w-3.5 h-3.5" />
            AI-generated draft — review required
          </span>
        );
    }
  };

  const getReportTypeIcon = (type: string) => {
    switch (type) {
      case "bank_dispute":
        return <Landmark className="w-5 h-5 text-indigo-400" />;
      case "cybercrime_complaint":
        return <ShieldAlert className="w-5 h-5 text-rose-400" />;
      case "security_advisory":
        return <ShieldCheck className="w-5 h-5 text-emerald-400" />;
      default:
        return <FileText className="w-5 h-5 text-blue-400" />;
    }
  };

  const getReportTypeLabel = (type: string) => {
    switch (type) {
      case "bank_dispute":
        return "Bank Dispute Package";
      case "cybercrime_complaint":
        return "NCRP Cybercrime Complaint";
      case "security_advisory":
        return "Emergency Security Advisory";
      default:
        return type.replace("_", " ").toUpperCase();
    }
  };

  // Render Loading
  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center p-16 space-y-4">
        <RefreshCw className="w-8 h-8 text-indigo-400 animate-spin" />
        <p className="text-slate-400 font-medium tracking-wide">
          Retrieving response packages & intelligence drafts...
        </p>
      </div>
    );
  }

  // Render Not Ready
  if (errorStatus === "NOT_READY") {
    return (
      <div className="max-w-4xl mx-auto p-8 rounded-2xl bg-slate-900/60 border border-amber-500/30 text-center space-y-6">
        <div className="w-16 h-16 mx-auto rounded-2xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400">
          <Clock className="w-8 h-8" />
        </div>
        <div className="space-y-2">
          <h3 className="text-xl font-bold text-slate-100">Intelligence Analysis Required</h3>
          <p className="text-slate-300 max-w-lg mx-auto text-sm leading-relaxed">
            {errorMessage || "Incident intelligence has not been generated for this case yet."}
          </p>
        </div>
        <div className="flex items-center justify-center gap-4 pt-2">
          {onNavigateToEvidence && (
            <button
              onClick={onNavigateToEvidence}
              className="px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-sm transition-colors flex items-center gap-2"
            >
              Go to Evidence Vault & Run AI
              <ChevronRight className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-16">
      {/* Top Banner: Strict Safety Guarantee */}
      <div className="rounded-2xl p-5 bg-gradient-to-r from-indigo-950/40 via-slate-900/60 to-purple-950/40 border border-indigo-500/30 flex flex-col md:flex-row items-start md:items-center justify-between gap-4 shadow-xl">
        <div className="flex items-start gap-3.5">
          <div className="p-2.5 rounded-xl bg-indigo-500/20 border border-indigo-400/30 text-indigo-300 shrink-0 mt-0.5">
            <ShieldCheck className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs uppercase font-extrabold tracking-wider px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                Human-in-the-Loop Enforced
              </span>
              <span className="text-xs text-slate-400">Case ID: {caseId}</span>
            </div>
            <h2 className="text-lg font-bold text-white mt-1">Response Center & Statutory Reports</h2>
            <p className="text-xs text-slate-300 mt-0.5 leading-relaxed max-w-3xl">
              All documents are AI-formulated <strong>draft-only recommendations</strong> adhering to statutory banking guidelines (RBI Circular DBR.No.Leg.BC.78) and Cybercrime reporting protocols. <strong>CounterPulse never executes external transmissions without your explicit review and authorization.</strong>
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          {onNavigateToPassport && (
            <button
              onClick={onNavigateToPassport}
              className="px-3.5 py-2 rounded-xl bg-slate-800/80 hover:bg-slate-700/80 border border-slate-700 text-cyan-300 text-xs font-semibold flex items-center gap-1.5 transition-colors shadow"
              title="Inspect Fraud Case Passport & Download Dossier PDF"
            >
              <FileText className="w-3.5 h-3.5 text-cyan-400" />
              Case Passport
            </button>
          )}
          <button
            onClick={() => handleRegenerate(false)}
            disabled={isGenerating}
            className="px-4 py-2 rounded-xl bg-slate-800/80 hover:bg-slate-700/80 border border-slate-700 text-slate-200 text-xs font-semibold flex items-center gap-2 shrink-0 transition-colors shadow"
            title="Refresh draft packages from latest incident intelligence"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isGenerating ? "animate-spin text-indigo-400" : ""}`} />
            {isGenerating ? "Refreshing..." : "Refresh Drafts"}
          </button>
        </div>
      </div>

      {/* Notifications */}
      {successBanner && (
        <div className="p-4 rounded-xl bg-emerald-950/40 border border-emerald-500/40 text-emerald-300 text-sm flex items-center gap-3 animate-fadeIn">
          <CheckCircle2 className="w-5 h-5 shrink-0 text-emerald-400" />
          <span>{successBanner}</span>
        </div>
      )}
      {errorMessage && (
        <div className="p-4 rounded-xl bg-rose-950/40 border border-rose-500/40 text-rose-300 text-sm flex items-center gap-3 animate-fadeIn">
          <AlertTriangle className="w-5 h-5 shrink-0 text-rose-400" />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* Main Grid: Left Tabs / Right Document Workspace */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Report Selectors & Status */}
        <div className="lg:col-span-4 space-y-3">
          <div className="text-xs font-bold uppercase tracking-wider text-slate-400 px-1">
            Available Response Packages
          </div>

          {reports.map((rep) => {
            const isSelected = activeReport?.id === rep.id;
            return (
              <div
                key={rep.id}
                onClick={() => setActiveType(rep.report_type)}
                className={`p-4 rounded-2xl border cursor-pointer transition-all duration-200 ${
                  isSelected
                    ? "bg-slate-900/90 border-indigo-500/60 shadow-lg shadow-indigo-950/30 ring-1 ring-indigo-500/30"
                    : "bg-slate-900/40 border-slate-800 hover:border-slate-700 hover:bg-slate-900/60"
                }`}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-2.5">
                    <div className="p-2 rounded-xl bg-slate-800/80 border border-slate-700/60">
                      {getReportTypeIcon(rep.report_type)}
                    </div>
                    <div>
                      <h4 className="text-sm font-bold text-white">
                        {getReportTypeLabel(rep.report_type)}
                      </h4>
                      <p className="text-xs text-slate-400 line-clamp-1 mt-0.5">
                        {rep.title}
                      </p>
                    </div>
                  </div>
                </div>

                <div className="mt-3 pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs">
                  {getStatusBadge(rep.approval_status)}
                  <span className="text-[11px] text-slate-500">
                    {rep.sent_at
                      ? `Sent ${new Date(rep.sent_at).toLocaleDateString()}`
                      : rep.updated_at
                      ? `Updated ${new Date(rep.updated_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`
                      : "Draft"}
                  </span>
                </div>
              </div>
            );
          })}

          {/* Quick Help Card */}
          <div className="p-4 rounded-2xl bg-slate-950/40 border border-slate-800/80 text-xs text-slate-400 space-y-2">
            <div className="flex items-center gap-1.5 text-slate-300 font-semibold">
              <Info className="w-4 h-4 text-indigo-400" />
              Human Review Workflow
            </div>
            <ol className="list-decimal list-inside space-y-1 text-slate-400 pl-1 leading-relaxed">
              <li>Review the statutory text and edit any facts.</li>
              <li>Save changes or click <strong>Approve Report</strong>.</li>
              <li>Confirm target recipient before executing dispatch.</li>
              <li>Case Passport PDF is automatically attached.</li>
            </ol>
          </div>
        </div>

        {/* Right Column: Active Document Editor & Dispatch Controls */}
        <div className="lg:col-span-8 space-y-4">
          {activeReport ? (
            <div className="rounded-2xl bg-slate-900/60 border border-slate-700/60 p-6 space-y-6 shadow-2xl backdrop-blur-xl">
              {/* Header Info */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
                <div className="flex items-center gap-3">
                  <div className="p-2.5 rounded-xl bg-slate-800 border border-slate-700 text-indigo-400">
                    {getReportTypeIcon(activeReport.report_type)}
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <h3 className="text-base font-bold text-white">
                        {getReportTypeLabel(activeReport.report_type)}
                      </h3>
                      {getStatusBadge(activeReport.approval_status)}
                    </div>
                    <p className="text-xs text-slate-400 mt-0.5">
                      ID: {activeReport.id.slice(0, 13)}... • Created:{" "}
                      {new Date(activeReport.created_at).toLocaleString()}
                    </p>
                  </div>
                </div>

                {activeReport.approval_status === "sent" && (
                  <div className="text-xs bg-cyan-950/40 border border-cyan-500/30 text-cyan-300 px-3 py-1.5 rounded-xl flex items-center gap-1.5">
                    <CheckCircle2 className="w-4 h-4 text-cyan-400" />
                    Sent to: <strong>{activeReport.recipient_email}</strong>
                  </div>
                )}
              </div>

              {/* Editable Subject */}
              <div className="space-y-1.5">
                <label className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center justify-between">
                  <span>Subject Line</span>
                  {activeReport.approval_status === "sent" && (
                    <span className="text-[11px] text-slate-500 lowercase">(locked: sent)</span>
                  )}
                </label>
                <input
                  type="text"
                  value={editTitle}
                  disabled={activeReport.approval_status === "sent"}
                  onChange={(e) => {
                    setEditTitle(e.target.value);
                    setIsDirty(true);
                  }}
                  className="w-full px-4 py-2.5 rounded-xl bg-slate-950/70 border border-slate-700 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 text-slate-100 text-sm font-medium transition-all disabled:opacity-60"
                  placeholder="Official report subject..."
                />
              </div>

              {/* Target Recipient Field */}
              <div className="space-y-1.5">
                <label className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center justify-between">
                  <span>Designated Recipient Email</span>
                  <span className="text-[11px] text-slate-500">Defaults to configured emergency officer / demo inbox</span>
                </label>
                <div className="relative">
                  <Mail className="w-4 h-4 absolute left-3.5 top-3 text-slate-500" />
                  <input
                    type="email"
                    value={editRecipient}
                    disabled={activeReport.approval_status === "sent"}
                    onChange={(e) => {
                      setEditRecipient(e.target.value);
                      setIsDirty(true);
                    }}
                    className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-slate-950/70 border border-slate-700 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 text-slate-100 text-sm font-medium transition-all disabled:opacity-60"
                    placeholder="e.g. nodal.fraud@bank.com or cybercrime.portal@gov.in"
                  />
                </div>
              </div>

              {/* Editable Body */}
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-bold uppercase tracking-wider text-slate-400">
                    Report Narrative & Declaration
                  </label>
                  <span className="text-xs text-slate-500">
                    {editBody.length} characters
                  </span>
                </div>
                <textarea
                  rows={13}
                  value={editBody}
                  disabled={activeReport.approval_status === "sent"}
                  onChange={(e) => {
                    setEditBody(e.target.value);
                    setIsDirty(true);
                  }}
                  className="w-full p-4 rounded-xl bg-slate-950/70 border border-slate-700 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 text-slate-200 text-sm font-mono leading-relaxed transition-all disabled:opacity-60 resize-y"
                  placeholder="Draft complaint narrative..."
                />
              </div>

              {/* Evidence Provenance References */}
              {activeReport.evidence_references && activeReport.evidence_references.length > 0 && (
                <div className="p-3.5 rounded-xl bg-slate-950/40 border border-slate-800 space-y-2">
                  <div className="text-xs font-semibold text-slate-400 flex items-center gap-1.5">
                    <Paperclip className="w-3.5 h-3.5 text-indigo-400" />
                    Forensic Evidence Provenance Citing
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {activeReport.evidence_references.map((refId, i) => (
                      <span
                        key={i}
                        className="px-2.5 py-1 rounded-lg bg-slate-800/80 border border-slate-700 text-slate-300 text-xs font-mono"
                      >
                        Item #{refId.slice(0, 8)}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Action Buttons Bar */}
              <div className="pt-4 border-t border-slate-800 flex flex-col sm:flex-row items-center justify-between gap-3">
                <div className="flex items-center gap-2 w-full sm:w-auto">
                  <button
                    onClick={handleSaveDraft}
                    disabled={isSaving || activeReport.approval_status === "sent" || !isDirty}
                    className="px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 text-xs font-bold flex items-center justify-center gap-2 transition-colors disabled:opacity-40 w-full sm:w-auto"
                  >
                    <Save className="w-4 h-4" />
                    {isSaving ? "Saving..." : "Save Draft"}
                  </button>

                  {activeReport.approval_status !== "approved" &&
                    activeReport.approval_status !== "sent" && (
                      <button
                        onClick={handleApprove}
                        disabled={isApproving}
                        className="px-4 py-2.5 rounded-xl bg-emerald-600/90 hover:bg-emerald-500 text-white text-xs font-bold flex items-center justify-center gap-2 transition-colors shadow-lg shadow-emerald-950/30 disabled:opacity-40 w-full sm:w-auto"
                      >
                        <Check className="w-4 h-4" />
                        {isApproving ? "Approving..." : "Approve Report"}
                      </button>
                    )}
                </div>

                <div className="flex items-center gap-2 w-full sm:w-auto justify-end">
                  <button
                    onClick={handleOpenSendModal}
                    disabled={activeReport.approval_status === "sent"}
                    className={`px-5 py-2.5 rounded-xl text-xs font-bold flex items-center justify-center gap-2 transition-all shadow-lg w-full sm:w-auto ${
                      activeReport.approval_status === "approved"
                        ? "bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white shadow-indigo-950/50"
                        : "bg-slate-800 hover:bg-slate-700 text-indigo-300 border border-indigo-500/40"
                    } disabled:opacity-40`}
                  >
                    <Send className="w-4 h-4" />
                    {activeReport.approval_status === "approved" ? "Dispatch Report" : "Approve & Send"}
                  </button>
                </div>
              </div>
            </div>
          ) : (
            <div className="p-12 text-center text-slate-400 bg-slate-900/40 rounded-2xl border border-slate-800">
              Select a report package from the left panel.
            </div>
          )}
        </div>
      </div>

      {/* TWO-STEP CONFIRMATION MODAL */}
      {isModalOpen && activeReport && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fadeIn">
          <div className="bg-slate-900 border border-indigo-500/40 rounded-2xl max-w-lg w-full p-6 space-y-5 shadow-2xl relative">
            <button
              onClick={() => setIsModalOpen(false)}
              className="absolute top-4 right-4 p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>

            <div className="flex items-start gap-3.5">
              <div className="p-3 rounded-xl bg-indigo-500/20 border border-indigo-500/30 text-indigo-300 shrink-0">
                <Send className="w-6 h-6" />
              </div>
              <div>
                <h3 className="text-lg font-bold text-white">Review Before Sending</h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Consequential dispatch of {getReportTypeLabel(activeReport.report_type)}
                </p>
              </div>
            </div>

            {modalError && (
              <div className="p-3.5 rounded-xl bg-rose-950/50 border border-rose-500/40 text-rose-300 text-xs flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 shrink-0 text-rose-400" />
                <span>{modalError}</span>
              </div>
            )}

            <div className="space-y-4 text-xs">
              <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800 space-y-2">
                <div className="text-slate-400 font-medium">Report Subject:</div>
                <div className="font-semibold text-slate-200 line-clamp-2">
                  {editTitle}
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="font-bold uppercase tracking-wider text-slate-400">
                  Target Recipient Email Address
                </label>
                <input
                  type="email"
                  value={modalRecipient}
                  onChange={(e) => setModalRecipient(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-slate-700 text-slate-100 text-sm focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 font-medium"
                  placeholder="recipient@example.com"
                />
              </div>

              <label className="flex items-center gap-3 p-3 rounded-xl bg-slate-950/60 border border-slate-800 cursor-pointer hover:bg-slate-950/90 transition-colors">
                <input
                  type="checkbox"
                  checked={modalAttachPdf}
                  onChange={(e) => setModalAttachPdf(e.target.checked)}
                  className="rounded border-slate-700 text-indigo-600 focus:ring-indigo-500 w-4 h-4"
                />
                <div className="flex items-center gap-2 text-slate-300">
                  <Paperclip className="w-4 h-4 text-indigo-400" />
                  <span>Attach Official Case Passport PDF Dossier</span>
                </div>
              </label>

              <div className="p-3.5 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-300 text-[11px] leading-relaxed flex items-start gap-2">
                <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5 text-amber-400" />
                <div>
                  <strong>SAFETY AUDIT NOTICE:</strong> This action will send the reviewed report to the configured recipient and create an immutable audit record in the incident ledger.
                </div>
              </div>
            </div>

            <div className="flex items-center justify-end gap-3 pt-2 border-t border-slate-800">
              <button
                type="button"
                onClick={() => setIsModalOpen(false)}
                disabled={isSending}
                className="px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold transition-colors"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleConfirmSend}
                disabled={isSending || !modalRecipient}
                className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white text-xs font-bold shadow-lg shadow-indigo-950/50 flex items-center gap-2 transition-all disabled:opacity-40"
              >
                {isSending ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    Dispatching...
                  </>
                ) : (
                  <>
                    <Send className="w-4 h-4" />
                    Confirm & Dispatch
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
