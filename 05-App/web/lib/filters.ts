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

/** T6: the "View as" role lens (D6 -- a role lens is a preset scope plus one
 *  duty sentence, never a new page or nav tab). Default "ministry": the
 *  whole nation, no scope narrowing. */
export const VIEWS = ["ministry", "state", "district", "mp"] as const;
export type View = (typeof VIEWS)[number];

export function isView(value: string): value is View {
  return (VIEWS as readonly string[]).includes(value);
}

export interface FilterState {
  states: string[];
  year: string;
  category: string;
  flag: string;
  /** ALL or one of PENDENCY_KINDS below (T4's three MoSPI pendency kinds). */
  pendency: string;
  /** ALL or a district_authority value from /api/works/facets. Set by T6's
   *  "District Authority" lens picker; round-trips through the address bar
   *  and scopes fetchPendency/fetchWorksPage when set. */
  districtAuthority: string;
  /** ALL or a constituency value from /api/works/facets. Set by T6's
   *  "Member of Parliament" lens picker; same round-trip as
   *  districtAuthority above. */
  constituency: string;
  /** T6: which role's dashboard preset is showing. */
  view: View;
}

export const EMPTY_FILTERS: FilterState = {
  states: [],
  year: ALL,
  category: ALL,
  flag: ALL,
  pendency: ALL,
  districtAuthority: ALL,
  constituency: ALL,
  view: "ministry",
};

/**
 * Switching the role lens presets a fresh scope (T6 brief): the state list,
 * District Authority or constituency chosen under the previous lens belonged
 * to a different role and would otherwise linger as a filter that is no
 * longer visible under the new picker.
 */
export function withView(f: FilterState, next: View): FilterState {
  return { ...f, view: next, states: [], districtAuthority: ALL, constituency: ALL };
}

/**
 * T6 fix (review round 1, Critical): whether the current lens has a
 * concrete scope to state a duty about. The district and mp duty sentences
 * each name a single authority or constituency ("this District Authority
 * inspects...", "this constituency's..."); before the officer has actually
 * picked one, `districtAuthority`/`constituency` are still ALL and
 * fetchPendency(filters) returns the *national* summary, so rendering the
 * sentence would state a false, singular claim using national numbers.
 * Ministry and State never name a single authority, so they are always
 * scoped. One helper, used at both DutyLine call sites (DashboardClient,
 * InspectionListClient), so the gate cannot drift between the two.
 */
export function isLensScoped(f: Pick<FilterState, "view" | "districtAuthority" | "constituency">): boolean {
  if (f.view === "district") return f.districtAuthority !== ALL;
  if (f.view === "mp") return f.constituency !== ALL;
  return true;
}

export function isFilterActive(f: FilterState): boolean {
  return (
    f.states.length > 0 ||
    f.year !== ALL ||
    f.category !== ALL ||
    f.flag !== ALL ||
    f.pendency !== ALL ||
    f.districtAuthority !== ALL ||
    f.constituency !== ALL
  );
}

const FLAG_KEYS = Object.keys(STRINGS.filters.flag_names) as FlagType[];

export function isFlagType(value: string): value is FlagType {
  return (FLAG_KEYS as string[]).includes(value);
}

export function flagLabel(flag: string): string {
  return isFlagType(flag) ? STRINGS.filters.flag_names[flag] : flag;
}

/**
 * T4's three MoSPI pendency kinds (policy.PENDENCY_KINDS on the API side).
 * Mirrored as a literal list rather than derived from strings.json, unlike
 * FLAG_KEYS above: flag_names is a {slug: label} map, but the pendency block
 * keys its copy as late_sanction_label/open_past_one_year_label/
 * no_payment_label, not {slug: label}, so there is no object to read slugs
 * off of.
 */
export const PENDENCY_KINDS = ["late_sanction", "open_past_one_year", "no_payment_90_days"] as const;

export function isPendencyKind(value: string): value is (typeof PENDENCY_KINDS)[number] {
  return (PENDENCY_KINDS as readonly string[]).includes(value);
}

export function pendencyKindLabel(kind: string): string {
  const copy = STRINGS.pendency;
  switch (kind) {
    case "late_sanction":
      return copy.late_sanction_label;
    case "open_past_one_year":
      return copy.open_past_one_year_label;
    case "no_payment_90_days":
      return copy.no_payment_label;
    default:
      return kind;
  }
}

/** ALL plus the three kinds, for the Timeline SelectControl. No per-option
 *  count: unlike state/year/category/flag, pendency is not a
 *  /api/works/facets facet, and a fabricated count would be worse than none. */
export function pendencyOptions(): SelectOption[] {
  return [
    { value: ALL, label: STRINGS.pendency.filter_all },
    ...PENDENCY_KINDS.map((value) => ({ value, label: pendencyKindLabel(value) })),
  ];
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

/**
 * The scope-only params /api/works and /api/pendency both accept: repeatable
 * state, district_authority, constituency. fetchPendency (R3) sends only
 * this subset -- never year, category, flag, pendency, q or vendor_id -- so a
 * PendencyCards count always equals its matching Inspection List total. One
 * function so the two param names can never drift between the two callers.
 */
export function scopeQuery(f: Pick<FilterState, "states" | "districtAuthority" | "constituency">): URLSearchParams {
  const params = new URLSearchParams();
  for (const state of f.states) params.append("state", state);
  if (f.districtAuthority !== ALL) params.set("district_authority", f.districtAuthority);
  if (f.constituency !== ALL) params.set("constituency", f.constituency);
  return params;
}

/** The API query for a filter state: repeatable state, sentinels dropped. */
export function filtersToQuery(f: FilterState, q?: string | null, vendorId?: string | null): URLSearchParams {
  const params = scopeQuery(f);
  if (f.year !== ALL) params.set("year", f.year);
  if (f.category !== ALL) params.set("category", f.category);
  if (f.flag !== ALL) params.set("flag", f.flag);
  if (f.pendency !== ALL) params.set("pendency", f.pendency);
  if (vendorId) params.set("vendor_id", vendorId);
  const search = q?.trim();
  if (search) params.set("q", search.slice(0, MAX_QUERY_LENGTH));
  return params;
}

/** The Inspection List's address-bar form: the API query plus the page.
 *  vendorId is a link-in facet (arriving from a Fund Flow "View linked
 *  works" link), the same pattern Fund Flow's own agency/vendor deep links
 *  already use -- carried through the address bar, with no FilterPanel
 *  chip of its own. `view` rides along the same way: it is never sent to
 *  the API (filtersToQuery does not carry it, so fetchWorksPage/fetchPendency
 *  never see it), only round-tripped so a link built under one role lens
 *  (a PendencyCards card, "View the full inspection list") opens the list in
 *  that same lens. Omitted when it is the default, matching every other
 *  sentinel-valued param here. */
export function listSearchParams(
  f: FilterState,
  q: string | null,
  page: number,
  vendorId?: string | null,
): URLSearchParams {
  const params = filtersToQuery(f, q, vendorId);
  if (f.view !== EMPTY_FILTERS.view) params.set("view", f.view);
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
export function readListParams(
  params: ReadableParams,
): { filters: FilterState; q: string; page: number; vendorId: string | null } {
  const states = Array.from(new Set(params.getAll("state").map((s) => s.trim()).filter(Boolean))).slice(0, 64);
  const year = params.get("year")?.trim() || ALL;
  const category = params.get("category")?.trim() || ALL;
  const rawFlag = params.get("flag")?.trim() ?? "";
  const flag = isFlagType(rawFlag) ? rawFlag : ALL;
  const rawPendency = params.get("pendency")?.trim() ?? "";
  const pendency = isPendencyKind(rawPendency) ? rawPendency : ALL;
  const districtAuthority = params.get("district_authority")?.trim() || ALL;
  const constituency = params.get("constituency")?.trim() || ALL;
  const rawView = params.get("view")?.trim() ?? "";
  const view = isView(rawView) ? rawView : "ministry";
  const q = (params.get("q") ?? "").trim().slice(0, MAX_QUERY_LENGTH);
  const parsedPage = Number.parseInt(params.get("page") ?? "1", 10);
  const page = Number.isFinite(parsedPage) && parsedPage >= 1 ? parsedPage : 1;
  const vendorId = params.get("vendor_id")?.trim() || null;
  return { filters: { states, year, category, flag, pendency, districtAuthority, constituency, view }, q, page, vendorId };
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
