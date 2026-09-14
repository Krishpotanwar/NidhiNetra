"use client";

import { useCallback, useId, useState } from "react";
import Link from "next/link";
import { renderTemplate, STRINGS } from "@/lib/strings";
import { displayName, formatIndianInt } from "@/lib/format";
import {
  fetchAliasCandidates,
  reviewAliasCandidate,
  type AliasCandidate,
  type AliasDecision,
} from "@/lib/entity-aliases";
import { officerInitials, rowTreatment, useOfficerInitials, useRowTreatment } from "@/lib/preferences";
import { useApiResource } from "@/lib/use-api-resource";
import { DotCanvas } from "@/components/shared/DotCanvas";
import { Segmented } from "@/components/filters/Segmented";
import styles from "./AliasReviewQueue.module.css";

const s = STRINGS.entity_alias_review;
const PAGE_SIZE = 25;

export function AliasReviewQueue() {
  const [page, setPage] = useState(1);
  const [submittingId, setSubmittingId] = useState<number | null>(null);
  const [failedId, setFailedId] = useState<number | null>(null);
  const [announcement, setAnnouncement] = useState("");
  const reviewer = useOfficerInitials();
  const treatment = useRowTreatment();
  const reviewerId = useId();
  const treatmentId = useId();

  const load = useCallback(
    (signal: AbortSignal) => fetchAliasCandidates(page, PAGE_SIZE, signal),
    [page],
  );
  const queue = useApiResource(load);
  const result = queue.data;

  async function record(candidate: AliasCandidate, decision: AliasDecision) {
    setSubmittingId(candidate.candidate_id);
    setFailedId(null);
    try {
      await reviewAliasCandidate(candidate.candidate_id, decision, reviewer);
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
        <a href="#entity-alias-review" className={styles.pendingBadge}>
          {renderTemplate(s.pending_badge, { count: formatIndianInt(result.total) })}
        </a>
      )}

      <section id="entity-alias-review" className={styles.card} aria-labelledby="entity-alias-title">
        <header className={styles.header}>
          <div className={styles.intro}>
            <h2 id="entity-alias-title" className={styles.title}>
              {s.title}
            </h2>
            <p className={styles.body}>{s.body}</p>
          </div>

          <div className={styles.controls}>
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
            data-testid="alias-review-card"
          >
            <div className={styles.scroller}>
              <table className={styles.table}>
                <caption className="sr-only">{s.table_caption}</caption>
                <thead>
                  <tr>
                    <th scope="col">{s.column_record}</th>
                    <th scope="col">{s.column_reason}</th>
                    <th scope="col">{s.column_evidence}</th>
                    <th scope="col">{s.column_actions}</th>
                  </tr>
                </thead>
                <tbody>
                  {result.rows.map((candidate) => (
                    <AliasRow
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

function AliasRow({
  candidate,
  reviewerPresent,
  submitting,
  failed,
  onRecord,
}: {
  candidate: AliasCandidate;
  reviewerPresent: boolean;
  submitting: boolean;
  failed: boolean;
  onRecord: (candidate: AliasCandidate, decision: AliasDecision) => void;
}) {
  const evidenceById = new Map(candidate.evidence_works.map((work) => [work.work_id, work]));
  const disabled = !reviewerPresent || submitting;

  return (
    <tr className={styles.row}>
      <td>
        <span className={styles.alias}>{displayName(candidate.alias_label)}</span>
        <span className={styles.canonical}>
          {renderTemplate(s.canonical_id, { id: candidate.proposed_canonical_id })}
        </span>
      </td>
      <td>
        <div className={styles.reasonWrap}>
          <p className={styles.reason}>{s.reason[candidate.reason]}</p>
        </div>
      </td>
      <td>
        <ul className={styles.evidenceList}>
          {candidate.evidence_work_ids.map((workId) => {
            const work = evidenceById.get(workId);
            const context = work
              ? [displayName(work.constituency), displayName(work.implementing_agency ?? "")]
                  .filter(Boolean)
                  .join(" · ")
              : undefined;
            const vendorIdentity =
              work?.vendor_id && work.vendor_name
                ? renderTemplate(s.evidence_vendor, {
                    name: displayName(work.vendor_name),
                    id: work.vendor_id,
                  })
                : null;
            return (
              <li key={workId}>
                <Link href={`/inspections?q=${encodeURIComponent(workId)}`} title={context}>
                  {workId}
                </Link>
                {vendorIdentity && <span className={styles.evidenceIdentity}>{vendorIdentity}</span>}
              </li>
            );
          })}
        </ul>
      </td>
      <td>
        <div className={styles.actions}>
          <button
            type="button"
            disabled={disabled}
            onClick={() => onRecord(candidate, "confirmed_merge")}
          >
            {s.same}
          </button>
          <button
            type="button"
            disabled={disabled}
            onClick={() => onRecord(candidate, "rejected_distinct")}
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
