"use client";

import { useCallback, useMemo, useState } from "react";
import Link from "next/link";
import { ArrowRight } from "@phosphor-icons/react";
import { STRINGS } from "@/lib/strings";
import {
  fetchFacets,
  fetchSummary,
  fetchWorksPage,
  getSummaryFigures,
  isDemoDataset,
  triggerRefresh,
  ApiUnreachableError,
} from "@/lib/data";
import { EMPTY_FILTERS, inspectionListHref, type FilterState } from "@/lib/filters";
import { useApiResource } from "@/lib/use-api-resource";
import { useRowTreatment } from "@/lib/preferences";
import type { InspectionRow } from "@/lib/types";
import { KpiCards } from "./KpiCards";
import { QuotaCard, QuotaCardSkeleton } from "./QuotaCard";
import { FilterPanel, type PreviewState } from "@/components/filters/FilterPanel";
import { SummaryLine } from "@/components/inspection-list/SummaryLine";
import { InspectionTable, type TableDataState } from "@/components/inspection-list/InspectionTable";
import { DetailPanel } from "@/components/detail-panel/DetailPanel";
import type { RefreshState } from "@/components/data-provenance/RefreshControl";
import styles from "./DashboardClient.module.css";

/** The reference shows the top of the queue, not the whole queue: the full
 *  list, paginated, is one click away. */
const DASHBOARD_ROWS = 20;

export function DashboardClient() {
  const [filters, setFilters] = useState<FilterState>(EMPTY_FILTERS);
  const [selected, setSelected] = useState<InspectionRow | null>(null);
  const [preview, setPreview] = useState<PreviewState>("loaded");
  const [refreshState, setRefreshState] = useState<RefreshState>("idle");
  const treatment = useRowTreatment();

  const loadSummary = useCallback((signal: AbortSignal) => fetchSummary(signal), []);
  const loadFacets = useCallback((signal: AbortSignal) => fetchFacets(signal), []);
  const request = useMemo(
    () => ({ filters, q: null, page: 1, pageSize: DASHBOARD_ROWS }),
    [filters],
  );
  const loadWorks = useCallback((signal: AbortSignal) => fetchWorksPage(request, signal), [request]);

  const summary = useApiResource(loadSummary);
  const facets = useApiResource(loadFacets);
  const works = useApiResource(loadWorks);

  const figures = summary.data ? getSummaryFigures(summary.data) : null;
  const page = works.data;

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
        // Never render err.message: the server's rate-limit text is not
        // contract-approved copy (lib/data.ts triggerRefresh).
        if (!(err instanceof ApiUnreachableError)) console.error("Unexpected error refreshing", err);
        setRefreshState("failed");
      });
  }, [refreshState, summary, facets, works]);

  const dataState: TableDataState =
    preview === "loading" ? "loading" : preview === "empty" ? "empty" : !page
      ? works.status === "error"
        ? "error"
        : "loading"
      : page.rows.length === 0
        ? "empty"
        : "ready";

  return (
    <>
      <div className="page">
        <KpiCards figures={figures} status={summary.status} onRetry={summary.reload} />

        <div className={styles.stack}>
          {page && page.total > 0 ? (
            <QuotaCard
              totalN={page.total}
              quotaN={page.quotaN}
              flaggedTotal={page.flaggedTotal}
              flaggedBeyondQuota={page.flaggedBeyondQuota}
              stale={works.stale}
            />
          ) : (
            !page && works.status !== "error" && <QuotaCardSkeleton />
          )}

          <FilterPanel
            value={filters}
            onChange={setFilters}
            facets={facets.data}
            previewState={preview}
            onPreviewStateChange={setPreview}
          />

          <SummaryLine
            totalN={page?.total ?? 0}
            quotaN={page?.quotaN ?? 0}
            shownN={page?.rows.length ?? 0}
            dataAsOf={summary.data?.data_as_of ?? null}
            recordCount={summary.data?.total_works_all_statuses ?? null}
            demoDataset={isDemoDataset(page?.rows ?? [])}
            refreshState={refreshState}
            onRefresh={handleRefresh}
          />

          <InspectionTable
            caption={STRINGS.dashboard.table_title}
            rows={page?.rows ?? []}
            asOf={summary.data?.data_as_of ?? null}
            dataState={dataState}
            rowTreatment={treatment}
            selectedWorkId={selected?.work_id ?? null}
            onSelectRow={setSelected}
            onRetry={works.reload}
            filtered={filters.states.length > 0}
            onClearFilters={() => setFilters(EMPTY_FILTERS)}
            quotaN={page?.quotaN ?? 0}
            totalN={page?.total ?? 0}
            stale={works.stale}
            skeletonRows={6}
          />

          <div className={styles.footer}>
            <Link href={inspectionListHref(filters)} className={styles.more}>
              {STRINGS.dashboard.view_full_list}
              <ArrowRight size={15} weight="bold" aria-hidden="true" />
            </Link>
            <p className={styles.standing}>{STRINGS.framing.standing_note}</p>
          </div>
        </div>
      </div>

      <DetailPanel row={selected} onClose={() => setSelected(null)} quotaN={page?.quotaN ?? 0} />
    </>
  );
}
