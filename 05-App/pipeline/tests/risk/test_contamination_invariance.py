"""F-15 (nemotronreview.md): the contamination setting does not calibrate
the ensemble score.

ensemble_scores() min-max normalises IsolationForest's decision_function,
which contamination only shifts by a constant (offset_), and LOF's
negative_outlier_factor_, which does not depend on contamination at all.
Every contamination value therefore yields the same final scores. This test
locks that in, so no comment or document can again claim that the 10
percent inspection quota is used as a calibrated anomaly rate.
"""

from __future__ import annotations

import pytest
from nidhinetra_pipeline.risk import detectors

from .conftest import AS_OF, make_peer_group, make_record


def _records() -> list[dict]:
    return [
        *make_peer_group(60, spread=50_000.0),
        make_record(
            work_id="SYN-FAR",
            sanctioned_amount_inr=9_000_000.0,
            expenditure_amount_inr=0.0,
        ),
    ]


@pytest.mark.parametrize("contamination", [0.01, 0.05, 0.25, 0.5])
def test_contamination_does_not_change_the_ensemble_scores(monkeypatch, contamination):
    records = _records()
    baseline = detectors.ensemble_scores(records, AS_OF)

    monkeypatch.setattr(detectors, "ISOLATION_FOREST_CONTAMINATION", contamination)
    monkeypatch.setattr(detectors, "LOF_CONTAMINATION", contamination)
    changed = detectors.ensemble_scores(records, AS_OF)

    assert changed.keys() == baseline.keys()
    for work_id, score in baseline.items():
        assert changed[work_id] == pytest.approx(score, abs=1e-9)
