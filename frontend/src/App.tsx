import { useState, useEffect } from "react";
import {
  Shield,
  Phone,
  FolderOpen,
  PlusCircle,
  Activity,
  Layers,
} from "lucide-react";
import { EvidenceUploader } from "./components/EvidenceUploader";

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

  const fetchCases = async () => {
    try {
      const res = await fetch("/api/v1/cases");
      if (res.ok) {
        const data: CaseSummary[] = await res.json();
        setCases(data);
        if (data.length > 0 && !currentCaseId) {
          setCurrentCaseId(data[0].id);
          setCurrentCaseTitle(data[0].title);
        } else if (data.length === 0) {
          // Auto create initial case if none exist
          createInitialCase();
        }
      }
    } catch (err) {
      console.error("Error fetching cases:", err);
    }
  };

  const createInitialCase = async () => {
    try {
      const res = await fetch("/api/v1/cases", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: "Digital Arrest & Extortion Case (Primary)",
          description: "Initial cyber-fraud complaint intake with multimodal evidence.",
        }),
      });
      if (res.ok) {
        const newCase = await res.json();
        setCases([newCase]);
        setCurrentCaseId(newCase.id);
        setCurrentCaseTitle(newCase.title);
      }
    } catch (err) {
      console.error("Error creating initial case:", err);
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
      }
    } catch (err) {
      alert("Failed to create case");
    }
  };

  useEffect(() => {
    fetchCases();
  }, []);

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
                  onChange={(e) => {
                    const sel = cases.find((c) => c.id === e.target.value);
                    if (sel) {
                      setCurrentCaseId(sel.id);
                      setCurrentCaseTitle(sel.title);
                    }
                  }}
                  className="bg-transparent text-slate-200 focus:outline-none cursor-pointer max-w-[140px] sm:max-w-[200px] truncate"
                >
                  {cases.map((c) => (
                    <option key={c.id} value={c.id} className="bg-slate-900 text-white">
                      {c.title}
                    </option>
                  ))}
                </select>
              ) : (
                <span className="text-slate-400">Loading case...</span>
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
        <div className="glass-panel p-6 rounded-2xl border border-slate-800/90 shadow-xl flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold text-white">{currentCaseTitle}</h1>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-950/70 border border-emerald-800 text-emerald-400">
                ACTIVE
              </span>
            </div>
            <p className="text-xs text-slate-400 font-mono">
              CASE UUID: {currentCaseId || "Initializing..."} | Golden Hour Response Window Active
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

        {/* Core Evidence Intake Stream */}
        {currentCaseId ? (
          <EvidenceUploader caseId={currentCaseId} />
        ) : (
          <div className="glass-panel p-12 rounded-2xl text-center text-slate-400">
            Connecting to CounterPulse case registry...
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
