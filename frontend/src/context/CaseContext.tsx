import React, { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from "react";

export interface CaseSummary {
  id: string;
  title: string;
  status: string;
  scam_category?: string | null;
  severity_level?: string;
  financial_loss?: number | null;
  currency?: string;
  created_at: string;
  updated_at?: string;
}

export type ActiveTab =
  | "overview"
  | "evidence"
  | "intelligence"
  | "compromise"
  | "passport"
  | "reports"
  | "voice";

interface CaseContextType {
  cases: CaseSummary[];
  currentCaseId: string;
  currentCase: CaseSummary | null;
  activeTab: ActiveTab;
  selectedEvidenceId: string | null;
  isWhatsAppCaptureOpen: boolean;
  isLoadingCases: boolean;
  refreshCases: () => Promise<void>;
  selectCase: (caseId: string) => void;
  switchTab: (tab: ActiveTab) => void;
  setSelectedEvidenceId: (id: string | null) => void;
  setIsWhatsAppCaptureOpen: (open: boolean) => void;
  createCase: (title: string, description?: string) => Promise<CaseSummary | null>;
}

const CaseContext = createContext<CaseContextType | undefined>(undefined);

const STORAGE_KEY_CURRENT_CASE = "counterpulse_current_case_id";

export const CaseProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [cases, setCases] = useState<CaseSummary[]>([]);
  const [currentCaseId, setCurrentCaseId] = useState<string>(() => {
    if (typeof window !== "undefined") {
      return localStorage.getItem(STORAGE_KEY_CURRENT_CASE) || "";
    }
    return "";
  });
  const [activeTab, setActiveTabState] = useState<ActiveTab>("overview");
  const [selectedEvidenceId, setSelectedEvidenceId] = useState<string | null>(null);
  const [isWhatsAppCaptureOpen, setIsWhatsAppCaptureOpen] = useState<boolean>(false);
  const [isLoadingCases, setIsLoadingCases] = useState<boolean>(true);

  // Sync tab and case from URL route on initial load and popstate
  useEffect(() => {
    const handleUrlChange = () => {
      const path = window.location.pathname;
      if (path.includes("/intelligence") || path.includes("/scam-intel")) {
        setActiveTabState("intelligence");
      } else if (path.includes("/compromise")) {
        setActiveTabState("compromise");
      } else if (path.includes("/voice")) {
        setActiveTabState("voice");
      } else if (path.includes("/reports")) {
        setActiveTabState("reports");
      } else if (path.includes("/passport")) {
        setActiveTabState("passport");
      } else if (path.includes("/evidence")) {
        setActiveTabState("evidence");
      } else if (path.includes("/overview")) {
        setActiveTabState("overview");
      }

      const match = path.match(/\/cases\/([a-zA-Z0-9_-]+)/);
      if (match && match[1]) {
        const idFromUrl = match[1];
        setCurrentCaseId(idFromUrl);
        localStorage.setItem(STORAGE_KEY_CURRENT_CASE, idFromUrl);
      }
    };

    handleUrlChange();
    window.addEventListener("popstate", handleUrlChange);
    return () => window.removeEventListener("popstate", handleUrlChange);
  }, []);

  // Fetch all cases and reconcile with stored currentCaseId
  const fetchCases = useCallback(async () => {
    try {
      setIsLoadingCases(true);
      const res = await fetch("/api/v1/cases");
      if (res.ok) {
        const data: CaseSummary[] = await res.json();
        setCases(data);

        if (data.length > 0) {
          const storedId = localStorage.getItem(STORAGE_KEY_CURRENT_CASE);
          const foundStored = storedId ? data.find((c) => c.id === storedId) : null;

          if (foundStored) {
            setCurrentCaseId(foundStored.id);
          } else if (!currentCaseId || !data.some((c) => c.id === currentCaseId)) {
            // Select first real case if stored ID does not exist
            const fallbackId = data[0].id;
            setCurrentCaseId(fallbackId);
            localStorage.setItem(STORAGE_KEY_CURRENT_CASE, fallbackId);
          }
        } else {
          setCurrentCaseId("");
          localStorage.removeItem(STORAGE_KEY_CURRENT_CASE);
        }
      }
    } catch (err) {
      console.error("Failed to fetch cases:", err);
    } finally {
      setIsLoadingCases(false);
    }
  }, [currentCaseId]);

  useEffect(() => {
    fetchCases();
  }, [fetchCases]);

  const selectCase = (caseId: string) => {
    const sel = cases.find((c) => c.id === caseId);
    if (sel) {
      setCurrentCaseId(sel.id);
      localStorage.setItem(STORAGE_KEY_CURRENT_CASE, sel.id);
      setSelectedEvidenceId(null);
      const subpath = activeTab === "overview" ? "" : `/${activeTab}`;
      const newPath = `/cases/${sel.id}${subpath}`;
      window.history.pushState(null, "", newPath);
    }
  };

  const switchTab = (tab: ActiveTab) => {
    setActiveTabState(tab);
    if (currentCaseId) {
      const subpath = tab === "overview" ? "" : `/${tab}`;
      const newPath = `/cases/${currentCaseId}${subpath}`;
      window.history.pushState(null, "", newPath);
    }
  };

  const createCase = async (title: string, description?: string): Promise<CaseSummary | null> => {
    try {
      const res = await fetch("/api/v1/cases", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: title.trim(),
          description: description || "Defensive cyber-fraud evidence case.",
        }),
      });
      if (res.ok) {
        const created: CaseSummary = await res.json();
        setCases((prev) => [created, ...prev]);
        setCurrentCaseId(created.id);
        localStorage.setItem(STORAGE_KEY_CURRENT_CASE, created.id);
        setSelectedEvidenceId(null);
        setActiveTabState("overview");
        window.history.pushState(null, "", `/cases/${created.id}`);
        return created;
      }
    } catch (err) {
      console.error("Error creating case:", err);
    }
    return null;
  };

  const currentCase = cases.find((c) => c.id === currentCaseId) || null;

  return (
    <CaseContext.Provider
      value={{
        cases,
        currentCaseId,
        currentCase,
        activeTab,
        selectedEvidenceId,
        isWhatsAppCaptureOpen,
        isLoadingCases,
        refreshCases: fetchCases,
        selectCase,
        switchTab,
        setSelectedEvidenceId,
        setIsWhatsAppCaptureOpen,
        createCase,
      }}
    >
      {children}
    </CaseContext.Provider>
  );
};

export const useCase = (): CaseContextType => {
  const context = useContext(CaseContext);
  if (!context) {
    throw new Error("useCase must be used within a CaseProvider");
  }
  return context;
};
