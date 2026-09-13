/**
 * Filter state for the Dashboard and the Inspection List, its address-bar
 * form, and the API query it becomes.
 *
 * 2026-09-11: filtering moved server-side. Options now come from
 * GET /api/works/facets, counted over the whole quota population, so a
 * state absent from the first page of results is still offered (ultra-review
 * F05). State is multi-select, as in the pinned reference.
 *
 * Nothing here is hardcoded: every option list arrives as data, and the flag
 * list is the four detectors the engine can emit (contracts/strings.json
 * filters.flag_names), never the ones that happened to fire on one page.
 */
import type { FacetOption, FlagType, InspectionRow } from "./types";
import { STRINGS } from "./strings";

/** Sentinel for "no constraint on this dimension". */
export const ALL = "__all__";

/** Matches the API's own bound on q (models.py works_query). */
export const MAX_QUERY_LENGTH = 120;

export interface FilterState {
  states: string[];
  year: string;
  category: string;
  flag: string;
}

export const EMPTY_FILTERS: FilterState = {
  states: [],
  year: ALL,
  category: ALL,
  flag: ALL,
};

export function isFilterActive(f: FilterState): boolean {
  return f.states.length > 0 || f.year !== ALL || f.category !== ALL || f.flag !== ALL;
}

const FLAG_KEYS = Object.keys(STRINGS.filters.flag_names) as FlagType[];

export function isFlagType(value: string): value is FlagType {
  return (FLAG_KEYS as string[]).includes(value);
}

export function flagLabel(flag: string): string {
  return isFlagType(flag) ? STRINGS.filters.flag_names[flag] : flag;
}

/**
 * Indian financial year label (April to March) for a row, e.g. "2023-24".
 *
 * Deliberately a line-for-line mirror of the pipeline's
 * risk/peer_groups.py financial_year_of, including its fallback from
 * sanction_date to last_updated: the year a work is shown in must be the
 * same year it was placed in a peer cohort by the scorer, or the detail
 * panel and its own peer-group sentence would disagree about which year the
 * comparison used. pipeline/tests/test_web_mirror_drift.py reads this
 * function's source to hold the two together.
 */
export function financialYearOf(row: Pick<InspectionRow, "sanction_date" | "last_updated">): string | null {
  const raw = row.sanction_date ?? row.last_updated;
  if (!raw) return null;
  const d = new Date(raw);
  if (Number.isNaN(d.getTime())) return null;
  // getMonth() is 0-indexed, so month >= 3 is April onward.
  const startYear = d.getMonth() >= 3 ? d.getFullYear() : d.getFullYear() - 1;
  const endLabel = String((startYear + 1) % 100).padStart(2, "0");
  return `${startYear}-${endLabel}`;
}

/** The API query for a filter state: repeatable state, sentinels dropped. */
export function filtersToQuery(f: FilterState, q?: string | null): URLSearchParams {
  const params = new URLSearchParams();
  for (const state of f.states) params.append("state", state);
  if (f.year !== ALL) params.set("year", f.year);
  if (f.category !== ALL) params.set("category", f.category);
  if (f.flag !== ALL) params.set("flag", f.flag);
  const search = q?.trim();
  if (search) params.set("q", search.slice(0, MAX_QUERY_LENGTH));
  return params;
}

/** The Inspection List's address-bar form: the API query plus the page. */
export function listSearchParams(f: FilterState, q: string | null, page: number): URLSearchParams {
  const params = filtersToQuery(f, q);
  if (page > 1) params.set("page", String(page));
  return params;
}

export function inspectionListHref(f: FilterState, q: string | null = null, page = 1): string {
  const qs = listSearchParams(f, q, page).toString();
  return qs ? `/inspections?${qs}` : "/inspections";
}

interface ReadableParams {
  get(name: string): string | null;
  getAll(name: string): string[];
}

/**
 * Parses the address bar back into state, trusting none of it: unknown
 * flags, malformed pages and over-long searches fall back to defaults
 * rather than reaching the API.
 */
export function readListParams(params: ReadableParams): { filters: FilterState; q: string; page: number } {
  const states = Array.from(new Set(params.getAll("state").map((s) => s.trim()).filter(Boolean))).slice(0, 64);
  const year = params.get("year")?.trim() || ALL;
  const category = params.get("category")?.trim() || ALL;
  const rawFlag = params.get("flag")?.trim() ?? "";
  const flag = isFlagType(rawFlag) ? rawFlag : ALL;
  const q = (params.get("q") ?? "").trim().slice(0, MAX_QUERY_LENGTH);
  const parsedPage = Number.parseInt(params.get("page") ?? "1", 10);
  const page = Number.isFinite(parsedPage) && parsedPage >= 1 ? parsedPage : 1;
  return { filters: { states, year, category, flag }, q, page };
}

export interface SelectOption {
  value: string;
  label: string;
  count?: number;
}

export function optionsFromFacet(
  facet: FacetOption[] | undefined,
  allLabel: string,
  label: (value: string) => string = (value) => value,
): SelectOption[] {
  return [
    { value: ALL, label: allLabel },
    ...(facet ?? []).map((f) => ({ value: f.value, label: label(f.value), count: f.count })),
  ];
}
