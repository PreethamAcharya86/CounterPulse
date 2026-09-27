import React, { useState, useEffect, useRef } from "react";
import {
  Upload,
  FileText,
  Image as ImageIcon,
  PhoneCall,
  Link as LinkIcon,
  MessageSquare,
  AlertCircle,
  CheckCircle2,
  Clock,
  RefreshCw,
  Trash2,
  Eye,
  X,
  FileCode,
  ShieldAlert,
  Camera,
} from "lucide-react";
import { WhatsAppCaptureModal } from "./WhatsAppCaptureModal";

export interface EvidenceItem {
  id: string;
  case_id: string;
  evidence_type: "image" | "pdf" | "text" | "chat" | "audio" | "url";
  filename: string;
  mime_type: string;
  file_size: number;
  file_path?: string;
  raw_content?: string;
  sha256_hash?: string;
  processing_status: "uploaded" | "processing" | "processed" | "failed";
  normalized_data?: {
    text?: string;
    segments?: Array<{
      segment_id: string;
      start_time?: number;
      end_time?: number;
      speaker?: string;
      sender?: string;
      timestamp_str?: string;
      text: string;
      confidence?: number;
    }>;
    pages?: Array<{
      page_number: number;
      text: string;
      char_count: number;
      is_ocr_fallback?: boolean;
    }>;
    provenance?: Array<{
      source_evidence_id: string;
      source_reference: string;
      extracted_value: string;
      confidence: string;
      verification_status: string;
    }>;
    metadata?: Record<string, any>;
  };
  error_message?: string;
  created_at: string;
}

interface Props {
  caseId: string;
  onEvidenceChange?: () => void;
  onNavigateToScamIntel?: (evidenceId?: string) => void;
}

export const EvidenceUploader: React.FC<Props> = ({
  caseId,
  onEvidenceChange,
  onNavigateToScamIntel,
}) => {
  const [evidenceList, setEvidenceList] = useState<EvidenceItem[]>([]);
  const [isWhatsAppCaptureOpen, setIsWhatsAppCaptureOpen] = useState(false);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [activeTab, setActiveTab] = useState<"file" | "text" | "chat" | "url">("file");
  
  // Text & URL form inputs
  const [pastedText, setPastedText] = useState("");
  const [textSubtype, setTextSubtype] = useState<"text" | "sms">("text");
  const [chatText, setChatText] = useState("");
  const [inputUrl, setInputUrl] = useState("");
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Selected item for normalized provenance inspection
  const [inspectItem, setInspectItem] = useState<EvidenceItem | null>(null);

  // Drag and drop state
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const fetchEvidence = async () => {
    if (!caseId) return;
    try {
      const res = await fetch(`/api/v1/cases/${caseId}/evidence`);
      if (res.ok) {
        const data = await res.json();
        setEvidenceList(data);
      }
    } catch (err) {
      console.error("Failed to fetch evidence:", err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchEvidence();
    // Poll every 3 seconds if any evidence is currently in "processing" state
    const interval = setInterval(() => {
      setEvidenceList((prev) => {
        const hasProcessing = prev.some((e) => e.processing_status === "processing" || e.processing_status === "uploaded");
        if (hasProcessing) {
          fetchEvidence();
        }
        return prev;
      });
    }, 3000);

    return () => clearInterval(interval);
  }, [caseId]);

  const handleFileUpload = async (files: FileList | File[]) => {
    setUploadError(null);
    setIsSubmitting(true);

    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      const formData = new FormData();
      formData.append("file", file);

      try {
        const res = await fetch(`/api/v1/cases/${caseId}/evidence`, {
          method: "POST",
          body: formData,
        });

        if (!res.ok) {
          const errData = await res.json().catch(() => ({ detail: "Upload failed" }));
          setUploadError(`Failed to upload ${file.name}: ${errData.detail || "Server error"}`);
        }
      } catch (err: any) {
        setUploadError(`Network error uploading ${file.name}: ${err.message}`);
      }
    }

    setIsSubmitting(false);
    await fetchEvidence();
    if (onEvidenceChange) onEvidenceChange();
  };

  const handleTextSubmit = async () => {
    if (!pastedText.trim()) return;
    setUploadError(null);
    setIsSubmitting(true);

    try {
      const res = await fetch(`/api/v1/cases/${caseId}/evidence/text`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text: pastedText.trim(),
          evidence_type: "text",
          description: textSubtype === "sms" ? "Bank SMS Notification" : "Incident Description",
        }),
      });

      if (!res.ok) {
        const errData = await res.json();
        setUploadError(errData.detail || "Text submission failed");
      } else {
        setPastedText("");
        await fetchEvidence();
        if (onEvidenceChange) onEvidenceChange();
      }
    } catch (err: any) {
      setUploadError(`Network error: ${err.message}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleChatSubmit = async () => {
    if (!chatText.trim()) return;
    setUploadError(null);
    setIsSubmitting(true);

    try {
      const res = await fetch(`/api/v1/cases/${caseId}/evidence/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          chat_text: chatText.trim(),
          platform: "whatsapp",
        }),
      });

      if (!res.ok) {
        const errData = await res.json();
        setUploadError(errData.detail || "Chat upload failed");
      } else {
        setChatText("");
        await fetchEvidence();
        if (onEvidenceChange) onEvidenceChange();
      }
    } catch (err: any) {
      setUploadError(`Network error: ${err.message}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleUrlSubmit = async () => {
    if (!inputUrl.trim()) return;
    setUploadError(null);
    setIsSubmitting(true);

    try {
      const res = await fetch(`/api/v1/cases/${caseId}/evidence/url`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: inputUrl.trim() }),
      });

      if (!res.ok) {
        const errData = await res.json();
        setUploadError(errData.detail || "URL submission failed");
      } else {
        setInputUrl("");
        await fetchEvidence();
        if (onEvidenceChange) onEvidenceChange();
      }
    } catch (err: any) {
      setUploadError(`Network error: ${err.message}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRetryProcessing = async (evidenceId: string) => {
    try {
      // Optimistic state update
      setEvidenceList((prev) =>
        prev.map((item) =>
          item.id === evidenceId ? { ...item, processing_status: "processing", error_message: undefined } : item
        )
      );

      const res = await fetch(`/api/v1/evidence/${evidenceId}/process`, { method: "POST" });
      if (res.ok) {
        await fetchEvidence();
        if (onEvidenceChange) onEvidenceChange();
      } else {
        const err = await res.json();
        setUploadError(`Retry failed for ${evidenceId}: ${err.detail || "Unknown error"}`);
      }
    } catch (err: any) {
      setUploadError(`Network error retrying processing: ${err.message}`);
    }
  };

  const handleDeleteEvidence = async (evidenceId: string) => {
    if (!confirm("Are you sure you want to remove this evidence artifact?")) return;
    try {
      const res = await fetch(`/api/v1/evidence/${evidenceId}`, { method: "DELETE" });
      if (res.ok) {
        setEvidenceList((prev) => prev.filter((item) => item.id !== evidenceId));
        if (inspectItem?.id === evidenceId) setInspectItem(null);
        if (onEvidenceChange) onEvidenceChange();
      }
    } catch (err: any) {
      alert(`Failed to delete evidence: ${err.message}`);
    }
  };

  const formatFileSize = (bytes: number): string => {
    if (!bytes || bytes === 0) return "0 B";
    const k = 1024;
    const sizes = ["B", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
  };

  const getEvidenceIcon = (type: string) => {
    switch (type) {
      case "image":
        return <ImageIcon className="w-5 h-5 text-sky-400" />;
      case "pdf":
        return <FileText className="w-5 h-5 text-rose-400" />;
      case "chat":
        return <MessageSquare className="w-5 h-5 text-emerald-400" />;
      case "audio":
        return <PhoneCall className="w-5 h-5 text-amber-400" />;
      case "url":
        return <LinkIcon className="w-5 h-5 text-purple-400" />;
      default:
        return <FileCode className="w-5 h-5 text-slate-400" />;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header & Tabs */}
      <div className="glass-panel p-6 rounded-2xl border border-slate-800 shadow-xl">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-5 border-b border-slate-800">
          <div>
            <h2 className="text-xl font-bold text-white flex items-center gap-2">
              <Upload className="w-5 h-5 text-emerald-400" />
              Evidence Ingestion & Intake
            </h2>
            <p className="text-xs text-slate-400 mt-1">
              Supports screenshots, bank SMS, fake FIRs/notices, call audio, and chat logs. Tamper-evident SHA-256 validation.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <button
              onClick={() => setIsWhatsAppCaptureOpen(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white text-xs font-semibold shadow-md shadow-emerald-950/40 transition cursor-pointer"
            >
              <Camera className="w-3.5 h-3.5" />
              <span>Capture WhatsApp</span>
            </button>

            <div className="flex bg-slate-950/80 p-1 rounded-xl border border-slate-800/80">
            <button
              onClick={() => setActiveTab("file")}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                activeTab === "file" ? "bg-slate-800 text-white shadow-sm" : "text-slate-400 hover:text-white"
              }`}
            >
              Files & Media
            </button>
            <button
              onClick={() => setActiveTab("text")}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                activeTab === "text" ? "bg-slate-800 text-white shadow-sm" : "text-slate-400 hover:text-white"
              }`}
            >
              Paste Text / SMS
            </button>
            <button
              onClick={() => setActiveTab("chat")}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                activeTab === "chat" ? "bg-slate-800 text-white shadow-sm" : "text-slate-400 hover:text-white"
              }`}
            >
              WhatsApp Log
            </button>
            <button
              onClick={() => setActiveTab("url")}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                activeTab === "url" ? "bg-slate-800 text-white shadow-sm" : "text-slate-400 hover:text-white"
              }`}
            >
              Add URL
            </button>
          </div>
        </div>
      </div>

        {uploadError && (
          <div className="mt-4 p-3 bg-rose-950/40 border border-rose-800/50 rounded-xl flex items-center gap-2 text-rose-300 text-xs">
            <AlertCircle className="w-4 h-4 flex-shrink-0" />
            <span>{uploadError}</span>
            <button onClick={() => setUploadError(null)} className="ml-auto text-rose-400 hover:text-rose-200">
              <X className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* Tab 1: File / Audio / Image Upload */}
        {activeTab === "file" && (
          <div className="mt-5">
            <div
              onDragOver={(e) => {
                e.preventDefault();
                setIsDragging(true);
              }}
              onDragLeave={() => setIsDragging(false)}
              onDrop={(e) => {
                e.preventDefault();
                setIsDragging(false);
                if (e.dataTransfer.files?.length) {
                  handleFileUpload(e.dataTransfer.files);
                }
              }}
              onClick={() => fileInputRef.current?.click()}
              className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all ${
                isDragging
                  ? "border-emerald-500 bg-emerald-950/20"
                  : "border-slate-700/70 hover:border-slate-600 bg-slate-900/40 hover:bg-slate-900/60"
              }`}
            >
              <input
                ref={fileInputRef}
                type="file"
                multiple
                accept="image/png,image/jpeg,image/webp,application/pdf,audio/mpeg,audio/wav,audio/mp4,audio/x-m4a,text/plain"
                className="hidden"
                onChange={(e) => {
                  if (e.target.files?.length) {
                    handleFileUpload(e.target.files);
                  }
                }}
              />
              <div className="w-12 h-12 rounded-full bg-slate-800/80 border border-slate-700 flex items-center justify-center mx-auto mb-3 text-emerald-400">
                <Upload className="w-6 h-6" />
              </div>
              <p className="text-sm font-medium text-slate-200">
                Drag & drop evidence files, or <span className="text-emerald-400 underline underline-offset-2">browse</span>
              </p>
              <p className="text-xs text-slate-500 mt-1">
                PNG, JPG, WEBP, PDF, WAV, MP3, M4A, TXT (Up to 25 MB per file)
              </p>
            </div>
          </div>
        )}

        {/* Tab 2: Paste Text / SMS */}
        {activeTab === "text" && (
          <div className="mt-5 space-y-3">
            <div className="flex items-center gap-2 mb-1">
              <span className="text-xs text-slate-400 font-medium">Text Type:</span>
              <button
                type="button"
                onClick={() => setTextSubtype("text")}
                className={`text-xs px-2.5 py-1 rounded-lg border transition ${
                  textSubtype === "text"
                    ? "bg-emerald-950/70 border-emerald-500/50 text-emerald-300 font-medium"
                    : "bg-slate-900 border-slate-800 text-slate-400 hover:text-slate-200"
                }`}
              >
                Incident Narrative
              </button>
              <button
                type="button"
                onClick={() => setTextSubtype("sms")}
                className={`text-xs px-2.5 py-1 rounded-lg border transition ${
                  textSubtype === "sms"
                    ? "bg-emerald-950/70 border-emerald-500/50 text-emerald-300 font-medium"
                    : "bg-slate-900 border-slate-800 text-slate-400 hover:text-slate-200"
                }`}
              >
                Bank SMS / Debit Alert
              </button>
            </div>
            <textarea
              rows={4}
              value={pastedText}
              onChange={(e) => setPastedText(e.target.value)}
              placeholder={
                textSubtype === "sms"
                  ? "Paste raw bank SMS debit notification (e.g. INR 95,000 debited from A/c ending...)..."
                  : "Paste narrative of the incident, scammer demands, or written interaction..."
              }
              className="w-full bg-slate-950/80 border border-slate-800 rounded-xl p-3 text-sm text-slate-100 placeholder-slate-600 focus:outline-none focus:border-emerald-500 font-mono"
            />
            <div className="flex justify-end">
              <button
                onClick={handleTextSubmit}
                disabled={isSubmitting || !pastedText.trim()}
                className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white rounded-xl text-xs font-semibold flex items-center gap-1.5 shadow-lg shadow-emerald-950/50 transition"
              >
                {isSubmitting ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Upload className="w-3.5 h-3.5" />}
                Ingest Text Evidence
              </button>
            </div>
          </div>
        )}

        {/* Tab 3: WhatsApp Chat */}
        {activeTab === "chat" && (
          <div className="mt-5 space-y-3">
            <textarea
              rows={5}
              value={chatText}
              onChange={(e) => setChatText(e.target.value)}
              placeholder="Paste exported or copied WhatsApp conversation text (preserves [HH:MM] and sender tags without invention)..."
              className="w-full bg-slate-950/80 border border-slate-800 rounded-xl p-3 text-sm text-slate-100 placeholder-slate-600 focus:outline-none focus:border-emerald-500 font-mono"
            />
            <div className="flex justify-end">
              <button
                onClick={handleChatSubmit}
                disabled={isSubmitting || !chatText.trim()}
                className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white rounded-xl text-xs font-semibold flex items-center gap-1.5 shadow-lg shadow-emerald-950/50 transition"
              >
                {isSubmitting ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <MessageSquare className="w-3.5 h-3.5" />}
                Ingest & Parse Chat
              </button>
            </div>
          </div>
        )}

        {/* Tab 4: Add URL */}
        {activeTab === "url" && (
          <div className="mt-5 space-y-3">
            <div className="flex gap-2">
              <input
                type="text"
                value={inputUrl}
                onChange={(e) => setInputUrl(e.target.value)}
                placeholder="https://fake-sbi-portal.xyz/verification or suspicious link"
                className="flex-1 bg-slate-950/80 border border-slate-800 rounded-xl px-3.5 py-2 text-sm text-slate-100 placeholder-slate-600 focus:outline-none focus:border-emerald-500 font-mono"
              />
              <button
                onClick={handleUrlSubmit}
                disabled={isSubmitting || !inputUrl.trim()}
                className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white rounded-xl text-xs font-semibold flex items-center gap-1.5 shadow-lg shadow-emerald-950/50 transition"
              >
                {isSubmitting ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <LinkIcon className="w-3.5 h-3.5" />}
                Add URL Evidence
              </button>
            </div>
            <p className="text-[11px] text-slate-500 flex items-center gap-1.5">
              <ShieldAlert className="w-3.5 h-3.5 text-amber-400" />
              Safety guarantee: URLs are stored and normalized as UNVERIFIED evidence. Never executes JavaScript or auto-downloads files.
            </p>
          </div>
        )}
      </div>

      {/* Evidence List */}
      <div className="space-y-3">
        <div className="flex items-center justify-between px-1">
          <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-2">
            Forensic Artifacts ({evidenceList.length})
          </h3>
          <button
            onClick={fetchEvidence}
            className="text-xs text-slate-400 hover:text-slate-200 flex items-center gap-1 transition"
          >
            <RefreshCw className="w-3 h-3" /> Refresh
          </button>
        </div>

        {isLoading ? (
          <div className="glass-panel p-8 rounded-2xl text-center text-slate-500 text-sm">
            Loading evidence catalog...
          </div>
        ) : evidenceList.length === 0 ? (
          <div className="glass-panel p-8 rounded-2xl text-center text-slate-500 text-sm border border-slate-800/80">
            No evidence artifacts uploaded yet. Upload a screenshot, PDF, bank SMS, or recording above to begin.
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-3">
            {evidenceList.map((item) => (
              <div
                key={item.id}
                className="glass-panel p-4 rounded-xl border border-slate-800/80 hover:border-slate-700/80 transition flex flex-col md:flex-row md:items-center justify-between gap-4"
              >
                <div className="flex items-start gap-3.5 min-w-0">
                  <div className="p-2.5 rounded-lg bg-slate-800/70 border border-slate-700/60 flex-shrink-0">
                    {getEvidenceIcon(item.evidence_type)}
                  </div>
                  <div className="min-w-0 space-y-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-sm font-semibold text-white truncate max-w-xs sm:max-w-md">
                        {item.filename}
                      </span>
                      <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                        {item.evidence_type}
                      </span>
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-900 text-slate-400">
                        {item.id}
                      </span>
                    </div>

                    <div className="flex items-center gap-3 text-xs text-slate-400 font-mono">
                      <span>{formatFileSize(item.file_size)}</span>
                      {item.sha256_hash && (
                        <span className="hidden sm:inline truncate max-w-[120px] text-slate-500" title={item.sha256_hash}>
                          SHA256: {item.sha256_hash.slice(0, 10)}...
                        </span>
                      )}
                      <span>{new Date(item.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</span>
                    </div>

                    {item.error_message && (
                      <div className="mt-2 text-xs text-rose-400 bg-rose-950/30 border border-rose-900/40 p-2 rounded-lg flex items-center gap-2">
                        <AlertCircle className="w-3.5 h-3.5 flex-shrink-0" />
                        <span>{item.error_message}</span>
                      </div>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-2.5 self-end md:self-center">
                  {/* Processing Status Badge */}
                  {item.processing_status === "processed" && (
                    <span className="inline-flex items-center gap-1 text-xs font-medium text-emerald-400 bg-emerald-950/40 border border-emerald-800/60 px-2.5 py-1 rounded-full">
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      Processed
                    </span>
                  )}
                  {item.processing_status === "processing" && (
                    <span className="inline-flex items-center gap-1.5 text-xs font-medium text-amber-400 bg-amber-950/40 border border-amber-800/60 px-2.5 py-1 rounded-full animate-pulse">
                      <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                      Processing...
                    </span>
                  )}
                  {item.processing_status === "uploaded" && (
                    <span className="inline-flex items-center gap-1 text-xs font-medium text-slate-400 bg-slate-800/60 border border-slate-700 px-2.5 py-1 rounded-full">
                      <Clock className="w-3.5 h-3.5" />
                      Uploaded
                    </span>
                  )}
                  {item.processing_status === "failed" && (
                    <div className="flex items-center gap-2">
                      <span className="inline-flex items-center gap-1 text-xs font-medium text-rose-400 bg-rose-950/40 border border-rose-800/60 px-2.5 py-1 rounded-full">
                        <AlertCircle className="w-3.5 h-3.5" />
                        Failed
                      </span>
                      <button
                        onClick={() => handleRetryProcessing(item.id)}
                        className="text-xs px-2.5 py-1 rounded-lg bg-rose-900/40 hover:bg-rose-900/60 text-rose-200 border border-rose-700/60 font-medium transition"
                      >
                        Retry
                      </button>
                    </div>
                  )}

                  {/* Actions */}
                  <button
                    onClick={() => setInspectItem(item)}
                    className="p-1.5 rounded-lg bg-slate-800/80 hover:bg-slate-700 text-slate-300 hover:text-white transition"
                    title="Inspect Normalized Extraction & Provenance"
                  >
                    <Eye className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => handleDeleteEvidence(item.id)}
                    className="p-1.5 rounded-lg bg-slate-800/80 hover:bg-rose-950/60 text-slate-400 hover:text-rose-400 transition"
                    title="Delete Evidence"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Normalized Evidence Inspection Modal */}
      {inspectItem && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="glass-panel w-full max-w-3xl max-h-[85vh] rounded-2xl border border-slate-700 shadow-2xl flex flex-col overflow-hidden animate-in fade-in duration-200">
            {/* Modal Header */}
            <div className="p-4 border-b border-slate-800 flex items-center justify-between bg-slate-900/90">
              <div className="flex items-center gap-2.5">
                {getEvidenceIcon(inspectItem.evidence_type)}
                <div>
                  <h4 className="text-sm font-bold text-white flex items-center gap-2">
                    {inspectItem.filename}
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-emerald-400 border border-emerald-900">
                      {inspectItem.id}
                    </span>
                  </h4>
                  <p className="text-[11px] text-slate-400 font-mono">
                    MIME: {inspectItem.mime_type} | Status: {inspectItem.processing_status}
                  </p>
                </div>
              </div>
              <button
                onClick={() => setInspectItem(null)}
                className="p-1 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-5 overflow-y-auto space-y-5 text-sm">
              {/* Provenance Indicators Block */}
              {inspectItem.normalized_data?.provenance && inspectItem.normalized_data.provenance.length > 0 && (
                <div>
                  <h5 className="text-xs font-semibold text-emerald-400 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    Verified Forensic Provenance Links
                  </h5>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    {inspectItem.normalized_data.provenance.map((prov, pidx) => (
                      <div
                        key={pidx}
                        className="p-2.5 rounded-lg bg-emerald-950/20 border border-emerald-800/40 text-xs space-y-1"
                      >
                        <div className="font-semibold text-emerald-300 font-mono">{prov.extracted_value}</div>
                        <div className="text-[11px] text-slate-400 flex items-center justify-between">
                          <span>Source: {prov.source_reference}</span>
                          <span className="uppercase text-[10px] text-emerald-400 font-mono">{prov.confidence} conf</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Extracted Normalized Text */}
              <div>
                <h5 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                  Extracted Normalized Text
                </h5>
                <div className="bg-slate-950 p-4 rounded-xl border border-slate-800/90 font-mono text-xs text-slate-300 max-h-60 overflow-y-auto whitespace-pre-wrap select-text">
                  {inspectItem.raw_content || inspectItem.normalized_data?.text || "[No extracted text]"}
                </div>
              </div>

              {/* Segments / Pages Table */}
              {inspectItem.normalized_data?.segments && inspectItem.normalized_data.segments.length > 0 && (
                <div>
                  <h5 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                    Content Segments ({inspectItem.normalized_data.segments.length})
                  </h5>
                  <div className="space-y-1.5 max-h-48 overflow-y-auto">
                    {inspectItem.normalized_data.segments.map((seg, sidx) => (
                      <div
                        key={sidx}
                        className="p-2 rounded bg-slate-900/80 border border-slate-800 text-xs flex items-start gap-2.5"
                      >
                        <span className="font-mono text-[10px] text-slate-400 bg-slate-800 px-1.5 py-0.5 rounded flex-shrink-0">
                          {seg.segment_id}
                        </span>
                        {seg.sender && (
                          <span className="font-semibold text-emerald-300 text-[11px]">{seg.sender}:</span>
                        )}
                        {seg.timestamp_str && (
                          <span className="text-[10px] text-slate-500 font-mono">[{seg.timestamp_str}]</span>
                        )}
                        <span className="text-slate-300 flex-1">{seg.text}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Metadata */}
              {inspectItem.normalized_data?.metadata && (
                <div>
                  <h5 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                    Technical Metadata & Audit Trail
                  </h5>
                  <pre className="bg-slate-950/80 p-3 rounded-lg border border-slate-800 text-[11px] font-mono text-slate-400 overflow-x-auto">
                    {JSON.stringify(inspectItem.normalized_data.metadata, null, 2)}
                  </pre>
                </div>
              )}
            </div>

            {/* Modal Footer */}
            <div className="p-3 bg-slate-900/90 border-t border-slate-800 flex justify-end gap-2">
              {inspectItem.processing_status === "failed" && (
                <button
                  onClick={() => {
                    handleRetryProcessing(inspectItem.id);
                    setInspectItem(null);
                  }}
                  className="px-3.5 py-1.5 bg-rose-600 hover:bg-rose-500 text-white rounded-lg text-xs font-semibold transition"
                >
                  Retry Processing
                </button>
              )}
              <button
                onClick={() => setInspectItem(null)}
                className="px-3.5 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-xs font-semibold transition"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* WhatsApp Screen / Window / Android Share Capture Modal */}
      <WhatsAppCaptureModal
        isOpen={isWhatsAppCaptureOpen}
        onClose={() => setIsWhatsAppCaptureOpen(false)}
        caseId={caseId}
        onCaptureSuccess={(evidenceId) => {
          fetchEvidence();
          if (onEvidenceChange) onEvidenceChange();
          if (onNavigateToScamIntel) onNavigateToScamIntel(evidenceId);
        }}
      />
    </div>
  );
};
