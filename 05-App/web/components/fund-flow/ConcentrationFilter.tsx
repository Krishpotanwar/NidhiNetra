"use client";

import { useId } from "react";
import { ArrowClockwise, MagnifyingGlass, Minus, Plus } from "@phosphor-icons/react";
import { renderTemplate, STRINGS } from "@/lib/strings";
import { formatIndianInt } from "@/lib/format";
import styles from "./ConcentrationFilter.module.css";

const s = STRINGS.fund_flow;

interface ConcentrationFilterProps {
  threshold: number;
  onThresholdChange: (next: number) => void;
  search: string;
  onSearchChange: (next: string) => void;
  /** Vendors the list offers. */
  shown: number;
  /** Vendors matching the filter, of which `shown` are offered. */
  matching: number;
  isDefault: boolean;
  onReset: () => void;
}

/**
 * One row: the minimum-Members stepper, the vendor search, how many vendors that leaves and a reset.
 * Floor of 1, not 0: a vendor paid on works from "0 or more Members" is every vendor, which is not a
 * filter. Every number is computed from the real graph by the caller.
 */
export function ConcentrationFilter({
  threshold,
  onThresholdChange,
  search,
  onSearchChange,
  shown,
  matching,
  isDefault,
  onReset,
}: ConcentrationFilterProps) {
  const searchId = useId();
  return (
    <section className={styles.toolbar} aria-label={s.concentration_filter_label}>
      <div className={styles.group}>
        <span className={styles.label}>{s.min_members_label}</span>
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

      <div className={styles.searchField}>
        <label className="sr-only" htmlFor={searchId}>
          {s.search_label}
        </label>
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

      <p className={styles.count}>
        {renderTemplate(s.toolbar_count, { shown: formatIndianInt(shown), matching: formatIndianInt(matching) })}
      </p>

      <button type="button" className={styles.reset} onClick={onReset} disabled={isDefault}>
        <ArrowClockwise size={16} aria-hidden="true" />
        {s.reset}
      </button>
    </section>
  );
}
