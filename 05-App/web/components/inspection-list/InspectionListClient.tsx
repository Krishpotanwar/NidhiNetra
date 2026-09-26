"use client";

import { useCallback, useMemo, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { renderTemplate, STRINGS } from "@/lib/strings";
import {
  ApiUnreachableError,
  fetchEarlyWarning,
  fetchFacets,
  fetchPendency,
  fetchSummary,
  fetchWorksPage,
  isDemoDataset,
  triggerRefresh,
} from "@/lib/data";
import { EMPTY_FILTERS, isLensScoped, listSearchParams, readListParams, type FilterState } from "@/lib/filters";
import { formatDate } from "@/lib/format";
import { useApiResource } from "@/lib/use-api-resource";
import { useRowTreatment } from "@/lib/preferences";
import type { InspectionRow } from "@/lib/types";
import { DutyLine } from "@/components/dashboard/DutyLine";
import { FilterPanel, type PreviewState } from "@/components/filters/FilterPanel";
import { DetailPanel } from "@/components/detail-panel/DetailPanel";
import type { RefreshState } from "@/components/data-provenance/RefreshControl";
import { DuplicateReviewQueue } from "./DuplicateReviewQueue";
import { InspectionTable, type TableDataState } from "./InspectionTable";
import { Pagination } from "./Pagination";
import { SummaryLine } from "./SummaryLine";
import styles from "./InspectionListClient.module.css";

const PAGE_SIZE = 50;
/** T7: once an officer has picked a District Authority, one page must hold
 *  its whole quota for printing -- the largest today is 82 (global context's
 *  verified numbers), so 100 covers every authority with room to spare. */
const DISTRICT_AUTHORITY_PAGE_SIZE = 100;

/**
 * The whole national queue, paginated. Filters, the search and the page all
 * live in the address bar, so a filtered view is a link an officer can send
 * and the browser's back button does what it should.
 */
export function InspectionListClient() {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const { filters, q, page, vendorId } = useMemo(() => readListParams(params), [params]);

  const [selected, setSelected] = useState<InspectionRow | null>(null);
  const [preview, setPreview] = useState<PreviewState>("loaded");
  const [refreshState, setRefreshState] = useState<RefreshState>("idle");
  const treatment = useRowTreatment();

  // vendorId (a "View linked works" deep link, not a FilterPanel chip) rides
  // along on every navigation unchanged -- the same address-bar-only pattern
  // Fund Flow's own agency/vendor deep links already use.
  const navigate = useCallback(
    (next: FilterState, nextQ: string, nextPage: number) => {
      const qs = listSearchParams(next, nextQ, nextPage, vendorId).toString();
      router.push(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
    },
    [pathname, router, vendorId],
  );

  const loadSummary = useCallback((signal: AbortSignal) => fetchSummary(signal), []);
  const loadFacets = useCallback((signal: AbortSignal) => fetchFacets(signal), []);
  const loadPendency = useCallback((signal: AbortSignal) => fetchPendency(filters, signal), [filters]);
  const loadEarlyWarning = useCallback((signal: AbortSignal) => fetchEarlyWarning(signal), []);
  const pageSize = filters.districtAuthority === EMPTY_FILTERS.districtAuthority ? PAGE_SIZE : DISTRICT_AUTHORITY_PAGE_SIZE;
  const request = useMemo(
    () => ({ filters, q, page, pageSize, vendorId }),
    [filters, q, page, pageSize, vendorId],
  );
  const loadWorks = useCallback((signal: AbortSignal) => fetchWorksPage(request, signal), [request]);

  const summary = useApiResource(loadSummary);
  const facets = useApiResource(loadFacets);
  const pendency = useApiResource(loadPendency);
  const earlyWarning = useApiResource(loadEarlyWarning);
  const works = useApiResource(loadWorks);
  const result = works.data;

  const handleRefresh = useCallback(() => {
    if (refreshState === "refreshing") return;
    setRefreshState("refreshing");
    triggerRefresh()
      .then(() => {
        summary.reload();
        facets.reload();
        pendency.reload();
        works.reload();
        setRefreshState("idle");
      })
      .catch((err: unknown) => {
        if (!(err instanceof ApiUnreachableError)) console.error("Unexpected error refreshing", err);
        setRefreshState("failed");
      });
  }, [refreshState, summary, facets, pendency, works]);

  const dataState: TableDataState =
    preview === "loading" ? "loading" : preview === "empty" ? "empty" : !result
      ? works.status === "error"
        ? "error"
        : "loading"
      : result.rows.length === 0
        ? "empty"
        : "ready";

  // R22 (Task 5 review, carried to T7): a District Authority, constituency or
  // pendency lens narrows the list exactly like a state or year filter does,
  // so the empty state's "Clear filters" button must offer to clear those
  // too -- otherwise an officer scoped to an authority with zero matching
  // works sees a dead end with no way back.
  const filtered =
    filters.states.length > 0 ||
    filters.year !== EMPTY_FILTERS.year ||
    filters.pendency !== EMPTY_FILTERS.pendency ||
    filters.districtAuthority !== EMPTY_FILTERS.districtAuthority ||
    filters.constituency !== EMPTY_FILTERS.constituency ||
    Boolean(q);

  // T7: the print-only header reuses DutyLine itself (same props as the
  // on-screen call below) rather than a second copy of its sentence switch,
  // plus the snapshot's own as-of date and the standing note -- everything
  // an officer needs on a printed page with no nav, filters or detail panel.
  const dutyPendency = isLensScoped(filters) ? pendency.data : null;
  const asOf = summary.data?.data_as_of ?? null;

  return (
    <>
      <div className={`page ${styles.stack}`}>
        <div className="print-only">
          <DutyLine view={filters.view} pendency={dutyPendency} />
          {asOf && <p>{renderTemplate(STRINGS.print.as_of, { date: formatDate(asOf.slice(0, 10)) })}</p>}
          <p>{STRINGS.framing.standing_note}</p>
        </div>

        <div data-print="hide">
          <FilterPanel
            value={filters}
            onChange={(next) => navigate(next, q, 1)}
            facets={facets.data}
            previewState={preview}
            onPreviewStateChange={setPreview}
            earlyWarningAvailable={earlyWarning.data !== null}
          />
        </div>

        <button type="button" data-print="hide" className={styles.printButton} onClick={() => window.print()}>
          {STRINGS.print.button}
        </button>

        {/* Screen-only: the print-only header above already states the same
            duty sentence and as-of date, and Refresh Now does nothing on
            paper. styles.stack (not just a bare div) keeps the same gap
            between SummaryLine and DutyLine that .stack gave them as direct
            siblings before this wrapper existed. */}
        <div data-print="hide" className={styles.stack}>
          <SummaryLine
            totalN={result?.total ?? 0}
            quotaN={result?.quotaN ?? 0}
            q={q || undefined}
            onClearSearch={() => navigate(filters, "", 1)}
            dataAsOf={summary.data?.data_as_of ?? null}
            recordCount={summary.data?.total_works_all_statuses ?? null}
            demoDataset={isDemoDataset(result?.rows ?? [])}
            refreshState={refreshState}
            onRefresh={handleRefresh}
          />
          <DutyLine view={filters.view} pendency={dutyPendency} />
        </div>

        <InspectionTable
          caption={STRINGS.nav.inspection_list}
          rows={result?.rows ?? []}
          asOf={summary.data?.data_as_of ?? null}
          dataState={dataState}
          rowTreatment={treatment}
          selectedWorkId={selected?.work_id ?? null}
          onSelectRow={setSelected}
          onRetry={works.reload}
          filtered={filtered}
          onClearFilters={() => navigate(EMPTY_FILTERS, "", 1)}
          quotaN={result?.quotaN ?? 0}
          totalN={result?.total ?? 0}
          stale={works.stale}
          skeletonRows={10}
        />

        {result && (
          <Pagination
            page={result.page}
            totalPages={result.totalPages}
            totalN={result.total}
            pageSize={result.pageSize}
            quotaN={result.quotaN}
            onPage={(next) => navigate(filters, q, next)}
          />
        )}

        {/* Screen-only: a national review queue, unscoped to this District
            Authority -- no part of one authority's own inspection plan. */}
        <div data-print="hide">
          <DuplicateReviewQueue />
        </div>

        <p className={styles.standing}>{STRINGS.framing.standing_note}</p>
      </div>

      <div data-print="hide">
        <DetailPanel row={selected} onClose={() => setSelected(null)} quotaN={result?.quotaN ?? 0} />
      </div>
    </>
  );
}
