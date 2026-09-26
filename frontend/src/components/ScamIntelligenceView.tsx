import { useState, useEffect, useCallback } from "react";
import {
  Brain,
  Shield,
  ShieldAlert,
  Phone,
  CreditCard,
  Globe,
  Building,
  AlertTriangle,
  Play,
  Copy,
  Check,
  PlusCircle,
  FileText,
  Send,
  Sparkles,
  RefreshCw,
  Search,
  MessageSquare,
  Lock,
} from "lucide-react";

export interface ScamIntelligenceItem {
  indicator_type: string;
  value: string;
  confidence: string;
  verification_status: string;
  source_message_index?: number | null;
  source_reference: string;
  source_evidence_id?: string | null;
  context?: string | null;
}

export interface ScamIntelligenceAnalysisResponse {
  case_id: string;
  conversation_summary: string;
  scam_type: string;
  threat_assessment: string;
  tactics_observed: string[];
  psychological_triggers: string[];
  urgency_level: string;
  indicators: ScamIntelligenceItem[];
  phone_numbers: ScamIntelligenceItem[];
  upi_ids: ScamIntelligenceItem[];
  urls: ScamIntelligenceItem[];
  emails: ScamIntelligenceItem[];
  claimed_entities: ScamIntelligenceItem[];
  financial_amounts: ScamIntelligenceItem[];
  transaction_references: ScamIntelligenceItem[];
  scam_tactics: ScamIntelligenceItem[];
  requested_actions: ScamIntelligenceItem[];
  disclaimer: string;
  added_to_case_count: number;
}

export interface CaseEvidenceItem {
  id: string;
  filename: string;
  evidence_type: string;
  raw_content?: string | null;
  processing_status: string;
}

interface ScamIntelligenceViewProps {
  caseId: string;
  onNavigateToPassport?: () => void;
  onNavigateToReports?: () => void;
}

const PRESET_SCENARIOS = [
  {
    id: "digital_arrest",
    title: "Digital Arrest & Narcotics Extortion",
    description: "Impersonator posing as DCP Crime Branch alleging seized parcel containing contraband.",
    conversation: `[10:01] Suspect: This is DCP Vikram from Delhi Police Crime Branch. You are under immediate digital arrest under Section 420/NDPS Act.
[10:02] Suspect: Call our verification desk immediately at +91 98765 43210 or face physical remand within 2 hours.
[10:03] Victim: Sir please, I am a school teacher in Bangalore! I have never ordered anything from Mumbai or abroad!
[10:04] Suspect: A customs package in your name containing 140g of MDMA and 5 fake passports was intercepted at Mumbai Air Cargo.
[10:05] Suspect: Supreme Court has issued high-priority search warrants. Stay on video call and do not disconnect under penalty of law.
[10:06] Suspect: To prove your innocence, transfer an urgent verification security deposit of INR 1,50,000 to the statutory RBI holding account.
[10:07] Suspect: Beneficiary UPI: clearance.vault@icici. Reference UTR will be generated automatically.
[10:08] Suspect: Verify your clearance token at https://narcotics-case-clearance.gov-portal.org/clearance with case ID NDPS-8827.
[10:09] Suspect: Direct confirmation queries to officer desk: investigator.vikram@delhi-crimecell.gov.in.`,
  },
  {
    id: "power_disconnection",
    title: "Electricity Power Disconnection Threat",
    description: "Fake power board alert threatening immediate power cutoff without payment/app install.",
    conversation: `[18:30] Suspect: URGENT NOTICE from BESCOM Electricity Board: Your electricity power will be disconnected tonight at 9:30 PM due to unpaid bill of INR 4,850.
[18:31] Victim: But I paid my monthly bill last week through the BESCOM portal!
[18:32] Suspect: Last month update was not updated in our master server. Call officer Rajesh at 9845123456 immediately.
[18:33] Suspect: Download our official QuickSupport verification update app from https://bescom-bill-update.cc/app.apk to clear status.
[18:34] Suspect: Or pay immediate re-verification charge of ₹10 to bescom.recharge@oksbi to abort automated grid disconnection.`,
  },
  {
    id: "job_review_scam",
    title: "Telegram Part-Time Rating & Review Scam",
    description: "High-yield task investment scam requiring progressive deposits into mule UPI IDs.",
    conversation: `[11:00] Suspect: Hello! Earn INR 3,000 to 8,000 daily from home by rating hotels and Google Maps locations.
[11:01] Victim: How does this work? Is there any registration fee?
[11:02] Suspect: No registration fee! We pay you INR 150 for each 5-star rating. Join our task team at https://telegram.me/global_hotels_marketing.
[11:05] Suspect: Congratulations on completing 3 ratings! We have credited ₹450 to you.
[11:08] Suspect: Next task is VIP Merchant Task: Deposit ₹10,000 to upi handle merchant.escrow@hdfcbank to unlock 40% immediate commission of ₹14,000.
[11:09] Suspect: Transfer reference UTR: TXN20260926001. Send screenshot to coordinator at vip.desk@marketing-tasks.net.`,
  },
];

export function ScamIntelligenceView({
  caseId,
  onNavigateToPassport,
  onNavigateToReports,
}: ScamIntelligenceViewProps) {
  const [sourceType, setSourceType] = useState<"preset" | "evidence" | "custom">("evidence");
  const [selectedScenarioId, setSelectedScenarioId] = useState<string>("digital_arrest");
  const [conversationText, setConversationText] = useState<string>("");
  const [customText, setCustomText] = useState<string>("");
  const [caseEvidenceList, setCaseEvidenceList] = useState<CaseEvidenceItem[]>([]);
  const [selectedEvidenceId, setSelectedEvidenceId] = useState<string>("");
  const [selectedMessageIndex, setSelectedMessageIndex] = useState<number | null>(null);

  // Analysis State
  const [intelligence, setIntelligence] = useState<ScamIntelligenceAnalysisResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [addingToCase, setAddingToCase] = useState(false);
  const [addSuccessMsg, setAddSuccessMsg] = useState<string | null>(null);
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  // Fetch existing case evidence and pre-existing indicators
  const fetchCaseEvidence = useCallback(async () => {
    if (!caseId) return;
    try {
      const res = await fetch(`/api/v1/cases/${caseId}/evidence`);
      if (res.ok) {
        const data: CaseEvidenceItem[] = await res.json();
        setCaseEvidenceList(data);
        const validEv = data.find((e) => e.raw_content && e.raw_content.trim().length > 0);
        if (validEv) {
          setSourceType("evidence");
          setSelectedEvidenceId(validEv.id);
          setConversationText(validEv.raw_content || "");
        }
      }
    } catch (e) {
      console.error("Failed to load case evidence:", e);
    }
  }, [caseId]);

  // Load existing intelligence on mount
  useEffect(() => {
    fetchCaseEvidence();
    setSelectedMessageIndex(null);
    setIntelligence(null);
    setError(null);
  }, [caseId, fetchCaseEvidence]);

  const handleScenarioChange = (scenarioId: string) => {
    setSelectedScenarioId(scenarioId);
    const scen = PRESET_SCENARIOS.find((s) => s.id === scenarioId);
    if (scen) {
      setConversationText(scen.conversation);
      setSelectedMessageIndex(null);
    }
  };

  const handleSelectEvidenceSource = (evId: string) => {
    setSelectedEvidenceId(evId);
    const ev = caseEvidenceList.find((e) => e.id === evId);
    if (ev && ev.raw_content) {
      setConversationText(ev.raw_content);
      setSelectedMessageIndex(null);
    }
  };

  const handleCopy = (text: string, key: string) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  const runAnalysis = async (focusMessageIndex?: number | null) => {
    if (!caseId) return;
    const textToAnalyze =
      sourceType === "custom"
        ? customText
        : conversationText;

    if (!textToAnalyze || textToAnalyze.trim() === "") {
      setError("Please provide or select conversation text to analyze.");
      return;
    }

    setLoading(true);
    setError(null);
    setAddSuccessMsg(null);

    try {
      const res = await fetch(`/api/v1/cases/${caseId}/scam-intelligence/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          conversation_text: textToAnalyze,
          evidence_id: sourceType === "evidence" ? selectedEvidenceId || null : null,
          selected_message_index: focusMessageIndex !== undefined ? focusMessageIndex : selectedMessageIndex,
          add_to_case: false,
        }),
      });

      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new Error(errJson.detail || `Analysis failed with status ${res.status}`);
      }

      const data: ScamIntelligenceAnalysisResponse = await res.json();
      setIntelligence(data);
    } catch (err: any) {
      console.error("Scam intelligence error:", err);
      setError(err.message || "Failed to analyze conversation intelligence.");
    } finally {
      setLoading(false);
    }
  };

  const handleAddToCase = async () => {
    if (!caseId || !intelligence || !intelligence.indicators.length) return;
    setAddingToCase(true);
    setAddSuccessMsg(null);

    try {
      const res = await fetch(`/api/v1/cases/${caseId}/scam-intelligence/add-to-case`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          indicators: intelligence.indicators,
          evidence_id: sourceType === "evidence" ? selectedEvidenceId || null : null,
        }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Failed to add indicators to case.");
      }

      const result = await res.json();
      setAddSuccessMsg(result.message);
    } catch (err: any) {
      console.error("Failed to add indicators:", err);
      setError(err.message || "Could not add indicators to case vault.");
    } finally {
      setAddingToCase(false);
    }
  };

  // Parse lines for message bubble rendering
  const activeTranscript = sourceType === "custom" ? customText : conversationText;
  const parsedLines = activeTranscript
    .split("\n")
    .map((l) => l.trim())
    .filter((l) => l.length > 0);

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5 shadow-xl backdrop-blur-xl">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-cyan-950/80 border border-cyan-800/80 text-cyan-400 shadow-inner">
              <Brain className="h-6 w-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-lg font-bold text-slate-100 tracking-wide">
                  Scam Intelligence & Controlled Conversation
                </h2>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-cyan-950/90 text-cyan-300 border border-cyan-800/60 uppercase">
                  Agentic Intel
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                Defensive conversational analysis, real-time indicator extraction, and CaseIntelligence integration.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-950/80 border border-slate-800 text-[11px] font-mono text-emerald-400">
              <Shield className="w-3.5 h-3.5 text-emerald-400" />
              <span>Safety Gate: Defensive Only</span>
            </div>
            {onNavigateToPassport && (
              <button
                onClick={onNavigateToPassport}
                className="px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs font-semibold flex items-center gap-1.5 transition cursor-pointer"
              >
                <FileText className="w-3.5 h-3.5 text-cyan-400" />
                <span>Case Passport</span>
              </button>
            )}
            {onNavigateToReports && (
              <button
                onClick={onNavigateToReports}
                className="px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs font-semibold flex items-center gap-1.5 transition cursor-pointer"
              >
                <Send className="w-3.5 h-3.5 text-indigo-400" />
                <span>Response Center</span>
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Main Two-Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* LEFT COLUMN: Controlled Conversation / Evidence (5 Cols) */}
        <div className="lg:col-span-5 space-y-4">
          <div className="rounded-2xl border border-slate-800 bg-slate-900/50 p-4 shadow-xl backdrop-blur-md space-y-4">
            {/* Source Selection Tabs */}
            <div className="flex items-center justify-between border-b border-slate-800/80 pb-3">
              <div className="flex items-center gap-1 bg-slate-950/80 p-1 rounded-xl border border-slate-800 text-xs">
                <button
                  onClick={() => setSourceType("evidence")}
                  className={`px-3 py-1 rounded-lg font-medium transition cursor-pointer ${
                    sourceType === "evidence"
                      ? "bg-cyan-950 text-cyan-300 border border-cyan-800/80"
                      : "text-slate-400 hover:text-slate-200"
                  }`}
                >
                  Case Evidence ({caseEvidenceList.length})
                </button>
                <button
                  onClick={() => setSourceType("custom")}
                  className={`px-3 py-1 rounded-lg font-medium transition cursor-pointer ${
                    sourceType === "custom"
                      ? "bg-cyan-950 text-cyan-300 border border-cyan-800/80"
                      : "text-slate-400 hover:text-slate-200"
                  }`}
                >
                  Custom Transcript
                </button>
                <button
                  onClick={() => setSourceType("preset")}
                  className={`px-3 py-1 rounded-lg font-medium transition cursor-pointer ${
                    sourceType === "preset"
                      ? "bg-cyan-950 text-cyan-300 border border-cyan-800/80"
                      : "text-slate-400 hover:text-slate-200"
                  }`}
                >
                  ⚡ Synthetic Demo (Testing)
                </button>
              </div>

              <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded bg-slate-800/80 text-slate-400 border border-slate-700/60">
                {sourceType === "preset"
                  ? "Synthetic Demo"
                  : sourceType === "evidence"
                  ? "Real Case Evidence"
                  : "User Supplied"}
              </span>
            </div>

            {/* Scenario Chooser or Evidence Chooser */}
            {sourceType === "preset" && (
              <div className="space-y-2">
                <label className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
                  <Sparkles className="w-3.5 h-3.5 text-cyan-400" />
                  Select Synthetic Scam Scenario:
                </label>
                <div className="grid grid-cols-1 gap-2">
                  {PRESET_SCENARIOS.map((scen) => (
                    <button
                      key={scen.id}
                      onClick={() => handleScenarioChange(scen.id)}
                      className={`text-left p-2.5 rounded-xl border text-xs transition cursor-pointer ${
                        selectedScenarioId === scen.id
                          ? "bg-cyan-950/40 border-cyan-800/80 text-slate-100 shadow-sm"
                          : "bg-slate-950/40 border-slate-850 text-slate-400 hover:border-slate-700 hover:text-slate-200"
                      }`}
                    >
                      <div className="font-semibold text-slate-200 flex items-center justify-between">
                        <span>{scen.title}</span>
                        {selectedScenarioId === scen.id && (
                          <span className="h-2 w-2 rounded-full bg-cyan-400 shadow-sm shadow-cyan-400" />
                        )}
                      </div>
                      <p className="text-[11px] text-slate-400 mt-0.5 line-clamp-1">
                        {scen.description}
                      </p>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {sourceType === "evidence" && (
              <div className="space-y-2">
                <label className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
                  <FileText className="w-3.5 h-3.5 text-emerald-400" />
                  Select Case Evidence Source:
                </label>
                {caseEvidenceList.length === 0 ? (
                  <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800 text-xs text-slate-400 text-center">
                    No evidence items uploaded yet in this case vault. Use synthetic scenarios or upload chat logs in Evidence Vault.
                  </div>
                ) : (
                  <select
                    value={selectedEvidenceId}
                    onChange={(e) => handleSelectEvidenceSource(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-850 rounded-xl px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
                  >
                    <option value="">-- Choose Evidence Item --</option>
                    {caseEvidenceList.map((ev) => (
                      <option key={ev.id} value={ev.id}>
                        [{ev.id}] {ev.filename} ({ev.evidence_type})
                      </option>
                    ))}
                  </select>
                )}
              </div>
            )}

            {sourceType === "custom" && (
              <div className="space-y-2">
                <label className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
                  <MessageSquare className="w-3.5 h-3.5 text-purple-400" />
                  Paste Custom Dialogue Transcript:
                </label>
                <textarea
                  rows={6}
                  value={customText}
                  onChange={(e) => setCustomText(e.target.value)}
                  placeholder="Paste dialogue here: [timestamp] Speaker: content..."
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-xs font-mono text-slate-200 focus:outline-none focus:border-cyan-500 placeholder-slate-600"
                />
              </div>
            )}

            {/* Conversation Messages Display */}
            <div className="space-y-2">
              <div className="flex items-center justify-between text-xs text-slate-400">
                <span className="font-semibold text-slate-300">
                  Dialogue Flow ({parsedLines.length} Messages):
                </span>
                <span className="text-[11px] text-slate-500">
                  Click message to inspect / focus
                </span>
              </div>

              <div className="space-y-2 max-h-[360px] overflow-y-auto pr-1">
                {parsedLines.map((line, idx) => {
                  const msgNum = idx + 1;
                  const isSelected = selectedMessageIndex === msgNum;
                  const isSuspect =
                    line.toLowerCase().includes("suspect:") ||
                    line.toLowerCase().includes("caller:") ||
                    line.toLowerCase().includes("officer") ||
                    line.toLowerCase().includes("dcp");

                  return (
                    <div
                      key={idx}
                      onClick={() =>
                        setSelectedMessageIndex(isSelected ? null : msgNum)
                      }
                      className={`p-3 rounded-xl border text-xs cursor-pointer transition relative group ${
                        isSelected
                          ? "bg-cyan-950/40 border-cyan-500 shadow-md shadow-cyan-950/50"
                          : isSuspect
                          ? "bg-slate-950/70 border-red-950/50 hover:border-red-900/60 text-slate-200"
                          : "bg-slate-950/50 border-slate-800/80 hover:border-slate-700 text-slate-300"
                      }`}
                    >
                      <div className="flex items-center justify-between gap-2 mb-1">
                        <div className="flex items-center gap-1.5">
                          <span
                            className={`text-[10px] font-mono px-1.5 py-0.2 rounded font-semibold ${
                              isSuspect
                                ? "bg-red-950 text-red-300 border border-red-800/60"
                                : "bg-emerald-950 text-emerald-300 border border-emerald-800/60"
                            }`}
                          >
                            {isSuspect ? "SUSPECT / CALLER" : "VICTIM / CALLEE"}
                          </span>
                          <span className="text-[10px] font-mono text-slate-500">
                            Message #{msgNum}
                          </span>
                        </div>
                        {isSelected && (
                          <span className="text-[10px] font-mono text-cyan-400 font-semibold">
                            ACTIVE FOCUS
                          </span>
                        )}
                      </div>
                      <p className="font-mono text-[11px] leading-relaxed break-words">
                        {line}
                      </p>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Selected Message Inspector Banner */}
            {selectedMessageIndex !== null && (
              <div className="p-3 rounded-xl bg-cyan-950/30 border border-cyan-800/60 text-xs flex items-center justify-between">
                <div>
                  <span className="font-semibold text-cyan-300">
                    Focused on Message #{selectedMessageIndex}
                  </span>
                  <p className="text-[11px] text-slate-400">
                    Targeted analysis will isolate indicators from this message only.
                  </p>
                </div>
                <button
                  onClick={() => setSelectedMessageIndex(null)}
                  className="px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-[11px] cursor-pointer"
                >
                  Clear Selection
                </button>
              </div>
            )}

            {/* Action Bar */}
            <div className="flex items-center gap-2 pt-2 border-t border-slate-800/80">
              <button
                onClick={() => runAnalysis(null)}
                disabled={loading}
                className="flex-1 py-2.5 px-4 rounded-xl bg-cyan-600 hover:bg-cyan-500 disabled:bg-cyan-900 text-white font-semibold text-xs flex items-center justify-center gap-2 shadow-lg shadow-cyan-950/50 transition cursor-pointer"
              >
                {loading ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    <span>Analyzing Conversation Stream...</span>
                  </>
                ) : (
                  <>
                    <Brain className="w-4 h-4" />
                    <span>Analyze Full Conversation</span>
                  </>
                )}
              </button>

              {selectedMessageIndex !== null && (
                <button
                  onClick={() => runAnalysis(selectedMessageIndex)}
                  disabled={loading}
                  className="py-2.5 px-3 rounded-xl bg-slate-800 hover:bg-slate-700 text-cyan-300 border border-cyan-800 text-xs font-semibold flex items-center gap-1.5 transition cursor-pointer"
                >
                  <Search className="w-3.5 h-3.5" />
                  <span>Analyze #{selectedMessageIndex}</span>
                </button>
              )}
            </div>
          </div>
        </div>

        {/* RIGHT COLUMN: Live Extracted Intelligence & Case Integration (7 Cols) */}
        <div className="lg:col-span-7 space-y-4">
          {error && (
            <div className="p-4 rounded-2xl border border-red-800/80 bg-red-950/40 text-red-200 text-xs flex items-start gap-3 shadow-lg">
              <AlertTriangle className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />
              <div>
                <span className="font-semibold text-red-300">Analysis Notice</span>
                <p className="mt-1 text-slate-300">{error}</p>
              </div>
            </div>
          )}

          {addSuccessMsg && (
            <div className="p-4 rounded-2xl border border-emerald-800/80 bg-emerald-950/40 text-emerald-200 text-xs flex items-start gap-3 shadow-lg">
              <Check className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
              <div>
                <span className="font-semibold text-emerald-300">Case Vault Integration Verified</span>
                <p className="mt-1 text-slate-300">{addSuccessMsg}</p>
                <div className="mt-2 flex items-center gap-2">
                  {onNavigateToPassport && (
                    <button
                      onClick={onNavigateToPassport}
                      className="text-xs text-cyan-400 hover:text-cyan-300 underline font-semibold cursor-pointer"
                    >
                      View in Case Passport →
                    </button>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Empty / Unanalyzed State */}
          {!intelligence && !loading && (
            <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-12 text-center shadow-xl space-y-4 backdrop-blur-md">
              <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-slate-950 border border-slate-800 text-cyan-400 shadow-inner">
                <Brain className="h-7 w-7" />
              </div>
              <div className="max-w-md mx-auto space-y-1">
                <h3 className="text-sm font-bold text-slate-200">
                  Standing By for Conversation Intelligence
                </h3>
                <p className="text-xs text-slate-400 leading-relaxed">
                  Select a synthetic conversation or evidence source from the left and click{" "}
                  <strong className="text-cyan-300 font-medium">"Analyze Full Conversation"</strong>.
                  The system will dynamically extract phone numbers, UPI handles, phishing URLs,
                  financial demands, and coercive psychological tactics with source provenance.
                </p>
              </div>
              <button
                onClick={() => runAnalysis(null)}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 text-xs font-semibold cursor-pointer transition shadow-md"
              >
                <Play className="w-3.5 h-3.5 text-cyan-400" />
                <span>Launch Analysis Now</span>
              </button>
            </div>
          )}

          {/* Loading State */}
          {loading && (
            <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-12 text-center shadow-xl space-y-4 backdrop-blur-md">
              <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-cyan-950/80 border border-cyan-800 text-cyan-400 shadow-inner animate-pulse">
                <RefreshCw className="h-7 w-7 animate-spin" />
              </div>
              <div className="space-y-1">
                <h3 className="text-sm font-bold text-slate-200">
                  Extracting Real-Time Conversation Intelligence
                </h3>
                <p className="text-xs text-slate-400 font-mono">
                  Running ScamIntelligenceAgent + forensic regex extractors + entity profiling...
                </p>
              </div>
            </div>
          )}

          {/* Analyzed Intelligence Dashboard */}
          {intelligence && !loading && (
            <div className="space-y-4">
              {/* Executive Overview Card */}
              <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5 shadow-xl backdrop-blur-md space-y-3">
                <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800/80 pb-3">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold text-slate-300">Scam Typology:</span>
                    <span className="text-xs font-semibold px-2.5 py-1 rounded-lg bg-red-950/80 text-red-300 border border-red-800/60">
                      {intelligence.scam_type}
                    </span>
                  </div>

                  <div className="flex items-center gap-2">
                    <span className="text-xs text-slate-400">Threat Urgency:</span>
                    <span
                      className={`text-xs font-bold px-2 py-0.5 rounded font-mono ${
                        intelligence.urgency_level === "critical"
                          ? "bg-red-950 text-red-300 border border-red-800"
                          : "bg-amber-950 text-amber-300 border border-amber-800"
                      }`}
                    >
                      {intelligence.urgency_level.toUpperCase()}
                    </span>
                  </div>
                </div>

                <div className="space-y-1">
                  <span className="text-xs font-semibold text-slate-300">Threat Vector Assessment:</span>
                  <p className="text-xs text-slate-300 leading-relaxed bg-slate-950/60 p-3 rounded-xl border border-slate-850">
                    {intelligence.threat_assessment}
                  </p>
                </div>

                {/* Case Integration Action Bar */}
                <div className="flex flex-wrap items-center justify-between gap-3 pt-2">
                  <div className="flex items-center gap-2 text-xs text-slate-400 font-mono">
                    <span>{intelligence.indicators.length} forensic items extracted</span>
                  </div>

                  <button
                    onClick={handleAddToCase}
                    disabled={addingToCase || intelligence.indicators.length === 0}
                    className="py-2 px-4 rounded-xl bg-emerald-600 hover:bg-emerald-500 disabled:bg-emerald-900 text-white font-semibold text-xs flex items-center gap-2 shadow-lg shadow-emerald-950/50 transition cursor-pointer"
                  >
                    {addingToCase ? (
                      <>
                        <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                        <span>Merging into Case Vault...</span>
                      </>
                    ) : (
                      <>
                        <PlusCircle className="w-3.5 h-3.5" />
                        <span>Add {intelligence.indicators.length} Indicators to Case Vault</span>
                      </>
                    )}
                  </button>
                </div>
              </div>

              {/* Categorized Intelligence Panels */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* 1. Phone Numbers */}
                <div className="rounded-2xl border border-slate-800 bg-slate-900/50 p-4 shadow-md space-y-2.5">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 text-xs font-bold text-slate-200">
                      <Phone className="w-4 h-4 text-cyan-400" />
                      <span>Phone Numbers ({intelligence.phone_numbers.length})</span>
                    </div>
                    <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-950 text-slate-400 border border-slate-800">
                      Identifier
                    </span>
                  </div>

                  {intelligence.phone_numbers.length === 0 ? (
                    <p className="text-xs text-slate-500 italic">No phone numbers detected.</p>
                  ) : (
                    <div className="space-y-1.5">
                      {intelligence.phone_numbers.map((item, idx) => (
                        <div
                          key={idx}
                          className="flex items-center justify-between p-2 rounded-xl bg-slate-950/80 border border-slate-850 text-xs"
                        >
                          <div>
                            <span className="font-mono text-cyan-300 font-semibold">
                              {item.value}
                            </span>
                            <div className="flex items-center gap-1.5 text-[10px] text-slate-400 mt-0.5">
                              <span>{item.source_reference}</span>
                              <span>•</span>
                              <span className="text-amber-400 uppercase font-mono">
                                {item.verification_status}
                              </span>
                            </div>
                          </div>
                          <button
                            onClick={() => handleCopy(item.value, `phone-${idx}`)}
                            className="p-1 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-slate-200 transition cursor-pointer"
                            title="Copy Phone Number"
                          >
                            {copiedKey === `phone-${idx}` ? (
                              <Check className="w-3.5 h-3.5 text-emerald-400" />
                            ) : (
                              <Copy className="w-3.5 h-3.5" />
                            )}
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* 2. UPI IDs */}
                <div className="rounded-2xl border border-slate-800 bg-slate-900/50 p-4 shadow-md space-y-2.5">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 text-xs font-bold text-slate-200">
                      <CreditCard className="w-4 h-4 text-emerald-400" />
                      <span>Payee UPI Handles ({intelligence.upi_ids.length})</span>
                    </div>
                    <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-950 text-slate-400 border border-slate-800">
                      Banking
                    </span>
                  </div>

                  {intelligence.upi_ids.length === 0 ? (
                    <p className="text-xs text-slate-500 italic">No UPI IDs detected.</p>
                  ) : (
                    <div className="space-y-1.5">
                      {intelligence.upi_ids.map((item, idx) => (
                        <div
                          key={idx}
                          className="flex items-center justify-between p-2 rounded-xl bg-slate-950/80 border border-slate-850 text-xs"
                        >
                          <div>
                            <span className="font-mono text-emerald-300 font-semibold">
                              {item.value}
                            </span>
                            <div className="flex items-center gap-1.5 text-[10px] text-slate-400 mt-0.5">
                              <span>{item.source_reference}</span>
                              <span>•</span>
                              <span className="text-amber-400 uppercase font-mono">
                                {item.verification_status}
                              </span>
                            </div>
                          </div>
                          <button
                            onClick={() => handleCopy(item.value, `upi-${idx}`)}
                            className="p-1 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-slate-200 transition cursor-pointer"
                            title="Copy UPI ID"
                          >
                            {copiedKey === `upi-${idx}` ? (
                              <Check className="w-3.5 h-3.5 text-emerald-400" />
                            ) : (
                              <Copy className="w-3.5 h-3.5" />
                            )}
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* 3. Phishing URLs & Portals */}
                <div className="rounded-2xl border border-slate-800 bg-slate-900/50 p-4 shadow-md space-y-2.5">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 text-xs font-bold text-slate-200">
                      <Globe className="w-4 h-4 text-purple-400" />
                      <span>Phishing URLs & Portals ({intelligence.urls.length})</span>
                    </div>
                    <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-950 text-slate-400 border border-slate-800">
                      Network
                    </span>
                  </div>

                  {intelligence.urls.length === 0 ? (
                    <p className="text-xs text-slate-500 italic">No URLs detected.</p>
                  ) : (
                    <div className="space-y-1.5">
                      {intelligence.urls.map((item, idx) => (
                        <div
                          key={idx}
                          className="flex items-center justify-between p-2 rounded-xl bg-slate-950/80 border border-slate-850 text-xs"
                        >
                          <div className="truncate max-w-[240px]">
                            <span className="font-mono text-purple-300 font-semibold truncate block">
                              {item.value}
                            </span>
                            <div className="flex items-center gap-1.5 text-[10px] text-slate-400 mt-0.5">
                              <span>{item.source_reference}</span>
                              <span>•</span>
                              <span className="text-amber-400 uppercase font-mono">
                                {item.verification_status}
                              </span>
                            </div>
                          </div>
                          <button
                            onClick={() => handleCopy(item.value, `url-${idx}`)}
                            className="p-1 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-slate-200 transition cursor-pointer"
                            title="Copy URL"
                          >
                            {copiedKey === `url-${idx}` ? (
                              <Check className="w-3.5 h-3.5 text-emerald-400" />
                            ) : (
                              <Copy className="w-3.5 h-3.5" />
                            )}
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* 4. Financial Demands & Amounts */}
                <div className="rounded-2xl border border-slate-800 bg-slate-900/50 p-4 shadow-md space-y-2.5">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 text-xs font-bold text-slate-200">
                      <CreditCard className="w-4 h-4 text-amber-400" />
                      <span>Financial Demands ({intelligence.financial_amounts.length})</span>
                    </div>
                    <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-950 text-slate-400 border border-slate-800">
                      Financial
                    </span>
                  </div>

                  {intelligence.financial_amounts.length === 0 ? (
                    <p className="text-xs text-slate-500 italic">No monetary demands detected.</p>
                  ) : (
                    <div className="space-y-1.5">
                      {intelligence.financial_amounts.map((item, idx) => (
                        <div
                          key={idx}
                          className="flex items-center justify-between p-2 rounded-xl bg-slate-950/80 border border-slate-850 text-xs"
                        >
                          <div>
                            <span className="font-mono text-amber-300 font-bold">
                              {item.value}
                            </span>
                            <div className="flex items-center gap-1.5 text-[10px] text-slate-400 mt-0.5">
                              <span>{item.source_reference}</span>
                              <span>•</span>
                              <span className="text-amber-400 uppercase font-mono">
                                UNVERIFIED DEMAND
                              </span>
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* 5. Claimed Persons & Impersonated Entities */}
                <div className="rounded-2xl border border-slate-800 bg-slate-900/50 p-4 shadow-md space-y-2.5">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 text-xs font-bold text-slate-200">
                      <Building className="w-4 h-4 text-sky-400" />
                      <span>Claimed Entities & Authorities</span>
                    </div>
                    <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-950 text-slate-400 border border-slate-800">
                      Impersonation
                    </span>
                  </div>

                  {intelligence.claimed_entities.length === 0 ? (
                    <p className="text-xs text-slate-500 italic">No specific authorities extracted.</p>
                  ) : (
                    <div className="space-y-1.5">
                      {intelligence.claimed_entities.map((item, idx) => (
                        <div
                          key={idx}
                          className="p-2 rounded-xl bg-slate-950/80 border border-slate-850 text-xs"
                        >
                          <span className="font-medium text-slate-200 block">
                            {item.value}
                          </span>
                          <span className="text-[10px] text-slate-400 block mt-0.5">
                            Source: {item.source_reference} •{" "}
                            <span className="text-amber-400 font-mono">UNVERIFIED CLAIM</span>
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* 6. Coercive Tactics & Modus Operandi */}
                <div className="rounded-2xl border border-slate-800 bg-slate-900/50 p-4 shadow-md space-y-2.5">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 text-xs font-bold text-slate-200">
                      <ShieldAlert className="w-4 h-4 text-red-400" />
                      <span>Observed Coercive Tactics</span>
                    </div>
                    <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-950 text-slate-400 border border-slate-800">
                      Psychology
                    </span>
                  </div>

                  {intelligence.tactics_observed.length === 0 ? (
                    <p className="text-xs text-slate-500 italic">No tactical tags recorded.</p>
                  ) : (
                    <div className="flex flex-wrap gap-1.5">
                      {intelligence.tactics_observed.map((tactic, idx) => (
                        <span
                          key={idx}
                          className="px-2.5 py-1 rounded-lg bg-red-950/40 text-red-300 border border-red-900/60 text-[11px] font-medium"
                        >
                          {tactic}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              {/* Legal & Forensic Disclaimer */}
              <div className="p-3.5 rounded-xl border border-slate-800 bg-slate-950/80 text-slate-400 text-xs flex items-center gap-2.5 shadow-inner">
                <Lock className="w-4 h-4 text-slate-500 shrink-0" />
                <p className="text-[11px] leading-relaxed">
                  <strong className="text-slate-300 font-medium">Forensic Integrity Disclaimer:</strong>{" "}
                  {intelligence.disclaimer}
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
