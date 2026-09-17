import { fetchEnvelope, fetchEnvelopeWithMeta } from "./api-client";

export type AliasReason =
  | "identifier_has_multiple_labels"
  | "label_has_multiple_identifiers"
  | "identifier_and_label_ambiguous";

export type AliasReviewStatus = "pending" | "confirmed_merge" | "rejected_distinct";
export type AliasDecision = Exclude<AliasReviewStatus, "pending">;

export interface AliasCurrentReview {
  review_id: number;
  status: AliasDecision;
  reviewed_by: string;
  reviewed_at: string;
  reviewer_note: string;
  supersedes: number | null;
}

export interface AliasEvidenceWork {
  work_id: string;
  state: string;
  constituency: string;
  mp_name: string;
  implementing_district_authority: string | null;
  implementing_agency: string | null;
  vendor_id: string | null;
  vendor_name: string | null;
  work_category: string;
  sanctioned_amount_inr: number;
  completion_status: string;
}

export interface AliasCandidateRecord {
  candidate_id: number;
  entity_type: "vendor";
  proposed_canonical_id: string;
  alias_label: string;
  reason: AliasReason;
  evidence_work_ids: string[];
  status: AliasReviewStatus;
  current_review: AliasCurrentReview | null;
}

export interface AliasCandidate extends AliasCandidateRecord {
  evidence_works: AliasEvidenceWork[];
}

export interface AliasCandidatePage {
  rows: AliasCandidate[];
  page: number;
  pageSize: number;
  total: number;
  totalPages: number;
}

function metaNumber(meta: Record<string, unknown> | null, key: string, fallback: number): number {
  const value = meta?.[key];
  return typeof value === "number" && Number.isFinite(value) ? value : fallback;
}

export async function fetchAliasCandidates(
  page: number,
  pageSize: number,
  signal?: AbortSignal,
): Promise<AliasCandidatePage> {
  const query = new URLSearchParams({
    status: "pending",
    page: String(page),
    page_size: String(pageSize),
  });
  const result = await fetchEnvelopeWithMeta<AliasCandidate[]>(
    `/api/entity-aliases?${query.toString()}`,
    { signal },
  );
  return {
    rows: result.data,
    page: metaNumber(result.meta, "page", page),
    pageSize: metaNumber(result.meta, "page_size", pageSize),
    total: metaNumber(result.meta, "total", result.data.length),
    totalPages: metaNumber(result.meta, "total_pages", result.data.length > 0 ? 1 : 0),
  };
}

export async function reviewAliasCandidate(
  candidateId: number,
  status: AliasDecision,
  reviewedBy: string,
): Promise<AliasCandidateRecord> {
  return fetchEnvelope<AliasCandidateRecord>(`/api/entity-aliases/${candidateId}/review`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      status,
      reviewed_by: reviewedBy.trim(),
      reviewer_note: "",
    }),
  });
}
