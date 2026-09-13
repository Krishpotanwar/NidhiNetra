/**
 * Data access for every view.
 *
 * 2026-09-11: filtering, counting, the quota and pagination all happen on
 * the server now. Nothing here derives a population figure from a page of
 * rows, which is how the summary strip once read "200 of 200 works" against
 * a real 44,810 (Logbook, 2026-09-04). API_BASE is overridable via
 * NEXT_PUBLIC_API_BASE_URL; see lib/api-client.ts.
 */
import type { Facets, InspectionRow, InspectionsReport, NormalizedRecord } from "./types";
import { ApiUnreachableError, fetchEnvelope, fetchEnvelopeWithMeta } from "./api-client";
import { filtersToQuery, type FilterState } from "./filters";
import { displayName } from "./format";

export { ApiUnreachableError };

/** Raw shape /api/works returns per row: NormalizedRecord + RiskScoredRecord,
 *  already merged server-side (see api/routers/works.py). */
type ApiWorkRow = Omit<InspectionRow, "displayRank">;

/** GET /api/stats/summary. Every figure is computed server-side across the
 *  whole snapshot, never from the rows a table happens to have fetched. */
export interface ApiSummary {
  works_under_implementation: number;
  flagged_count: number;
  total_flagged_amount_inr: number;
  idle_beyond_12_months_amount_inr: number;
  total_works_all_statuses: number;
  idle_work_count: number;
  total_sanctioned_under_implementation_inr: number;
  state_count: number;
  constituency_count: number;
  data_as_of: string;
}

export interface WorksPageRequest {
  filters: FilterState;
  q?: string | null;
  page: number;
  pageSize: number;
}

export interface WorksPage {
  rows: InspectionRow[];
  page: number;
  pageSize: number;
  /** Works under implementation in this filter, across every page. */
  total: number;
  totalPages: number;
  /** The ten percent quota over `total`, owned by the API's policy module. */
  quotaN: number;
  flaggedTotal: number;
  flaggedBeyondQuota: number;
}

function metaCount(meta: Record<string, unknown> | null, key: string, fallback = 0): number {
  const value = meta?.[key];
  return typeof value === "number" && Number.isFinite(value) && value >= 0 ? value : fallback;
}

/**
 * One page of the ranked queue, scoped to the District Authority population.
 * displayRank is the row's position in the filtered queue across all pages
 * (1..total, no gaps), which is what the quota cutoff is measured against.
 */
export async function fetchWorksPage(request: WorksPageRequest, signal?: AbortSignal): Promise<WorksPage> {
  const params = filtersToQuery(request.filters, request.q);
  params.set("scope", "under_implementation");
  params.set("page", String(request.page));
  params.set("page_size", String(request.pageSize));
  const { data, meta } = await fetchEnvelopeWithMeta<ApiWorkRow[]>(`/api/works?${params.toString()}`, { signal });
  const page = metaCount(meta, "page", request.page) || request.page;
  const pageSize = metaCount(meta, "page_size", request.pageSize) || request.pageSize;
  const offset = (page - 1) * pageSize;
  const rows = (Array.isArray(data) ? data : []).map((row, i) => ({ ...row, displayRank: offset + i + 1 }));
  return {
    rows,
    page,
    pageSize,
    total: metaCount(meta, "total"),
    totalPages: metaCount(meta, "total_pages"),
    quotaN: metaCount(meta, "quota_n"),
    flaggedTotal: metaCount(meta, "flagged_total"),
    flaggedBeyondQuota: metaCount(meta, "flagged_beyond_quota"),
  };
}

export function fetchFacets(signal?: AbortSignal): Promise<Facets> {
  return fetchEnvelope<Facets>("/api/works/facets", { signal });
}

export function fetchSummary(signal?: AbortSignal): Promise<ApiSummary> {
  return fetchEnvelope<ApiSummary>("/api/stats/summary", { signal });
}

export function fetchInspectionsReport(signal?: AbortSignal): Promise<InspectionsReport> {
  return fetchEnvelope<InspectionsReport>("/api/inspections", { signal });
}

/**
 * POST /api/refresh. Server-side rate limit is 30s (api/routers/refresh.py).
 * A refusal throws ApiUnreachableError carrying the server's own English as
 * .message, which is deliberately NOT surfaced: that text is not from
 * contracts/strings.json. The caller renders refresh_failed's copy for the
 * whole failure class.
 */
export async function triggerRefresh(): Promise<void> {
  await fetchEnvelope<Record<string, unknown>>("/api/refresh", { method: "POST" });
}

/**
 * normalized_record.schema.json has no free-text work title field, so the
 * row's headline is composed from the two fields that identify the work: its
 * category and where it sits. Every word is the record's own value; the
 * constituency is only re-cased for reading (lib/format.ts displayName).
 */
export function workTitle(record: Pick<NormalizedRecord, "work_category" | "constituency">): string {
  return `${record.work_category} work, ${displayName(record.constituency)}`;
}

/** True when every row is the hand-curated seed set (source_rung 5), which
 *  must be labelled in the UI as a demo dataset (Execution Plan, rung 5). */
export function isDemoDataset(rows: Pick<NormalizedRecord, "source_rung">[]): boolean {
  return rows.length > 0 && rows.every((r) => r.source_rung === 5);
}

export interface SummaryFigures {
  worksUnderImplementation: number;
  totalWorksAllStatuses: number;
  flaggedForInspection: number;
  flaggedPercent: number;
  valueUnderFlaggedInr: number;
  valueUnderFlaggedPercentOfSanctioned: number;
  averageFlaggedInr: number;
  idleBeyond12MonthsInr: number;
  idleWorkCount: number;
  stateCount: number;
  constituencyCount: number;
}

export function getSummaryFigures(summary: ApiSummary): SummaryFigures {
  const underImpl = summary.works_under_implementation;
  const flagged = summary.flagged_count;
  const totalSanctioned = summary.total_sanctioned_under_implementation_inr;
  return {
    worksUnderImplementation: underImpl,
    totalWorksAllStatuses: summary.total_works_all_statuses,
    flaggedForInspection: flagged,
    flaggedPercent: underImpl > 0 ? (flagged / underImpl) * 100 : 0,
    valueUnderFlaggedInr: summary.total_flagged_amount_inr,
    valueUnderFlaggedPercentOfSanctioned:
      totalSanctioned > 0 ? (summary.total_flagged_amount_inr / totalSanctioned) * 100 : 0,
    averageFlaggedInr: flagged > 0 ? summary.total_flagged_amount_inr / flagged : 0,
    idleBeyond12MonthsInr: summary.idle_beyond_12_months_amount_inr,
    idleWorkCount: summary.idle_work_count,
    stateCount: summary.state_count,
    constituencyCount: summary.constituency_count,
  };
}
