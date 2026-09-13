"""A supervised model on a question this dataset can honestly answer: will a work
still be incomplete? -- the evidence behind slide 14 of the round-2 deck.

Run from `05 App/`:
    uv run python scripts/delay_model.py

This predicts DELAY RISK, never fraud. No labelled fraud data exists for this scheme,
so no fraud classifier is trained anywhere in this project. `completion_status` is a
real, observed label, and it supports a real train/test evaluation.

Three leakage traps are closed deliberately, and each is worth stating out loud:
  1. Expenditure is excluded -- it is observed after sanction and would leak the answer.
  2. The agency prior is computed only from works sanctioned before the training
     cutoff, and smoothed, so no test-period information flows backwards.
  3. Exposure is held roughly constant by fixing one sanction window -- otherwise the
     model mostly learns which works are simply newer.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

ROOT = Path(__file__).resolve().parent.parent
SNAPSHOT_DATE = pd.Timestamp("2026-09-04")
COHORT_START, COHORT_END = "2024-07-01", "2025-03-31"
TRAIN_CUTOFF = "2025-01-01"
AGENCY_PRIOR_SMOOTHING = 20  # pseudo-counts pulling a small agency toward the global rate

NUMERIC = ["log_sanctioned", "exposure_months", "agency_prior", "sanction_month"]
CATEGORICAL = ["work_category", "state"]


def build_cohort() -> tuple[pd.DataFrame, pd.DataFrame]:
    works = pd.read_parquet(ROOT / "data" / "snapshot" / "works.parquet")
    works["sanction_date"] = pd.to_datetime(works["sanction_date"], errors="coerce")
    works = works.dropna(subset=["sanction_date"]).copy()
    works["y"] = (works["completion_status"] != "Completed").astype(int)
    works["exposure_months"] = ((SNAPSHOT_DATE - works["sanction_date"]).dt.days / 30.44).round(1)

    cohort = works[(works.sanction_date >= COHORT_START) & (works.sanction_date <= COHORT_END)]
    train = cohort[cohort.sanction_date < TRAIN_CUTOFF].copy()
    test = cohort[cohort.sanction_date >= TRAIN_CUTOFF].copy()

    history = works[works.sanction_date < TRAIN_CUTOFF]
    global_rate = history.y.mean()
    stats = history.groupby("implementing_agency")["y"].agg(["mean", "count"])
    smoothed = ((stats["mean"] * stats["count"] + global_rate * AGENCY_PRIOR_SMOOTHING)
                / (stats["count"] + AGENCY_PRIOR_SMOOTHING)).to_dict()
    for frame in (train, test):
        frame["agency_prior"] = frame["implementing_agency"].map(smoothed).fillna(global_rate)
        frame["log_sanctioned"] = np.log1p(frame["sanctioned_amount_inr"].fillna(0))
        frame["sanction_month"] = frame["sanction_date"].dt.month
    return train, test


def evaluate(train: pd.DataFrame, test: pd.DataFrame) -> None:
    pre = ColumnTransformer([
        ("numeric", StandardScaler(), NUMERIC),
        ("categorical", OneHotEncoder(handle_unknown="ignore", min_frequency=30,
                                      sparse_output=False), CATEGORICAL),
    ])
    x_train, y_train = train[NUMERIC + CATEGORICAL], train.y.values
    x_test, y_test = test[NUMERIC + CATEGORICAL], test.y.values

    models = {
        "baseline -- predict the base rate": DummyClassifier(strategy="prior"),
        "logistic regression": LogisticRegression(max_iter=2000),
        "gradient boosting (HistGBM)": HistGradientBoostingClassifier(
            max_iter=300, learning_rate=0.06, random_state=42),
        "logistic + Platt calibration": CalibratedClassifierCV(
            LogisticRegression(max_iter=2000), method="sigmoid", cv=5),
    }
    print(f"cohort sanctioned {COHORT_START}..{COHORT_END}, observed {SNAPSHOT_DATE.date()}")
    print(f"train n={len(train):,} (base rate {y_train.mean():.3f})   "
          f"test n={len(test):,} (base rate {y_test.mean():.3f})\n")
    print(f"{'model':<36}{'ROC-AUC':>9}{'PR-AUC':>9}{'Brier':>9}{'lift@10%':>10}")
    for name, estimator in models.items():
        pipe = Pipeline([("pre", pre), ("clf", estimator)]).fit(x_train, y_train)
        probability = pipe.predict_proba(x_test)[:, 1]
        k = max(1, int(0.10 * len(test)))
        lift = y_test[np.argsort(-probability)[:k]].mean() / y_test.mean()
        auc = roc_auc_score(y_test, probability) if len(set(probability)) > 1 else 0.5
        print(f"{name:<36}{auc:>9.3f}{average_precision_score(y_test, probability):>9.3f}"
              f"{brier_score_loss(y_test, probability):>9.3f}{lift:>10.2f}")

    fitted = Pipeline([("pre", pre), ("clf", LogisticRegression(max_iter=2000))]).fit(x_train, y_train)
    names = NUMERIC + list(
        fitted.named_steps["pre"].named_transformers_["categorical"]
        .get_feature_names_out(CATEGORICAL))
    print("\nstrongest standardised coefficients (positive = more likely to stay incomplete)")
    for name, coef in sorted(zip(names, fitted.named_steps["clf"].coef_[0], strict=True),
                             key=lambda t: -abs(t[1]))[:6]:
        print(f"  {coef:>+7.3f}  {name}")


if __name__ == "__main__":
    evaluate(*build_cohort())
