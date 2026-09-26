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
  implementing_district_authority: string | null;
  implementing_agency: string | null;
  vendor_id: string | null;
  vendor_name: string | null;
  work_category: WorkCategory;
  work_description: string | null;
  activity_name: string | null;
  recommendation_date: string | null;
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
  /** T4: recommendation_date to sanction_date, in days. Null whenever either
   *  date is missing (routers/works.py _decorate). */
  days_to_sanction: number | null;
  /** T4: sanction_date to the snapshot's as_of, in days. Null when
   *  sanction_date or as_of is missing. */
  days_since_sanction: number | null;
  /** T8B: true when this work is in the early-warning model's watch tenth
   *  (routers/works.py _decorate). Always a real boolean from the API; the
   *  `?` only covers a plain object literal built by hand (a test fixture)
   *  that has not bothered to set it. */
  early_warning?: boolean;
}

/** GET /api/early-warning (T8B): the shipped early-warning model's own
 *  cohort and metrics -- the artifact minus its watch list, which never
 *  leaves the server (honesty rule: no per-work number, only membership in
 *  the watch tenth via InspectionRow.early_warning above). */
export interface EarlyWarningMeta {
  model_version: string;
  data_as_of: string;
  status: "shipped";
  cohort: {
    start: string;
    train_cutoff: string;
    end: string;
    train_n: number;
    test_n: number;
  };
  features: {
    numeric: string[];
    categorical: string[];
  };
  metrics: {
    roc_auc: number;
    average_precision: number;
    base_rate: number;
    lift_at_10: number;
  };
  scored_n: number;
  watch_n: number;
}

/** Risk band, 0 (unflagged) to 4 (highest priority). Keys into strings.json risk_labels. */
export type RiskBand = 0 | 1 | 2 | 3 | 4;

/** GET /api/works/facets: filter options with counts over the quota population. */
export interface FacetOption {
  value: string;
  count: number;
  /** Constituencies only: the sitting MP for that constituency. */
  mp_name?: string;
}

export interface Facets {
  states: FacetOption[];
  years: FacetOption[];
  categories: FacetOption[];
  /** T4: District Authority scope for the "View as" role lenses (D6). */
  district_authorities: FacetOption[];
  constituencies: FacetOption[];
  flags: FacetOption[];
}

/** GET /api/pendency (T4): one of the three MoSPI monthly pendency checks,
 *  over works under implementation in the requested scope. */
export interface PendencyKindSummary {
  count: number;
  sanctioned_inr: number;
}

/** T4's median is over the whole scoped population with both dates present,
 *  not just the >45-day-late subset -- see routers/pendency.py's comment on
 *  why (matches the verified snapshot number, global-context.md). */
export interface LateSanctionSummary extends PendencyKindSummary {
  median_days_to_sanction: number | null;
}

/** GET /api/pendency?group_by=... row. Not rendered by T5 (T6 territory);
 *  typed now so the contract is not left as `any` at the boundary. */
export interface PendencyGroupSummary {
  group: string;
  population_n: number;
  late_sanction: number;
  open_past_one_year: number;
  no_payment_90_days: number;
  quota_n: number;
}

export interface PendencySummary {
  as_of: string;
  population_n: number;
  population_inr: number;
  kinds: {
    late_sanction: LateSanctionSummary;
    open_past_one_year: PendencyKindSummary;
    no_payment_90_days: PendencyKindSummary;
  };
  district_authority_n: number;
  quota_sum: number;
  third_party: {
    at_or_above_25_lakh: number;
    between_15_and_25_lakh: number;
    required_n: number;
  };
  /** Null unless the request set group_by. */
  groups: PendencyGroupSummary[] | null;
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
  implementing_district_authority: string | null;
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
