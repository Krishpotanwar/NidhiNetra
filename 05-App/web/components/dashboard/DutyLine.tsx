"use client";

import { renderTemplate, STRINGS } from "@/lib/strings";
import { formatIndianInt } from "@/lib/format";
import type { FilterState } from "@/lib/filters";
import type { PendencySummary } from "@/lib/types";
import styles from "./DutyLine.module.css";

const copy = STRINGS.lens;

interface DutyLineProps {
  view: FilterState["view"];
  pendency: PendencySummary | null;
}

/**
 * The one sentence a role lens adds to a preset scope (D6): which legal duty
 * applies, with real numbers. Every number comes from `pendency`, the
 * scope-only GET /api/pendency summary (ruling R5) -- never the works-page
 * meta a table's quota bar uses, which moves with the flag/category filters
 * and would make this sentence describe a different population than the
 * scope picker says it does. Renders nothing until that summary has loaded.
 */
export function DutyLine({ view, pendency }: DutyLineProps) {
  if (!pendency) return null;

  const sentence = (() => {
    switch (view) {
      case "state":
        return renderTemplate(copy.duty_state, {
          n25: formatIndianInt(pendency.third_party.at_or_above_25_lakh),
          n15: formatIndianInt(pendency.third_party.between_15_and_25_lakh),
          required: formatIndianInt(pendency.third_party.required_n),
        });
      case "district":
        return renderTemplate(copy.duty_district, {
          quota: formatIndianInt(pendency.quota_sum),
          n: formatIndianInt(pendency.population_n),
        });
      case "mp":
        return renderTemplate(copy.duty_mp, {
          late: formatIndianInt(pendency.kinds.late_sanction.count),
          n: formatIndianInt(pendency.population_n),
          open: formatIndianInt(pendency.kinds.open_past_one_year.count),
        });
      case "ministry":
      default:
        return renderTemplate(copy.duty_ministry, {
          da_n: formatIndianInt(pendency.district_authority_n),
          quota_sum: formatIndianInt(pendency.quota_sum),
        });
    }
  })();

  return <p className={styles.line}>{sentence}</p>;
}
