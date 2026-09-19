import Link from "next/link";
import { ArrowRight, Bank, Database, FileText, type Icon, UsersThree, Warning } from "@phosphor-icons/react";
import { renderTemplate, STRINGS } from "@/lib/strings";
import { displayName, formatCurrency, formatIndianInt } from "@/lib/format";
import { realVendorId } from "@/lib/graph-data";
import type { VendorConcentration } from "@/lib/vendor-concentration";
import styles from "./ClusterInFocus.module.css";

const s = STRINGS.fund_flow;

interface ClusterInFocusProps {
  vendor: VendorConcentration;
}

/**
 * Four figures, not five: the graph has no district field, so a Districts count would have to be
 * invented (see lib/vendor-concentration.ts). The amount is the sanctioned value on those works,
 * which is what the graph's edges actually carry; the risk box below sums the same edges' real
 * flagged_work_count, never an invented concentration tier.
 */
export function ClusterInFocus({ vendor }: ClusterInFocusProps) {
  return (
    <section className={styles.card}>
      <h2 className="t-label">{s.cluster_in_focus_label}</h2>
      <p className={styles.name}>{displayName(vendor.vendorLabel)}</p>
      <ul className={styles.figures}>
        <Figure icon={UsersThree} label={s.cluster_members} value={formatIndianInt(vendor.memberCount)} />
        <Figure icon={Bank} label={s.cluster_agencies} value={formatIndianInt(vendor.agencyCount)} />
        <Figure icon={FileText} label={s.cluster_works} value={formatIndianInt(vendor.workCount)} />
        <Figure icon={Database} tone="rose" label={s.cluster_paid} value={formatCurrency(vendor.paidInr)} />
      </ul>
      {vendor.flaggedWorkCount > 0 && (
        <div className={styles.risk}>
          <Warning size={24} weight="fill" aria-hidden="true" className={styles.riskIcon} />
          <div>
            <p className={styles.riskLine}>
              {renderTemplate(s.cluster_risk_flag_note, {
                flagged: formatIndianInt(vendor.flaggedWorkCount),
                total: formatIndianInt(vendor.workCount),
              })}
            </p>
            <p className={styles.riskNote}>{STRINGS.framing.standing_note}</p>
          </div>
        </div>
      )}
      <Link
        href={`/inspections?vendor_id=${encodeURIComponent(realVendorId(vendor.vendorId))}`}
        className={styles.viewLinkedWorks}
      >
        {s.view_linked_works}
        <ArrowRight size={16} weight="bold" aria-hidden="true" />
      </Link>
    </section>
  );
}

function Figure({
  icon: Glyph,
  label,
  value,
  tone = "blue",
}: {
  icon: Icon;
  label: string;
  value: string;
  tone?: "blue" | "rose";
}) {
  return (
    <li className={styles.figure} data-tone={tone}>
      <span className={styles.figureIcon} aria-hidden="true">
        <Glyph size={20} />
      </span>
      <div>
        <p className={styles.figureValue}>{value}</p>
        <p className={styles.figureLabel}>{label}</p>
      </div>
    </li>
  );
}
