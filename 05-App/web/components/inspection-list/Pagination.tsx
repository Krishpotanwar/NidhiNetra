"use client";

import { CaretLeft, CaretRight } from "@phosphor-icons/react";
import { renderTemplate, STRINGS } from "@/lib/strings";
import { formatIndianInt } from "@/lib/format";
import styles from "./Pagination.module.css";

const copy = STRINGS.pagination;

interface PaginationProps {
  page: number;
  totalPages: number;
  totalN: number;
  pageSize: number;
  /** Quota size for this filter, so an officer can jump straight to where
   *  this year's obligation ends rather than paging to it. */
  quotaN: number;
  onPage: (page: number) => void;
}

/** 1 ... 7 8 [9] 10 11 ... 897, with no duplicates and no gaps of one. */
function pageItems(page: number, totalPages: number): (number | "gap")[] {
  const pages = new Set<number>([1, totalPages, page, page - 1, page + 1]);
  const sorted = [...pages].filter((p) => p >= 1 && p <= totalPages).sort((a, b) => a - b);
  const items: (number | "gap")[] = [];
  let previous = 0;
  for (const value of sorted) {
    if (previous && value - previous === 2) items.push(previous + 1);
    else if (previous && value - previous > 2) items.push("gap");
    items.push(value);
    previous = value;
  }
  return items;
}

export function Pagination({ page, totalPages, totalN, pageSize, quotaN, onPage }: PaginationProps) {
  if (totalPages <= 1 && totalN <= pageSize) return null;
  const from = totalN === 0 ? 0 : (page - 1) * pageSize + 1;
  const to = Math.min(page * pageSize, totalN);
  const cutoffPage = quotaN > 0 ? Math.ceil(quotaN / pageSize) : 0;

  return (
    <nav className={styles.pagination} aria-label={copy.label}>
      <p className={styles.showing}>
        {renderTemplate(copy.showing, {
          from: formatIndianInt(from),
          to: formatIndianInt(to),
          total_n: formatIndianInt(totalN),
        })}
      </p>
      <div className={styles.controls}>
        {cutoffPage > 0 && cutoffPage !== page && cutoffPage <= totalPages && (
          <button type="button" className={styles.jump} onClick={() => onPage(cutoffPage)}>
            {copy.jump_to_cutoff}
          </button>
        )}
        <button
          type="button"
          className={styles.step}
          disabled={page <= 1}
          onClick={() => onPage(page - 1)}
        >
          <CaretLeft size={13} weight="bold" aria-hidden="true" />
          {copy.previous}
        </button>
        <ul className={styles.pages}>
          {pageItems(page, totalPages).map((item, index) =>
            item === "gap" ? (
              <li key={`gap-${index}`} className={styles.gap} aria-hidden="true">
                &hellip;
              </li>
            ) : (
              <li key={item}>
                <button
                  type="button"
                  className={styles.page}
                  aria-current={item === page ? "page" : undefined}
                  aria-label={renderTemplate(copy.page, { page: formatIndianInt(item) })}
                  onClick={() => onPage(item)}
                >
                  {formatIndianInt(item)}
                </button>
              </li>
            ),
          )}
        </ul>
        <button
          type="button"
          className={styles.step}
          disabled={page >= totalPages}
          onClick={() => onPage(page + 1)}
        >
          {copy.next}
          <CaretRight size={13} weight="bold" aria-hidden="true" />
        </button>
      </div>
    </nav>
  );
}
