import React, { useState, useEffect, useCallback } from "react";
import {
  PhoneCall,
  User,
  Send,
  Sparkles,
  RefreshCw,
  AlertTriangle,
  Play,
  Layers,
  Copy,
  Check,
  CreditCard,
  Globe,
  DollarSign,
  Flag,
  FileText,
} from "lucide-react";

export interface ExtractedIndicatorItem {
  type: string;
  value: string;
  source_message_index: number;
  source_reference: string;
  confidence: string;
  status: string; // UNVERIFIED, SUPPORTED, FLAGGED
  context?: string | null;
}

export interface LiveExtractedIntelligence {
  indicators: ExtractedIndicatorItem[];
  phone_numbers: ExtractedIndicatorItem[];
  upi_ids: ExtractedIndicatorItem[];
  urls: ExtractedIndicatorItem[];
  emails: ExtractedIndicatorItem[];
  claimed_persons: ExtractedIndicatorItem[];
  claimed_organizations: ExtractedIndicatorItem[];
  financial_amounts: ExtractedIndicatorItem[];
  scam_tactics: ExtractedIndicatorItem[];
  requested_actions: ExtractedIndicatorItem[];
  summary?: string | null;
  disclaimer: string;
}

export interface CallMessage {
  id: string;
  session_id: string;
  speaker: string;
  message_index: number;
  content: string;
  timestamp_offset?: string | null;
  created_at: string;
}

export interface CallSession {
  id: string;
  case_id: string;
  title: string;
  caller_label: string;
  callee_label: string;
  status: string;
  message_count: number;
  messages: CallMessage[];
  intelligence?: LiveExtractedIntelligence | null;
  evidence_id?: string | null;
  created_at: string;
  updated_at?: string | null;
}

interface Props {
  caseId: string;
  onNavigateToPassport?: () => void;
  onNavigateToEvidence?: () => void;
}

// Realistic Synthetic Scam Conversation Scenario for Dynamic Demo
const SYNTHETIC_DEMO_SCRIPT = [
  { speaker: "caller", content: "This is Inspector Ajay Rathore from Mumbai Crime Branch Cyber Cell. Do not disconnect this call.", offset: "00:05" },
  { speaker: "callee", content: "What is this about? I have not done anything illegal.", offset: "00:15" },
  { speaker: "caller", content: "A FedEx parcel linked to Aadhaar ending 4321 was intercepted at customs containing 140 grams of narcotics and fake passports. An arrest warrant has been issued under Case NCRP-2026/88.", offset: "00:32" },
  { speaker: "callee", content: "Someone must have stolen my identity! How can I verify this is legitimate?", offset: "00:48" },
  { speaker: "caller", content: "Visit our clearance portal at https://cbi-verification.gov-in.cc/verify or contact our official nodal desk at 9876543210. You can also reach our desk at clearance@cbi-legal.org.", offset: "01:05" },
  { speaker: "callee", content: "What do I need to do right now to avoid police coming to my home?", offset: "01:20" },
  { speaker: "caller", content: "You are placed under immediate digital arrest. Transfer ₹2,40,000 security bond to RBI clearance account upi@okhdfcbank within 60 minutes for verification. Keep this line open.", offset: "01:45" },
];

export const LiveCallLogView: React.FC<Props> = ({
  caseId,
  onNavigateToPassport,
  onNavigateToEvidence,
}) => {
  const [sessions, setSessions] = useState<CallSession[]>([]);
  const [activeSession, setActiveSession] = useState<CallSession | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isSendingMsg, setIsSendingMsg] = useState<boolean>(false);
  const [isPromoting, setIsPromoting] = useState<boolean>(false);
  const [isSimulating, setIsSimulating] = useState<boolean>(false);

  // New message form state
  const [newMessage, setNewMessage] = useState<string>("");
  const [newSpeaker, setNewSpeaker] = useState<string>("caller");
  const [notification, setNotification] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [copiedText, setCopiedText] = useState<string | null>(null);

  const fetchSessions = useCallback(async () => {
    if (!caseId) return;
    setIsLoading(true);
    setErrorMsg(null);

    try {
      const res = await fetch(`/api/v1/cases/${caseId}/calls`);
      if (res.ok) {
        const data: CallSession[] = await res.json();
        setSessions(data);
        if (data.length > 0) {
          setActiveSession(data[0]);
        } else {
          // Auto create initial session
          const createRes = await fetch(`/api/v1/cases/${caseId}/calls`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              title: "Digital Arrest & Extortion Call",
              caller_label: "Suspect / Impersonator",
              callee_label: "Victim / Callee",
            }),
          });
          if (createRes.ok) {
            const newSess: CallSession = await createRes.json();
            setSessions([newSess]);
            setActiveSession(newSess);
          }
        }
      } else {
        const err = await res.json().catch(() => ({}));
        setErrorMsg(err.detail || "Failed to load call sessions.");
      }
    } catch (err: any) {
      setErrorMsg(err.message || "Network error loading call logs.");
    } finally {
      setIsLoading(false);
    }
  }, [caseId]);

  useEffect(() => {
    fetchSessions();
  }, [fetchSessions]);

  const handleSendMessage = async (speaker: string, text: string, offset?: string) => {
    if (!activeSession || !text.trim()) return;
    setIsSendingMsg(true);
    setErrorMsg(null);

    try {
      const res = await fetch(`/api/v1/cases/${caseId}/calls/${activeSession.id}/messages`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          speaker,
          content: text.trim(),
          timestamp_offset: offset || null,
        }),
      });

      if (res.ok) {
        const updatedSession: CallSession = await res.json();
        setActiveSession(updatedSession);
        setSessions((prev) => prev.map((s) => (s.id === updatedSession.id ? updatedSession : s)));
        setNewMessage("");
      } else {
        const err = await res.json().catch(() => ({}));
        setErrorMsg(err.detail || "Failed to append message.");
      }
    } catch (err: any) {
      setErrorMsg(err.message || "Network error sending message.");
    } finally {
      setIsSendingMsg(false);
    }
  };

  const handlePromoteToEvidence = async () => {
    if (!activeSession) return;
    setIsPromoting(true);
    setErrorMsg(null);

    try {
      const res = await fetch(`/api/v1/cases/${caseId}/calls/${activeSession.id}/promote`, {
        method: "POST",
      });

      if (res.ok) {
        const result = await res.json();
        setNotification(
          `Transcript promoted to Evidence Vault (${result.indicators_created_count} indicators linked).`
        );
        setTimeout(() => setNotification(null), 5000);
        // Refresh session
        fetchSessions();
      } else {
        const err = await res.json().catch(() => ({}));
        setErrorMsg(err.detail || "Promotion failed.");
      }
    } catch (err: any) {
      setErrorMsg(err.message || "Network error promoting transcript.");
    } finally {
      setIsPromoting(false);
    }
  };

  const handleRunSyntheticDemo = async () => {
    if (!activeSession || isSimulating) return;
    setIsSimulating(true);
    setErrorMsg(null);

    try {
      for (const line of SYNTHETIC_DEMO_SCRIPT) {
        await handleSendMessage(line.speaker, line.content, line.offset);
        // Brief natural pause
        await new Promise((r) => setTimeout(r, 600));
      }
      setNotification("Synthetic scam conversation simulated and live intelligence extracted!");
      setTimeout(() => setNotification(null), 5000);
    } catch (err: any) {
      setErrorMsg("Error during demo simulation.");
    } finally {
      setIsSimulating(false);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedText(text);
    setTimeout(() => setCopiedText(null), 2000);
  };

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center p-16 space-y-4">
        <RefreshCw className="w-8 h-8 text-cyan-400 animate-spin" />
        <p className="text-slate-400 text-sm">Initializing Live Call Intelligence Environment...</p>
      </div>
    );
  }

  const intel = activeSession?.intelligence;

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-16">
      {/* Top Banner */}
      <div className="rounded-2xl p-5 bg-gradient-to-r from-cyan-950/40 via-slate-900/60 to-indigo-950/40 border border-cyan-500/30 flex flex-col md:flex-row items-start md:items-center justify-between gap-4 shadow-xl">
        <div className="flex items-start gap-3.5">
          <div className="p-2.5 rounded-xl bg-cyan-500/20 border border-cyan-400/30 text-cyan-300 shrink-0 mt-0.5">
            <PhoneCall className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs uppercase font-extrabold tracking-wider px-2 py-0.5 rounded bg-cyan-500/20 text-cyan-300 border border-cyan-500/30">
                Live Conversation Intelligence
              </span>
              <span className="text-xs text-slate-400">Case ID: {caseId}</span>
            </div>
            <h2 className="text-lg font-bold text-white mt-1">Live Call & Dialogue Intelligence Monitor</h2>
            <p className="text-xs text-slate-300 mt-0.5 max-w-3xl leading-relaxed">
              Streams and records defensive scam conversation transcripts. Dynamically extracts fraudulent UPI handles, phone numbers, URLs, and coercive tactics with exact message provenance.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          {onNavigateToEvidence && (
            <button
              onClick={onNavigateToEvidence}
              className="px-3 py-2 rounded-xl bg-slate-800/80 hover:bg-slate-700/80 border border-slate-700 text-slate-300 text-xs font-semibold flex items-center gap-1.5 transition-colors shadow"
              title="Return to Evidence Vault"
            >
              <Layers className="w-3.5 h-3.5 text-emerald-400" />
              Evidence Vault
            </button>
          )}
          {onNavigateToPassport && (
            <button
              onClick={onNavigateToPassport}
              className="px-3 py-2 rounded-xl bg-slate-800/80 hover:bg-slate-700/80 border border-slate-700 text-cyan-300 text-xs font-semibold flex items-center gap-1.5 transition-colors shadow"
              title="Inspect Case Passport Dossier"
            >
              <FileText className="w-3.5 h-3.5 text-cyan-400" />
              Case Passport
            </button>
          )}
          <button
            onClick={handleRunSyntheticDemo}
            disabled={isSimulating}
            className="px-4 py-2 rounded-xl bg-gradient-to-r from-cyan-600 to-indigo-600 hover:from-cyan-500 hover:to-indigo-500 text-white text-xs font-bold flex items-center gap-2 transition-all shadow shadow-cyan-950/50 disabled:opacity-50"
          >
            <Play className={`w-3.5 h-3.5 ${isSimulating ? "animate-spin" : ""}`} />
            {isSimulating ? "Streaming Demo..." : `Simulate Scam Call (${sessions.length})`}
          </button>
        </div>
      </div>

      {/* Notifications */}
      {notification && (
        <div className="p-3.5 rounded-xl bg-emerald-950/40 border border-emerald-500/40 text-emerald-300 text-xs flex items-center gap-2.5 animate-fadeIn">
          <Check className="w-4 h-4 text-emerald-400 shrink-0" />
          <span>{notification}</span>
        </div>
      )}
      {errorMsg && (
        <div className="p-3.5 rounded-xl bg-rose-950/40 border border-rose-500/40 text-rose-300 text-xs flex items-center gap-2.5 animate-fadeIn">
          <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Two-Column Split Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* LEFT COLUMN: Transcript Stream & Message Entry */}
        <div className="lg:col-span-6 space-y-4">
          <div className="rounded-2xl bg-slate-900/60 border border-slate-700/60 p-5 space-y-4 shadow-xl backdrop-blur-xl">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse"></span>
                <h3 className="text-sm font-bold text-white uppercase tracking-wider">
                  Live Dialogue Stream
                </h3>
              </div>
              <span className="text-xs font-mono text-slate-400">
                {activeSession?.messages.length || 0} Turns Recorded
              </span>
            </div>

            {/* Messages Scroll Area */}
            <div className="space-y-3 max-h-[500px] overflow-y-auto pr-2">
              {!activeSession?.messages || activeSession.messages.length === 0 ? (
                <div className="p-8 text-center text-slate-400 text-xs space-y-2">
                  <PhoneCall className="w-8 h-8 text-slate-600 mx-auto" />
                  <p>No messages recorded yet in this call session.</p>
                  <p className="text-slate-500">
                    Type a message below or click "Simulate Scam Call" to test live extraction.
                  </p>
                </div>
              ) : (
                activeSession.messages.map((m) => {
                  const isCaller = m.speaker === "caller";
                  return (
                    <div
                      key={m.id}
                      className={`p-3.5 rounded-2xl border text-xs space-y-1.5 transition-all ${
                        isCaller
                          ? "bg-rose-950/20 border-rose-500/30 text-rose-100"
                          : "bg-slate-950/50 border-slate-800 text-slate-200"
                      }`}
                    >
                      <div className="flex items-center justify-between font-mono text-[11px] text-slate-400">
                        <span className="font-bold flex items-center gap-1.5">
                          {isCaller ? (
                            <span className="text-rose-400 font-semibold">
                              [Caller / Suspect]
                            </span>
                          ) : (
                            <span className="text-sky-400 font-semibold">
                              [Victim / Callee]
                            </span>
                          )}
                          <span className="text-slate-500 text-[10px]">
                            Message #{m.message_index}
                          </span>
                        </span>
                        <span className="text-[10px] text-slate-500">
                          {m.timestamp_offset || "00:00"}
                        </span>
                      </div>
                      <p className="text-xs leading-relaxed font-sans">{m.content}</p>
                    </div>
                  );
                })
              )}
            </div>

            {/* Input Form */}
            <div className="pt-3 border-t border-slate-800 space-y-2">
              <div className="flex items-center gap-2">
                <select
                  value={newSpeaker}
                  onChange={(e) => setNewSpeaker(e.target.value)}
                  className="px-3 py-2 rounded-xl bg-slate-950 border border-slate-700 text-xs text-slate-200 font-semibold"
                >
                  <option value="caller">Caller (Suspect)</option>
                  <option value="callee">Callee (Victim)</option>
                  <option value="system">System Notice</option>
                </select>

                <div className="relative flex-1">
                  <input
                    type="text"
                    value={newMessage}
                    disabled={isSendingMsg || isSimulating}
                    onChange={(e) => setNewMessage(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && !e.shiftKey) {
                        e.preventDefault();
                        handleSendMessage(newSpeaker, newMessage);
                      }
                    }}
                    placeholder="Enter transcript line (e.g. 'Transfer ₹95,000 to upi@okhdfcbank')..."
                    className="w-full px-3.5 py-2 rounded-xl bg-slate-950 border border-slate-700 text-xs text-white focus:border-cyan-500 focus:outline-none"
                  />
                </div>

                <button
                  onClick={() => handleSendMessage(newSpeaker, newMessage)}
                  disabled={!newMessage.trim() || isSendingMsg || isSimulating}
                  className="p-2 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white transition-colors disabled:opacity-40 shrink-0"
                >
                  <Send className="w-4 h-4" />
                </button>
              </div>
            </div>

            {/* Promote Action */}
            <div className="pt-2 flex items-center justify-between text-xs text-slate-400">
              <span>Promote dialogue to official evidence vault:</span>
              <button
                onClick={handlePromoteToEvidence}
                disabled={isPromoting || !activeSession?.messages.length}
                className="px-3.5 py-1.5 rounded-xl bg-indigo-600/90 hover:bg-indigo-500 text-white font-semibold text-xs flex items-center gap-1.5 transition-colors disabled:opacity-40 shadow"
              >
                <Layers className="w-3.5 h-3.5" />
                {isPromoting ? "Promoting..." : "Ingest Into Evidence"}
              </button>
            </div>
          </div>
        </div>

        {/* RIGHT COLUMN: Live Extracted Intelligence */}
        <div className="lg:col-span-6 space-y-4">
          <div className="rounded-2xl bg-slate-900/60 border border-slate-700/60 p-5 space-y-5 shadow-xl backdrop-blur-xl">
            {/* Header */}
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div className="flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-cyan-400" />
                <h3 className="text-sm font-bold text-white uppercase tracking-wider">
                  Live Extracted Intelligence
                </h3>
              </div>
              <span className="text-xs px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 font-mono">
                {intel?.indicators.length || 0} Extracted Artifacts
              </span>
            </div>

            {/* Mandatory Forensic Disclaimer */}
            <div className="p-3 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-300 text-[11px] leading-relaxed flex items-start gap-2">
              <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5 text-amber-400" />
              <div>
                <strong>FORENSIC DISCLAIMER:</strong>{" "}
                {intel?.disclaimer ||
                  "Extracted indicators represent investigative artifacts; does not establish criminality of named individuals."}
              </div>
            </div>

            {/* Extracted Artifacts Categories */}
            <div className="space-y-4 max-h-[520px] overflow-y-auto pr-1 text-xs">
              {/* Phone Numbers */}
              {intel?.phone_numbers && intel.phone_numbers.length > 0 && (
                <div className="space-y-1.5">
                  <div className="text-[11px] font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                    <PhoneCall className="w-3.5 h-3.5 text-indigo-400" />
                    Phone Numbers & Calling Desks
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    {intel.phone_numbers.map((item, idx) => (
                      <div
                        key={idx}
                        className="p-2.5 rounded-xl bg-slate-950/70 border border-slate-800 flex items-center justify-between gap-2"
                      >
                        <div className="space-y-0.5">
                          <div className="font-mono font-bold text-cyan-300 text-xs">
                            {item.value}
                          </div>
                          <div className="text-[10px] text-slate-500">
                            {item.source_reference} •{" "}
                            <span className="text-amber-400">{item.status}</span>
                          </div>
                        </div>
                        <button
                          onClick={() => copyToClipboard(item.value)}
                          className="p-1 rounded text-slate-500 hover:text-slate-300"
                        >
                          {copiedText === item.value ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* UPI Handles */}
              {intel?.upi_ids && intel.upi_ids.length > 0 && (
                <div className="space-y-1.5">
                  <div className="text-[11px] font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                    <CreditCard className="w-3.5 h-3.5 text-emerald-400" />
                    Fraudulent Payment Handles (UPI)
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    {intel.upi_ids.map((item, idx) => (
                      <div
                        key={idx}
                        className="p-2.5 rounded-xl bg-slate-950/70 border border-slate-800 flex items-center justify-between gap-2"
                      >
                        <div className="space-y-0.5">
                          <div className="font-mono font-bold text-emerald-300 text-xs">
                            {item.value}
                          </div>
                          <div className="text-[10px] text-slate-500">
                            {item.source_reference} •{" "}
                            <span className="text-amber-400">{item.status}</span>
                          </div>
                        </div>
                        <button
                          onClick={() => copyToClipboard(item.value)}
                          className="p-1 rounded text-slate-500 hover:text-slate-300"
                        >
                          {copiedText === item.value ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* URLs & Phishing Portals */}
              {intel?.urls && intel.urls.length > 0 && (
                <div className="space-y-1.5">
                  <div className="text-[11px] font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                    <Globe className="w-3.5 h-3.5 text-rose-400" />
                    Claimed URLs & Impersonation Portals
                  </div>
                  {intel.urls.map((item, idx) => (
                    <div
                      key={idx}
                      className="p-2.5 rounded-xl bg-slate-950/70 border border-slate-800 flex items-center justify-between gap-2"
                    >
                      <div className="space-y-0.5 overflow-hidden">
                        <div className="font-mono text-rose-300 text-xs truncate">
                          {item.value}
                        </div>
                        <div className="text-[10px] text-slate-500">
                          {item.source_reference} •{" "}
                          <span className="text-amber-400">{item.status}</span>
                        </div>
                      </div>
                      <button
                        onClick={() => copyToClipboard(item.value)}
                        className="p-1 rounded text-slate-500 hover:text-slate-300 shrink-0"
                      >
                        {copiedText === item.value ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                      </button>
                    </div>
                  ))}
                </div>
              )}

              {/* Impersonated Persons & Roles */}
              {intel?.claimed_persons && intel.claimed_persons.length > 0 && (
                <div className="space-y-1.5">
                  <div className="text-[11px] font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                    <User className="w-3.5 h-3.5 text-purple-400" />
                    Claimed Impersonated Personas
                  </div>
                  <div className="space-y-1.5">
                    {intel.claimed_persons.map((item, idx) => (
                      <div
                        key={idx}
                        className="p-2 rounded-xl bg-slate-950/60 border border-slate-800 flex items-center justify-between text-xs"
                      >
                        <span className="font-semibold text-purple-300">{item.value}</span>
                        <span className="text-[10px] text-slate-500">
                          {item.source_reference} •{" "}
                          <span className="text-amber-400">{item.status}</span>
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Psychological Tactics & Coercion */}
              {intel?.scam_tactics && intel.scam_tactics.length > 0 && (
                <div className="space-y-1.5">
                  <div className="text-[11px] font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                    <Flag className="w-3.5 h-3.5 text-amber-400" />
                    Detected Coercive Tactics & Psychological Triggers
                  </div>
                  <div className="space-y-1.5">
                    {intel.scam_tactics.map((item, idx) => (
                      <div
                        key={idx}
                        className="p-2.5 rounded-xl bg-amber-500/10 border border-amber-500/20 text-xs space-y-1"
                      >
                        <div className="font-bold text-amber-300">{item.value}</div>
                        <div className="text-[10px] text-slate-400">
                          {item.source_reference} • Status:{" "}
                          <span className="text-rose-400 font-semibold">{item.status}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Demanded Transactions & Amounts */}
              {intel?.financial_amounts && intel.financial_amounts.length > 0 && (
                <div className="space-y-1.5">
                  <div className="text-[11px] font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                    <DollarSign className="w-3.5 h-3.5 text-emerald-400" />
                    Demanded Extortion Amounts
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {intel.financial_amounts.map((item, idx) => (
                      <div
                        key={idx}
                        className="px-3 py-1.5 rounded-xl bg-emerald-950/40 border border-emerald-500/30 text-emerald-300 text-xs font-mono font-bold"
                      >
                        {item.value} ({item.source_reference})
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* If empty */}
              {(!intel?.indicators || intel.indicators.length === 0) && (
                <div className="p-8 text-center text-slate-500 text-xs space-y-1">
                  <p>Awaiting conversation stream...</p>
                  <p className="text-[11px] text-slate-600">
                    Phone numbers, UPI handles, URLs, and extortion demands will appear here automatically.
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
