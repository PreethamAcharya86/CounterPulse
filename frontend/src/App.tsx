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
} from "lucide-react";
import { EvidenceUploader } from "./components/EvidenceUploader";
import { CasePassportView } from "./components/CasePassportView";
import { ReportsView } from "./components/ReportsView";

interface CaseSummary {
  id: string;
  title: string;
  status: string;
  created_at: string;
}

export function App() {
  const [cases, setCases] = useState<CaseSummary[]>([]);
  const [currentCaseId, setCurrentCaseId] = useState<string>("");
  const [currentCaseTitle, setCurrentCaseTitle] = useState<string>("Active Investigation");
  const [isCreatingCase, setIsCreatingCase] = useState(false);
  const [newCaseTitle, setNewCaseTitle] = useState("");
  const [activeTab, setActiveTab] = useState<"evidence" | "passport" | "reports">("evidence");

  // Sync with URL route: e.g. /cases/:caseId/passport, /cases/:caseId/reports, or /cases/:caseId
  useEffect(() => {
    const handleUrlChange = () => {
      const path = window.location.pathname;
      if (path.includes("/reports")) {
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

  const switchTab = (tab: "evidence" | "passport" | "reports") => {
    setActiveTab(tab);
    if (currentCaseId) {
      const subpath = tab === "passport" ? "/passport" : tab === "reports" ? "/reports" : "";
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
                <span className="font-extrabold text-base tracking-tight text-white">COUNTERPULSE</span>
                <span className="text-[10px] uppercase font-bold font-mono px-2 py-0.5 rounded bg-emerald-950/80 text-emerald-400 border border-emerald-800/60">
                  AI FORENSICS
                </span>
              </div>
              <p className="text-[11px] text-slate-400 -mt-0.5">Turn panic into an actionable fraud case</p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {/* National 1930 Cyber Helpline Badge */}
            <a
              href="tel:1930"
              className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-xl bg-rose-950/40 border border-rose-800/50 text-rose-300 text-xs font-semibold hover:bg-rose-900/50 transition group"
              title="Official National Cyber Crime Reporting Portal Helpline (1930)"
            >
              <Phone className="w-3.5 h-3.5 text-rose-400 group-hover:animate-bounce" />
              <span>Helpline 1930</span>
            </a>

            {/* Case Selector */}
            <div className="flex items-center gap-2 bg-slate-900/80 border border-slate-800 px-3 py-1.5 rounded-xl text-xs">
              <FolderOpen className="w-3.5 h-3.5 text-slate-400" />
              {cases.length > 0 ? (
                <select
                  value={currentCaseId}
                  onChange={(e) => handleSelectCase(e.target.value)}
                  className="bg-transparent text-slate-200 focus:outline-none cursor-pointer max-w-[140px] sm:max-w-[200px] truncate"
                >
                  {cases.map((c) => (
                    <option key={c.id} value={c.id} className="bg-slate-900 text-white">
                      {c.title}
                    </option>
                  ))}
                </select>
              ) : (
                <span className="text-slate-400">No cases</span>
              )}
              <button
                onClick={() => setIsCreatingCase(true)}
                className="text-slate-400 hover:text-emerald-400 transition"
                title="Create New Case"
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
              Create New Fraud Incident Case
            </h3>
            <input
              type="text"
              value={newCaseTitle}
              onChange={(e) => setNewCaseTitle(e.target.value)}
              placeholder="e.g. Telegram Job Scam - ₹1,20,000 Loss"
              className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-sm text-white focus:outline-none focus:border-emerald-500"
            />
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setIsCreatingCase(false)}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl text-xs font-semibold"
              >
                Cancel
              </button>
              <button
                onClick={handleCreateCase}
                disabled={!newCaseTitle.trim()}
                className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl text-xs font-semibold"
              >
                Create Case
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
                    ACTIVE
                  </span>
                </div>
                <p className="text-xs text-slate-400 font-mono">
                  CASE UUID: {currentCaseId} | Golden Hour Response Window Active
                </p>
              </div>

              <div className="flex items-center gap-4 text-xs text-slate-400">
                <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-900/60 border border-slate-800">
                  <Activity className="w-3.5 h-3.5 text-emerald-400" />
                  <span>Evidence Pipeline: Ready</span>
                </div>
                <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-slate-900/60 border border-slate-800">
                  <Layers className="w-3.5 h-3.5 text-sky-400" />
                  <span>OCR: RapidOCR ONNX</span>
                </div>
              </div>
            </div>

            {/* Navigation Tabs Switcher */}
            <div className="flex items-center gap-2 border-b border-slate-800/80 pb-3">
              <button
                onClick={() => switchTab("evidence")}
                className={`px-4 py-2 rounded-xl text-xs font-semibold flex items-center gap-2 transition cursor-pointer ${
                  activeTab === "evidence"
                    ? "bg-slate-800 text-white border border-slate-700 shadow-md shadow-slate-950/50"
                    : "text-slate-400 hover:text-slate-200 hover:bg-slate-900/60"
                }`}
              >
                <Layers className="w-4 h-4 text-emerald-400" />
                <span>Evidence Intake & Vault</span>
              </button>
              <button
                onClick={() => switchTab("passport")}
                className={`px-4 py-2 rounded-xl text-xs font-semibold flex items-center gap-2 transition cursor-pointer ${
                  activeTab === "passport"
                    ? "bg-slate-800 text-white border border-slate-700 shadow-md shadow-slate-950/50"
                    : "text-slate-400 hover:text-slate-200 hover:bg-slate-900/60"
                }`}
              >
                <FileText className="w-4 h-4 text-cyan-400" />
                <span>Fraud Case Passport & Dossier</span>
                <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-cyan-950 border border-cyan-800/60 text-cyan-300">
                  PDF
                </span>
              </button>
              <button
                onClick={() => switchTab("reports")}
                className={`px-4 py-2 rounded-xl text-xs font-semibold flex items-center gap-2 transition cursor-pointer ${
                  activeTab === "reports"
                    ? "bg-slate-800 text-white border border-slate-700 shadow-md shadow-slate-950/50"
                    : "text-slate-400 hover:text-slate-200 hover:bg-slate-900/60"
                }`}
              >
                <Send className="w-4 h-4 text-indigo-400" />
                <span>Response Center & Dispatch</span>
                <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-indigo-950 border border-indigo-800/60 text-indigo-300">
                  Reports
                </span>
              </button>
            </div>
          </div>
        ) : null}

        {/* View Content: Evidence Ingest vs Case Passport vs Response Reports */}
        {currentCaseId ? (
          activeTab === "evidence" ? (
            <EvidenceUploader caseId={currentCaseId} />
          ) : activeTab === "passport" ? (
            <CasePassportView
              caseId={currentCaseId}
              onNavigateToEvidence={() => switchTab("evidence")}
            />
          ) : (
            <ReportsView
              caseId={currentCaseId}
              onNavigateToEvidence={() => switchTab("evidence")}
              onNavigateToPassport={() => switchTab("passport")}
            />
          )
        ) : (
          <div className="glass-panel p-12 rounded-2xl text-center border border-slate-800/80 max-w-lg mx-auto space-y-4">
            <div className="w-12 h-12 rounded-2xl bg-emerald-950/50 border border-emerald-500/30 flex items-center justify-center text-emerald-400 mx-auto shadow-lg shadow-emerald-950/30">
              <FolderOpen className="w-6 h-6" />
            </div>
            <div className="space-y-1">
              <h2 className="text-lg font-bold text-white">No Incident Case Selected</h2>
              <p className="text-xs text-slate-400 max-w-sm mx-auto">
                Create a new fraud incident case from real complaint details to begin evidence intake and multimodal forensic analysis.
              </p>
            </div>
            <button
              onClick={() => setIsCreatingCase(true)}
              className="px-4 py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl text-xs font-semibold inline-flex items-center gap-2 shadow-lg shadow-emerald-950/50 transition cursor-pointer"
            >
              <PlusCircle className="w-4 h-4" />
              Create Incident Case
            </button>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-900 bg-slate-950/80 py-6 text-center text-xs text-slate-500 font-mono">
        <p>CounterPulse AI — Team: The Valiente | Track: Agentic AI For Billions | Zero-Fake Evidence Provenance</p>
      </footer>
    </div>
  );
}

export default App;
