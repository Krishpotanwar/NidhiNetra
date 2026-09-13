import { renderTemplate, STRINGS } from "@/lib/strings";
import { displayName, formatCurrencyFull, formatIndianInt } from "@/lib/format";
import type { VendorConcentration } from "@/lib/vendor-concentration";
import styles from "./SideCard.module.css";

const s = STRINGS.fund_flow;

interface ClusterInFocusProps {
  vendor: VendorConcentration;
  medianMemberCount: number;
}

/**
 * Three figures, not four: the graph has no district field, so a Districts
 * count would have to be invented (see lib/vendor-concentration.ts). The
 * amount is the sanctioned value on those works, which is what the graph's
 * edges actually carry.
 */
export function ClusterInFocus({ vendor, medianMemberCount }: ClusterInFocusProps) {
  const memberWord = medianMemberCount === 1 ? s.member_singular : s.member_plural;
  return (
    <section className={styles.card}>
      <h2 className="t-label">{s.cluster_in_focus_label}</h2>
      <p className={styles.clusterName}>{displayName(vendor.vendorLabel)}</p>
      <dl className={styles.figures}>
        <dt>{s.cluster_members}</dt>
        <dd className="t-num">{formatIndianInt(vendor.memberCount)}</dd>
        <dt>{s.cluster_works}</dt>
        <dd className="t-num">{formatIndianInt(vendor.workCount)}</dd>
        <dt>{s.cluster_paid}</dt>
        <dd className="t-num">{formatCurrencyFull(vendor.paidInr)}</dd>
      </dl>
      <p className={styles.note}>
        {renderTemplate(s.cluster_median_note, {
          median: formatIndianInt(medianMemberCount),
          member_word: memberWord,
        })}
      </p>
    </section>
  );
}
