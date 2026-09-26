import { fetchEnvelope, fetchEnvelopeWithMeta } from "./api-client";

export type DuplicateFinder =
  | "identical_batch"
  | "district_identical_batch"
  | "judged_same_asset_same_place";
export type DuplicateReviewStatus = "pending" | "confirmed_same" | "rejected_different";
export type DuplicateDecision = Exclude<DuplicateReviewStatus, "pending">;

export interface DuplicateCurrentReview {
  review_id: number;
  status: DuplicateDecision;
  reviewed_by: string;
  reviewed_at: string;
  reviewer_note: string;
  supersedes: number | null;
}

export interface DuplicateEvidenceWork {
  work_id: string;
  state: string;
  constituency: string;
  mp_name: string;
  implementing_district_authority: string | null;
  implementing_agency: string | null;
  work_description: string | null;
  sanctioned_amount_inr: number;
  completion_status: string;
}

export interface DuplicateCandidateRecord {
  candidate_id: number;
  finder: DuplicateFinder;
  scope: string;
  threshold_crossing_batch: boolean;
  text: string;
  text_b?: string;
  quote_a?: string;
  quote_b?: string;
  work_relation?: "duplicate_candidate" | "split_or_phase_candidate";
  work_ids: string[];
  status: DuplicateReviewStatus;
  current_review: DuplicateCurrentReview | null;
}

export interface DuplicateCandidate extends DuplicateCandidateRecord {
  evidence_works: DuplicateEvidenceWork[];
}

export interface DuplicateCandidatePage {
  rows: DuplicateCandidate[];
  page: number;
  pageSize: number;
  total: number;
  totalPages: number;
  judgeAbstentionRate: number | null;
  judgeQuoteRejectionRate: number | null;
  judgePairsTotal: number | null;
}

/** The work-detail endpoint's summary of the batches one work belongs to (nidhinetra_pipeline's
 * outcomes/duplicate_store.py `duplicate_context`). */
export interface DuplicateContextEntry {
  candidate_id: number;
  finder: DuplicateFinder;
  threshold_crossing_batch: boolean;
  text: string;
  text_b?: string;
  quote_a?: string;
  quote_b?: string;
  work_relation?: "duplicate_candidate" | "split_or_phase_candidate";
  work_count: number;
  other_work_ids: string[];
  status: DuplicateReviewStatus;
}

function metaNumber(meta: Record<string, unknown> | null, key: string, fallback: number): number {
  const value = meta?.[key];
  return typeof value === "number" && Number.isFinite(value) ? value : fallback;
}

function metaNullableNumber(meta: Record<string, unknown> | null, key: string): number | null {
  const value = meta?.[key];
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

export async function fetchDuplicateCandidates(
  page: number,
  pageSize: number,
  signal?: AbortSignal,
): Promise<DuplicateCandidatePage> {
  const query = new URLSearchParams({
    status: "pending",
    page: String(page),
    page_size: String(pageSize),
  });
  const result = await fetchEnvelopeWithMeta<DuplicateCandidate[]>(
    `/api/duplicates?${query.toString()}`,
    { signal },
  );
  return {
    rows: result.data,
    page: metaNumber(result.meta, "page", page),
    pageSize: metaNumber(result.meta, "page_size", pageSize),
    total: metaNumber(result.meta, "total", result.data.length),
    totalPages: metaNumber(result.meta, "total_pages", result.data.length > 0 ? 1 : 0),
    judgeAbstentionRate: metaNullableNumber(result.meta, "judge_abstention_rate"),
    judgeQuoteRejectionRate: metaNullableNumber(result.meta, "judge_quote_rejection_rate"),
    judgePairsTotal: metaNullableNumber(result.meta, "judge_pairs_total"),
  };
}

export async function reviewDuplicateCandidate(
  candidateId: number,
  status: DuplicateDecision,
  reviewedBy: string,
): Promise<DuplicateCandidateRecord> {
  return fetchEnvelope<DuplicateCandidateRecord>(`/api/duplicates/${candidateId}/review`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      status,
      reviewed_by: reviewedBy.trim(),
      reviewer_note: "",
    }),
  });
}

/** Fetches the merged work-detail record and returns only its duplicate_context: the panel
 * already has every other field from the row it was opened with. */
export async function fetchWorkDuplicateContext(
  workId: string,
  signal?: AbortSignal,
): Promise<DuplicateContextEntry[]> {
  const record = await fetchEnvelope<{ duplicate_context: DuplicateContextEntry[] }>(
    `/api/works/${encodeURIComponent(workId)}`,
    { signal },
  );
  return record.duplicate_context;
}
