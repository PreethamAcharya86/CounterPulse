import React, { createContext, useContext, useState } from "react";
import { translations } from "./translations";
import type { SupportedLanguage, TranslationDictionary } from "./translations";

interface LanguageContextType {
  language: SupportedLanguage;
  setLanguage: (lang: SupportedLanguage) => void;
  t: (key: keyof TranslationDictionary, fallback?: string) => string;
}

const LanguageContext = createContext<LanguageContextType | undefined>(undefined);

const STORAGE_KEY = "counterpulse_lang";

export const LanguageProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [language, setLanguageState] = useState<SupportedLanguage>(() => {
    if (typeof window !== "undefined") {
      const saved = localStorage.getItem(STORAGE_KEY) as SupportedLanguage;
      if (saved && (saved === "en" || saved === "hi" || saved === "kn")) {
        return saved;
      }
    }
    return "en";
  });

  const setLanguage = (lang: SupportedLanguage) => {
    setLanguageState(lang);
    if (typeof window !== "undefined") {
      localStorage.setItem(STORAGE_KEY, lang);
    }
  };

  const t = (key: keyof TranslationDictionary, fallback?: string): string => {
    const dict = translations[language] || translations.en;
    if (dict && dict[key]) {
      return dict[key];
    }
    return translations.en[key] || fallback || key;
  };

  return (
    <LanguageContext.Provider value={{ language, setLanguage, t }}>
      {children}
    </LanguageContext.Provider>
  );
};

export const useTranslation = () => {
  const context = useContext(LanguageContext);
  if (!context) {
    // Graceful fallback if rendered outside provider
    return {
      language: "en" as SupportedLanguage,
      setLanguage: () => {},
      t: (key: keyof TranslationDictionary, fallback?: string) =>
        translations.en[key] || fallback || key,
    };
  }
  return context;
};
