import React from "react";
import { Globe } from "lucide-react";
import { useTranslation } from "../i18n/LanguageContext";
import type { SupportedLanguage } from "../i18n/translations";

export const LanguageSelector: React.FC = () => {
  const { language, setLanguage } = useTranslation();

  const options: { code: SupportedLanguage; label: string; nativeName: string }[] = [
    { code: "en", label: "EN", nativeName: "English" },
    { code: "hi", label: "HI", nativeName: "हिंदी" },
    { code: "kn", label: "KN", nativeName: "ಕನ್ನಡ" },
  ];

  return (
    <div className="flex items-center gap-1 bg-slate-900/80 border border-slate-800 p-1 rounded-xl text-xs font-semibold">
      <Globe className="w-3.5 h-3.5 text-slate-400 ml-1.5 mr-0.5" />
      {options.map((opt) => (
        <button
          key={opt.code}
          onClick={() => setLanguage(opt.code)}
          className={`px-2 py-1 rounded-lg transition-colors cursor-pointer text-xs ${
            language === opt.code
              ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 font-bold"
              : "text-slate-400 hover:text-slate-200"
          }`}
          title={`${opt.nativeName} (${opt.label})`}
        >
          {opt.nativeName}
        </button>
      ))}
    </div>
  );
};
