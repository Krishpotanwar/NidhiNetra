"use client";

import { createStoredValue, useStoredValue } from "./stored-value";

/**
 * Presenter mode: a demo device, confirmed with the user 2026-09-11. When on,
 * the filter bar shows a Data state control that previews the designed
 * loading and empty screens. Session-scoped, so it never survives into an
 * officer's next visit, and switched on only by ?present=1.
 */
export const presenterMode = createStoredValue<boolean>({
  key: "nidhinetra_presenter",
  storage: "session",
  fallback: false,
  parse: (raw) => raw === "1",
  serialize: (on) => (on ? "1" : null),
});

export function usePresenterMode(): boolean {
  return useStoredValue(presenterMode);
}

/**
 * Row treatment: a real density preference. "two-line" keeps the reason
 * visible on every row (the default, because the reason is the product's
 * voice); "hover-reveal" shows it only on the hovered or focused row.
 */
export type RowTreatment = "two-line" | "hover-reveal";

export const rowTreatment = createStoredValue<RowTreatment>({
  key: "nidhinetra_row_treatment",
  storage: "local",
  fallback: "two-line",
  parse: (raw) => (raw === "hover-reveal" ? "hover-reveal" : "two-line"),
  serialize: (value) => (value === "two-line" ? null : value),
});

export function useRowTreatment(): RowTreatment {
  return useStoredValue(rowTreatment);
}

/**
 * Officer initials. The same key InspectionCapture has always used, so the
 * header menu and the recording form share one self-reported value. Not an
 * identity: no sign-in exists in this prototype.
 */
export const INSPECTOR_ID_STORAGE_KEY = "nidhinetra_inspector_id";

export const officerInitials = createStoredValue<string>({
  key: INSPECTOR_ID_STORAGE_KEY,
  storage: "local",
  fallback: "",
  parse: (raw) => raw ?? "",
  serialize: (value) => (value.trim() ? value.trim() : null),
});

export function useOfficerInitials(): string {
  return useStoredValue(officerInitials);
}
