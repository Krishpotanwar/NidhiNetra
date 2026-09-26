"""Task 8 Part A: the offline, pipeline-side early-warning model.

Ports the validated cohort and model from `scripts/delay_model.py` (see that file for the full
rationale behind each choice) into a deterministic artifact builder. Given the served snapshot's
works and an as_of date, `build()` trains a logistic regression on a fixed sanction-date window to
check whether it can honestly rank works by risk of staying open past one year, then -- only if it
clears the ship gate -- refits on the whole cohort and scores every young work under
implementation, putting the top tenth on a "watch" list. `write()` commits the result to
data/snapshot/early_warning.json, touching nothing else in an existing snapshot (same discipline
as build_snapshot.write_duplicate_candidates).

Three leakage guards carry over unchanged from the reference script:
  1. expenditure_amount_inr is never read here -- NUMERIC/CATEGORICAL exclude it entirely, so
     changing it cannot change the output.
  2. The agency prior used to train/evaluate the model is computed only from works sanctioned
     before the train cutoff (or, for the final scoring model, on or before the cohort's own
     end), smoothed toward the global rate by AGENCY_PRIOR_SMOOTHING pseudo-counts.
  3. exposure_months is deliberately not a feature: every scored work is young by construction
     (sanctioned within the last year), so exposure would only encode that fact, not risk.
"""

from __future__ import annotations

import math
from datetime import date
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from .build_snapshot import SNAPSHOT_DIR, _commit_staged, _stage_json
from .risk.detectors import STALLABLE_STATUSES

MODEL_VERSION = "early_warning_v1"
# exposure_months is excluded on purpose: see the module docstring's leakage guard 3.
NUMERIC = ["log_sanctioned", "agency_prior", "sanction_month"]
CATEGORICAL = ["work_category", "state"]
AGENCY_PRIOR_SMOOTHING = 20  # pseudo-counts pulling a small agency toward the global rate
WATCH_SHARE = 0.10
MIN_TEST_AUC = 0.65
MIN_TEST_LIFT = 1.8

_FEATURE_COLUMNS = NUMERIC + CATEGORICAL


def _agency_prior_map(history: pd.DataFrame) -> tuple[dict[str, float], float]:
    """The smoothed mean of `y` by `implementing_agency` over `history`, and history's own
    global rate -- the fallback for a null or unseen agency. Same formula as delay_model.py.
    """
    global_rate = float(history["y"].mean())
    stats = history.groupby("implementing_agency")["y"].agg(["mean", "count"])
    smoothed = (
        (stats["mean"] * stats["count"] + global_rate * AGENCY_PRIOR_SMOOTHING)
        / (stats["count"] + AGENCY_PRIOR_SMOOTHING)
    ).to_dict()
    return smoothed, global_rate


def _add_features(
    frame: pd.DataFrame, smoothed: dict[str, float], global_rate: float
) -> pd.DataFrame:
    frame = frame.copy()
    frame["agency_prior"] = frame["implementing_agency"].map(smoothed).fillna(global_rate)
    frame["log_sanctioned"] = np.log1p(frame["sanctioned_amount_inr"].fillna(0))
    frame["sanction_month"] = frame["sanction_date"].dt.month
    return frame


def _make_pipeline() -> Pipeline:
    pre = ColumnTransformer(
        [
            ("n", StandardScaler(), NUMERIC),
            (
                "c",
                OneHotEncoder(handle_unknown="ignore", min_frequency=30, sparse_output=False),
                CATEGORICAL,
            ),
        ]
    )
    return Pipeline([("pre", pre), ("clf", LogisticRegression(max_iter=2000))])


def build(works: pd.DataFrame, as_of: date) -> dict[str, Any]:
    """Deterministic: the same `works` and `as_of` always produce an identical dict.

    Algorithm (Task 8's brief has the exact windows, smoothing and ship-gate thresholds):
      1. Parse sanction_date, drop unparseable rows, label y = completion_status != "Completed".
      2. Cohort = works sanctioned in [as_of-26mo, as_of-17mo]; train is the part before
         as_of-20mo, test is the rest.
      3. agency_prior is the smoothed mean of y by implementing_agency over works sanctioned
         before the train cutoff; a null or unseen agency gets that history's global rate.
      4. A StandardScaler+OneHotEncoder-preprocessed logistic regression.
      5. Test metrics: roc_auc, average_precision, base_rate, lift_at_10, rounded to 3 decimals.
      6. Below the ship gate: status "not_shipped", nothing scored. Otherwise refit on the whole
         cohort (prior recomputed from works sanctioned on or before the cohort's end) and score
         every young work under implementation (STALLABLE_STATUSES, sanctioned 0 to 365 days
         ago), ranked by score desc then work_id asc, watch = the top tenth.
    """
    works = works.copy()
    works["sanction_date"] = pd.to_datetime(works["sanction_date"], errors="coerce")
    works = works.dropna(subset=["sanction_date"]).copy()
    works["y"] = (works["completion_status"] != "Completed").astype(int)

    as_of_ts = pd.Timestamp(as_of)
    start = as_of_ts - pd.DateOffset(months=26)
    cutoff = as_of_ts - pd.DateOffset(months=20)
    end = as_of_ts - pd.DateOffset(months=17)

    cohort = works[(works["sanction_date"] >= start) & (works["sanction_date"] <= end)]
    train_mask = cohort["sanction_date"] < cutoff
    train = cohort[train_mask]
    test = cohort[~train_mask]

    history = works[works["sanction_date"] < cutoff]
    smoothed, global_rate = _agency_prior_map(history)
    train = _add_features(train, smoothed, global_rate)
    test = _add_features(test, smoothed, global_rate)

    pipe = _make_pipeline().fit(train[_FEATURE_COLUMNS], train["y"])
    probability = pipe.predict_proba(test[_FEATURE_COLUMNS])[:, 1]
    y_test = test["y"].to_numpy()

    base_rate = float(y_test.mean())
    roc_auc = float(roc_auc_score(y_test, probability)) if len(set(probability)) > 1 else 0.5
    average_precision = float(average_precision_score(y_test, probability))
    k = max(1, int(0.10 * len(test)))
    lift_at_10 = float(y_test[np.argsort(-probability)[:k]].mean() / base_rate)

    metrics = {
        "roc_auc": round(roc_auc, 3),
        "average_precision": round(average_precision, 3),
        "base_rate": round(base_rate, 3),
        "lift_at_10": round(lift_at_10, 3),
    }

    artifact: dict[str, Any] = {
        "model_version": MODEL_VERSION,
        "data_as_of": as_of.isoformat(),
        "status": "not_shipped",
        "cohort": {
            "start": start.date().isoformat(),
            "train_cutoff": cutoff.date().isoformat(),
            "end": end.date().isoformat(),
            "train_n": int(len(train)),
            "test_n": int(len(test)),
        },
        "features": {"numeric": list(NUMERIC), "categorical": list(CATEGORICAL)},
        "metrics": metrics,
        "scored_n": 0,
        "watch_n": 0,
        "watch": [],
    }

    if metrics["roc_auc"] < MIN_TEST_AUC or metrics["lift_at_10"] < MIN_TEST_LIFT:
        return artifact

    # Ships: refit on the whole cohort, with the prior recomputed from works sanctioned on or
    # before `end` -- richer than the training-only history above, and still bounded by the
    # cohort's own end, so nothing after `end` leaks in.
    final_history = works[works["sanction_date"] <= end]
    final_smoothed, final_global_rate = _agency_prior_map(final_history)
    cohort_fitted = _add_features(cohort, final_smoothed, final_global_rate)
    final_pipe = _make_pipeline().fit(cohort_fitted[_FEATURE_COLUMNS], cohort_fitted["y"])

    age_days = (as_of_ts - works["sanction_date"]).dt.days
    young = works[works["completion_status"].isin(STALLABLE_STATUSES) & age_days.between(0, 365)]
    young = _add_features(young, final_smoothed, final_global_rate)
    # sklearn's transform() refuses a zero-row frame just as fit() does, and a snapshot can
    # (in principle, and in a small test fixture, in practice) have no young works at all.
    scores = final_pipe.predict_proba(young[_FEATURE_COLUMNS])[:, 1] if len(young) else np.array([])

    ranked = pd.DataFrame({"work_id": young["work_id"].to_numpy(), "score": scores})
    ranked = ranked.sort_values(["score", "work_id"], ascending=[False, True])

    scored_n = int(len(ranked))
    watch_n = math.ceil(WATCH_SHARE * scored_n)
    artifact.update(
        {
            "status": "shipped",
            "scored_n": scored_n,
            "watch_n": watch_n,
            "watch": ranked["work_id"].head(watch_n).tolist(),
        }
    )
    return artifact


def write(artifact: dict[str, Any], snapshot_dir: Path | None = None) -> Path:
    """Adds or refreshes early_warning.json in an existing snapshot and touches nothing else.
    Mirrors build_snapshot.write_duplicate_candidates: a full rebuild would score again as of
    today, so this cannot move a score, rank or flag.
    """
    final_path = (snapshot_dir or SNAPSHOT_DIR) / "early_warning.json"
    _commit_staged(_stage_json(artifact, final_path), final_path)
    return final_path


__all__ = [
    "AGENCY_PRIOR_SMOOTHING",
    "CATEGORICAL",
    "MIN_TEST_AUC",
    "MIN_TEST_LIFT",
    "MODEL_VERSION",
    "NUMERIC",
    "WATCH_SHARE",
    "build",
    "write",
]
