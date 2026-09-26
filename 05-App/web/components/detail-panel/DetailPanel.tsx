"use client";

import { Fragment, useCallback, useEffect, useRef } from "react";
import Link from "next/link";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { ArrowRight, X } from "@phosphor-icons/react";
import { renderTemplate, STRINGS } from "@/lib/strings";
import { fetchWorkDuplicateContext } from "@/lib/duplicates";
import { useApiResource } from "@/lib/use-api-resource";
import {
  FLAG_LABELS,
  displayName,
  formatCurrencyFull,
  formatDate,
  formatIndianInt,
  formatRank,
  formatRiskScore,
  riskBand,
} from "@/lib/format";
import { financialYearOf } from "@/lib/filters";
import { peerGroupSentence } from "@/lib/peer-group";
import { FLAGS_COMPONENT_CAP, riskBreakdown } from "@/lib/risk-weights";
import { workTitle } from "@/lib/data";
import type { InspectionRow } from "@/lib/types";
import { BandPill } from "@/components/inspection-list/BandPill";
import { InspectionCapture } from "./InspectionCapture";
import styles from "./DetailPanel.module.css";

const strings = STRINGS.detail_panel;
const missing = STRINGS.missing_fields;
const pendencyStrings = STRINGS.pendency;

/**
 * T5: "Timelines against the guidelines" -- the three MoSPI monthly
 * pendency checks (T4), as facts about this one work rather than counts
 * over a population. Each condition is independent (D4): a work can be open
 * past one year, have unpublished dates, and show a payment line, all at
 * once, or none of them.
 */
function pendencyLines(row: InspectionRow): string[] {
  const lines: string[] = [];

  lines.push(
    row.days_to_sanction !== null
      ? renderTemplate(pendencyStrings.detail_days_to_sanction, { days: row.days_to_sanction })
      : pendencyStrings.detail_dates_missing,
  );

  const underImplementation = row.completion_status === "Sanctioned" || row.completion_status === "In Progress";
  if (underImplementation && row.days_since_sanction !== null && row.days_since_sanction > 365) {
    lines.push(renderTemplate(pendencyStrings.detail_open, { days: row.days_since_sanction }));
  }

  if (row.expenditure_amount_inr > 0) {
    lines.push(pendencyStrings.detail_payment_seen);
  } else if (row.days_since_sanction !== null && row.days_since_sanction > 90) {
    // R4: expenditure_amount_inr is 0 here (the branch above already claims
    // anything positive) -- never a payment line for a zero-spend work
    // still inside the 90-day window.
    lines.push(renderTemplate(pendencyStrings.detail_no_payment, { days: row.days_since_sanction }));
  }

  return lines;
}

interface DetailPanelProps {
  row: InspectionRow | null;
  onClose: () => void;
  quotaN: number;
}

/**
 * A parallel surface, not a blocking task: no scrim, because the officer is
 * comparing this work against the list behind it. Opens on a click, so it is
 * critically damped with no overshoot (design brief section 8), and Escape
 * closes it. Focus moves in on open and returns to the row on close.
 */
export function DetailPanel({ row, onClose, quotaN }: DetailPanelProps) {
  const reduce = useReducedMotion();
  const panelRef = useRef<HTMLElement>(null);
  const returnFocusRef = useRef<HTMLElement | null>(null);
  const workId = row?.work_id ?? null;

  useEffect(() => {
    if (!workId) {
      returnFocusRef.current?.focus?.();
      returnFocusRef.current = null;
      return;
    }
    if (!returnFocusRef.current) {
      returnFocusRef.current = document.activeElement as HTMLElement | null;
    }
    panelRef.current?.focus({ preventScroll: true });
  }, [workId]);

  useEffect(() => {
    if (!workId) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [workId, onClose]);

  return (
    <AnimatePresence>
      {row && (
        <motion.aside
          key="detail-panel"
          ref={panelRef}
          tabIndex={-1}
          role="dialog"
          aria-modal="false"
          aria-labelledby="detail-panel-title"
          className={styles.panel}
          initial={reduce ? { opacity: 0 } : { x: "104%" }}
          animate={reduce ? { opacity: 1 } : { x: 0 }}
          exit={reduce ? { opacity: 0 } : { x: "104%" }}
          transition={reduce ? { duration: 0.12 } : { type: "spring", stiffness: 320, damping: 34, mass: 0.9 }}
        >
          <PanelBody row={row} onClose={onClose} quotaN={quotaN} />
        </motion.aside>
      )}
    </AnimatePresence>
  );
}

function PanelBody({ row, onClose, quotaN }: { row: InspectionRow; onClose: () => void; quotaN: number }) {
  const band = riskBand(row.risk_score, row.flags);
  const breakdown = riskBreakdown(row.flags, row.risk_score, FLAG_LABELS, strings.breakdown_ensemble);
  const insideQuota = quotaN > 0 && row.displayRank <= quotaN;
  const year = financialYearOf(row);

  const fields: { key: keyof typeof strings.record_fields; value: string }[] = [
    { key: "work_id", value: row.work_id },
    { key: "mp_name", value: displayName(row.mp_name) },
    { key: "state", value: row.state },
    { key: "constituency", value: displayName(row.constituency) },
    {
      key: "activity",
      value: row.activity_name || missing.generic,
    },
    {
      key: "recommendation_date",
      value: row.recommendation_date ? formatDate(row.recommendation_date) : missing.date,
    },
    {
      key: "district_authority",
      value: row.implementing_district_authority
        ? displayName(row.implementing_district_authority)
        : missing.district_authority,
    },
    { key: "agency", value: row.implementing_agency ? displayName(row.implementing_agency) : missing.agency },
    { key: "vendor", value: row.vendor_name ? displayName(row.vendor_name) : missing.vendor },
    { key: "category", value: row.work_category },
    { key: "sanctioned", value: formatCurrencyFull(row.sanctioned_amount_inr) },
    { key: "spent", value: formatCurrencyFull(row.expenditure_amount_inr) },
    { key: "sanction_date", value: row.sanction_date ? formatDate(row.sanction_date) : missing.date },
    { key: "financial_year", value: year ?? missing.date },
    { key: "status", value: row.completion_status },
    { key: "last_updated", value: formatDate(row.last_updated) },
    { key: "source", value: sourceLabel(row.source_rung) },
  ];

  return (
    <>
      <header className={styles.head}>
        <div className={styles.headTop}>
          <span className={styles.rankChip}>
            {renderTemplate(strings.rank_label, { rank: formatRank(row.displayRank) })}
          </span>
          <BandPill band={band} />
          <span className={styles.quotaNote}>{insideQuota ? strings.within_quota : strings.beyond_quota}</span>
          <button type="button" onClick={onClose} aria-label={strings.close} className={styles.close}>
            <X size={18} aria-hidden="true" />
          </button>
        </div>
        <h2 id="detail-panel-title" className={styles.title}>
          {workTitle(row)}
        </h2>
        <p className={styles.description}>
          <span className={styles.descriptionLabel}>{strings.record_fields.work_description}</span>
          {row.work_description || missing.description}
        </p>
        <p className={styles.place}>
          {displayName(row.constituency)}, {row.state}
        </p>
      </header>

      <div className={styles.body}>
        <section className={styles.section}>
          <div className={styles.scoreRow}>
            <div>
              <p className={styles.score} data-band={band}>
                {formatRiskScore(row.risk_score)}
              </p>
              <p className="t-label">{STRINGS.risk_labels.score_label}</p>
            </div>
            <p className={styles.scoreCaption}>{STRINGS.risk_labels.score_caption}</p>
          </div>

          <h3 className={`t-label ${styles.sectionTitle}`}>{strings.breakdown_title}</h3>
          {row.flags.length === 0 ? (
            <p className={styles.note}>{STRINGS.framing.unflagged_caveat}</p>
          ) : (
            <>
              {breakdown.contributions.map((contribution) => {
                // Rounded before the plural test: the sentence has to agree
                // with the number actually shown.
                const weight = Math.round(contribution.weight);
                const reason = contribution.flag ? row.why_flagged[contribution.flag] : null;
                return (
                  <div key={contribution.flag ?? "ensemble"} className={styles.contribution}>
                    <p className={styles.contributionHead}>
                      {renderTemplate(strings.breakdown_row, {
                        factor: contribution.label,
                        weight,
                        point_word: weight === 1 ? strings.point_singular : strings.point_plural,
                      })}
                    </p>
                    <div className={styles.bar}>
                      <span
                        className={styles.barFill}
                        data-band={contribution.flag ? band : undefined}
                        style={{ width: `${Math.round(contribution.share * 100)}%` }}
                      />
                    </div>
                    {reason && <p className={styles.reason}>{reason}</p>}
                    {contribution.flag === null && <p className={styles.note}>{strings.breakdown_ensemble_note}</p>}
                  </div>
                );
              })}
              {breakdown.capped && (
                <p className={styles.note}>
                  {renderTemplate(strings.breakdown_capped, { cap: FLAGS_COMPONENT_CAP })}
                </p>
              )}
            </>
          )}
        </section>

        {row.peer_group ? (
          <section className={styles.peer}>
            <p className="t-label">{STRINGS.peer_group.label}</p>
            <p className={styles.peerSentence}>{peerGroupSentence(row.peer_group)}</p>
          </section>
        ) : (
          row.flags.length > 0 && <p className={styles.note}>{STRINGS.peer_group.missing}</p>
        )}

        <section className={styles.section}>
          <h3 className={`t-label ${styles.sectionTitle}`}>{pendencyStrings.detail_title}</h3>
          {pendencyLines(row).map((line) => (
            <p key={line} className={styles.reason}>
              {line}
            </p>
          ))}
        </section>

        <section className={styles.section}>
          <h3 className={`t-label ${styles.sectionTitle}`}>{strings.record_title}</h3>
          <dl className={styles.fields}>
            {fields.map((field) => (
              <Fragment key={field.key}>
                <dt className={styles.fieldName}>{strings.record_fields[field.key]}</dt>
                <dd className={styles.fieldValue}>{field.value}</dd>
              </Fragment>
            ))}
          </dl>
        </section>

        <DuplicateContextSection workId={row.work_id} />

        <section className={styles.actions}>
          {row.implementing_agency && (
            <Link
              href={`/fund-flow?agency=${encodeURIComponent(row.implementing_agency)}`}
              className={styles.secondaryButton}
            >
              {strings.fund_flow_entry}
              <ArrowRight size={14} weight="bold" aria-hidden="true" />
            </Link>
          )}
          <InspectionCapture workId={row.work_id} />
        </section>
      </div>
    </>
  );
}

const duplicateStrings = STRINGS.duplicate_review;

/**
 * Phase 1 Stage C. Fetched separately from the row the panel already has --
 * the list endpoint that populates `row` was never given this field (Stage C
 * Decision: only GET /api/works/{work_id} carries duplicate_context, and
 * only for the works synced from Stage A's identical batches). Renders
 * nothing while loading or when the work is in no synced batch, so an
 * unflagged work's panel looks exactly as it did before this section
 * existed.
 */
function DuplicateContextSection({ workId }: { workId: string }) {
  const load = useCallback((signal: AbortSignal) => fetchWorkDuplicateContext(workId, signal), [workId]);
  const context = useApiResource(load);
  const entries = context.data;

  if (!entries || entries.length === 0) return null;

  return (
    <section className={styles.section}>
      <h3 className={`t-label ${styles.sectionTitle}`}>{duplicateStrings.context_title}</h3>
      {entries.map((entry) => (
        <div key={entry.candidate_id} className={styles.contribution}>
          <p className={styles.contributionHead}>{displayName(entry.text)}</p>
          <p className={styles.reason}>
            {renderTemplate(duplicateStrings.context_count, { count: entry.work_count - 1 })}
          </p>
          {entry.threshold_crossing_batch && (
            <p className={styles.note}>{duplicateStrings.context_threshold}</p>
          )}
          <ul className={styles.evidenceList}>
            {entry.other_work_ids.map((otherId) => (
              <li key={otherId}>
                <Link href={`/inspections?q=${encodeURIComponent(otherId)}`}>{otherId}</Link>
              </li>
            ))}
          </ul>
        </div>
      ))}
    </section>
  );
}

/**
 * Rung 1 is the live MPLADS dashboard pull, rung 5 the hand-curated demo
 * set. Other rungs have no agreed copy yet, so they show their number rather
 * than prose invented here.
 */
function sourceLabel(rung: number): string {
  if (rung === 5) return STRINGS.data_states.showing_cached_data.demo_dataset_variant.label;
  const labels = STRINGS.detail_panel.source_labels as Record<string, string | undefined>;
  return labels[String(rung)] ?? formatIndianInt(rung);
}
