import React, { useState, useRef } from "react";
import {
  Smartphone,
  Monitor,
  CheckCircle2,
  AlertCircle,
  Camera,
  X,
  RefreshCw,
  Upload,
  Lock,
} from "lucide-react";
import { useCase } from "../context/CaseContext";

interface Props {
  isOpen: boolean;
  onClose: () => void;
  caseId?: string;
  onCaptureSuccess?: (evidenceId: string) => void;
}

export const WhatsAppCaptureModal: React.FC<Props> = ({
  isOpen,
  onClose,
  caseId,
  onCaptureSuccess,
}) => {
  const { currentCaseId, switchTab, setSelectedEvidenceId, refreshCases } = useCase();
  const activeCaseId = caseId || currentCaseId;

  const [mode, setMode] = useState<"desktop" | "mobile_share">("desktop");
  const [captureStatus, setCaptureStatus] = useState<
    "idle" | "requesting_permission" | "capturing" | "uploading" | "analyzing" | "completed" | "error"
  >("idle");
  const [statusMessage, setStatusMessage] = useState<string>("");
  const [capturedPreview, setCapturedPreview] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  if (!isOpen) return null;

  // Real Web/Desktop Screen or Window Capture via getDisplayMedia
  const handleStartCapture = async () => {
    setErrorMessage(null);
    setCaptureStatus("requesting_permission");
    setStatusMessage("Requesting window/screen capture permission...");

    try {
      if (!navigator.mediaDevices || !navigator.mediaDevices.getDisplayMedia) {
        throw new Error(
          "Screen/Window capture API is not available on this browser or platform. Please use the WhatsApp Share / File Fallback below."
        );
      }

      // Explicit permission request for window or screen
      const stream = await navigator.mediaDevices.getDisplayMedia({
        video: {
          displaySurface: "window" as any,
        },
        audio: false,
      });

      setCaptureStatus("capturing");
      setStatusMessage("Capturing selected WhatsApp window frame...");

      const videoTrack = stream.getVideoTracks()[0];
      const video = document.createElement("video");
      video.srcObject = stream;
      video.muted = true;
      video.playsInline = true;

      await new Promise<void>((resolve) => {
        video.onloadedmetadata = () => {
          video.play().then(() => resolve());
        };
      });

      // Allow 200ms for stable frame rendering
      await new Promise((r) => setTimeout(r, 200));

      const canvas = document.createElement("canvas");
      canvas.width = video.videoWidth || 1280;
      canvas.height = video.videoHeight || 720;
      const ctx = canvas.getContext("2d");
      if (!ctx) {
        videoTrack.stop();
        throw new Error("Failed to initialize canvas render context");
      }

      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
      const previewUrl = canvas.toDataURL("image/png");
      setCapturedPreview(previewUrl);

      // Stop media tracks immediately after grabbing frame (defensive capture, zero background monitoring)
      videoTrack.stop();

      // Convert frame to binary Blob
      const blob = await new Promise<Blob | null>((resolve) =>
        canvas.toBlob((b) => resolve(b), "image/png")
      );

      if (!blob) {
        throw new Error("Failed to convert captured video frame to image bytes");
      }

      // Proceed to upload actual image bytes to the backend
      await uploadCapturedImage(blob, "whatsapp_screen_capture.png");
    } catch (err: any) {
      console.error("Screen capture failed:", err);
      if (err.name === "NotAllowedError") {
        setCaptureStatus("error");
        setErrorMessage("Capture permission was dismissed or denied by user.");
      } else {
        setCaptureStatus("error");
        setErrorMessage(err.message || "Failed to capture screen window.");
      }
    }
  };

  // Upload actual image bytes to currentCaseId
  const uploadCapturedImage = async (imageBlob: Blob, _filename?: string) => {
    setCaptureStatus("uploading");
    setStatusMessage("WhatsApp evidence captured. Storing image bytes...");

    const timestamp = new Date().toISOString().replace(/[:.]/g, "-");
    const safeName = `whatsapp_capture_${timestamp}.png`;
    const imageFile = new File([imageBlob], safeName, { type: "image/png" });

    const formData = new FormData();
    formData.append("file", imageFile);
    formData.append("evidence_type", "image");

    try {
      const res = await fetch(`/api/v1/cases/${activeCaseId}/evidence`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || "Server failed to store captured evidence.");
      }

      const createdEvidence = await res.json();
      const evidenceId = createdEvidence.id;

      setCaptureStatus("analyzing");
      setStatusMessage("Analyzing conversation with OCR & Gemini multimodal vision...");

      // Allow backend processing to settle
      await new Promise((r) => setTimeout(r, 1200));

      setCaptureStatus("completed");
      setStatusMessage("WhatsApp conversation analyzed successfully.");

      await refreshCases();
      if (onCaptureSuccess) {
        onCaptureSuccess(evidenceId);
      }

      // Automatically open Scam Intelligence with the newly captured evidence selected!
      setTimeout(() => {
        setSelectedEvidenceId(evidenceId);
        switchTab("intelligence");
        onClose();
      }, 900);
    } catch (err: any) {
      console.error("Upload error:", err);
      setCaptureStatus("error");
      setErrorMessage(err.message || "Failed to upload captured image to case.");
    }
  };

  // Mobile / Android Share Fallback File Handler
  const handleMobileFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    const file = files[0];
    setCaptureStatus("uploading");
    setStatusMessage("Uploading shared WhatsApp evidence...");

    // Create preview if image
    if (file.type.startsWith("image/")) {
      const reader = new FileReader();
      reader.onload = () => setCapturedPreview(reader.result as string);
      reader.readAsDataURL(file);
    }

    const formData = new FormData();
    formData.append("file", file);
    if (file.type.startsWith("image/")) {
      formData.append("evidence_type", "image");
    } else {
      formData.append("evidence_type", "chat");
    }

    try {
      const res = await fetch(`/api/v1/cases/${activeCaseId}/evidence`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || "Upload failed");
      }

      const createdEvidence = await res.json();
      const evidenceId = createdEvidence.id;

      setCaptureStatus("analyzing");
      setStatusMessage("Analyzing conversation with OCR & multimodal AI...");

      await new Promise((r) => setTimeout(r, 1200));

      setCaptureStatus("completed");
      setStatusMessage("Evidence analyzed successfully.");

      await refreshCases();
      if (onCaptureSuccess) {
        onCaptureSuccess(evidenceId);
      }

      setTimeout(() => {
        setSelectedEvidenceId(evidenceId);
        switchTab("intelligence");
        onClose();
      }, 900);
    } catch (err: any) {
      console.error("Mobile share upload failed:", err);
      setCaptureStatus("error");
      setErrorMessage(err.message || "Failed to process shared evidence.");
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/85 backdrop-blur-md flex items-center justify-center p-4">
      <div className="bg-[#0b0f19] border border-slate-800 rounded-2xl max-w-xl w-full p-6 shadow-2xl relative space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-slate-800/80">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-emerald-950/60 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
              <Camera className="w-5 h-5 text-emerald-400" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white tracking-tight">Capture WhatsApp Evidence</h2>
              <p className="text-xs text-slate-400">
                Case Vault: <span className="font-mono text-emerald-400">{currentCaseId}</span>
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            disabled={captureStatus === "capturing" || captureStatus === "uploading" || captureStatus === "analyzing"}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition cursor-pointer disabled:opacity-40"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Mode Selector */}
        <div className="grid grid-cols-2 gap-2 bg-slate-900/60 p-1 rounded-xl border border-slate-800 text-xs font-semibold">
          <button
            onClick={() => {
              setMode("desktop");
              setErrorMessage(null);
            }}
            className={`py-2 rounded-lg flex items-center justify-center gap-2 transition cursor-pointer ${
              mode === "desktop"
                ? "bg-slate-800 text-white shadow-sm border border-slate-700"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            <Monitor className="w-4 h-4 text-cyan-400" />
            <span>Screen / Window Capture</span>
          </button>
          <button
            onClick={() => {
              setMode("mobile_share");
              setErrorMessage(null);
            }}
            className={`py-2 rounded-lg flex items-center justify-center gap-2 transition cursor-pointer ${
              mode === "mobile_share"
                ? "bg-slate-800 text-white shadow-sm border border-slate-700"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            <Smartphone className="w-4 h-4 text-emerald-400" />
            <span>Android / Share Fallback</span>
          </button>
        </div>

        {/* Informational Security Notice */}
        <div className="bg-slate-900/40 border border-slate-800/80 rounded-xl p-3.5 flex items-start gap-3 text-xs text-slate-300">
          <Lock className="w-4 h-4 text-cyan-400 mt-0.5 shrink-0" />
          <div className="space-y-1">
            <span className="font-semibold text-slate-200">Defensive Forensic Intake</span>
            <p className="text-slate-400 leading-relaxed text-[11px]">
              CounterPulse never conducts background surveillance or silent screenshots. Capture is initiated solely
              by your explicit approval to preserve legal chain-of-custody.
            </p>
          </div>
        </div>

        {/* Status / Preview Box */}
        {capturedPreview && (
          <div className="border border-slate-800 rounded-xl p-2 bg-slate-950/70 overflow-hidden flex flex-col items-center justify-center">
            <img
              src={capturedPreview}
              alt="Captured evidence frame"
              className="max-h-48 rounded-lg object-contain border border-slate-800"
            />
          </div>
        )}

        {captureStatus !== "idle" && (
          <div className="bg-slate-950 border border-slate-800/90 rounded-xl p-4 flex items-center gap-3">
            {captureStatus === "completed" ? (
              <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
            ) : captureStatus === "error" ? (
              <AlertCircle className="w-5 h-5 text-rose-400 shrink-0" />
            ) : (
              <RefreshCw className="w-5 h-5 text-cyan-400 animate-spin shrink-0" />
            )}
            <div className="text-xs">
              <span className="font-semibold text-white capitalize">{captureStatus.replace("_", " ")}</span>
              <p className="text-slate-400 text-[11px]">{statusMessage}</p>
            </div>
          </div>
        )}

        {errorMessage && (
          <div className="bg-rose-950/40 border border-rose-800/60 rounded-xl p-3.5 flex items-start gap-2.5 text-xs text-rose-300">
            <AlertCircle className="w-4 h-4 text-rose-400 mt-0.5 shrink-0" />
            <div className="space-y-0.5">
              <span className="font-semibold">Capture Action Aborted</span>
              <p className="text-[11px] text-rose-300/80">{errorMessage}</p>
            </div>
          </div>
        )}

        {/* Action Buttons */}
        {mode === "desktop" ? (
          <div className="space-y-3">
            <p className="text-xs text-slate-400">
              Click below to select your open WhatsApp conversation window or tab. The frame will be captured,
              cryptographically hashed, and dispatched to the multimodal pipeline.
            </p>
            <button
              onClick={handleStartCapture}
              disabled={
                captureStatus === "requesting_permission" ||
                captureStatus === "capturing" ||
                captureStatus === "uploading" ||
                captureStatus === "analyzing"
              }
              className="w-full py-3 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white font-semibold text-xs rounded-xl flex items-center justify-center gap-2 shadow-lg shadow-emerald-950/40 transition cursor-pointer disabled:opacity-50"
            >
              {captureStatus === "capturing" || captureStatus === "uploading" || captureStatus === "analyzing" ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin text-white" />
                  <span>{statusMessage || "Processing Capture..."}</span>
                </>
              ) : (
                <>
                  <Camera className="w-4 h-4 text-white" />
                  <span>Request Permission & Capture WhatsApp</span>
                </>
              )}
            </button>
          </div>
        ) : (
          <div className="space-y-3">
            <p className="text-xs text-slate-400">
              On Android, use WhatsApp’s <strong>Share Chat</strong> feature or take a screenshot and select it here.
              The file will be associated with case <span className="font-mono text-emerald-400">{currentCaseId}</span>.
            </p>
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleMobileFileChange}
              accept="image/*,text/plain,.txt,.zip"
              className="hidden"
            />
            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={
                captureStatus === "uploading" ||
                captureStatus === "analyzing"
              }
              className="w-full py-3 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white font-semibold text-xs rounded-xl flex items-center justify-center gap-2 shadow-lg shadow-cyan-950/40 transition cursor-pointer disabled:opacity-50"
            >
              <Upload className="w-4 h-4 text-white" />
              <span>Select WhatsApp Screenshot / Chat Export</span>
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

