"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { dictionaries, type Dictionary, type Locale } from "./dictionary";

type LanguageContextValue = {
  locale: Locale;
  dictionary: Dictionary;
  setLocale: (locale: Locale) => void;
};

const LanguageContext = createContext<LanguageContextValue | undefined>(undefined);

function readInitialLocale(): Locale {
  if (typeof window === "undefined") return "ko";
  return window.localStorage.getItem("paraworks-locale") === "en" ? "en" : "ko";
}

export function LanguageProvider({ children }: { children: React.ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>("ko");

  useEffect(() => {
    setLocaleState(readInitialLocale());
  }, []);

  useEffect(() => {
    document.documentElement.lang = locale;
  }, [locale]);

  function setLocale(nextLocale: Locale) {
    setLocaleState(nextLocale);
    window.localStorage.setItem("paraworks-locale", nextLocale);
    document.documentElement.lang = nextLocale;
  }

  const value = useMemo(
    () => ({
      locale,
      dictionary: dictionaries[locale],
      setLocale,
    }),
    [locale],
  );

  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>;
}

export function useLanguage() {
  const value = useContext(LanguageContext);
  if (!value) {
    throw new Error("useLanguage must be used inside LanguageProvider");
  }
  return value;
}
