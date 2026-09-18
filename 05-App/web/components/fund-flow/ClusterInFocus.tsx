import Link from "next/link";
import { renderTemplate, STRINGS } from "@/lib/strings";
import { displayName, formatCurrencyFull, formatIndianInt } from "@/lib/format";
import { realVendorId } from "@/lib/graph-data";
import type { VendorConcentration } from "@/lib/vendor-concentration";
import styles from "./SideCard.module.css";

const s = STRINGS.fund_flow;

interface ClusterInFocusProps {
  vendor: VendorConcentration;
  medianMemberCount: number;
}

/**
 * Four figures, not five: the graph has no district field, so a Districts
 * count would have to be invented (see lib/vendor-concentration.ts). The
 * amount is the sanctioned value on those works, which is what the graph's
 * edges actually carry; the risk-flag line below sums the same edges'
 * real flagged_work_count, never an invented concentration tier.
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
        <dt>{s.cluster_agencies}</dt>
        <dd className="t-num">{formatIndianInt(vendor.agencyCount)}</dd>
        <dt>{s.cluster_works}</dt>
        <dd className="t-num">{formatIndianInt(vendor.workCount)}</dd>
        <dt>{s.cluster_paid}</dt>
        <dd className="t-num">{formatCurrencyFull(vendor.paidInr)}</dd>
      </dl>
      {vendor.flaggedWorkCount > 0 && (
        <p className={styles.riskNote}>
          {renderTemplate(s.cluster_risk_flag_note, {
            flagged: formatIndianInt(vendor.flaggedWorkCount),
            total: formatIndianInt(vendor.workCount),
          })}
        </p>
      )}
      <p className={styles.note}>
        {renderTemplate(s.cluster_median_note, {
          median: formatIndianInt(medianMemberCount),
          member_word: memberWord,
        })}
      </p>
      <Link
        href={`/inspections?vendor_id=${encodeURIComponent(realVendorId(vendor.vendorId))}`}
        className={styles.viewLinkedWorks}
      >
        {s.view_linked_works}
      </Link>
    </section>
  );
}
