"use client";

import type { Icon } from "@phosphor-icons/react";
import { CurrencyInr, Database, FileText, Flag } from "@phosphor-icons/react";
import { renderTemplate, STRINGS } from "@/lib/strings";
import { formatCroreParts, formatCurrencyFull, formatIndianInt } from "@/lib/format";
import type { SummaryFigures } from "@/lib/data";
import type { ResourceStatus } from "@/lib/use-api-resource";
import { DotCanvas } from "@/components/shared/DotCanvas";
import styles from "./KpiCards.module.css";

const labels = STRINGS.summary_strip;
const copy = STRINGS.dashboard;

type Tone = "works" | "flagged" | "value" | "idle";

interface KpiItem {
  tone: Tone;
  Glyph: Icon;
  value: string;
  unit?: string;
  label: string;
  context: string[];
}

/**
 * The four figures the design brief names, each with a real relationship
 * underneath it rather than a trend chip: there is one snapshot and no time
 * series, so the reference's "+12%" deltas would have to be invented.
 */
function buildItems(f: SummaryFigures): KpiItem[] {
  const flaggedValue = formatCroreParts(f.valueUnderFlaggedInr);
  const idleValue = formatCroreParts(f.idleBeyond12MonthsInr);
  return [
    {
      tone: "works",
      Glyph: FileText,
      value: formatIndianInt(f.worksUnderImplementation),
      label: labels.works_under_implementation,
      context: [
        renderTemplate(copy.kpi_works_context, {
          constituency_n: formatIndianInt(f.constituencyCount),
          state_n: formatIndianInt(f.stateCount),
        }),
      ],
    },
    {
      tone: "flagged",
      Glyph: Flag,
      value: formatIndianInt(f.flaggedForInspection),
      label: labels.flagged_for_inspection,
      context: [renderTemplate(copy.kpi_flagged_context, { percent: Math.round(f.flaggedPercent) })],
    },
    {
      tone: "value",
      Glyph: CurrencyInr,
      value: flaggedValue.value,
      unit: flaggedValue.unit,
      label: labels.value_under_flagged,
      context: [
        renderTemplate(copy.kpi_value_average, { amount: formatCurrencyFull(f.averageFlaggedInr) }),
        renderTemplate(copy.kpi_value_share, {
          percent: Math.round(f.valueUnderFlaggedPercentOfSanctioned),
        }),
      ],
    },
    {
      tone: "idle",
      Glyph: Database,
      value: idleValue.value,
      unit: idleValue.unit,
      label: labels.idle_beyond_12_months,
      context: [renderTemplate(copy.kpi_idle_context, { work_n: formatIndianInt(f.idleWorkCount) })],
    },
  ];
}

interface KpiCardsProps {
  figures: SummaryFigures | null;
  status: ResourceStatus;
  onRetry: () => void;
}

export function KpiCards({ figures, status, onRetry }: KpiCardsProps) {
  if (status === "error" && !figures) {
    const copyError = STRINGS.data_states.api_unreachable;
    return (
      <DotCanvas as="section" className={styles.errorCard} aria-label={copy.summary_label}>
        <div>
          <p className={styles.errorTitle}>{copyError.title}</p>
          <p className={styles.errorBody}>{copyError.body}</p>
        </div>
        <button type="button" onClick={onRetry} className={styles.retry}>
          {copyError.action}
        </button>
      </DotCanvas>
    );
  }

  const items = figures ? buildItems(figures) : null;
  const tones: Tone[] = ["works", "flagged", "value", "idle"];

  return (
    <section className={styles.grid} aria-label={copy.summary_label} aria-busy={!items}>
      {tones.map((tone, index) => {
        const item = items?.[index];
        return (
          <article key={tone} className={styles.card} data-tone={tone}>
            <span className={styles.tile} aria-hidden="true">
              {item ? <item.Glyph size={23} /> : null}
            </span>
            <div className={styles.text}>
              {item ? (
                <>
                  <p className={styles.value}>
                    {item.value}
                    {item.unit ? <span className={styles.unit}>{item.unit}</span> : null}
                  </p>
                  <p className={`t-label ${styles.label}`}>{item.label}</p>
                  {item.context.map((line) => (
                    <p key={line} className={styles.context}>
                      {line}
                    </p>
                  ))}
                </>
              ) : (
                <>
                  <span className={styles.skeletonValue} />
                  <span className={styles.skeletonLabel} />
                  <span className={styles.skeletonContext} />
                </>
              )}
            </div>
          </article>
        );
      })}
    </section>
  );
}
