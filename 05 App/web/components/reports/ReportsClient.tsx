"use client";

import { useCallback } from "react";
import Link from "next/link";
import { ArrowRight } from "@phosphor-icons/react";
import { renderTemplate, STRINGS } from "@/lib/strings";
import { fetchInspectionsReport } from "@/lib/data";
import { useApiResource } from "@/lib/use-api-resource";
import { displayName, formatDate, formatIndianInt, formatPercent } from "@/lib/format";
import type { GroupSummary, InspectionOutcome } from "@/lib/types";
import styles from "./ReportsClient.module.css";

const copy = STRINGS.reports;
const outcomes = STRINGS.inspection_capture.outcome_options as Record<string, string>;

/**
 * What the recorded inspections say so far. Rates are shown per group only
 * once that group has enough inspections that reached the work; below that
 * the page says how many more are needed rather than showing a number that
 * would move on the next entry.
 */
export function ReportsClient() {
  const load = useCallback((signal: AbortSignal) => fetchInspectionsReport(signal), []);
  const report = useApiResource(load);

  if (report.status === "error" && !report.data) {
    const error = STRINGS.data_states.api_unreachable;
    return (
      <div className={`page ${styles.stack}`}>
        <section className={styles.card}>
          <p className={styles.stateTitle}>{error.title}</p>
          <p className={styles.stateBody}>{error.body}</p>
          <button type="button" className={styles.action} onClick={report.reload}>
            {error.action}
          </button>
        </section>
      </div>
    );
  }

  const data = report.data;
  const summary = data?.summary;
  const need = summary?.min_reached_per_group ?? 0;
  const amended = data ? data.outcomes.filter((outcome) => outcome.superseded).length : 0;

  return (
    <div className={`page ${styles.stack}`}>
      <section className={styles.figures} aria-busy={!data}>
        <article className={styles.figureCard}>
          <p className={styles.figure}>{data ? formatIndianInt(summary?.total ?? 0) : ""}</p>
          <p className="t-label">{copy.recorded}</p>
          {amended > 0 && (
            <p className={styles.figureNote}>
              {renderTemplate(copy.amended_context, { amended_n: formatIndianInt(amended) })}
            </p>
          )}
        </article>
        <GroupCard title={copy.ranked_group} group={summary?.ranked} need={need} />
        <GroupCard title={copy.spot_group} group={summary?.spot_check} need={need} />
      </section>

      <section className={styles.card}>
        <h2 className={styles.cardTitle}>{copy.comparison_title}</h2>
        {summary?.comparison_ready && summary.ranked.issue_rate && summary.spot_check.issue_rate ? (
          <p className={styles.comparison}>
            {renderTemplate(copy.comparison_ready, {
              ranked: formatPercent(summary.ranked.issue_rate.value * 100, "word").replace(" percent", ""),
              spot: formatPercent(summary.spot_check.issue_rate.value * 100, "word").replace(" percent", ""),
            })}
          </p>
        ) : (
          <p className={styles.comparison}>
            {renderTemplate(copy.comparison_waiting, { need: formatIndianInt(need) })}
          </p>
        )}
        <p className={styles.method}>{copy.method}</p>
      </section>

      <section className={styles.card}>
        <h2 className={styles.cardTitle}>{copy.table_title}</h2>
        {data && data.outcomes.length === 0 ? (
          <div className={styles.empty}>
            <p className={styles.stateTitle}>{copy.empty_title}</p>
            <p className={styles.stateBody}>{copy.empty_body}</p>
            <Link href="/inspections" className={styles.action}>
              {copy.empty_action}
              <ArrowRight size={14} weight="bold" aria-hidden="true" />
            </Link>
          </div>
        ) : (
          <div className={styles.scroller}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th scope="col">{copy.col_date}</th>
                  <th scope="col">{copy.col_work}</th>
                  <th scope="col" className={styles.num}>
                    {copy.col_rank}
                  </th>
                  <th scope="col">{copy.col_outcome}</th>
                  <th scope="col">{copy.col_group}</th>
                  <th scope="col">{copy.col_inspector}</th>
                </tr>
              </thead>
              <tbody>
                {(data?.outcomes ?? []).map((outcome) => (
                  <OutcomeRow key={outcome.outcome_id} outcome={outcome} />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}

function GroupCard({ title, group, need }: { title: string; group: GroupSummary | undefined; need: number }) {
  const rate = group?.issue_rate;
  return (
    <article className={styles.figureCard}>
      <p className={styles.figure}>{group ? formatIndianInt(group.n) : ""}</p>
      <p className="t-label">{title}</p>
      {group && (
        <>
          <p className={styles.figureNote}>
            {renderTemplate(copy.reached, { n: formatIndianInt(group.reached_work) })}
          </p>
          <p className={styles.figureNote}>
            {renderTemplate(copy.within_quota, { n: formatIndianInt(group.within_quota) })}
          </p>
          <p className={styles.rateRow}>
            <span className="t-label">{copy.issue_rate}</span>
            {rate ? (
              <span className={styles.rateValue}>
                {renderTemplate(copy.rate_value, { percent: Math.round(rate.value * 100) })}
                <span className={styles.interval}>
                  {renderTemplate(copy.interval, {
                    low: Math.round(rate.low * 100),
                    high: Math.round(rate.high * 100),
                  })}
                </span>
              </span>
            ) : (
              <span className={styles.pending}>
                {renderTemplate(copy.not_enough, {
                  need: formatIndianInt(need),
                  have: formatIndianInt(group.reached_work),
                })}
              </span>
            )}
          </p>
        </>
      )}
    </article>
  );
}

function OutcomeRow({ outcome }: { outcome: InspectionOutcome }) {
  const inside = outcome.inspection_rank_at_time <= outcome.cutoff_rank_at_time;
  return (
    <tr className={styles.row} data-superseded={outcome.superseded || undefined}>
      <td>{formatDate(outcome.inspected_on)}</td>
      <td>
        <span className={styles.work}>
          {outcome.work_category}, {displayName(outcome.constituency)}
        </span>
        {outcome.superseded && <span className={styles.amended}>{copy.superseded}</span>}
      </td>
      <td className={styles.num}>
        <span className="t-num">{formatIndianInt(outcome.inspection_rank_at_time)}</span>
        <span className={styles.rankNote}>
          {inside ? STRINGS.detail_panel.within_quota : STRINGS.detail_panel.beyond_quota}
        </span>
      </td>
      <td>{outcomes[outcome.outcome] ?? outcome.outcome}</td>
      <td>{outcome.in_control_sample ? copy.group_spot : copy.group_ranked}</td>
      <td>{outcome.inspector_id}</td>
    </tr>
  );
}
