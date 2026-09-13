"""Independent risk detectors.

cost_outlier, stalled_work and expenditure_mismatch are per-record: each
takes one record (and, where relevant, its PeerGroup) and returns a
DetectorFinding. agency_concentration is cross-record by nature -- it asks
whether one agency or vendor appears across an unusual number of MPs or
districts, which is a question about the whole dataset, not any single row
-- so it is implemented as its own pass (`detect_agency_concentration`)
over every record at once, not folded into the per-record loop.

None of these functions enforce the peer-group-n-30 rule themselves.
risk/engine.py enforces it once, centrally, before any detector runs, so
there is exactly one place in the codebase that rule can be gotten wrong.
See risk/peer_groups.py `peer_group_for`.

IsolationForest and LocalOutlierFactor are wired in at the bottom of this
module as `ensemble_scores`, an ensemble signal that feeds risk_score
(risk/rank.py) only. They are not a fifth flag type -- the contract
(risk_scored_record.schema.json) caps flags at the four named ones above.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from statistics import mean, pstdev
from typing import Any

import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor
from sklearn.preprocessing import StandardScaler

from .peer_groups import PeerGroup


@dataclass(frozen=True)
class DetectorFinding:
    """`fired=False` findings still carry the flag name so callers can log
    or test "this detector ran and did not fire" without special-casing.
    `variant` is the why_flagged template_id (contracts/strings.json) to
    render when fired; `params` are the raw values explain.render needs.
    """

    flag: str
    fired: bool
    variant: str = ""
    params: dict[str, Any] = field(default_factory=dict)


def _months_between(start: date, end: date) -> int:
    return max(0, (end.year - start.year) * 12 + (end.month - start.month))


# --------------------------------------------------------------------- #
# cost_outlier
# --------------------------------------------------------------------- #

# Threshold rationale: z > 2.5 on the peer group's sanctioned_amount_inr.
# For an approximately normal peer distribution, |z| > 2.5 covers roughly
# the outer ~1.2% of the distribution (two-tailed) -- rare enough that
# routine, explainable cost variation (a hill road costing more than a
# plains road, an urban work costing more than a rural one of the same
# category) does not flood the inspection list, while still catching a
# clearly outsized cost like the worked reference example in Execution
# Plan 3.2 ("Cost is 3.2x the median"). sanctioned_amount_inr is bounded at
# zero and right-skewed in practice (overruns are unbounded above, savings
# are not), which if anything makes a std-based z on the raw amount already
# a conservative (harder-to-trip) threshold, not a lenient one -- we do not
# need to tighten it further to control false positives.
COST_Z_THRESHOLD = 2.5


def cost_outlier(record: dict[str, Any], peer: PeerGroup) -> DetectorFinding:
    amount = record.get("sanctioned_amount_inr")
    if amount is None or peer.std_cost <= 0:
        # std == 0 means every peer costs the same -- nothing can be a
        # statistical outlier against a distribution with no spread.
        return DetectorFinding("cost_outlier", False)

    z = (amount - peer.mean_cost) / peer.std_cost
    if z <= COST_Z_THRESHOLD:
        return DetectorFinding("cost_outlier", False)

    category = record["work_category"]
    if peer.median_cost <= 0:
        # Peer median unavailable/zero -- cannot honestly state a multiple.
        return DetectorFinding("cost_outlier", True, "no_multiple", {"category": category})

    multiple = amount / peer.median_cost
    return DetectorFinding(
        "cost_outlier", True, "default", {"multiple": multiple, "category": category}
    )


# --------------------------------------------------------------------- #
# stalled_work
# --------------------------------------------------------------------- #

STALL_MONTHS_THRESHOLD = 6
# A work sanctioned less than half a year ago routinely still shows low or
# zero recorded expenditure while procurement and mobilisation happen --
# that is the innocent, common case (Understanding NidhiNetra part 6).
# Six months is long enough that "still mobilising" stops being a
# sufficient explanation on its own.

STALL_SPEND_PERCENT_THRESHOLD = 10
# Percent of sanction spent. Below this after STALL_MONTHS_THRESHOLD
# months, the work is stalled or the money is sitting unused -- the two
# honest readings the why_flagged copy itself allows (it never accuses).

STALLABLE_STATUSES = {"In Progress", "Sanctioned"}
# "Recommended" has no sanction clock running yet; "Completed" already
# finished. Only these two statuses describe a work that is supposed to be
# actively spending down its sanction.


def stalled_work(record: dict[str, Any], as_of: date) -> DetectorFinding:
    status = record.get("completion_status")
    if status not in STALLABLE_STATUSES:
        return DetectorFinding("stalled_work", False)

    sanctioned = record.get("sanctioned_amount_inr") or 0.0
    spent = record.get("expenditure_amount_inr") or 0.0
    sanction_date_str = record.get("sanction_date")

    if sanction_date_str:
        months = _months_between(date.fromisoformat(sanction_date_str), as_of)
        if months < STALL_MONTHS_THRESHOLD or sanctioned <= 0:
            return DetectorFinding("stalled_work", False)
        if spent <= 0:
            return DetectorFinding("stalled_work", True, "zero_spend", {"months": months})
        percent_spent = (spent / sanctioned) * 100
        if percent_spent < STALL_SPEND_PERCENT_THRESHOLD:
            return DetectorFinding(
                "stalled_work", True, "part_spend",
                {"months": months, "percent_spent": percent_spent},
            )
        return DetectorFinding("stalled_work", False)

    # sanction_date missing: never fabricate a computed age from it
    # (strings.json why_flagged._rules / stalled_work.no_update use_when).
    # Fall back to staleness of last_updated instead, which is a different
    # but honestly-stated signal.
    last_updated_str = record.get("last_updated")
    if not last_updated_str:
        return DetectorFinding("stalled_work", False)
    months = _months_between(date.fromisoformat(last_updated_str), as_of)
    if months < STALL_MONTHS_THRESHOLD or spent > 0:
        return DetectorFinding("stalled_work", False)
    return DetectorFinding("stalled_work", True, "no_update", {"months": months})


# --------------------------------------------------------------------- #
# expenditure_mismatch
# --------------------------------------------------------------------- #

EXPENDITURE_RATIO_Z_THRESHOLD = 2.0
# Lower than COST_Z_THRESHOLD: the spend ratio (expenditure / sanctioned)
# is already bounded at zero and clusters tightly around a typical
# spend-down curve for a given peer group, so it takes less statistical
# separation for a ratio to be a genuine peer-relative outlier than it
# does for an unbounded currency amount.


def expenditure_mismatch(record: dict[str, Any], peer: PeerGroup) -> DetectorFinding:
    sanctioned = record.get("sanctioned_amount_inr") or 0.0
    spent = record.get("expenditure_amount_inr") or 0.0
    if sanctioned <= 0:
        return DetectorFinding("expenditure_mismatch", False)

    ratio = spent / sanctioned

    if peer.std_ratio > 0:
        z = (ratio - peer.mean_ratio) / peer.std_ratio
        outside_band = z > EXPENDITURE_RATIO_Z_THRESHOLD
    else:
        # Every peer spent exactly the same fraction of its sanction --
        # cannot compute a z-score, but spending more than sanctioned, or
        # spending exactly all of it while still open, are absolute
        # violations regardless of what peers happened to do.
        outside_band = True

    if not outside_band:
        return DetectorFinding("expenditure_mismatch", False)

    if ratio > 1.0:
        percent_over = (ratio - 1.0) * 100
        return DetectorFinding(
            "expenditure_mismatch", True, "over_sanction", {"percent_over": percent_over}
        )
    if abs(ratio - 1.0) < 1e-9 and record.get("completion_status") != "Completed":
        return DetectorFinding("expenditure_mismatch", True, "full_spend_open", {})

    # The peer z-score fired but the ratio sits inside [0, 1) without being
    # exactly a full spend -- none of the three frozen templates
    # (over_sanction, amounts, full_spend_open) honestly describe "spend
    # ratio is unusually high for this peer group but still under
    # sanction" without inventing language contracts/strings.json does not
    # have. We deliberately do not fire here rather than force a mismatch
    # onto the wrong template; see this agent's final report for a note on
    # this residual gap.
    return DetectorFinding("expenditure_mismatch", False)


# --------------------------------------------------------------------- #
# agency_concentration (cross-record pass)
# --------------------------------------------------------------------- #

CONCENTRATION_Z_THRESHOLD = 2.0
MIN_SPAN_FOR_CONCENTRATION = 3
# Absolute floor: never flag an agency/vendor for spanning just two MPs or
# districts even if the surrounding population is itself unusually
# concentrated (guards against a small-n false positive when most agencies
# in the batch happen to serve exactly one MP each).
MIN_WORKS_FOR_CONCENTRATION_CANDIDACY = 2
# An agency or vendor with a single work cannot "concentrate" anything.


@dataclass(frozen=True)
class ConcentrationFinding:
    work_ids: frozenset[str]
    variant: str
    params: dict[str, Any]


def _zscores(counts: dict[str, int]) -> dict[str, float]:
    values = list(counts.values())
    if len(values) < 2:
        return dict.fromkeys(counts, 0.0)
    m = mean(values)
    s = pstdev(values)
    if s <= 0:
        return dict.fromkeys(counts, 0.0)
    return {k: (v - m) / s for k, v in counts.items()}


def detect_agency_concentration(
    records: list[dict[str, Any]],
) -> dict[str, ConcentrationFinding]:
    """Cross-record pass: for every implementing_agency and vendor_name
    that appears on at least two works, compares how many distinct MPs and
    districts (constituency is the closest field the 3.1 contract has to
    "district") it spans against every other agency's/vendor's span in
    this same batch, and flags the ones whose span is both statistically
    unusual (z > CONCENTRATION_Z_THRESHOLD across agencies/vendors in this
    run) and above an absolute floor (MIN_SPAN_FOR_CONCENTRATION), so a
    population where most agencies serve exactly one MP does not produce a
    flag on an agency serving two.

    Deliberately not part of the per-record loop: this detector's premise
    only makes sense computed once, across the whole dataset, up front.
    """
    by_agency: dict[str, list[dict[str, Any]]] = {}
    by_vendor: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        agency = record.get("implementing_agency")
        if agency:
            by_agency.setdefault(agency, []).append(record)
        vendor = record.get("vendor_name")
        if vendor:
            by_vendor.setdefault(vendor, []).append(record)

    # Spans (and the z-scores that flag "unusual") are computed across
    # EVERY agency, including ones with a single work -- those single-work
    # agencies are exactly what makes the comparison population honest.
    # Excluding them here would have silently shrunk "unusual against the
    # whole population" into "unusual against other already-busy
    # agencies", which is a much weaker and more easily gamed claim.
    # MIN_WORKS_FOR_CONCENTRATION_CANDIDACY / MIN_SPAN_FOR_CONCENTRATION
    # are applied afterward, only to decide which agencies are eligible to
    # actually fire.
    mp_span = {a: len({r["mp_name"] for r in rs}) for a, rs in by_agency.items()}
    district_span = {a: len({r["constituency"] for r in rs}) for a, rs in by_agency.items()}
    mp_z = _zscores(mp_span)
    district_z = _zscores(district_span)

    candidate_agencies = {
        a: rs for a, rs in by_agency.items() if len(rs) >= MIN_WORKS_FOR_CONCENTRATION_CANDIDACY
    }
    findings: dict[str, ConcentrationFinding] = {}
    for agency, rs in candidate_agencies.items():
        mp_unusual = (
            mp_span[agency] >= MIN_SPAN_FOR_CONCENTRATION
            and mp_z[agency] > CONCENTRATION_Z_THRESHOLD
        )
        district_unusual = (
            district_span[agency] >= MIN_SPAN_FOR_CONCENTRATION
            and district_z[agency] > CONCENTRATION_Z_THRESHOLD
        )
        if not (mp_unusual or district_unusual):
            continue

        work_ids = frozenset(r["work_id"] for r in rs)
        if mp_unusual and district_unusual:
            variant, params = "districts_and_mps", {
                "district_count": district_span[agency],
                "mp_count": mp_span[agency],
            }
        else:
            # "mps" is the declared default variant (strings.json
            # why_flagged.agency_concentration.mps.use_when: "Default.").
            variant, params = "mps", {"mp_count": mp_span[agency]}

        for work_id in work_ids:
            findings[work_id] = ConcentrationFinding(work_ids, variant, params)

    # Vendor concentration: districts only, via the dedicated "vendor"
    # template. An agency-level finding on the same work takes precedence
    # (a work can only carry one agency_concentration explanation). As
    # above, spans/z-scores are computed across every vendor so
    # single-work vendors still count in the comparison population;
    # candidacy is applied only when deciding who can fire.
    vendor_district_span = {v: len({r["constituency"] for r in rs}) for v, rs in by_vendor.items()}
    vendor_z = _zscores(vendor_district_span)
    candidate_vendors = {
        v: rs for v, rs in by_vendor.items() if len(rs) >= MIN_WORKS_FOR_CONCENTRATION_CANDIDACY
    }
    for vendor, rs in candidate_vendors.items():
        unusual = (
            vendor_district_span[vendor] >= MIN_SPAN_FOR_CONCENTRATION
            and vendor_z[vendor] > CONCENTRATION_Z_THRESHOLD
        )
        if not unusual:
            continue
        for record in rs:
            work_id = record["work_id"]
            if work_id in findings:
                continue
            findings[work_id] = ConcentrationFinding(
                frozenset(r["work_id"] for r in rs),
                "vendor",
                {"district_count": vendor_district_span[vendor]},
            )

    return findings


# --------------------------------------------------------------------- #
# Ensemble: IsolationForest + LocalOutlierFactor
# --------------------------------------------------------------------- #
# Contributes to risk_score only (risk/rank.py) -- not a fifth flag type.
# Both models look across several numeric features at once, which is what
# lets them catch a work that looks unremarkable on any single measurement
# (so none of the per-record detectors above fire) but strange across
# several at once. See Understanding NidhiNetra.html part 6, Method 2 and
# Method 3, for the plain-language intuition this mirrors.

ISOLATION_FOREST_N_ESTIMATORS = 200
# sklearn's default is 100. At hackathon-batch scale (low hundreds to low
# thousands of records) 100 trees still leave visible run-to-run wobble in
# decision_function even with random_state fixed for a *given* dataset,
# because the wobble that matters here is snapshot-to-snapshot (today's
# pull vs tomorrow's), not just literal re-runs. 200 halves that variance
# for a small constant-time cost, which is what actually backs the "stable
# inspection list" promise (Checkpoints CP2), not the random_state alone.

ISOLATION_FOREST_CONTAMINATION = 0.1
# Matches the product's own framing: District Authorities must inspect at
# least 10 percent of works under implementation every year (README, PRD).
# Calibrating the model's assumed anomaly rate to that same figure keeps
# the ensemble's internal notion of "unusual" in the same order of
# magnitude as the quota the product already exists to serve, rather than
# leaving it at sklearn's arbitrary default of "auto".

ISOLATION_FOREST_RANDOM_STATE = 42
# Eng review finding: without a fixed random_state, IsolationForest's
# bootstrap sampling reshuffles the ranking on every fit of the *same*
# data, which breaks the product's promise that an inspection list is a
# stable, reproducible document (Execution Plan 3.2, Checkpoints CP2).
# Fixed once, here, and never regenerated per run.

LOF_CONTAMINATION = 0.1  # see ISOLATION_FOREST_CONTAMINATION above.

LOF_N_NEIGHBORS_DEFAULT = 20
# Balances two failure modes described in Understanding NidhiNetra part 6,
# Method 3: too few neighbours makes the local density estimate noisy (a
# handful of nearby points can make almost anything look normal or
# strange); too many washes local outliers out into the global trend,
# which is the exact failure mode LOF exists to catch that a single global
# detector like IsolationForest would miss. Clamped down for small batches
# by `_safe_n_neighbors` below, since sklearn requires n_neighbors <
# n_samples.

_ENSEMBLE_FEATURE_RATIO_CAP = 5.0
# Spend ratio is clipped before scaling so one extreme over-sanction
# record cannot single-handedly stretch the StandardScaler's variance and
# flatten every other record's ratio feature toward zero.


def _safe_n_neighbors(n_samples: int) -> int:
    return max(1, min(LOF_N_NEIGHBORS_DEFAULT, n_samples - 1))


def _feature_matrix(records: list[dict[str, Any]], as_of: date) -> np.ndarray:
    rows = []
    for record in records:
        sanctioned = record.get("sanctioned_amount_inr") or 0.0
        spent = record.get("expenditure_amount_inr") or 0.0
        ratio = min(spent / sanctioned, _ENSEMBLE_FEATURE_RATIO_CAP) if sanctioned > 0 else 0.0
        sanction_date_str = record.get("sanction_date")
        months = (
            _months_between(date.fromisoformat(sanction_date_str), as_of)
            if sanction_date_str
            else 0
        )
        rows.append(
            [
                np.log1p(max(0.0, sanctioned)),
                np.log1p(max(0.0, spent)),
                ratio,
                float(months),
            ]
        )
    return np.array(rows, dtype=float)


def _normalize(values: np.ndarray) -> np.ndarray:
    lo, hi = float(values.min()), float(values.max())
    if hi - lo < 1e-12:
        return np.zeros_like(values)
    return (values - lo) / (hi - lo)


def ensemble_scores(records: list[dict[str, Any]], as_of: date) -> dict[str, float]:
    """Returns work_id -> anomaly score in [0, 1], the average of
    normalized IsolationForest and LOF anomaly signals over the whole
    batch. A batch smaller than 2 records cannot support either model
    meaningfully, so every score is 0.0 in that case (risk_score then
    comes entirely from the four named flags, which is the correct
    degenerate behaviour for a batch this small).
    """
    n = len(records)
    if n < 2:
        return {r["work_id"]: 0.0 for r in records}

    features = _feature_matrix(records, as_of)
    scaled = StandardScaler().fit_transform(features)

    iso = IsolationForest(
        n_estimators=ISOLATION_FOREST_N_ESTIMATORS,
        contamination=ISOLATION_FOREST_CONTAMINATION,
        random_state=ISOLATION_FOREST_RANDOM_STATE,
    )
    iso.fit(scaled)
    iso_anomaly = -iso.decision_function(scaled)  # higher = more anomalous

    lof = LocalOutlierFactor(
        n_neighbors=_safe_n_neighbors(n),
        contamination=LOF_CONTAMINATION,
    )
    lof.fit_predict(scaled)
    lof_anomaly = -lof.negative_outlier_factor_  # higher = more anomalous

    combined = (_normalize(iso_anomaly) + _normalize(lof_anomaly)) / 2.0
    return {records[i]["work_id"]: float(combined[i]) for i in range(n)}
