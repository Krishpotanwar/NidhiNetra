"use client";

import { renderTemplate, STRINGS } from "@/lib/strings";
import { formatDate, formatIndianInt } from "@/lib/format";
import { RefreshControl, type RefreshState } from "@/components/data-provenance/RefreshControl";
import styles from "./SummaryLine.module.css";

interface SummaryLineProps {
  totalN: number;
  quotaN: number;
  /** Rows on screen now. Given only where the page shows one slice from the
   *  top (the Dashboard); the paginated list says so in its pagination. */
  shownN?: number;
  q?: string;
  onClearSearch?: () => void;
  dataAsOf: string | null;
  recordCount: number | null;
  demoDataset?: boolean;
  refreshState: RefreshState;
  onRefresh: () => void;
}

/**
 * The sentence the reference sets above the table, plus the provenance line
 * PRD M6 requires: which snapshot this is, how many records it holds, and a
 * way to rebuild it. Provenance, not decoration.
 */
export function SummaryLine({
  totalN,
  quotaN,
  shownN,
  q,
  onClearSearch,
  dataAsOf,
  recordCount,
  demoDataset = false,
  refreshState,
  onRefresh,
}: SummaryLineProps) {
  const sentence =
    shownN === undefined
      ? renderTemplate(STRINGS.table.filtered_summary_short, {
          total_n: formatIndianInt(totalN),
          cutoff_rank: formatIndianInt(quotaN),
        })
      : renderTemplate(STRINGS.table.filtered_summary, {
          total_n: formatIndianInt(totalN),
          cutoff_rank: formatIndianInt(quotaN),
          shown_n: formatIndianInt(shownN),
        });

  const cached = STRINGS.data_states.showing_cached_data;
  const demo = cached.demo_dataset_variant;

  return (
    <div className={styles.line}>
      <p className={styles.sentence}>
        {q && (
          <>
            <span className={styles.match}>{renderTemplate(STRINGS.search.results_for, { q })}</span>{" "}
            {onClearSearch && (
              <button type="button" onClick={onClearSearch} className={styles.clear}>
                {STRINGS.search.clear}
              </button>
            )}{" "}
          </>
        )}
        {totalN > 0 && sentence}
      </p>
      <div className={styles.provenance}>
        {demoDataset ? (
          <span>
            <span className={styles.provenanceStrong}>{demo.label}</span> {demo.detail}
          </span>
        ) : (
          dataAsOf && (
            <span>
              {renderTemplate(cached.label, { date: formatDate(dataAsOf.slice(0, 10)) })}{" "}
              {recordCount !== null &&
                renderTemplate(cached.detail, { record_count: formatIndianInt(recordCount) })}
            </span>
          )
        )}
        <RefreshControl state={refreshState} lastGoodTime={dataAsOf} onRefresh={onRefresh} />
      </div>
    </div>
  );
}
