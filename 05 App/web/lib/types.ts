/**
 * Mirrors contracts/normalized_record.schema.json and
 * contracts/risk_scored_record.schema.json. Hand-written rather than
 * generated, since `make contracts` (pydantic + TypeScript codegen) is not
 * wired up in this pass -- see web/lib/generated/.gitkeep, which is where
 * that generator's output lands once it exists. Field names and nullability
 * match the schema files exactly.
 */

export type WorkCategory =
  | "Road"
  | "Drinking Water"
  | "School"
  | "Health"
  | "Community Infrastructure"
  | "Electricity"
  | "Sanitation";

export type CompletionStatus = "Recommended" | "Sanctioned" | "In Progress" | "Completed";

export type FlagType =
  | "cost_outlier"
  | "stalled_work"
  | "expenditure_mismatch"
  | "agency_concentration";

export interface NormalizedRecord {
  work_id: string;
  state: string;
  constituency: string;
  mp_name: string;
  tenure: string;
  implementing_agency: string | null;
  vendor_name: string | null;
  work_category: WorkCategory;
  sanctioned_amount_inr: number;
  expenditure_amount_inr: number;
  sanction_date: string | null;
  completion_status: CompletionStatus;
  last_updated: string;
  source_rung: number;
}

export interface PeerGroup {
  label: string;
  n: number;
}

export interface RiskScoredRecord {
  work_id: string;
  inspection_rank: number;
  risk_score: number;
  flags: FlagType[];
  why_flagged: Partial<Record<FlagType, string>>;
  peer_group: PeerGroup | null;
}

/** The join of both contracts by work_id -- the shape every A5 component renders. */
export interface InspectionRow extends NormalizedRecord, RiskScoredRecord {
  /** Position within the currently displayed (under-implementation) list, 1..N, no gaps. */
  displayRank: number;
}

/** Risk band, 0 (unflagged) to 4 (highest priority). Keys into strings.json risk_labels. */
export type RiskBand = 0 | 1 | 2 | 3 | 4;

/** GET /api/works/facets: filter options with counts over the quota population. */
export interface FacetOption {
  value: string;
  count: number;
}

export interface Facets {
  states: FacetOption[];
  years: FacetOption[];
  categories: FacetOption[];
  flags: FacetOption[];
}

/** GET /api/inspections: the Reports page. */
export interface IssueRate {
  value: number;
  low: number;
  high: number;
}

export interface GroupSummary {
  n: number;
  reached_work: number;
  issues: number;
  within_quota: number;
  issue_rate: IssueRate | null;
}

export interface InspectionOutcome {
  outcome_id: number;
  work_id: string;
  inspected_on: string;
  outcome: string;
  notes: string;
  inspector_id: string;
  state: string;
  constituency: string;
  implementing_agency: string | null;
  work_category: string;
  sanctioned_amount_inr: number;
  inspection_rank_at_time: number;
  risk_score_at_time: number;
  cutoff_rank_at_time: number;
  population_n_at_time: number;
  in_control_sample: boolean;
  supersedes: number | null;
  superseded: boolean;
}

export interface InspectionsReport {
  outcomes: InspectionOutcome[];
  summary: {
    total: number;
    ranked: GroupSummary;
    spot_check: GroupSummary;
    min_reached_per_group: number;
    comparison_ready: boolean;
  };
}
