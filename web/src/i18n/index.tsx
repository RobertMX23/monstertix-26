/* The page's own words, in the reader's language.

   Every string the interface shows goes through t(). The English catalog is
   the source; another language is one more JSON file next to it with the
   same keys, registered in CATALOGS. A key missing from a translation falls
   back to English, so a partial translation still works.

   Step content is translated separately, on the server (content/README.md).

   t("Load step {n}", { n: 6 }) fills {n}. */

import { createContext, useContext, type ReactNode } from "react";

import en from "./en.json";

type Catalog = Record<string, string>;

// Add a language: import its JSON here and list it.
export const CATALOGS: Record<string, Catalog> = { en };

export const LANGUAGE_NAMES: Record<string, string> = {
  en: "English",
  es: "Español",
  pt: "Português",
  fr: "Français",
  de: "Deutsch",
  ja: "日本語",
  ko: "한국어",
  "zh-TW": "繁體中文",
  id: "Bahasa Indonesia",
};

const STORAGE = "monstertix.lang";

export function savedLang(): string {
  try {
    const fromUrl = new URLSearchParams(window.location.search).get("lang");
    if (fromUrl) return fromUrl;
    return localStorage.getItem(STORAGE) || navigator.language.split("-")[0] || "en";
  } catch {
    return "en";
  }
}

export function saveLang(lang: string) {
  try {
    localStorage.setItem(STORAGE, lang);
  } catch {
    /* blocked storage: the choice lasts for this visit */
  }
}

let current = "en";

export function setLang(lang: string) {
  current = lang;
  document.documentElement.lang = lang;
}

export function t(key: string, values?: Record<string, string | number>): string {
  const text = CATALOGS[current]?.[key] ?? (en as Catalog)[key] ?? key;
  if (!values) return text;
  return text.replace(/\{(\w+)\}/g, (_, name) => String(values[name] ?? `{${name}}`));
}

const LangContext = createContext("en");

export function LangProvider({ lang, children }: { lang: string; children: ReactNode }) {
  setLang(lang);
  return <LangContext.Provider value={lang}>{children}</LangContext.Provider>;
}

/** Re-renders a component when the language changes. */
export function useLang() {
  return useContext(LangContext);
}
