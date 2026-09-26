import { useState, useEffect, useCallback } from "react";
import {
  Shield,
  Phone,
  FolderOpen,
  PlusCircle,
  Activity,
  Layers,
  FileText,
  Send,
  PhoneCall,
  Mic,
  Brain,
  Sparkles,
  RefreshCw,
} from "lucide-react";
import { EvidenceUploader } from "./components/EvidenceUploader";
import { CasePassportView } from "./components/CasePassportView";
import { ReportsView } from "./components/ReportsView";
import { LiveCallLogView } from "./components/LiveCallLogView";
import { VoiceControlView } from "./components/VoiceControlView";
import { ScamIntelligenceView } from "./components/ScamIntelligenceView";
import { LanguageSelector } from "./components/LanguageSelector";
import { useTranslation } from "./i18n/LanguageContext";

interface CaseSummary {
  id: string;
  title: string;
  status: string;
  created_at: string;
}

export function App() {
  const { t } = useTranslation();
  const [cases, setCases] = useState<CaseSummary[]>([]);
  const [currentCaseId, setCurrentCaseId] = useState<string>("");
  const [currentCaseTitle, setCurrentCaseTitle] = useState<string>("Active Investigation");
  const [isCreatingCase, setIsCreatingCase] = useState(false);
  const [newCaseTitle, setNewCaseTitle] = useState("");
  const [isDemoLoading, setIsDemoLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<"evidence" | "passport" | "reports" | "call-log" | "voice" | "scam-intel">("evidence");

  // Sync with URL route: e.g. /cases/:caseId/passport, /cases/:caseId/reports, /cases/:caseId/call-log, /cases/:caseId/voice, /cases/:caseId/scam-intel, or /cases/:caseId
  useEffect(() => {
    const handleUrlChange = () => {
      const path = window.location.pathname;
      if (path.includes("/scam-intel")) {
        setActiveTab("scam-intel");
      } else if (path.includes("/voice")) {
        setActiveTab("voice");
      } else if (path.includes("/call-log")) {
        setActiveTab("call-log");
      } else if (path.includes("/reports")) {
        setActiveTab("reports");
      } else if (path.includes("/passport")) {
        setActiveTab("passport");
      } else {
        setActiveTab("evidence");
      }
      const match = path.match(/\/cases\/([a-zA-Z0-9_-]+)/);
      if (match && match[1]) {
        setCurrentCaseId(match[1]);
      }
    };

    handleUrlChange();
    window.addEventListener("popstate", handleUrlChange);
    return () => window.removeEventListener("popstate", handleUrlChange);
  }, []);

  const switchTab = (tab: "evidence" | "passport" | "reports" | "call-log" | "voice" | "scam-intel") => {
    setActiveTab(tab);
    if (currentCaseId) {
      const subpath =
        tab === "scam-intel"
          ? "/scam-intel"
          : tab === "passport"
          ? "/passport"
          : tab === "reports"
          ? "/reports"
          : tab === "call-log"
          ? "/call-log"
          : tab === "voice"
          ? "/voice"
          : "";
      const newPath = `/cases/${currentCaseId}${subpath}`;
      window.history.pushState(null, "", newPath);
    }
  };

  const fetchCases = useCallback(async () => {
    try {
      const res = await fetch("/api/v1/cases");
      if (res.ok) {
        const data: CaseSummary[] = await res.json();
        setCases(data);
        if (data.length > 0) {
          if (!currentCaseId || !data.some((c) => c.id === currentCaseId)) {
            setCurrentCaseId(data[0].id);
            setCurrentCaseTitle(data[0].title);
          } else {
            const found = data.find((c) => c.id === currentCaseId);
            if (found) setCurrentCaseTitle(found.title);
          }
        } else {
          setCurrentCaseId("");
          setCurrentCaseTitle("");
        }
      }
    } catch (err) {
      console.error("Error fetching cases:", err);
    }
  }, [currentCaseId]);

  const handleSelectCase = (id: string) => {
    const sel = cases.find((c) => c.id === id);
    if (sel) {
      setCurrentCaseId(sel.id);
      setCurrentCaseTitle(sel.title);
      const newPath = activeTab === "passport" ? `/cases/${sel.id}/passport` : `/cases/${sel.id}`;
      window.history.pushState(null, "", newPath);
    }
  };

  const handleCreateCase = async () => {
    if (!newCaseTitle.trim()) return;
    try {
      const res = await fetch("/api/v1/cases", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: newCaseTitle.trim(),
          description: "Cyber-fraud incident investigation case.",
        }),
      });
      if (res.ok) {
        const created = await res.json();
        setCases((prev) => [created, ...prev]);
        setCurrentCaseId(created.id);
        setCurrentCaseTitle(created.title);
        setNewCaseTitle("");
        setIsCreatingCase(false);
        const newPath = activeTab === "passport" ? `/cases/${created.id}/passport` : `/cases/${created.id}`;
        window.history.pushState(null, "", newPath);
      }
    } catch (err) {
      console.error("Failed to create case:", err);
      alert("Failed to create case");
    }
  };

  const handleLoadDemoCase = async () => {
    try {
      setIsDemoLoading(true);
      const res = await fetch("/api/v1/cases/demo", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ scenario: "digital_arrest" }),
      });
      if (res.ok) {
        const demoCase = await res.json();
        setCases((prev) => [demoCase, ...prev.filter((c) => c.id !== demoCase.id)]);
        setCurrentCaseId(demoCase.id);
        setCurrentCaseTitle(demoCase.title);
        setActiveTab("passport");
        window.history.pushState(null, "", `/cases/${demoCase.id}/passport`);
      } else {
        const err = await res.json().catch(() => ({}));
        alert(`Failed to initialize demo case: ${err.detail || "Server error"}`);
      }
    } catch (e) {
      console.error("Demo creation failed:", e);
      alert("Network error connecting to demo case generator.");
    } finally {
      setIsDemoLoading(false);
    }
  };

  useEffect(() => {
    fetchCases();
  }, [fetchCases]);

  return (
    <div className="min-h-screen bg-[#0b0f17] text-slate-100 flex flex-col font-sans selection:bg-emerald-500/30 selection:text-emerald-200">
      {/* Top Banner / Emergency Helpline */}
      <header className="border-b border-slate-800/80 bg-slate-950/80 backdrop-blur-md sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-emerald-950/50 border border-emerald-500/30 flex items-center justify-center text-emerald-400 shadow-lg shadow-emerald-950/30">
              <Shield className="w-5 h-5 text-emerald-400" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-extrabold text-base tracking-tight text-white">{t("brand")}</span>
                <span className="text-[10px] uppercase font-bold font-mono px-2 py-0.5 rounded bg-emerald-950/80 text-emerald-400 border border-emerald-800/60">
                  {t("brandSubtitle")}
                </span>
              </div>
              <p className="text-[11px] text-slate-400 -mt-0.5">{t("brandTagline")}</p>
            </div>
          </div>

          <div className="flex items-center gap-2.5 sm:gap-3">
            {/* Multilingual Selector */}
            <LanguageSelector />

            {/* Synthetic Demo Mode Trigger */}
            <button
              onClick={handleLoadDemoCase}
              disabled={isDemoLoading}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-gradient-to-r from-amber-500/20 to-orange-500/20 border border-amber-500/40 text-amber-300 text-xs font-semibold hover:from-amber-500/30 hover:to-orange-500/30 transition shadow-sm cursor-pointer disabled:opacity-50"
              title="Load Synthetic Demo Case with Dynamic AI Orchestration"
            >
              {isDemoLoading ? (
                <RefreshCw className="w-3.5 h-3.5 animate-spin text-amber-400" />
              ) : (
                <Sparkles className="w-3.5 h-3.5 text-amber-400" />
              )}
              <span className="hidden sm:inline">{isDemoLoading ? t("syntheticDemoLoading") : t("syntheticDemoBtn")}</span>
              <span className="sm:hidden">Demo</span>
            </button>

            {/* National 1930 Cyber Helpline Badge */}
            <a
              href="tel:1930"
              className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-xl bg-rose-950/40 border border-rose-800/50 text-rose-300 text-xs font-semibold hover:bg-rose-900/50 transition group"
              title={t("helplineTitle")}
            >
              <Phone className="w-3.5 h-3.5 text-rose-400 group-hover:animate-bounce" />
              <span>{t("helpline")}</span>
            </a>

            {/* Case Selector */}
            <div className="flex items-center gap-2 bg-slate-900/80 border border-slate-800 px-3 py-1.5 rounded-xl text-xs">
              <FolderOpen className="w-3.5 h-3.5 text-slate-400" />
              {cases.length > 0 ? (
                <select
                  value={currentCaseId}
                  onChange={(e) => handleSelectCase(e.target.value)}
                  className="bg-transparent text-slate-200 focus:outline-none cursor-pointer max-w-[120px] sm:max-w-[180px] truncate"
                >
                  {cases.map((c) => (
                    <option key={c.id} value={c.id} className="bg-slate-900 text-white">
                      {c.title}
                    </option>
                  ))}
                </select>
              ) : (
                <span className="text-slate-400">{t("noCases")}</span>
              )}
              <button
                onClick={() => setIsCreatingCase(true)}
                className="text-slate-400 hover:text-emerald-400 transition cursor-pointer"
                title={t("createNewCase")}
              >
                <PlusCircle className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* New Case Modal */}
      {isCreatingCase && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="glass-panel p-6 rounded-2xl border border-slate-700 max-w-md w-full space-y-4">
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <PlusCircle className="w-5 h-5 text-emerald-400" />
              {t("modalCreateTitle")}
            </h3>
            <input
              type="text"
              value={newCaseTitle}
              onChange={(e) => setNewCaseTitle(e.target.value)}
              placeholder={t("modalTitlePlaceholder")}
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-sm text-white focus:outline-none focus:border-emerald-500"
            />
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setIsCreatingCase(false)}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl text-xs font-semibold cursor-pointer"
              >
                {t("cancel")}
              </button>
              <button
                onClick={handleCreateCase}
                disabled={!newCaseTitle.trim()}
                className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl text-xs font-semibold cursor-pointer"
              >
                {t("create")}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Main Workspace */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 flex-1 w-full space-y-8">
        {/* Case Context Header */}
        {currentCaseId ? (
          <div className="space-y-6">
            <div className="glass-panel p-6 rounded-2xl border border-slate-800/90 shadow-xl flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <h1 className="text-xl font-bold text-white">{currentCaseTitle}</h1>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-950/70 border border-emerald-800 text-emerald-400">
                    {t("active")}
                  </span>
                </div>
                <p className="text-xs text-slate-400 font-mono">
                  {t("caseUuid")}: {currentCaseId} | {t("goldenHourActive")}
                </p>
              </div>

              <div className="flex items-center gap-4 text-xs text-slate-400">
                <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-900/60 border border-slate-800">
                  <Activity className="w-3.5 h-3.5 text-emerald-400" />
                  <span>{t("evidencePipelineReady")}</span>
                </div>
                <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-900/60 border border-slate-800">
                  <Layers className="w-3.5 h-3.5 text-sky-400" />
                  <span>{t("ocrEngine")}</span>
                </div>
              </div>
            </div>

            {/* Navigation Tabs Switcher */}
            <div className="flex items-center gap-2 border-b border-slate-800/80 pb-3 overflow-x-auto">
              <button
                onClick={() => switchTab("evidence")}
                className={`px-4 py-2 rounded-xl text-xs font-semibold flex items-center gap-2 transition cursor-pointer whitespace-nowrap ${
                  activeTab === "evidence"
                    ? "bg-slate-800 text-white border border-slate-700 shadow-md shadow-slate-950/50"
                    : "text-slate-400 hover:text-slate-200 hover:bg-slate-900/60"
                }`}
              >
                <Layers className="w-4 h-4 text-emerald-400" />
                <span>{t("tabEvidence")}</span>
              </button>
              <button
                onClick={() => switchTab("passport")}
                className={`px-4 py-2 rounded-xl text-xs font-semibold flex items-center gap-2 transition cursor-pointer whitespace-nowrap ${
                  activeTab === "passport"
                    ? "bg-slate-800 text-white border border-slate-700 shadow-md shadow-slate-950/50"
                    : "text-slate-400 hover:text-slate-200 hover:bg-slate-900/60"
                }`}
              >
                <FileText className="w-4 h-4 text-cyan-400" />
                <span>{t("tabPassport")}</span>
                <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-cyan-950 border border-cyan-800/60 text-cyan-300">
                  PDF
                </span>
              </button>
              <button
                onClick={() => switchTab("reports")}
                className={`px-4 py-2 rounded-xl text-xs font-semibold flex items-center gap-2 transition cursor-pointer whitespace-nowrap ${
                  activeTab === "reports"
                    ? "bg-slate-800 text-white border border-slate-700 shadow-md shadow-slate-950/50"
                    : "text-slate-400 hover:text-slate-200 hover:bg-slate-900/60"
                }`}
              >
                <Send className="w-4 h-4 text-indigo-400" />
                <span>{t("tabReports")}</span>
                <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-indigo-950 border border-indigo-800/60 text-indigo-300">
                  Reports
                </span>
              </button>
              <button
                onClick={() => switchTab("scam-intel")}
                className={`px-4 py-2 rounded-xl text-xs font-semibold flex items-center gap-2 transition cursor-pointer whitespace-nowrap ${
                  activeTab === "scam-intel"
                    ? "bg-slate-800 text-white border border-slate-700 shadow-md shadow-slate-950/50"
                    : "text-slate-400 hover:text-slate-200 hover:bg-slate-900/60"
                }`}
              >
                <Brain className="w-4 h-4 text-cyan-400" />
                <span>{t("tabScamIntel")}</span>
                <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-cyan-950 border border-cyan-800/60 text-cyan-300">
                  AI Intel
                </span>
              </button>
              <button
                onClick={() => switchTab("call-log")}
                className={`px-4 py-2 rounded-xl text-xs font-semibold flex items-center gap-2 transition cursor-pointer whitespace-nowrap ${
                  activeTab === "call-log"
                    ? "bg-slate-800 text-white border border-slate-700 shadow-md shadow-slate-950/50"
                    : "text-slate-400 hover:text-slate-200 hover:bg-slate-900/60"
                }`}
              >
                <PhoneCall className="w-4 h-4 text-cyan-400" />
                <span>{t("tabCallLog")}</span>
                <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-cyan-950 border border-cyan-800/60 text-cyan-300">
                  Intel
                </span>
              </button>
              <button
                onClick={() => switchTab("voice")}
                className={`px-4 py-2 rounded-xl text-xs font-semibold flex items-center gap-2 transition cursor-pointer whitespace-nowrap ${
                  activeTab === "voice"
                    ? "bg-slate-800 text-white border border-slate-700 shadow-md shadow-slate-950/50"
                    : "text-slate-400 hover:text-slate-200 hover:bg-slate-900/60"
                }`}
              >
                <Mic className="w-4 h-4 text-purple-400" />
                <span>{t("tabVoice")}</span>
                <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-purple-950 border border-purple-800/60 text-purple-300">
                  Live
                </span>
              </button>
            </div>
          </div>
        ) : null}

        {/* View Content: Evidence vs Case Passport vs Response Reports vs Call Log vs Voice Control vs Scam Intelligence */}
        {currentCaseId ? (
          activeTab === "evidence" ? (
            <EvidenceUploader caseId={currentCaseId} />
          ) : activeTab === "passport" ? (
            <CasePassportView
              caseId={currentCaseId}
              onNavigateToEvidence={() => switchTab("evidence")}
            />
          ) : activeTab === "reports" ? (
            <ReportsView
              caseId={currentCaseId}
              onNavigateToEvidence={() => switchTab("evidence")}
              onNavigateToPassport={() => switchTab("passport")}
            />
          ) : activeTab === "scam-intel" ? (
            <ScamIntelligenceView
              caseId={currentCaseId}
              onNavigateToPassport={() => switchTab("passport")}
              onNavigateToReports={() => switchTab("reports")}
            />
          ) : activeTab === "call-log" ? (
            <LiveCallLogView
              caseId={currentCaseId}
              onNavigateToEvidence={() => switchTab("evidence")}
              onNavigateToPassport={() => switchTab("passport")}
            />
          ) : (
            <VoiceControlView
              caseId={currentCaseId}
              onNavigateToEvidence={() => switchTab("evidence")}
              onNavigateToPassport={() => switchTab("passport")}
              onNavigateToReports={() => switchTab("reports")}
            />
          )
        ) : (
          <div className="glass-panel p-12 rounded-2xl text-center border border-slate-800/80 max-w-lg mx-auto space-y-4">
            <div className="w-12 h-12 rounded-2xl bg-emerald-950/50 border border-emerald-500/30 flex items-center justify-center text-emerald-400 mx-auto shadow-lg shadow-emerald-950/30">
              <FolderOpen className="w-6 h-6" />
            </div>
            <div className="space-y-1">
              <h2 className="text-lg font-bold text-white">{t("noCaseSelectedTitle")}</h2>
              <p className="text-xs text-slate-400 max-w-sm mx-auto">
                {t("noCaseSelectedDesc")}
              </p>
            </div>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
              <button
                onClick={() => setIsCreatingCase(true)}
                className="px-4 py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl text-xs font-semibold inline-flex items-center gap-2 shadow-lg shadow-emerald-950/50 transition cursor-pointer"
              >
                <PlusCircle className="w-4 h-4" />
                {t("createIncidentCase")}
              </button>
              <button
                onClick={handleLoadDemoCase}
                disabled={isDemoLoading}
                className="px-4 py-2.5 bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 border border-amber-500/40 rounded-xl text-xs font-semibold inline-flex items-center gap-2 shadow-lg transition cursor-pointer disabled:opacity-50"
              >
                {isDemoLoading ? <RefreshCw className="w-4 h-4 animate-spin text-amber-400" /> : <Sparkles className="w-4 h-4 text-amber-400" />}
                {isDemoLoading ? t("syntheticDemoLoading") : t("syntheticDemoBtn")}
              </button>
            </div>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-900 bg-slate-950/80 py-6 text-center text-xs text-slate-500 font-mono">
        <p>{t("footerText")}</p>
      </footer>
    </div>
  );
}

export default App;

