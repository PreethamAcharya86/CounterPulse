import React, { useState, useEffect, useRef, useCallback } from "react";
import {
  Mic,
  MicOff,
  Volume2,
  VolumeX,
  Send,
  AlertTriangle,
  CheckCircle2,
  RefreshCw,
  FileText,
  Layers,
  HelpCircle,
} from "lucide-react";

interface Props {
  caseId: string;
  onNavigateToPassport?: () => void;
  onNavigateToReports?: () => void;
  onNavigateToEvidence?: () => void;
}

interface MessageTurn {
  sender: "user" | "assistant";
  text: string;
  intent?: string;
  timestamp: string;
  requiresConfirmation?: boolean;
  actionExecuted?: string;
}

export const VoiceControlView: React.FC<Props> = ({
  caseId,
  onNavigateToPassport,
  onNavigateToReports,
  onNavigateToEvidence,
}) => {
  const [voiceState, setVoiceState] = useState<"IDLE" | "LISTENING" | "PROCESSING" | "RESPONDING" | "ERROR">("IDLE");
  const [transcript, setTranscript] = useState<string>("");
  const [inputText, setInputText] = useState<string>("");
  const [turns, setTurns] = useState<MessageTurn[]>([
    {
      sender: "assistant",
      text: "CounterPulse Voice Layer active. I can analyze this case, summarize findings, read dispute packages, or assist with authorized dispatch. Speak your command.",
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    },
  ]);
  const [pendingAction, setPendingAction] = useState<any>(null);
  const [isAudioEnabled, setIsAudioEnabled] = useState<boolean>(true);
  const [errorStatus, setErrorStatus] = useState<string | null>(null);

  const recognitionRef = useRef<any>(null);
  const turnsEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll
  useEffect(() => {
    turnsEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [turns]);

  // Text to speech helper
  const speakText = useCallback(
    (text: string) => {
      if (!isAudioEnabled || typeof window === "undefined" || !("speechSynthesis" in window)) return;
      try {
        window.speechSynthesis.cancel();
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.rate = 1.05;
        utterance.pitch = 1.0;
        utterance.onend = () => setVoiceState("IDLE");
        window.speechSynthesis.speak(utterance);
      } catch (e) {
        console.warn("Speech synthesis error:", e);
      }
    },
    [isAudioEnabled]
  );

  // Initialize Web Speech Recognition if supported
  useEffect(() => {
    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (SpeechRecognition) {
      const recognition = new SpeechRecognition();
      recognition.continuous = false;
      recognition.interimResults = true;
      recognition.lang = "en-US";

      recognition.onstart = () => {
        setVoiceState("LISTENING");
        setErrorStatus(null);
      };

      recognition.onresult = (event: any) => {
        let currentTranscript = "";
        for (let i = event.resultIndex; i < event.results.length; ++i) {
          currentTranscript += event.results[i][0].transcript;
        }
        setTranscript(currentTranscript);
      };

      recognition.onerror = (event: any) => {
        console.warn("Speech recognition event:", event.error);
        if (event.error !== "no-speech") {
          setErrorStatus(`Microphone: ${event.error}`);
        }
        setVoiceState("IDLE");
      };

      recognition.onend = () => {
        if (voiceState === "LISTENING") {
          setVoiceState("IDLE");
        }
      };

      recognitionRef.current = recognition;
    }
  }, [voiceState]);

  // Handle command dispatch to backend
  const handleSendCommand = async (commandText: string) => {
    if (!commandText.trim()) return;

    setVoiceState("PROCESSING");
    setErrorStatus(null);

    const now = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    const userTurn: MessageTurn = {
      sender: "user",
      text: commandText.trim(),
      timestamp: now,
    };
    setTurns((prev) => [...prev, userTurn]);
    setInputText("");
    setTranscript("");

    try {
      const res = await fetch(`/api/v1/cases/${caseId}/voice/command`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          transcript: commandText.trim(),
          session_id: `vsession-${caseId}`,
        }),
      });

      if (res.ok) {
        const data = await res.json();
        setVoiceState("RESPONDING");
        setPendingAction(data.pending_action);

        const assistantTurn: MessageTurn = {
          sender: "assistant",
          text: data.response_text,
          intent: data.intent,
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
          requiresConfirmation: data.requires_confirmation,
          actionExecuted: data.action_executed,
        };
        setTurns((prev) => [...prev, assistantTurn]);

        speakText(data.response_text);
      } else {
        const err = await res.json().catch(() => ({}));
        setErrorStatus(err.detail || "Voice command execution failed.");
        setVoiceState("ERROR");
      }
    } catch (err: any) {
      setErrorStatus(err.message || "Network error sending voice command.");
      setVoiceState("ERROR");
    }
  };

  const toggleListening = () => {
    if (voiceState === "LISTENING") {
      recognitionRef.current?.stop();
      setVoiceState("IDLE");
      if (transcript.trim()) {
        handleSendCommand(transcript);
      }
    } else {
      setTranscript("");
      try {
        recognitionRef.current?.start();
      } catch (e) {
        console.warn("Recognition already started or error:", e);
      }
    }
  };

  const QUICK_COMMANDS = [
    "Analyze this case.",
    "What happened?",
    "What accounts are compromised?",
    "Show me the evidence.",
    "Read the cybercrime complaint.",
    "Generate a bank dispute.",
    "Read the security advisory.",
    "Send the complaint email.",
  ];

  const getStatePill = () => {
    switch (voiceState) {
      case "LISTENING":
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/40 animate-pulse">
            <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
            LISTENING
          </span>
        );
      case "PROCESSING":
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-amber-500/20 text-amber-400 border border-amber-500/40 animate-pulse">
            <RefreshCw className="w-3 h-3 animate-spin" />
            PROCESSING
          </span>
        );
      case "RESPONDING":
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-cyan-500/20 text-cyan-300 border border-cyan-500/40">
            <Volume2 className="w-3.5 h-3.5 animate-bounce" />
            RESPONDING
          </span>
        );
      case "ERROR":
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-rose-500/20 text-rose-400 border border-rose-500/40">
            <AlertTriangle className="w-3.5 h-3.5" />
            ERROR / DISCONNECTED
          </span>
        );
      case "IDLE":
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-slate-800 text-slate-400 border border-slate-700">
            <span className="w-2 h-2 rounded-full bg-slate-500"></span>
            IDLE
          </span>
        );
    }
  };

  return (
    <div className="space-y-6 max-w-5xl mx-auto pb-16">
      {/* Top Banner */}
      <div className="rounded-2xl p-5 bg-gradient-to-r from-purple-950/40 via-slate-900/60 to-indigo-950/40 border border-purple-500/30 flex flex-col md:flex-row items-start md:items-center justify-between gap-4 shadow-xl">
        <div className="flex items-start gap-3.5">
          <div className="p-2.5 rounded-xl bg-purple-500/20 border border-purple-400/30 text-purple-300 shrink-0 mt-0.5">
            <Mic className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs uppercase font-extrabold tracking-wider px-2 py-0.5 rounded bg-purple-500/20 text-purple-300 border border-purple-500/30">
                Bidirectional Voice Control
              </span>
              {getStatePill()}
            </div>
            <h2 className="text-lg font-bold text-white mt-1">Gemini Live Voice Control Console</h2>
            <p className="text-xs text-slate-300 mt-0.5 max-w-2xl leading-relaxed">
              Real-time voice controller over case reconstruction, compromise assessment, and dispute reports. <strong>Strict safety rule: Voice commands cannot bypass human approval for consequential email dispatch.</strong>
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          {onNavigateToEvidence && (
            <button
              onClick={onNavigateToEvidence}
              className="px-3 py-2 rounded-xl bg-slate-800/80 hover:bg-slate-700/80 border border-slate-700 text-slate-300 text-xs font-semibold flex items-center gap-1.5 transition-colors shadow"
              title="Open Evidence Vault"
            >
              <Layers className="w-3.5 h-3.5 text-emerald-400" />
              Vault
            </button>
          )}
          {onNavigateToPassport && (
            <button
              onClick={onNavigateToPassport}
              className="px-3 py-2 rounded-xl bg-slate-800/80 hover:bg-slate-700/80 border border-slate-700 text-cyan-300 text-xs font-semibold flex items-center gap-1.5 transition-colors shadow"
              title="Open Case Passport"
            >
              <FileText className="w-3.5 h-3.5 text-cyan-400" />
              Passport
            </button>
          )}
          {onNavigateToReports && (
            <button
              onClick={onNavigateToReports}
              className="px-3 py-2 rounded-xl bg-slate-800/80 hover:bg-slate-700/80 border border-slate-700 text-indigo-300 text-xs font-semibold flex items-center gap-1.5 transition-colors shadow"
              title="Open Response Center"
            >
              <Send className="w-3.5 h-3.5 text-indigo-400" />
              Reports
            </button>
          )}
          <button
            onClick={() => setIsAudioEnabled(!isAudioEnabled)}
            className={`p-2.5 rounded-xl border text-xs font-semibold flex items-center gap-1.5 transition-colors ${
              isAudioEnabled
                ? "bg-slate-800 border-slate-700 text-slate-200"
                : "bg-rose-950/40 border-rose-500/30 text-rose-300"
            }`}
            title="Toggle Voice Speech Audio"
          >
            {isAudioEnabled ? <Volume2 className="w-4 h-4 text-cyan-400" /> : <VolumeX className="w-4 h-4 text-rose-400" />}
          </button>
        </div>
      </div>

      {errorStatus && (
        <div className="p-3.5 rounded-xl bg-rose-950/40 border border-rose-500/40 text-rose-300 text-xs flex items-center gap-2.5 animate-fadeIn">
          <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
          <span>{errorStatus}</span>
        </div>
      )}

      {/* Main Conversation Box */}
      <div className="rounded-2xl bg-slate-900/60 border border-slate-700/60 p-6 space-y-5 shadow-2xl backdrop-blur-xl">
        {/* Turns List */}
        <div className="space-y-4 max-h-[460px] overflow-y-auto pr-2">
          {turns.map((turn, idx) => (
            <div
              key={idx}
              className={`flex flex-col ${turn.sender === "user" ? "items-end" : "items-start"}`}
            >
              <div
                className={`max-w-[85%] rounded-2xl p-4 text-xs space-y-1.5 leading-relaxed shadow-lg ${
                  turn.sender === "user"
                    ? "bg-gradient-to-r from-indigo-600 to-purple-600 text-white rounded-br-none"
                    : "bg-slate-950/80 border border-slate-800 text-slate-200 rounded-bl-none"
                }`}
              >
                <div className="flex items-center justify-between gap-4 font-mono text-[10px] text-slate-400">
                  <span className="font-bold flex items-center gap-1">
                    {turn.sender === "user" ? "YOU (Spoken)" : "COUNTERPULSE ASSISTANT"}
                  </span>
                  <span>{turn.timestamp}</span>
                </div>
                <p className="text-sm font-sans">{turn.text}</p>

                {turn.requiresConfirmation && (
                  <div className="mt-2 pt-2 border-t border-slate-800 text-[11px] text-amber-300 flex items-center gap-1.5">
                    <AlertTriangle className="w-3.5 h-3.5 text-amber-400 shrink-0" />
                    <span>Consequential action pending confirmation. Speak <strong>"Yes"</strong> to dispatch or <strong>"No"</strong> to cancel.</span>
                  </div>
                )}

                {turn.actionExecuted && (
                  <div className="mt-2 pt-2 border-t border-slate-800 text-[11px] text-emerald-300 flex items-center gap-1.5">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                    <span>Action executed: {turn.actionExecuted}</span>
                  </div>
                )}
              </div>
            </div>
          ))}

          {/* Pending Action Confirmation Banner */}
          {pendingAction && (
            <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/40 text-amber-200 text-xs space-y-3 animate-fadeIn">
              <div className="flex items-center gap-2 font-bold text-amber-300 text-sm">
                <AlertTriangle className="w-4 h-4 text-amber-400" />
                Confirmation Required Before Consequential Dispatch
              </div>
              <p className="text-slate-300 leading-relaxed">
                The system is ready to transmit <strong>{pendingAction.report_type.replace('_', ' ').toUpperCase()}</strong> to <strong>{pendingAction.recipient}</strong>.
              </p>
              <div className="flex items-center gap-2 pt-1">
                <button
                  onClick={() => handleSendCommand("Yes")}
                  className="px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs shadow-md transition-colors"
                >
                  Yes, Confirm & Send
                </button>
                <button
                  onClick={() => handleSendCommand("No")}
                  className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 font-semibold text-xs transition-colors"
                >
                  No, Cancel
                </button>
              </div>
            </div>
          )}

          <div ref={turnsEndRef} />
        </div>

        {/* Live Audio Transcript Preview */}
        {voiceState === "LISTENING" && (
          <div className="p-3 rounded-xl bg-emerald-950/30 border border-emerald-500/30 text-emerald-300 text-xs flex items-center justify-between animate-pulse">
            <div className="flex items-center gap-2">
              <Mic className="w-4 h-4 text-emerald-400 animate-spin" />
              <span>Listening: "{transcript || "Speak your command..."}"</span>
            </div>
            <button
              onClick={() => handleSendCommand(transcript)}
              disabled={!transcript.trim()}
              className="text-[11px] font-bold text-emerald-400 hover:underline"
            >
              Submit
            </button>
          </div>
        )}

        {/* Microphone and Command Entry Bar */}
        <div className="pt-4 border-t border-slate-800 space-y-4">
          <div className="flex items-center gap-3">
            {/* Big Mic Button */}
            <button
              onClick={toggleListening}
              className={`p-4 rounded-2xl transition-all shadow-xl flex items-center justify-center shrink-0 ${
                voiceState === "LISTENING"
                  ? "bg-rose-600 hover:bg-rose-500 text-white animate-pulse ring-4 ring-rose-500/30"
                  : "bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white shadow-purple-950/50"
              }`}
              title={voiceState === "LISTENING" ? "Stop Listening" : "Start Voice Input"}
            >
              {voiceState === "LISTENING" ? <MicOff className="w-6 h-6" /> : <Mic className="w-6 h-6" />}
            </button>

            {/* Manual text input */}
            <div className="relative flex-1">
              <input
                type="text"
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    handleSendCommand(inputText);
                  }
                }}
                placeholder="Or type a voice command e.g. 'Analyze this case', 'What happened?', 'Send complaint email'..."
                className="w-full px-4 py-3 rounded-xl bg-slate-950 border border-slate-700 text-sm text-white focus:border-purple-500 focus:outline-none pr-10 font-medium"
              />
              <button
                onClick={() => handleSendCommand(inputText)}
                disabled={!inputText.trim()}
                className="absolute right-2.5 top-2.5 p-1 rounded-lg text-slate-400 hover:text-white disabled:opacity-30"
              >
                <Send className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Quick Voice Command Buttons */}
          <div className="space-y-1.5">
            <div className="text-[11px] font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
              <HelpCircle className="w-3.5 h-3.5 text-purple-400" />
              Supported Voice Commands
            </div>
            <div className="flex flex-wrap gap-2">
              {QUICK_COMMANDS.map((cmd, idx) => (
                <button
                  key={idx}
                  onClick={() => handleSendCommand(cmd)}
                  className="px-3 py-1.5 rounded-xl bg-slate-950/70 hover:bg-slate-800 border border-slate-800 text-slate-300 text-xs font-mono transition-colors text-left"
                >
                  "{cmd}"
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
