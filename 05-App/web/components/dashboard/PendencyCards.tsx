"use client";

import Link from "next/link";
import { ArrowRight } from "@phosphor-icons/react";
import { renderTemplate, STRINGS } from "@/lib/strings";
import { formatCurrencyCrore, formatDate, formatIndianInt } from "@/lib/format";
import { EMPTY_FILTERS, PENDENCY_KINDS, inspectionListHref, type FilterState } from "@/lib/filters";
import type { PendencySummary } from "@/lib/types";
import type { ResourceStatus } from "@/lib/use-api-resource";
import styles from "./PendencyCards.module.css";

const copy = STRINGS.pendency;

type PendencyKind = (typeof PENDENCY_KINDS)[number];

interface CardData {
  kind: PendencyKind;
  label: string;
  count: number;
  sanctionedInr: number;
  context: string;
}

/**
 * D10 (KpiCards -> PendencyCards): one card per MoSPI kind (D5 forbids a
 * combined "any pendency" figure), in the same order as PENDENCY_KINDS/the
 * API's kinds dict/the verified numbers in global-context.md. Only
 * late_sanction's context takes a template param (median days); the other
 * two are static sentences.
 */
function buildCards(summary: PendencySummary): CardData[] {
  const { kinds } = summary;
  return [
    {
      kind: "late_sanction",
      label: copy.late_sanction_label,
      count: kinds.late_sanction.count,
      sanctionedInr: kinds.late_sanction.sanctioned_inr,
      // median_days_to_sanction is null only when nothing in the current
      // scope has both dates recorded -- reachable once T6's District
      // Authority/constituency pickers narrow the scope that far. Never
      // invent a day-count for it (review finding a): render the same
      // 45-day rule with no median clause at all instead.
      context:
        kinds.late_sanction.median_days_to_sanction === null
          ? copy.late_sanction_context_no_median
          : renderTemplate(copy.late_sanction_context, {
              days: kinds.late_sanction.median_days_to_sanction,
            }),
    },
    {
      kind: "open_past_one_year",
      label: copy.open_past_one_year_label,
      count: kinds.open_past_one_year.count,
      sanctionedInr: kinds.open_past_one_year.sanctioned_inr,
      context: copy.open_past_one_year_context,
    },
    {
      kind: "no_payment_90_days",
      label: copy.no_payment_label,
      count: kinds.no_payment_90_days.count,
      sanctionedInr: kinds.no_payment_90_days.sanctioned_inr,
      context: copy.no_payment_context,
    },
  ];
}

/** R3: scope only (states/districtAuthority/constituency) plus pendency, so
 *  the card's count and the list it links to always agree on population.
 *  T6 adds `view`, so a card clicked under a role lens opens the list in
 *  that same lens rather than resetting to Ministry. */
function cardHref(kind: PendencyKind, filters: FilterState): string {
  return inspectionListHref({
    ...EMPTY_FILTERS,
    states: filters.states,
    districtAuthority: filters.districtAuthority,
    constituency: filters.constituency,
    view: filters.view,
    pendency: kind,
  });
}

interface PendencyCardsProps {
  summary: PendencySummary | null;
  status: ResourceStatus;
  onRetry: () => void;
  filters: FilterState;
}

export function PendencyCards({ summary, status, onRetry, filters }: PendencyCardsProps) {
  if (status === "error" && !summary) {
    const copyError = STRINGS.data_states.api_unreachable;
    return (
      <section className={styles.errorCard} aria-label={copy.title}>
        <div>
          <p className={styles.errorTitle}>{copyError.title}</p>
          <p className={styles.errorBody}>{copyError.body}</p>
        </div>
        <button type="button" onClick={onRetry} className={styles.retry}>
          {copyError.action}
        </button>
      </section>
    );
  }

  const cards = summary ? buildCards(summary) : null;

  return (
    <section aria-label={copy.title} aria-busy={!cards}>
      {summary && <p className={styles.lede}>{renderTemplate(copy.lede, { date: formatDate(summary.as_of) })}</p>}
      <div className={styles.grid}>
        {PENDENCY_KINDS.map((kind, index) => {
          const card = cards?.[index];
          return (
            <article key={kind} className={styles.card}>
              {card ? (
                <>
                  <p className={styles.value}>{formatIndianInt(card.count)}</p>
                  <p className={`t-label ${styles.label}`}>{card.label}</p>
                  <p className={styles.context}>
                    {renderTemplate(copy.value_line, {
                      count: formatIndianInt(card.count),
                      amount: formatCurrencyCrore(card.sanctionedInr),
                    })}
                  </p>
                  <p className={styles.context}>{card.context}</p>
                  <Link href={cardHref(kind, filters)} className={styles.link}>
                    {copy.view_list}
                    <ArrowRight size={13} weight="bold" aria-hidden="true" />
                  </Link>
                </>
              ) : (
                <>
                  <span className={styles.skeletonValue} aria-hidden="true" />
                  <span className={styles.skeletonLabel} aria-hidden="true" />
                  <span className={styles.skeletonContext} aria-hidden="true" />
                </>
              )}
            </article>
          );
        })}
      </div>
      {summary && (
        <p className={styles.caveat}>{renderTemplate(copy.caveat, { date: formatDate(summary.as_of) })}</p>
      )}
    </section>
  );
}
