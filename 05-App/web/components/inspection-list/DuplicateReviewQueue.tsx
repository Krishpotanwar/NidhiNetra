"use client";

import { useCallback, useId, useState } from "react";
import Link from "next/link";
import { renderTemplate, STRINGS } from "@/lib/strings";
import { displayName, formatIndianInt, formatPercent } from "@/lib/format";
import {
  fetchDuplicateCandidates,
  reviewDuplicateCandidate,
  type DuplicateCandidate,
  type DuplicateDecision,
  type DuplicateKindFilter,
} from "@/lib/duplicates";
import { officerInitials, rowTreatment, useOfficerInitials, useRowTreatment } from "@/lib/preferences";
import { useApiResource } from "@/lib/use-api-resource";
import { DotCanvas } from "@/components/shared/DotCanvas";
import { Segmented } from "@/components/filters/Segmented";
import styles from "./DuplicateReviewQueue.module.css";

const s = STRINGS.duplicate_review;
const PAGE_SIZE = 25;

/** The "Show" filter's UI value: "all" means the request omits kind entirely. A function, not a
 * module-level constant (T11B R24 precedent, FilterPanel.tsx's getLensOptions): s's leaves are
 * overwritten in place when the Hindi overlay runs (lib/strings.ts setLocale), and an array built
 * once at module load would freeze the English labels into it forever. Called at render time. */
type KindOption = "all" | DuplicateKindFilter;

function kindOptions(): { value: KindOption; label: string }[] {
  return [
    { value: "all", label: s.filter_all },
    { value: "identical", label: s.filter_identical },
    { value: "judged", label: s.filter_judged },
  ];
}

export function DuplicateReviewQueue() {
  const [page, setPage] = useState(1);
  const [kind, setKind] = useState<KindOption>("all");
  const [submittingId, setSubmittingId] = useState<number | null>(null);
  const [failedId, setFailedId] = useState<number | null>(null);
  const [announcement, setAnnouncement] = useState("");
  const reviewer = useOfficerInitials();
  const treatment = useRowTreatment();
  const reviewerId = useId();
  const kindId = useId();
  const treatmentId = useId();

  const load = useCallback(
    (signal: AbortSignal) =>
      fetchDuplicateCandidates(page, PAGE_SIZE, signal, kind === "all" ? undefined : kind),
    [page, kind],
  );
  const queue = useApiResource(load);
  const result = queue.data;

  function changeKind(next: KindOption) {
    setKind(next);
    setPage(1);
  }

  async function record(candidate: DuplicateCandidate, decision: DuplicateDecision) {
    setSubmittingId(candidate.candidate_id);
    setFailedId(null);
    try {
      await reviewDuplicateCandidate(candidate.candidate_id, decision, reviewer);
      setAnnouncement(s.saved);
      if (result && result.rows.length === 1 && page > 1) {
        setPage((current) => current - 1);
      } else {
        queue.reload();
      }
    } catch {
      setFailedId(candidate.candidate_id);
    } finally {
      setSubmittingId(null);
    }
  }

  return (
    <div className={styles.stack}>
      {result && (
        <a href="#duplicate-review" className={styles.pendingBadge}>
          {renderTemplate(s.pending_badge, { count: formatIndianInt(result.total) })}
        </a>
      )}

      <section id="duplicate-review" className={styles.card} aria-labelledby="duplicate-review-title">
        <header className={styles.header}>
          <div className={styles.intro}>
            <h2 id="duplicate-review-title" className={styles.title}>
              {s.title}
            </h2>
            <p className={styles.body}>{s.body}</p>
            {result && result.judgePairsTotal !== null && (
              <p className={styles.body}>
                {renderTemplate(s.judge_rates_note, {
                  total: formatIndianInt(result.judgePairsTotal),
                  abstained_percent: formatPercent(result.judgeAbstentionRate ?? 0),
                  rejected_percent: formatPercent(result.judgeQuoteRejectionRate ?? 0),
                })}
              </p>
            )}
          </div>

          <div className={styles.controls}>
            <div className={styles.control}>
              <span id={kindId} className="t-label">
                {s.filter_label}
              </span>
              <Segmented labelId={kindId} value={kind} onChange={changeKind} options={kindOptions()} />
            </div>

            <div className={styles.control}>
              <label htmlFor={reviewerId} className="t-label">
                {STRINGS.inspection_capture.inspector_id_label}
              </label>
              <input
                id={reviewerId}
                className={styles.initials}
                type="text"
                value={reviewer}
                onChange={(event) => officerInitials.set(event.target.value)}
                autoComplete="off"
              />
              <span className={styles.controlNote}>{s.reviewer_note}</span>
            </div>

            <div className={styles.control}>
              <span id={treatmentId} className="t-label">
                {STRINGS.view_options.row_treatment}
              </span>
              <Segmented
                labelId={treatmentId}
                value={treatment}
                onChange={(next) => rowTreatment.set(next)}
                options={[
                  { value: "two-line", label: STRINGS.view_options.two_line },
                  { value: "hover-reveal", label: STRINGS.view_options.hover_reveal },
                ]}
              />
            </div>
          </div>
        </header>

        {!result && queue.status === "loading" && (
          <div className={styles.skeleton} aria-hidden="true">
            {Array.from({ length: 3 }).map((_, index) => (
              <span key={index} />
            ))}
          </div>
        )}
        {!result && queue.status === "loading" && (
          <span className="sr-only" role="status">
            {s.loading_screen_reader}
          </span>
        )}

        {!result && queue.status === "error" && (
          <DotCanvas className={styles.state}>
            <p className={styles.stateTitle}>{s.error_title}</p>
            <p className={styles.stateBody}>{s.error_body}</p>
            <button type="button" className={styles.stateAction} onClick={queue.reload}>
              {STRINGS.actions.retry}
            </button>
          </DotCanvas>
        )}

        {result && result.rows.length === 0 && (
          <DotCanvas className={styles.state}>
            <p className={styles.stateTitle}>{s.empty_title}</p>
            <p className={styles.stateBody}>{s.empty_body}</p>
          </DotCanvas>
        )}

        {result && result.rows.length > 0 && (
          <div
            className={styles.tableCard}
            data-treatment={treatment}
            data-stale={queue.stale || undefined}
            data-testid="duplicate-review-card"
          >
            <div className={styles.scroller}>
              <table className={styles.table}>
                <caption className="sr-only">{s.table_caption}</caption>
                <thead>
                  <tr>
                    <th scope="col">{s.column_record}</th>
                    <th scope="col">{s.column_works}</th>
                    <th scope="col">{s.column_actions}</th>
                  </tr>
                </thead>
                <tbody>
                  {result.rows.map((candidate) => (
                    <DuplicateRow
                      key={candidate.candidate_id}
                      candidate={candidate}
                      reviewerPresent={reviewer.trim().length > 0}
                      submitting={submittingId === candidate.candidate_id}
                      failed={failedId === candidate.candidate_id}
                      onRecord={record}
                    />
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {result && result.totalPages > 1 && (
          <nav className={styles.pagination} aria-label={s.title}>
            <button
              type="button"
              onClick={() => setPage((current) => Math.max(1, current - 1))}
              disabled={page <= 1}
            >
              {s.previous_page}
            </button>
            <span>
              {renderTemplate(s.page_summary, {
                page: formatIndianInt(result.page),
                total_pages: formatIndianInt(result.totalPages),
              })}
            </span>
            <button
              type="button"
              onClick={() => setPage((current) => Math.min(result.totalPages, current + 1))}
              disabled={page >= result.totalPages}
            >
              {s.next_page}
            </button>
          </nav>
        )}

        <span className="sr-only" role="status" aria-live="polite">
          {announcement}
        </span>
      </section>
    </div>
  );
}

function DuplicateRow({
  candidate,
  reviewerPresent,
  submitting,
  failed,
  onRecord,
}: {
  candidate: DuplicateCandidate;
  reviewerPresent: boolean;
  submitting: boolean;
  failed: boolean;
  onRecord: (candidate: DuplicateCandidate, decision: DuplicateDecision) => void;
}) {
  const disabled = !reviewerPresent || submitting;

  return (
    <tr className={styles.row}>
      <td>
        <span className={styles.text}>{displayName(candidate.text)}</span>
        {candidate.text_b && <span className={styles.text}>{displayName(candidate.text_b)}</span>}
        <span className={styles.scope}>{displayName(candidate.scope)}</span>
        {candidate.threshold_crossing_batch && (
          <p className={styles.thresholdNote}>{s.threshold_note}</p>
        )}
        {candidate.finder === "judged_same_asset_same_place" && (
          <p className={styles.thresholdNote}>{s.judged_badge}</p>
        )}
      </td>
      <td>
        <p className={styles.workCount}>
          {renderTemplate(s.work_count, { count: formatIndianInt(candidate.work_ids.length) })}
        </p>
        <ul className={styles.workList}>
          {candidate.work_ids.map((workId) => (
            <li key={workId}>
              <Link href={`/inspections?q=${encodeURIComponent(workId)}`}>{workId}</Link>
            </li>
          ))}
        </ul>
      </td>
      <td>
        <div className={styles.actions}>
          <button type="button" disabled={disabled} onClick={() => onRecord(candidate, "confirmed_same")}>
            {s.same}
          </button>
          <button
            type="button"
            disabled={disabled}
            onClick={() => onRecord(candidate, "rejected_different")}
          >
            {s.different}
          </button>
        </div>
        {failed && (
          <p className={styles.rowError} role="alert">
            {s.save_error}
          </p>
        )}
      </td>
    </tr>
  );
}
