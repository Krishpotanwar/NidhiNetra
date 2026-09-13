"use client";

import { useCallback, useMemo, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { STRINGS } from "@/lib/strings";
import {
  ApiUnreachableError,
  fetchFacets,
  fetchSummary,
  fetchWorksPage,
  isDemoDataset,
  triggerRefresh,
} from "@/lib/data";
import { EMPTY_FILTERS, listSearchParams, readListParams, type FilterState } from "@/lib/filters";
import { useApiResource } from "@/lib/use-api-resource";
import { useRowTreatment } from "@/lib/preferences";
import type { InspectionRow } from "@/lib/types";
import { FilterPanel, type PreviewState } from "@/components/filters/FilterPanel";
import { DetailPanel } from "@/components/detail-panel/DetailPanel";
import type { RefreshState } from "@/components/data-provenance/RefreshControl";
import { InspectionTable, type TableDataState } from "./InspectionTable";
import { Pagination } from "./Pagination";
import { SummaryLine } from "./SummaryLine";
import styles from "./InspectionListClient.module.css";

const PAGE_SIZE = 50;

/**
 * The whole national queue, paginated. Filters, the search and the page all
 * live in the address bar, so a filtered view is a link an officer can send
 * and the browser's back button does what it should.
 */
export function InspectionListClient() {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const { filters, q, page } = useMemo(() => readListParams(params), [params]);

  const [selected, setSelected] = useState<InspectionRow | null>(null);
  const [preview, setPreview] = useState<PreviewState>("loaded");
  const [refreshState, setRefreshState] = useState<RefreshState>("idle");
  const treatment = useRowTreatment();

  const navigate = useCallback(
    (next: FilterState, nextQ: string, nextPage: number) => {
      const qs = listSearchParams(next, nextQ, nextPage).toString();
      router.push(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
    },
    [pathname, router],
  );

  const loadSummary = useCallback((signal: AbortSignal) => fetchSummary(signal), []);
  const loadFacets = useCallback((signal: AbortSignal) => fetchFacets(signal), []);
  const request = useMemo(() => ({ filters, q, page, pageSize: PAGE_SIZE }), [filters, q, page]);
  const loadWorks = useCallback((signal: AbortSignal) => fetchWorksPage(request, signal), [request]);

  const summary = useApiResource(loadSummary);
  const facets = useApiResource(loadFacets);
  const works = useApiResource(loadWorks);
  const result = works.data;

  const handleRefresh = useCallback(() => {
    if (refreshState === "refreshing") return;
    setRefreshState("refreshing");
    triggerRefresh()
      .then(() => {
        summary.reload();
        facets.reload();
        works.reload();
        setRefreshState("idle");
      })
      .catch((err: unknown) => {
        if (!(err instanceof ApiUnreachableError)) console.error("Unexpected error refreshing", err);
        setRefreshState("failed");
      });
  }, [refreshState, summary, facets, works]);

  const dataState: TableDataState =
    preview === "loading" ? "loading" : preview === "empty" ? "empty" : !result
      ? works.status === "error"
        ? "error"
        : "loading"
      : result.rows.length === 0
        ? "empty"
        : "ready";

  const filtered = filters.states.length > 0 || filters.year !== EMPTY_FILTERS.year || Boolean(q);

  return (
    <>
      <div className={`page ${styles.stack}`}>
        <FilterPanel
          value={filters}
          onChange={(next) => navigate(next, q, 1)}
          facets={facets.data}
          previewState={preview}
          onPreviewStateChange={setPreview}
        />

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

        <p className={styles.standing}>{STRINGS.framing.standing_note}</p>
      </div>

      <DetailPanel row={selected} onClose={() => setSelected(null)} quotaN={result?.quotaN ?? 0} />
    </>
  );
}
