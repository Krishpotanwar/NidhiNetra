"use client";

import { ArrowClockwise } from "@phosphor-icons/react";
import { renderTemplate, STRINGS } from "@/lib/strings";
import { formatTimeIst } from "@/lib/format";
import styles from "./RefreshControl.module.css";

export type RefreshState = "idle" | "refreshing" | "failed";

interface RefreshControlProps {
  state: RefreshState;
  /** ISO timestamp of the data on screen, for refresh_failed's "{time}". */
  lastGoodTime: string | null;
  onRefresh: () => void;
}

/**
 * CP6: repeated refresh clicks are debounced. The caller ignores onRefresh
 * while a refresh is in flight, and the button is disabled here too, so a
 * rapid double click cannot even fire a second event.
 *
 * strings.json's refresh_in_progress is explicit about what this must NOT
 * do: do not blank the table, do not overlay a scrim, do not show a spinner,
 * do not disable the filters. It renders as one muted label, nothing else.
 */
export function RefreshControl({ state, lastGoodTime, onRefresh }: RefreshControlProps) {
  const inProgress = STRINGS.data_states.refresh_in_progress;
  const failed = STRINGS.data_states.refresh_failed;

  if (state === "refreshing") {
    return (
      <span role="status" className={styles.status}>
        <span className="sr-only">{inProgress.screen_reader}</span>
        <span aria-hidden="true">{inProgress.label}</span>
      </span>
    );
  }

  if (state === "failed") {
    return (
      <span className={styles.status}>
        <span>
          {lastGoodTime ? renderTemplate(failed.label, { time: formatTimeIst(lastGoodTime) }) : failed.body}
        </span>
        <button type="button" onClick={onRefresh} className={styles.link}>
          {failed.action}
        </button>
      </span>
    );
  }

  return (
    <button type="button" onClick={onRefresh} className={styles.button}>
      <ArrowClockwise size={14} aria-hidden="true" />
      {STRINGS.actions.refresh_now}
    </button>
  );
}
