"use client";

import { useState } from "react";
import { ArrowRight } from "@phosphor-icons/react";
import { renderTemplate, STRINGS } from "@/lib/strings";
import { displayName, formatIndianInt } from "@/lib/format";
import type { VendorConcentration } from "@/lib/vendor-concentration";
import styles from "./ConcentratedVendors.module.css";

const s = STRINGS.fund_flow;

// The reference shows five, with the rest one click away.
const COLLAPSED_ROWS = 5;

interface ConcentratedVendorsProps {
  vendors: VendorConcentration[];
  focusedId: string | undefined;
  onFocus: (vendorId: string) => void;
  /** True once the list has loaded, so an empty list can say so instead of looking unfinished. */
  loaded: boolean;
}

/** The vendors ranked by how many Members their works trace back to; each row focuses that vendor's cluster. */
export function ConcentratedVendors({ vendors, focusedId, onFocus, loaded }: ConcentratedVendorsProps) {
  const [expanded, setExpanded] = useState(false);
  const rows = expanded ? vendors : vendors.slice(0, COLLAPSED_ROWS);
  return (
    <section className={styles.card}>
      <h2 className={styles.title}>{s.clusters_title}</h2>
      {rows.length > 0 && (
        <div className={styles.header} aria-hidden="true">
          <span>{s.clusters_column_rank}</span>
          <span>{s.clusters_column_vendor}</span>
          <span className={styles.headerCount}>{s.clusters_column_mps}</span>
        </div>
      )}
      <ul className={expanded ? `${styles.list} ${styles.scroll}` : styles.list}>
        {rows.map((vendor, index) => (
          <li key={vendor.vendorId}>
            <button
              type="button"
              className={styles.row}
              aria-current={vendor.vendorId === focusedId ? "true" : undefined}
              onClick={() => onFocus(vendor.vendorId)}
            >
              <span className={styles.rank}>{index + 1}</span>
              <span className={styles.name}>{displayName(vendor.vendorLabel)}</span>
              <span className={styles.count}>{formatIndianInt(vendor.memberCount)}</span>
            </button>
          </li>
        ))}
        {vendors.length === 0 && loaded && <li className={styles.empty}>{s.empty}</li>}
      </ul>
      {vendors.length > COLLAPSED_ROWS && (
        <button type="button" className={styles.toggle} aria-expanded={expanded} onClick={() => setExpanded(!expanded)}>
          {expanded ? (
            s.show_fewer
          ) : (
            <>
              {renderTemplate(s.view_all, { count: formatIndianInt(vendors.length) })}
              <ArrowRight size={16} weight="bold" aria-hidden="true" />
            </>
          )}
        </button>
      )}
    </section>
  );
}
