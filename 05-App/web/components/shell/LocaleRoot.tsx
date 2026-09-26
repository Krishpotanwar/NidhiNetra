"use client";

import { createContext, Fragment, useContext, useState, useSyncExternalStore, type ReactNode } from "react";
import { setLocale, type Locale } from "@/lib/strings";

const STORAGE_KEY = "nn.locale";

function applyLocale(locale: Locale): void {
  setLocale(locale);
  document.documentElement.lang = locale;
}

function readStoredLocale(): Locale | null {
  if (new URLSearchParams(window.location.search).get("lang") === "hi") return "hi";
  try {
    return window.localStorage.getItem(STORAGE_KEY) === "hi" ? "hi" : null;
  } catch {
    // Storage can throw (private browsing, disabled storage). No stored
    // preference just means the page stays in English.
    return null;
  }
}

interface LocaleStore {
  subscribe: (listener: () => void) => () => void;
  getSnapshot: () => Locale;
  getServerSnapshot: () => Locale;
  change: (next: Locale) => void;
}

/**
 * One store per LocaleRoot mount (there is only ever one, at the root
 * layout). The locale legitimately differs between the server's render
 * (always "en") and the client's real starting value (?lang=hi or a stored
 * preference), so this reads through useSyncExternalStore -- React's own
 * mechanism for that -- rather than a useEffect that calls a useState
 * setter on mount, which starts a second render *and* nothing here needs
 * `hydrateRoot` to be able to tell apart from a plain double-render.
 */
function createLocaleStore(): LocaleStore {
  let locale: Locale = "en";
  const listeners = new Set<() => void>();

  function notify(): void {
    for (const listener of listeners) listener();
  }

  // Runs once subscribe is first called (React does this from an effect,
  // after the server-matching "en" render has already committed): reads
  // the one-time starting preference and, if it says Hindi, applies it and
  // notifies -- exactly the "subscribe, then setState in a callback when
  // external state changes" shape effects are meant to follow.
  function resolveInitialLocale(): void {
    if (locale !== "hi" && readStoredLocale() === "hi") {
      locale = "hi";
      applyLocale("hi");
      notify();
    }
  }

  function change(next: Locale): void {
    locale = next;
    applyLocale(next);
    try {
      window.localStorage.setItem(STORAGE_KEY, next);
    } catch {
      // Storage can throw; the toggle still works for this page view, it
      // just will not be remembered on the next visit.
    }
    notify();
  }

  return {
    subscribe(listener) {
      listeners.add(listener);
      resolveInitialLocale();
      return () => listeners.delete(listener);
    },
    getSnapshot: () => locale,
    getServerSnapshot: () => "en",
    change,
  };
}

interface LocaleContextValue {
  locale: Locale;
  change: (locale: Locale) => void;
}

const LocaleContext = createContext<LocaleContextValue>({ locale: "en", change: () => {} });

/** Used by LanguageToggle to read the current locale and switch it. */
export function useLocale(): LocaleContextValue {
  return useContext(LocaleContext);
}

/**
 * Starts in "en" so the server HTML and the first client render match.
 * `key={locale}` on the Fragment remounts every child on a locale change: a
 * Client Component that reads STRINGS.x.y at render time picks up the
 * overlay on remount, and so does a `<Str>` a Server Component handed a
 * dotted path instead of a frozen string.
 */
export function LocaleRoot({ children }: { children: ReactNode }) {
  const [store] = useState(createLocaleStore);
  const locale = useSyncExternalStore(store.subscribe, store.getSnapshot, store.getServerSnapshot);

  return (
    <LocaleContext.Provider value={{ locale, change: store.change }}>
      <Fragment key={locale}>{children}</Fragment>
    </LocaleContext.Provider>
  );
}
