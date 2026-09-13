"use client";

import { Fragment, useRef } from "react";
import { ArrowUp } from "@phosphor-icons/react";
import { renderTemplate, STRINGS } from "@/lib/strings";
import {
  daysStale,
  displayName,
  formatCurrencyFull,
  formatIndianInt,
  formatRank,
  formatRiskScore,
  riskBand,
} from "@/lib/format";
import { workTitle } from "@/lib/data";
import type { InspectionRow } from "@/lib/types";
import type { RowTreatment } from "@/lib/preferences";
import { DotCanvas } from "@/components/shared/DotCanvas";
import { BandPill } from "./BandPill";
import { MissingField } from "./MissingField";
import styles from "./InspectionTable.module.css";

export type TableDataState = "loading" | "ready" | "empty" | "error";

const columns = STRINGS.table.columns;
const tips = STRINGS.table.column_tooltips;

interface InspectionTableProps {
  rows: InspectionRow[];
  /** The snapshot's own data_as_of, for Days stale: two officers reading the
   *  same snapshot on different days must see the same age. */
  asOf: string | null;
  dataState: TableDataState;
  rowTreatment: RowTreatment;
  selectedWorkId: string | null;
  onSelectRow: (row: InspectionRow) => void;
  onRetry?: () => void;
  filtered?: boolean;
  onClearFilters?: () => void;
  /** Rank at or below which a row is inside this year's quota. */
  quotaN: number;
  /** Works in the whole filter, so the cutoff divider is only drawn when
   *  there really are rows past it. */
  totalN: number;
  /** True while a newer filter is loading and these rows are the old ones. */
  stale?: boolean;
  skeletonRows?: number;
  caption: string;
}

export function InspectionTable({
  rows,
  asOf,
  dataState,
  rowTreatment,
  selectedWorkId,
  onSelectRow,
  onRetry,
  filtered = false,
  onClearFilters,
  quotaN,
  totalN,
  stale = false,
  skeletonRows = 8,
  caption,
}: InspectionTableProps) {
  const bodyRef = useRef<HTMLTableSectionElement>(null);

  const moveFocus = (from: HTMLElement, step: 1 | -1) => {
    const buttons = Array.from(bodyRef.current?.querySelectorAll<HTMLButtonElement>("[data-row-button]") ?? []);
    const index = buttons.indexOf(from as HTMLButtonElement);
    buttons[index + step]?.focus();
  };

  const allUnflagged = dataState === "ready" && rows.length > 0 && rows.every((row) => row.flags.length === 0);

  return (
    <div className={styles.card} data-treatment={rowTreatment} data-stale={stale || undefined}>
      {allUnflagged && <NoFlagsNotice />}
      <div className={styles.scroller}>
        <table className={styles.table}>
          <caption className="sr-only">{caption}</caption>
          <colgroup>
            <col className={styles.colRank} />
            <col />
            <col className={styles.colConstituency} />
            <col className={styles.colAgency} />
            <col className={styles.colAmount} />
            <col className={styles.colAmount} />
            <col className={styles.colDays} />
            <col className={styles.colRisk} />
            <col className={styles.colBand} />
          </colgroup>
          <thead>
            <tr>
              <th scope="col" aria-sort="ascending">
                <span className={styles.rankHead}>
                  {columns.rank}
                  <ArrowUp size={11} weight="bold" aria-hidden="true" />
                </span>
                <span className="sr-only">{STRINGS.table.rank_order_hint}</span>
              </th>
              <th scope="col">{columns.work}</th>
              <th scope="col">{columns.district}</th>
              <th scope="col">{columns.agency}</th>
              <th scope="col" className={styles.num}>
                {columns.sanctioned}
              </th>
              <th scope="col" className={styles.num}>
                {columns.spent}
              </th>
              <th scope="col" className={styles.num} title={tips.days_stale}>
                {columns.days_stale}
              </th>
              <th scope="col" className={styles.num} title={tips.risk}>
                {columns.risk}
              </th>
              <th scope="col">
                <span className="sr-only">{STRINGS.table.band_column}</span>
              </th>
            </tr>
          </thead>
          <tbody ref={bodyRef}>
            {dataState === "loading" &&
              Array.from({ length: skeletonRows }).map((_, index) => <SkeletonRow key={index} />)}

            {dataState === "ready" &&
              rows.map((row) => (
                <Fragment key={row.work_id}>
                  <Row
                    row={row}
                    asOf={asOf}
                    selected={selectedWorkId === row.work_id}
                    insideQuota={row.displayRank <= quotaN}
                    onSelect={onSelectRow}
                    onMoveFocus={moveFocus}
                  />
                  {row.displayRank === quotaN && quotaN < totalN && <CutoffRow quotaN={quotaN} />}
                </Fragment>
              ))}
          </tbody>
        </table>
      </div>

      {dataState === "loading" && (
        <span className="sr-only" role="status">
          {STRINGS.data_states.loading.screen_reader}
        </span>
      )}
      {dataState === "empty" && <EmptyState filtered={filtered} onClearFilters={onClearFilters} />}
      {dataState === "error" && <ErrorState onRetry={onRetry} />}
    </div>
  );
}

function Row({
  row,
  asOf,
  selected,
  insideQuota,
  onSelect,
  onMoveFocus,
}: {
  row: InspectionRow;
  asOf: string | null;
  selected: boolean;
  insideQuota: boolean;
  onSelect: (row: InspectionRow) => void;
  onMoveFocus: (from: HTMLElement, step: 1 | -1) => void;
}) {
  const band = riskBand(row.risk_score, row.flags);
  const reason = Object.values(row.why_flagged).join(" ");
  const stalled = row.flags.includes("stalled_work");

  return (
    <tr
      className={styles.row}
      data-band={band}
      data-selected={selected || undefined}
      onClick={() => onSelect(row)}
    >
      <td className={`${styles.rank} ${insideQuota ? styles.rankQuota : ""}`}>{formatRank(row.displayRank)}</td>
      <td className={styles.work}>
        <button
          type="button"
          data-row-button
          className={styles.workButton}
          aria-haspopup="dialog"
          aria-expanded={selected}
          onClick={(event) => {
            event.stopPropagation();
            onSelect(row);
          }}
          onKeyDown={(event) => {
            if (event.key === "ArrowDown") {
              event.preventDefault();
              onMoveFocus(event.currentTarget, 1);
            } else if (event.key === "ArrowUp") {
              event.preventDefault();
              onMoveFocus(event.currentTarget, -1);
            }
          }}
        >
          {workTitle(row)}
        </button>
        {reason && (
          <div className={styles.reasonWrap}>
            <p className={`t-reason ${styles.reason}`}>{reason}</p>
          </div>
        )}
      </td>
      <td className={styles.muted}>{displayName(row.constituency)}</td>
      <td className={styles.agency} title={row.implementing_agency ?? undefined}>
        {row.implementing_agency ? (
          <span className={styles.clamp}>{displayName(row.implementing_agency)}</span>
        ) : (
          <MissingField field="agency" />
        )}
      </td>
      <td className={styles.num}>
        <Amount value={row.sanctioned_amount_inr} />
      </td>
      <td className={styles.num}>
        <Amount value={row.expenditure_amount_inr} />
      </td>
      <td className={`${styles.num} ${styles.days}`} data-stalled={stalled || undefined}>
        {asOf ? formatIndianInt(daysStale(row.last_updated, asOf)) : <MissingField field="generic" />}
      </td>
      <td className={`${styles.num} ${styles.score}`}>{formatRiskScore(row.risk_score)}</td>
      <td className={styles.bandCell}>
        <BandPill band={band} />
      </td>
    </tr>
  );
}

function Amount({ value }: { value: number | null }) {
  if (value === null) {
    return (
      <span className={styles.missing}>
        <MissingField field="amount" />
      </span>
    );
  }
  return <span className="t-num">{formatCurrencyFull(value)}</span>;
}

/** Where this year's ten percent ends, drawn in the table itself. */
function CutoffRow({ quotaN }: { quotaN: number }) {
  return (
    <tr className={styles.cutoffRow}>
      <td colSpan={9}>
        <span className={styles.cutoffLabel}>
          {renderTemplate(STRINGS.quota_meter.cutoff_marker, { cutoff_rank: formatIndianInt(quotaN) })}
        </span>
      </td>
    </tr>
  );
}

function SkeletonRow() {
  return (
    <tr className={styles.skeletonRow} aria-hidden="true">
      <td>
        <span className={styles.skeleton} style={{ width: "1.5rem" }} />
      </td>
      <td>
        <span className={styles.skeleton} style={{ width: "60%" }} />
        <span className={`${styles.skeleton} ${styles.skeletonReason}`} style={{ width: "80%" }} />
      </td>
      <td>
        <span className={styles.skeleton} style={{ width: "70%" }} />
      </td>
      <td>
        <span className={styles.skeleton} style={{ width: "85%" }} />
      </td>
      <td>
        <span className={`${styles.skeleton} ${styles.skeletonRight}`} style={{ width: "70%" }} />
      </td>
      <td>
        <span className={`${styles.skeleton} ${styles.skeletonRight}`} style={{ width: "70%" }} />
      </td>
      <td>
        <span className={`${styles.skeleton} ${styles.skeletonRight}`} style={{ width: "50%" }} />
      </td>
      <td>
        <span className={`${styles.skeleton} ${styles.skeletonRight}`} style={{ width: "50%" }} />
      </td>
      <td>
        <span className={styles.skeleton} style={{ width: "80%" }} />
      </td>
    </tr>
  );
}

function EmptyState({ filtered, onClearFilters }: { filtered: boolean; onClearFilters?: () => void }) {
  const copy = STRINGS.data_states.empty_after_filter;
  return (
    <DotCanvas className={styles.state}>
      <p className={styles.stateTitle}>{copy.title}</p>
      <p className={styles.stateBody}>{copy.body}</p>
      {filtered && onClearFilters && (
        <button type="button" onClick={onClearFilters} className={styles.stateAction}>
          {copy.action}
        </button>
      )}
    </DotCanvas>
  );
}

function ErrorState({ onRetry }: { onRetry?: () => void }) {
  const copy = STRINGS.data_states.api_unreachable;
  return (
    <DotCanvas className={styles.state}>
      <p className={styles.stateTitle}>{copy.title}</p>
      <p className={styles.stateBody}>{copy.body}</p>
      {onRetry && (
        <button type="button" onClick={onRetry} className={styles.stateAction}>
          {copy.action}
        </button>
      )}
    </DotCanvas>
  );
}

/** The filter returned works, but none of them are flagged. A distinct state
 *  from returning nothing: silence here would read as "these came back clean". */
function NoFlagsNotice() {
  const copy = STRINGS.data_states.empty_after_filter.no_flags_variant;
  return (
    <div className={styles.notice}>
      <p className={styles.noticeTitle}>{copy.title}</p>
      <p className={styles.noticeBody}>{copy.body}</p>
    </div>
  );
}
