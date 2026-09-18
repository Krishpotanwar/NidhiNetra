"use client";

import { useId } from "react";
import { MagnifyingGlass, Minus, Plus } from "@phosphor-icons/react";
import { renderTemplate, STRINGS } from "@/lib/strings";
import { formatIndianInt } from "@/lib/format";
import styles from "./SideCard.module.css";

const s = STRINGS.fund_flow;

interface ConcentrationFilterProps {
  threshold: number;
  onThresholdChange: (next: number) => void;
  search: string;
  onSearchChange: (next: string) => void;
  matchingCount: number;
  totalVendorCount: number;
  /** How many of the matches the list offers, when fewer than all of them. */
  drawnCount: number | null;
  isDefault: boolean;
  onReset: () => void;
}

/**
 * Floor of 1, not 0: a vendor paid on works from "0 or more Members" is every
 * vendor, which is not a filter. Every number in the description is computed
 * from the real graph by the caller.
 */
export function ConcentrationFilter({
  threshold,
  onThresholdChange,
  search,
  onSearchChange,
  matchingCount,
  totalVendorCount,
  drawnCount,
  isDefault,
  onReset,
}: ConcentrationFilterProps) {
  const searchId = useId();
  return (
    <section className={styles.card}>
      <div className={styles.filterHeader}>
        <h2 className="t-label">{s.concentration_filter_label}</h2>
        {!isDefault && (
          <button type="button" className={styles.resetButton} onClick={onReset}>
            {s.reset}
          </button>
        )}
      </div>
      <p className={styles.note}>
        {renderTemplate(s.concentration_filter_description, {
          threshold: formatIndianInt(threshold),
          matching: formatIndianInt(matchingCount),
          total: formatIndianInt(totalVendorCount),
        })}
      </p>
      {drawnCount !== null && (
        <p className={styles.note}>{renderTemplate(s.drawn_cap_note, { drawn: formatIndianInt(drawnCount) })}</p>
      )}
      <div className={styles.stepperRow}>
        <span className="t-label">{s.min_members_label}</span>
        <div className={styles.stepper}>
          <button
            type="button"
            className={styles.stepperButton}
            onClick={() => onThresholdChange(Math.max(1, threshold - 1))}
            disabled={threshold <= 1}
            aria-label={`${s.min_members_label}, ${formatIndianInt(Math.max(1, threshold - 1))}`}
          >
            <Minus size={14} weight="bold" aria-hidden="true" />
          </button>
          <span className={styles.stepperValue}>{formatIndianInt(threshold)}</span>
          <button
            type="button"
            className={styles.stepperButton}
            onClick={() => onThresholdChange(threshold + 1)}
            aria-label={`${s.min_members_label}, ${formatIndianInt(threshold + 1)}`}
          >
            <Plus size={14} weight="bold" aria-hidden="true" />
          </button>
        </div>
      </div>
      <div className={styles.searchRow}>
        <label className="t-label" htmlFor={searchId}>
          {s.search_label}
        </label>
        <div className={styles.searchField}>
          <MagnifyingGlass size={16} aria-hidden="true" className={styles.searchIcon} />
          <input
            id={searchId}
            type="search"
            className={styles.searchInput}
            placeholder={s.search_placeholder}
            value={search}
            onChange={(event) => onSearchChange(event.target.value)}
          />
        </div>
      </div>
    </section>
  );
}
