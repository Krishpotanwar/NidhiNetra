"use client";

import { useId } from "react";
import { Info } from "@phosphor-icons/react";
import { motion, useReducedMotion } from "motion/react";
import { renderTemplate, STRINGS } from "@/lib/strings";
import { formatIndianInt } from "@/lib/format";
import styles from "./QuotaCard.module.css";

const copy = STRINGS.quota_card;

interface QuotaCardProps {
  totalN: number;
  quotaN: number;
  flaggedTotal: number;
  flaggedBeyondQuota: number;
  /** Dims the card while a newer filter is still loading, without blanking it. */
  stale?: boolean;
}

/**
 * The whole filtered population as one bar: the filled segment is exactly the
 * ten percent the District Authority must inspect, drawn with the risk ramp
 * because rank 1 is where the ramp starts. A lighter warm segment carries the
 * flagged works that fall past the cutoff, which is the fact the officer
 * cannot see anywhere else: being outside the quota is not being clean.
 *
 * Every figure comes from the API's own meta, so the bar and the sentence
 * beside it can never disagree.
 */
export function QuotaCard({ totalN, quotaN, flaggedTotal, flaggedBeyondQuota, stale }: QuotaCardProps) {
  const reduce = useReducedMotion();
  const labelId = useId();
  if (totalN <= 0) return null;

  const quotaShare = Math.min(1, quotaN / totalN);
  const flaggedShare = Math.min(1, Math.max(flaggedTotal, quotaN) / totalN);

  const sentences = [
    renderTemplate(copy.explainer, {
      total_n: formatIndianInt(totalN),
      quota_n: formatIndianInt(quotaN),
    }),
  ];
  if (flaggedBeyondQuota > 0) {
    sentences.push(renderTemplate(copy.overflow, { flagged_beyond_n: formatIndianInt(flaggedBeyondQuota) }));
  } else if (flaggedTotal === 0) {
    sentences.push(copy.none_flagged);
  } else if (flaggedTotal < quotaN) {
    sentences.push(renderTemplate(copy.underfill, { flagged_n: formatIndianInt(flaggedTotal) }));
  }
  sentences.push(STRINGS.framing.unflagged_caveat);

  return (
    <section className={styles.card} aria-labelledby={labelId} data-stale={stale || undefined}>
      <div className={styles.meter}>
        <div className={styles.head}>
          <h2 id={labelId} className="t-label">
            {STRINGS.quota_meter.label}
          </h2>
          <ul className={styles.legend}>
            <li>
              <span className={styles.swatchQuota} aria-hidden="true" />
              {copy.legend_quota}
            </li>
            {flaggedBeyondQuota > 0 && (
              <li>
                <span className={styles.swatchFlagged} aria-hidden="true" />
                {copy.legend_flagged}
              </li>
            )}
          </ul>
        </div>

        <div className={styles.trackWrap}>
          <div
            className={styles.track}
            role="img"
            aria-label={renderTemplate(copy.bar_label, {
              quota_n: formatIndianInt(quotaN),
              total_n: formatIndianInt(totalN),
            })}
          >
            <motion.span
              className={styles.flagged}
              initial={reduce ? false : { scaleX: 0 }}
              animate={{ scaleX: flaggedShare }}
              transition={reduce ? { duration: 0 } : { duration: 0.65, ease: [0.22, 1, 0.36, 1] }}
            />
            <motion.span
              className={styles.fill}
              initial={reduce ? false : { scaleX: 0 }}
              animate={{ scaleX: quotaShare }}
              transition={reduce ? { duration: 0 } : { duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
            />
          </div>
          <span className={styles.tick} style={{ left: `${quotaShare * 100}%` }} aria-hidden="true" />
          <span
            className={styles.tickLabel}
            style={{ left: `${quotaShare * 100}%` }}
            data-flip={quotaShare > 0.7 || undefined}
          >
            {renderTemplate(copy.cutoff_tick, { cutoff_rank: formatIndianInt(quotaN) })}
          </span>
        </div>
      </div>

      <div className={styles.explainer}>
        <Info size={18} aria-hidden="true" className={styles.infoIcon} />
        <p>{sentences.join(" ")}</p>
      </div>
    </section>
  );
}

export function QuotaCardSkeleton() {
  return (
    <section className={styles.card} aria-hidden="true">
      <div className={styles.meter}>
        <span className={styles.skeletonLabel} />
        <div className={styles.trackWrap}>
          <div className={styles.track} />
        </div>
      </div>
      <div className={styles.explainer}>
        <span className={styles.skeletonText} />
      </div>
    </section>
  );
}
