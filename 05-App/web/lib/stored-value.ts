"use client";

import { useSyncExternalStore } from "react";

/**
 * A tiny external store over localStorage or sessionStorage, read through
 * useSyncExternalStore so every component that shows the same preference
 * (the header's presenter badge and the filter bar's data-state control,
 * say) updates together without a context provider.
 *
 * Storage can be missing (server render) or blocked (private window); every
 * access is guarded and the store falls back to its default, so a blocked
 * store degrades to "not remembered", never to a crash.
 */
export interface StoredValue<T> {
  get: () => T;
  set: (value: T) => void;
  subscribe: (listener: () => void) => () => void;
  fallback: T;
}

export function createStoredValue<T extends string | boolean>(options: {
  key: string;
  storage: "local" | "session";
  fallback: T;
  parse: (raw: string | null) => T;
  serialize: (value: T) => string | null;
}): StoredValue<T> {
  const listeners = new Set<() => void>();

  const area = (): Storage | null => {
    try {
      return options.storage === "local" ? window.localStorage : window.sessionStorage;
    } catch {
      return null;
    }
  };

  const get = (): T => {
    try {
      return options.parse(area()?.getItem(options.key) ?? null);
    } catch {
      return options.fallback;
    }
  };

  const set = (value: T) => {
    try {
      const raw = options.serialize(value);
      const store = area();
      if (raw === null) store?.removeItem(options.key);
      else store?.setItem(options.key, raw);
    } catch {
      // Not remembered this time; the in-memory notify below still updates the page.
    }
    listeners.forEach((listener) => listener());
  };

  const subscribe = (listener: () => void) => {
    listeners.add(listener);
    const onStorage = (event: StorageEvent) => {
      if (event.key === options.key) listener();
    };
    window.addEventListener("storage", onStorage);
    return () => {
      listeners.delete(listener);
      window.removeEventListener("storage", onStorage);
    };
  };

  return { get, set, subscribe, fallback: options.fallback };
}

export function useStoredValue<T extends string | boolean>(store: StoredValue<T>): T {
  return useSyncExternalStore(store.subscribe, store.get, () => store.fallback);
}
