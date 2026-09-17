"use client";

import { Fragment, useEffect, useRef } from "react";
import Link from "next/link";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { ArrowRight, X } from "@phosphor-icons/react";
import { renderTemplate, STRINGS } from "@/lib/strings";
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
