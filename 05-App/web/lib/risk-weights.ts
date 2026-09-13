/**
 * The scoring engine's own flag weights, mirrored for display.
 *
 * SOURCE OF TRUTH: pipeline/src/nidhinetra_pipeline/risk/rank.py. These
 * four numbers, the 80 point cap and the 20 point ensemble weight are
 * copied from it verbatim. Hand-mirrored for the same reason lib/types.ts
 * hand-mirrors the record schemas: the pydantic-to-TypeScript codegen
 * (`make contracts`) is not wired up yet, and web/lib/generated/ is where
 * that output will land. When it is, this file is the first thing that
 * should be deleted in favour of the generated constants.
 *
 * Until then the risk of drift is real and worth naming: if rank.py's
 * weights change and this file does not, the detail panel will confidently
 * itemise a breakdown that does not add up to the score beside it.
 * pipeline/tests/risk/test_rank.py is the place to add the assertion that
 * catches that.
 *
 * Why this file exists at all: the panel used to divide risk_score evenly
 * across however many flags had fired, which made a four flag record show
 * four identical weights. That is not what the engine did, and presenting
 * it as the breakdown was the exact "black box" the design brief's detail
 * panel section exists to rule out. The weights are not equal: cost_outlier
 * is worth half again what agency_concentration is.
 */
import type { FlagType } from "./types";

export const FLAG_WEIGHTS: Record<FlagType, number> = {
  cost_outlier: 30,
  stalled_work: 25,
  expenditure_mismatch: 25,
  agency_concentration: 20,
};

/** rank.py FLAGS_COMPONENT_CAP. All four flags sum to 100, so the cap bites. */
export const FLAGS_COMPONENT_CAP = 80;

/** rank.py ENSEMBLE_COMPONENT_WEIGHT: the ML signal's maximum contribution. */
export const ENSEMBLE_COMPONENT_WEIGHT = 20;

export interface RiskContribution {
  /** Display label, or null for the ensemble remainder which has no flag. */
  flag: FlagType | null;
  label: string;
  /** Points this contributed to the final score. */
  weight: number;
  /** Fraction of the final score, for the proportional bar. */
  share: number;
}

export interface RiskBreakdown {
  contributions: RiskContribution[];
  /** True when the flags summed past the cap and were clipped to it. */
  capped: boolean;
  /** Points lost to the cap, for the note under the list. */
  cappedBy: number;
}

/**
 * Decomposes a record's risk_score into the parts the engine actually
 * built it from: one line per fired flag at its real weight, plus whatever
 * remains, which is by construction the ensemble component.
 *
 * The remainder is derived by subtraction rather than read from the record
 * because the API does not return the raw ensemble score. That is sound
 * here precisely because compute_risk_score has only two terms: whatever
 * the flags did not account for is the ensemble's, exactly. It is floored
 * at zero so a rounding difference can never render as a negative
 * contribution.
 */
export function riskBreakdown(
  flags: FlagType[],
  riskScore: number,
  labels: Record<FlagType, string>,
  ensembleLabel: string,
): RiskBreakdown {
  const rawFlagSum = flags.reduce((sum, f) => sum + FLAG_WEIGHTS[f], 0);
  const flagsComponent = Math.min(FLAGS_COMPONENT_CAP, rawFlagSum);
  const capped = rawFlagSum > FLAGS_COMPONENT_CAP;

  // When the cap bites, each flag is shown scaled by the same factor the
  // engine applied to the group, so the lines still sum to what the score
  // actually contains rather than to a total the officer cannot find.
  const scale = rawFlagSum > 0 ? flagsComponent / rawFlagSum : 0;

  const contributions: RiskContribution[] = flags
    .map((flag) => ({
      flag,
      label: labels[flag],
      weight: FLAG_WEIGHTS[flag] * scale,
      share: 0,
    }))
    .sort((a, b) => b.weight - a.weight);

  const ensemble = Math.max(0, riskScore - flagsComponent);
  if (ensemble > 0.005) {
    contributions.push({ flag: null, label: ensembleLabel, weight: ensemble, share: 0 });
  }

  const total = contributions.reduce((s, c) => s + c.weight, 0);
  for (const c of contributions) {
    c.share = total > 0 ? c.weight / total : 0;
  }

  return { contributions, capped, cappedBy: rawFlagSum - flagsComponent };
}
