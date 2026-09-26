import React, { useState, useEffect } from "react";
import {
  FileDown,
  Clock,
  AlertTriangle,
  CheckCircle2,
  HelpCircle,
  Activity,
  FileText,
  Copy,
  Check,
  RefreshCw,
  Fingerprint,
  Lock,
  Smartphone,
  CreditCard,
  Globe,
  Shield,
  ArrowRight,
  Database,
  ExternalLink,
} from "lucide-react";

export interface IncidentInfo {
  incident_type: string;
  category: string;
  severity: "critical" | "high" | "medium" | "low" | string;
  summary: string;
  modus_operandi?: string;
}

export interface FinancialInfo {
  loss?: number | null;
  currency: string;
  transactions?: Array<{
    amount: number;
    currency: string;
    description: string;
    source_evidence_id?: string;
  }>;
}

export interface TimelineItem {
  timestamp: string;
  event_description: string;
  source_evidence_id?: string;
  source_reference?: string;
  is_inferred: boolean;
  confidence: string;
}

export interface IndicatorItem {
  indicator_type: string;
  value: string;
  confidence: string;
  verification_status: string;
  source_evidence_id?: string;
  source_reference?: string;
}

export interface CompromiseItem {
  category: string;
  risk_level: string;
  details: string;
  recommended_action: string;
  source_evidence_id?: string;
  source_reference?: string;
}

export interface EvidenceAuditItem {
  evidence_id: string;
  evidence_type: string;
  filename: string;
  processing_status: string;
  created_at: string;
  facts_count: number;
}

export interface CasePassportData {
  case_id: string;
  title: string;
  description?: string;
  status: string;
  created_at: string;
  updated_at: string;
  incident: IncidentInfo;
  financial: FinancialInfo;
  timeline: TimelineItem[];
  indicators: IndicatorItem[];
  compromise: CompromiseItem[];
  immediate_actions: string[];
  evidence_items: EvidenceAuditItem[];
  evidence_count: number;
  disclaimer: string;
}

interface Props {
  caseId: string;
  onNavigateToEvidence?: () => void;
}

export const CasePassportView: React.FC<Props> = ({ caseId, onNavigateToEvidence }) => {
  const [passport, setPassport] = useState<CasePassportData | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [errorStatus, setErrorStatus] = useState<"NOT_FOUND" | "NOT_READY" | "NETWORK_ERROR" | null>(null);
  const [errorMessage, setErrorMessage] = useState<string>("");
  const [isDownloadingPdf, setIsDownloadingPdf] = useState<boolean>(false);
  const [isAnalyzing, setIsAnalyzing] = useState<boolean>(false);
  const [copiedValue, setCopiedValue] = useState<string | null>(null);

  const fetchPassport = async () => {
    if (!caseId) return;
    setIsLoading(true);
    setErrorStatus(null);
    setErrorMessage("");

    try {
      const res = await fetch(`/api/v1/cases/${caseId}/passport`);
      if (res.ok) {
        const data: CasePassportData = await res.json();
        setPassport(data);
      } else if (res.status === 400) {
        const err = await res.json().catch(() => ({}));
        setErrorStatus("NOT_READY");
        setErrorMessage(err.detail || "Case analysis is not ready yet.");
      } else if (res.status === 404) {
        const err = await res.json().catch(() => ({}));
        setErrorStatus("NOT_FOUND");
        setErrorMessage(err.detail || `Case '${caseId}' not found.`);
      } else {
        const err = await res.json().catch(() => ({}));
        setErrorStatus("NETWORK_ERROR");
        setErrorMessage(err.detail || "Failed to load case passport.");
      }
    } catch (err: any) {
      setErrorStatus("NETWORK_ERROR");
      setErrorMessage(err.message || "Network connection error while fetching case passport.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleTriggerAnalysis = async () => {
    setIsAnalyzing(true);
    try {
      const res = await fetch(`/api/v1/cases/${caseId}/analyze`, {
        method: "POST",
      });
      if (res.ok) {
        await fetchPassport();
      } else {
        const err = await res.json().catch(() => ({}));
        alert(`Analysis failed: ${err.detail || "Unknown error"}`);
      }
    } catch (err: any) {
      alert(`Network error triggering analysis: ${err.message}`);
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleDownloadPdf = async () => {
    if (!caseId) return;
    setIsDownloadingPdf(true);
    try {
      const res = await fetch(`/api/v1/cases/${caseId}/passport/pdf`);
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Server returned ${res.status}`);
      }

      const blob = await res.blob();
      const contentDisposition = res.headers.get("Content-Disposition");
      let filename = `CounterPulse_Case_${caseId}.pdf`;
      if (contentDisposition) {
        const match = contentDisposition.match(/filename="?([^"]+)"?/);
        if (match && match[1]) {
          filename = match[1];
        }
      }

      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err: any) {
      alert(`PDF download failed: ${err.message}`);
    } finally {
      setIsDownloadingPdf(false);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedValue(text);
    setTimeout(() => setCopiedValue(null), 2000);
  };

  useEffect(() => {
    fetchPassport();
  }, [caseId]);

  // Loading State
  if (isLoading) {
    return (
      <div className="glass-panel p-16 rounded-2xl border border-slate-800 text-center space-y-4">
        <div className="w-12 h-12 rounded-2xl bg-cyan-950/50 border border-cyan-500/30 flex items-center justify-center text-cyan-400 mx-auto animate-spin">
          <RefreshCw className="w-6 h-6" />
        </div>
        <div>
          <h3 className="text-base font-bold text-white">Aggregating Fraud Case Passport</h3>
          <p className="text-xs text-slate-400 mt-1">
            Loading multimodal evidence artifacts, timeline milestones, and compromise intelligence...
          </p>
        </div>
      </div>
    );
  }

  // Not Ready State
  if (errorStatus === "NOT_READY") {
    return (
      <div className="glass-panel p-12 rounded-2xl border border-slate-800 text-center max-w-xl mx-auto space-y-6">
        <div className="w-14 h-14 rounded-2xl bg-amber-950/40 border border-amber-600/40 flex items-center justify-center text-amber-400 mx-auto shadow-lg shadow-amber-950/30">
          <Clock className="w-7 h-7" />
        </div>
        <div className="space-y-2">
          <h2 className="text-lg font-bold text-white">Case Analysis is Not Ready Yet</h2>
          <p className="text-xs text-slate-400 leading-relaxed max-w-md mx-auto">
            Multimodal incident evidence has been ingested into the case vault, but the multi-agent AI incident reconstruction
            and threat intelligence pipeline has not been executed yet.
          </p>
        </div>
        <div className="flex flex-col sm:flex-row items-center justify-center gap-3 pt-2">
          <button
            onClick={handleTriggerAnalysis}
            disabled={isAnalyzing}
            className="w-full sm:w-auto px-5 py-2.5 bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-800 text-white rounded-xl text-xs font-semibold flex items-center justify-center gap-2 shadow-lg shadow-emerald-950/50 transition cursor-pointer"
          >
            {isAnalyzing ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin text-emerald-200" />
                <span>Running Multi-Agent Orchestration...</span>
              </>
            ) : (
              <>
                <Activity className="w-4 h-4" />
                <span>Run Incident Analysis Now</span>
              </>
            )}
          </button>
          {onNavigateToEvidence && (
            <button
              onClick={onNavigateToEvidence}
              className="w-full sm:w-auto px-4 py-2.5 bg-slate-900 hover:bg-slate-800 border border-slate-700 text-slate-300 rounded-xl text-xs font-semibold flex items-center justify-center gap-2 transition cursor-pointer"
            >
              <span>Manage Evidence Files</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>
    );
  }

  // Not Found or Error State
  if (errorStatus || !passport) {
    return (
      <div className="glass-panel p-12 rounded-2xl border border-rose-900/40 text-center max-w-lg mx-auto space-y-4">
        <div className="w-12 h-12 rounded-2xl bg-rose-950/40 border border-rose-700/50 flex items-center justify-center text-rose-400 mx-auto">
          <AlertTriangle className="w-6 h-6" />
        </div>
        <div className="space-y-1">
          <h2 className="text-base font-bold text-white">Error Loading Case Passport</h2>
          <p className="text-xs text-rose-300 font-mono">{errorMessage || "Case not found."}</p>
        </div>
        <button
          onClick={fetchPassport}
          className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-xl text-xs font-semibold inline-flex items-center gap-2 transition cursor-pointer"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          <span>Retry</span>
        </button>
      </div>
    );
  }

  // Severity Badge Colors
  const severityBadgeClass = {
    critical: "bg-rose-950/70 border-rose-700 text-rose-300",
    high: "bg-amber-950/70 border-amber-700 text-amber-300",
    medium: "bg-sky-950/70 border-sky-700 text-sky-300",
    low: "bg-emerald-950/70 border-emerald-700 text-emerald-300",
  }[passport.incident.severity.toLowerCase()] || "bg-slate-800 border-slate-700 text-slate-300";

  // Category Icon helper
  const getCategoryIcon = (category: string) => {
    const cat = category.toLowerCase();
    if (cat.includes("bank") || cat.includes("financial")) return <CreditCard className="w-4 h-4 text-emerald-400" />;
    if (cat.includes("credential") || cat.includes("password")) return <Lock className="w-4 h-4 text-amber-400" />;
    if (cat.includes("remote")) return <Smartphone className="w-4 h-4 text-rose-400" />;
    if (cat.includes("identity") || cat.includes("pii") || cat.includes("aadhaar")) return <Fingerprint className="w-4 h-4 text-sky-400" />;
    return <Globe className="w-4 h-4 text-slate-400" />;
  };

  return (
    <div className="space-y-8 animate-fadeIn">
      {/* ------------------------------------------------------------- */}
      {/* 1. PASSPORT TOP BAR & DOWNLOAD BUTTON                         */}
      {/* ------------------------------------------------------------- */}
      <div className="glass-panel p-6 rounded-2xl border border-slate-800/90 shadow-2xl flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div className="space-y-1.5">
          <div className="flex items-center gap-3 flex-wrap">
            <span className="font-extrabold text-sm tracking-widest text-slate-400 uppercase font-mono">
              COUNTERPULSE AI
            </span>
            <span className="text-[10px] uppercase font-bold font-mono px-2 py-0.5 rounded bg-cyan-950/80 text-cyan-400 border border-cyan-800/60">
              FRAUD CASE PASSPORT
            </span>
            <span className={`text-[10px] uppercase font-bold font-mono px-2 py-0.5 rounded border ${severityBadgeClass}`}>
              {passport.incident.severity} SEVERITY
            </span>
            <span className="text-[10px] uppercase font-bold font-mono px-2 py-0.5 rounded bg-emerald-950/70 border border-emerald-800 text-emerald-300">
              STATUS: {passport.status.toUpperCase()}
            </span>
          </div>
          <h1 className="text-xl sm:text-2xl font-black text-white tracking-tight">
            {passport.title}
          </h1>
          <p className="text-xs text-slate-400 font-mono">
            CASE ID: {passport.case_id} • Ingested Evidence: {passport.evidence_count} file(s)
          </p>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-3">
          <button
            onClick={fetchPassport}
            className="p-2.5 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-700 text-slate-300 transition"
            title="Refresh Passport Data"
          >
            <RefreshCw className="w-4 h-4" />
          </button>

          <button
            onClick={handleDownloadPdf}
            disabled={isDownloadingPdf}
            className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 disabled:from-slate-800 disabled:to-slate-800 text-white text-xs font-bold tracking-wide shadow-lg shadow-cyan-950/50 flex items-center gap-2.5 transition transform active:scale-95 cursor-pointer"
          >
            {isDownloadingPdf ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin text-cyan-200" />
                <span>Generating Dossier PDF...</span>
              </>
            ) : (
              <>
                <FileDown className="w-4 h-4 text-cyan-200" />
                <span>DOWNLOAD CASE PASSPORT</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* ------------------------------------------------------------- */}
      {/* 2. INCIDENT OVERVIEW CARD                                     */}
      {/* ------------------------------------------------------------- */}
      <div className="glass-panel p-6 rounded-2xl border border-slate-800/90 shadow-xl space-y-6">
        <div className="border-b border-slate-800 pb-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Shield className="w-5 h-5 text-cyan-400" />
            <h2 className="text-sm font-bold text-white uppercase tracking-wider font-mono">
              Incident Reconstruction Overview
            </h2>
          </div>
          <span className="text-[11px] font-mono text-slate-400">
            Updated: {new Date(passport.updated_at).toLocaleString()}
          </span>
        </div>

        {/* Metrics Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800 space-y-1">
            <span className="text-[11px] text-slate-400 block font-mono">Scam Category</span>
            <span className="text-xs font-bold text-white block truncate" title={passport.incident.category}>
              {passport.incident.category}
            </span>
          </div>

          <div className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800 space-y-1">
            <span className="text-[11px] text-slate-400 block font-mono">Classification</span>
            <span className="text-xs font-bold text-slate-200 block truncate">
              {passport.incident.incident_type}
            </span>
          </div>

          <div className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800 space-y-1">
            <span className="text-[11px] text-slate-400 block font-mono">Severity Rating</span>
            <span className={`text-xs font-bold uppercase ${passport.incident.severity === 'critical' ? 'text-rose-400' : (passport.incident.severity === 'high' ? 'text-amber-400' : 'text-sky-400')}`}>
              {passport.incident.severity}
            </span>
          </div>

          <div className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800 space-y-1">
            <span className="text-[11px] text-slate-400 block font-mono">Assessed Financial Loss</span>
            <span className="text-xs font-bold text-rose-400 block truncate">
              {passport.financial.loss !== null && passport.financial.loss !== undefined
                ? `${passport.financial.currency} ${Number(passport.financial.loss).toLocaleString()}`
                : "None Confirmed"}
            </span>
          </div>
        </div>

        {/* Executive Summary */}
        <div className="space-y-2">
          <h3 className="text-xs font-bold text-slate-300 font-mono uppercase tracking-wide">
            Executive Summary
          </h3>
          <p className="text-xs sm:text-sm text-slate-300 leading-relaxed bg-slate-950/50 p-4 rounded-xl border border-slate-800/80">
            {passport.incident.summary}
          </p>
        </div>

        {/* Modus Operandi */}
        {passport.incident.modus_operandi && (
          <div className="space-y-2">
            <h3 className="text-xs font-bold text-slate-300 font-mono uppercase tracking-wide">
              Modus Operandi & Threat Vectors
            </h3>
            <p className="text-xs text-slate-400 leading-relaxed bg-slate-950/40 p-4 rounded-xl border border-slate-800/60">
              {passport.incident.modus_operandi}
            </p>
          </div>
        )}
      </div>

      {/* ------------------------------------------------------------- */}
      {/* 3. IMMEDIATE CONTAINMENT ACTIONS                              */}
      {/* ------------------------------------------------------------- */}
      {passport.immediate_actions && passport.immediate_actions.length > 0 && (
        <div className="glass-panel p-6 rounded-2xl border border-emerald-900/30 shadow-xl space-y-4">
          <div className="flex items-center gap-2 border-b border-slate-800 pb-3">
            <CheckCircle2 className="w-5 h-5 text-emerald-400" />
            <h2 className="text-sm font-bold text-white uppercase tracking-wider font-mono">
              Prioritized Immediate Containment Actions
            </h2>
          </div>
          <div className="grid gap-3">
            {passport.immediate_actions.map((act, idx) => (
              <div
                key={idx}
                className="flex items-start gap-3 p-3.5 rounded-xl bg-slate-950/60 border border-slate-800/90 text-xs text-slate-200"
              >
                <span className="w-5 h-5 rounded-full bg-emerald-950 border border-emerald-700/80 text-emerald-400 font-bold font-mono text-[10px] flex items-center justify-center shrink-0 mt-0.5">
                  {idx + 1}
                </span>
                <span className="leading-relaxed">{act}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ------------------------------------------------------------- */}
      {/* 4. CHRONOLOGICAL TIMELINE                                     */}
      {/* ------------------------------------------------------------- */}
      <div className="glass-panel p-6 rounded-2xl border border-slate-800/90 shadow-xl space-y-6">
        <div className="flex items-center justify-between border-b border-slate-800 pb-4">
          <div className="flex items-center gap-2">
            <Clock className="w-5 h-5 text-sky-400" />
            <h2 className="text-sm font-bold text-white uppercase tracking-wider font-mono">
              Chronological Incident Timeline
            </h2>
          </div>
          <span className="text-xs text-slate-400 font-mono">
            {passport.timeline.length} milestone(s)
          </span>
        </div>

        {passport.timeline.length > 0 ? (
          <div className="relative pl-6 sm:pl-8 space-y-6 before:absolute before:left-3 before:top-2 before:bottom-2 before:w-0.5 before:bg-slate-800">
            {passport.timeline.map((item, idx) => (
              <div key={idx} className="relative group">
                {/* Node icon */}
                <div className="absolute -left-[27px] sm:-left-[35px] top-1 w-3.5 h-3.5 rounded-full bg-sky-950 border-2 border-sky-400 ring-4 ring-[#0b0f17]" />
                <div className="bg-slate-900/50 p-4 rounded-xl border border-slate-800/80 hover:border-slate-700 transition space-y-1.5">
                  <div className="flex items-center justify-between gap-2 flex-wrap">
                    <span className="text-xs font-mono font-bold text-sky-300">
                      {item.timestamp}
                    </span>
                    {item.source_evidence_id && (
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-950 border border-slate-700 text-slate-300 flex items-center gap-1">
                        <FileText className="w-2.5 h-2.5 text-cyan-400" />
                        <span>Source: {item.source_evidence_id}</span>
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-slate-200 leading-relaxed">
                    {item.event_description}
                  </p>
                  {item.source_reference && (
                    <p className="text-[11px] text-slate-400 font-mono italic">
                      "{item.source_reference}"
                    </p>
                  )}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-xs text-slate-500 italic text-center py-4">
            No chronological timeline events established.
          </p>
        )}
      </div>

      {/* ------------------------------------------------------------- */}
      {/* 5. EXTRACTED FORENSIC INDICATORS                              */}
      {/* ------------------------------------------------------------- */}
      <div className="glass-panel p-6 rounded-2xl border border-slate-800/90 shadow-xl space-y-6">
        <div className="flex items-center justify-between border-b border-slate-800 pb-4">
          <div className="flex items-center gap-2">
            <Fingerprint className="w-5 h-5 text-cyan-400" />
            <h2 className="text-sm font-bold text-white uppercase tracking-wider font-mono">
              Extracted Forensic Indicators
            </h2>
          </div>
          <span className="text-xs text-slate-400 font-mono">
            {passport.indicators.length} artifact(s)
          </span>
        </div>

        <p className="text-[11px] text-slate-400 italic">
          Extracted indicators represent technical artifacts derived strictly from evidence; they do not establish criminality of named account holders.
        </p>

        {passport.indicators.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-950/80 text-slate-400 font-mono uppercase text-[10px] border-b border-slate-800">
                <tr>
                  <th className="py-2.5 px-3">Type</th>
                  <th className="py-2.5 px-3">Value</th>
                  <th className="py-2.5 px-3">Confidence</th>
                  <th className="py-2.5 px-3">Verification</th>
                  <th className="py-2.5 px-3">Source Evidence</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-sans">
                {passport.indicators.map((ind, idx) => (
                  <tr key={idx} className="hover:bg-slate-900/40 transition group">
                    <td className="py-3 px-3 font-mono font-bold text-slate-300">
                      {ind.indicator_type.replace("_", " ")}
                    </td>
                    <td className="py-3 px-3 font-mono text-cyan-300 break-all max-w-xs">
                      <div className="flex items-center gap-2">
                        <span>{ind.value}</span>
                        <button
                          onClick={() => copyToClipboard(ind.value)}
                          className="opacity-0 group-hover:opacity-100 text-slate-400 hover:text-white transition cursor-pointer"
                          title="Copy to clipboard"
                        >
                          {copiedValue === ind.value ? (
                            <Check className="w-3 h-3 text-emerald-400" />
                          ) : (
                            <Copy className="w-3 h-3" />
                          )}
                        </button>
                      </div>
                    </td>
                    <td className="py-3 px-3">
                      <span className={`text-[10px] font-mono px-2 py-0.5 rounded uppercase font-semibold ${
                        ind.confidence === "high" ? "bg-emerald-950/60 text-emerald-400 border border-emerald-800/60" : "bg-slate-800 text-slate-300"
                      }`}>
                        {ind.confidence}
                      </span>
                    </td>
                    <td className="py-3 px-3">
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-900 border border-slate-800 text-slate-300 uppercase">
                        {ind.verification_status}
                      </span>
                    </td>
                    <td className="py-3 px-3 font-mono text-[11px] text-slate-400">
                      {ind.source_evidence_id ? (
                        <div>
                          <span className="text-cyan-400 font-semibold">{ind.source_evidence_id}</span>
                          {ind.source_reference && (
                            <span className="block text-[10px] text-slate-500 italic truncate max-w-[160px]" title={ind.source_reference}>
                              {ind.source_reference}
                            </span>
                          )}
                        </div>
                      ) : (
                        "—"
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-xs text-slate-500 italic text-center py-4">
            No forensic indicators detected in evidence files.
          </p>
        )}
      </div>

      {/* ------------------------------------------------------------- */}
      {/* 6. COMPROMISE ASSESSMENT (4-TIER)                             */}
      {/* ------------------------------------------------------------- */}
      <div className="glass-panel p-6 rounded-2xl border border-slate-800/90 shadow-xl space-y-6">
        <div className="flex items-center justify-between border-b border-slate-800 pb-4">
          <div className="flex items-center gap-2">
            <Lock className="w-5 h-5 text-amber-400" />
            <h2 className="text-sm font-bold text-white uppercase tracking-wider font-mono">
              Systemic Compromise Assessment
            </h2>
          </div>
          <span className="text-xs text-slate-400 font-mono">
            {passport.compromise.length} vector(s)
          </span>
        </div>

        {passport.compromise.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {passport.compromise.map((comp, idx) => {
              const risk = comp.risk_level.toUpperCase();
              const badgeClass =
                risk === "CONFIRMED" || risk === "INSTALLED"
                  ? "bg-rose-950/70 border-rose-800 text-rose-300"
                  : risk === "DISCLOSED"
                  ? "bg-amber-950/70 border-amber-800 text-amber-300"
                  : "bg-sky-950/70 border-sky-800 text-sky-300";

              return (
                <div
                  key={idx}
                  className="p-5 rounded-xl bg-slate-900/50 border border-slate-800/80 hover:border-slate-700 transition space-y-3"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      {getCategoryIcon(comp.category)}
                      <span className="text-xs font-bold text-white font-mono uppercase">
                        {comp.category.replace("_", " ")}
                      </span>
                    </div>
                    <span className={`text-[10px] font-mono px-2 py-0.5 rounded border uppercase font-bold ${badgeClass}`}>
                      {comp.risk_level}
                    </span>
                  </div>

                  <p className="text-xs text-slate-300 leading-relaxed">
                    {comp.details}
                  </p>

                  <div className="pt-2 border-t border-slate-800/60 space-y-1">
                    <span className="text-[10px] font-mono uppercase text-slate-400 block font-semibold">
                      Recommended Containment Action:
                    </span>
                    <p className="text-xs text-emerald-400 font-medium">
                      {comp.recommended_action}
                    </p>
                  </div>

                  {comp.source_evidence_id && (
                    <div className="text-[10px] font-mono text-slate-500 pt-1">
                      Evidence Ref: <span className="text-slate-400">{comp.source_evidence_id}</span>
                      {comp.source_reference && ` ("${comp.source_reference}")`}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        ) : (
          <p className="text-xs text-slate-500 italic text-center py-4">
            No compromise vectors identified.
          </p>
        )}
      </div>

      {/* ------------------------------------------------------------- */}
      {/* 7. EVIDENCE & PROVENANCE AUDIT TRAIL                          */}
      {/* ------------------------------------------------------------- */}
      {passport.evidence_items && passport.evidence_items.length > 0 && (
        <div className="glass-panel p-6 rounded-2xl border border-slate-800/90 shadow-xl space-y-4">
          <div className="flex items-center gap-2 border-b border-slate-800 pb-3">
            <Database className="w-5 h-5 text-cyan-400" />
            <h2 className="text-sm font-bold text-white uppercase tracking-wider font-mono">
              Evidence Audit & Provenance Trail
            </h2>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-950/80 text-slate-400 font-mono uppercase text-[10px] border-b border-slate-800">
                <tr>
                  <th className="py-2 px-3">Evidence ID</th>
                  <th className="py-2 px-3">Type</th>
                  <th className="py-2 px-3">Filename</th>
                  <th className="py-2 px-3">Ingest Status</th>
                  <th className="py-2 px-3">Facts Derived</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-sans">
                {passport.evidence_items.map((ev, idx) => (
                  <tr key={idx} className="hover:bg-slate-900/30 transition">
                    <td className="py-2.5 px-3 font-mono font-bold text-cyan-400">{ev.evidence_id}</td>
                    <td className="py-2.5 px-3 uppercase text-[11px] text-slate-300 font-mono">{ev.evidence_type}</td>
                    <td className="py-2.5 px-3 text-slate-200">{ev.filename}</td>
                    <td className="py-2.5 px-3">
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-950/60 border border-emerald-800/60 text-emerald-400 uppercase">
                        {ev.processing_status}
                      </span>
                    </td>
                    <td className="py-2.5 px-3 font-mono font-bold text-slate-300">{ev.facts_count} item(s) cited</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ------------------------------------------------------------- */}
      {/* 8. STATUTORY DISCLAIMER FOOTER                                */}
      {/* ------------------------------------------------------------- */}
      <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800/80 text-center space-y-1">
        <p className="text-[11px] text-slate-400 font-mono">
          {passport.disclaimer}
        </p>
        <p className="text-[10px] text-slate-500 font-mono">
          CounterPulse AI Forensics Engine • Zero Fake Provenance Policy • Statutory 1930 / NCRP Incident Dossier
        </p>
      </div>
    </div>
  );
};
