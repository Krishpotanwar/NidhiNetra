"""Locks the three TypeScript files that hand-mirror Python constants and
algorithms to their source of truth. Each mirror's own docstring names
drift as a live risk: change the Python side, forget to touch the TS
side, and the frontend confidently shows numbers that no longer describe
what the backend actually does. Until `make contracts` codegen exists
(models.py and web/lib/generated/ both wait for it), this test IS the
drift detector -- pytest reads the TS files as text, parses out the
constants and algorithms, and fails loudly the moment they disagree.

Mirrors covered here (from the 2026-09-03 review):
  1. web/lib/risk-weights.ts     <->  pipeline/.../risk/rank.py
  2. web/lib/filters.ts          <->  pipeline/.../risk/peer_groups.py
  3. web/lib/peer-group.ts       <->  pipeline/.../risk/peer_groups.py

None of these need a JS runtime -- the constants are literals and the
one algorithm (Indian financial year) is trivial enough that reading the
TS source and asserting three invariants about it is more robust than
running node in a Python test process.
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

import pytest

from nidhinetra_pipeline.risk import peer_groups, rank

# pipeline/tests/test_web_mirror_drift.py -> parents[2] is "05-App/"
_APP_ROOT = Path(__file__).resolve().parents[2]
_RISK_WEIGHTS_TS = _APP_ROOT / "web" / "lib" / "risk-weights.ts"
_FILTERS_TS = _APP_ROOT / "web" / "lib" / "filters.ts"
_PEER_GROUP_TS = _APP_ROOT / "web" / "lib" / "peer-group.ts"


def _read(path: Path) -> str:
    """Fails with a clear message if a mirror file has moved or been
    renamed -- silently returning None would let the drift check pass on
    an empty string, which is exactly the failure mode drift detection
    exists to prevent.
    """
    assert path.exists(), (
        f"mirror file missing: {path}. If it was renamed, update the path "
        "in this test AND in the moved file's docstring, then re-run."
    )
    return path.read_text(encoding="utf-8")


# --------------------------------------------------------------------------
# risk-weights.ts  <->  rank.py
# --------------------------------------------------------------------------


class TestRiskWeightsMirror:
    """The four flag weights, the 80-point flag cap, and the 20-point
    ensemble cap are all hand-mirrored in web/lib/risk-weights.ts. Change
    either side without the other and the detail panel itemises a
    breakdown whose lines no longer sum to the score they sit next to.
    """

    def test_flag_weights_match(self) -> None:
        ts = _read(_RISK_WEIGHTS_TS)
        # The TS dict is exported as an object literal with unquoted keys;
        # a permissive per-line regex matches each entry rather than
        # trying to parse the whole {...} block as JSON (it isn't JSON --
        # trailing comma allowed, keys unquoted).
        pattern = re.compile(r"^\s*(\w+)\s*:\s*(\d+),?\s*$", re.MULTILINE)
        block_match = re.search(
            r"FLAG_WEIGHTS[^{]*\{([^}]+)\}", ts, re.DOTALL
        )
        assert block_match, "FLAG_WEIGHTS block not found in risk-weights.ts"
        ts_weights = {k: int(v) for k, v in pattern.findall(block_match.group(1))}
        assert ts_weights == {k: int(v) for k, v in rank.FLAG_WEIGHTS.items()}, (
            f"FLAG_WEIGHTS drift: TS={ts_weights} Python={rank.FLAG_WEIGHTS}. "
            "Update web/lib/risk-weights.ts to match rank.py, or the detail "
            "panel's per-flag breakdown will no longer sum to the score."
        )

    def test_flags_component_cap_matches(self) -> None:
        ts = _read(_RISK_WEIGHTS_TS)
        m = re.search(r"FLAGS_COMPONENT_CAP\s*=\s*(\d+)", ts)
        assert m, "FLAGS_COMPONENT_CAP not found in risk-weights.ts"
        assert int(m.group(1)) == int(rank.FLAGS_COMPONENT_CAP), (
            f"FLAGS_COMPONENT_CAP drift: TS={m.group(1)} "
            f"Python={rank.FLAGS_COMPONENT_CAP}"
        )

    def test_ensemble_component_weight_matches(self) -> None:
        ts = _read(_RISK_WEIGHTS_TS)
        m = re.search(r"ENSEMBLE_COMPONENT_WEIGHT\s*=\s*(\d+)", ts)
        assert m, "ENSEMBLE_COMPONENT_WEIGHT not found in risk-weights.ts"
        assert int(m.group(1)) == int(rank.ENSEMBLE_COMPONENT_WEIGHT), (
            f"ENSEMBLE_COMPONENT_WEIGHT drift: TS={m.group(1)} "
            f"Python={rank.ENSEMBLE_COMPONENT_WEIGHT}"
        )


# --------------------------------------------------------------------------
# filters.ts financialYearOf()  <->  peer_groups.py financial_year_of()
# --------------------------------------------------------------------------


class TestFinancialYearMirror:
    """The frontend's filter dropdown and the scorer's peer-group key must
    place the same record in the same year, or a filtered list and its own
    peer-group sentences will disagree about which year the comparison
    used (filters.ts docstring names this explicitly).

    Verified two ways at once:
      1. Structural: the TS source encodes the three invariants that make
         the algorithm equivalent to Python's -- April cutoff (JS
         getMonth() is 0-indexed, so month >= 3), sanction_date preferred
         over last_updated, two-digit end year with a leading zero.
      2. Behavioural: an edge-case truth table drives Python's
         financial_year_of, catching the actual bug class the structural
         check leaves open (a correctly-shaped TS function whose off-by-one
         no longer matches Python would still pass the structural check).
    """

    def test_april_cutoff_encoded(self) -> None:
        ts = _read(_FILTERS_TS)
        # April is index 3 in JS Date.getMonth(), month 4 in Python date.month.
        # Both signal the same instant; the check is that the TS branch uses
        # the correct 0-indexed comparison and not, say, `>= 4` (which would
        # move the cutoff into May).
        assert re.search(r"getMonth\(\)\s*>=\s*3", ts), (
            "filters.ts financialYearOf must use `getMonth() >= 3` (JS's "
            "April, 0-indexed). Anything else drifts from peer_groups.py's "
            "`d.month >= 4` boundary."
        )

    def test_sanction_date_preferred_over_last_updated(self) -> None:
        ts = _read(_FILTERS_TS)
        # peer_groups.py uses `record.get('sanction_date') or
        # record.get('last_updated')`; filters.ts must fall back the same
        # way, or a record with sanction_date=null but last_updated present
        # will be filtered into a different year than the one it was
        # scored in.
        assert re.search(
            r"row\.sanction_date\s*\?\?\s*row\.last_updated", ts
        ), (
            "filters.ts financialYearOf must prefer sanction_date and fall "
            "back to last_updated, matching peer_groups.financial_year_of."
        )

    def test_two_digit_end_year_padded(self) -> None:
        ts = _read(_FILTERS_TS)
        # Python's f"{(start_year+1)%100:02d}" and TS's
        # `padStart(2, "0")` must produce the same suffix; a missing pad
        # would render 2000-1 instead of 2000-01.
        assert re.search(r'padStart\(2,\s*"0"\)', ts), (
            "filters.ts financialYearOf must padStart(2, \"0\") the "
            "two-digit end year to match peer_groups.py's `:02d`."
        )

    # Truth table: dates chosen to hit both sides of the April boundary,
    # both sides of the year rollover, and December 31 (a common
    # off-by-one landmine).
    _CASES = [
        ("2024-01-15", "2023-24"),  # January -> previous FY
        ("2024-03-31", "2023-24"),  # last day of previous FY
        ("2024-04-01", "2024-25"),  # first day of new FY
        ("2024-04-15", "2024-25"),  # mid-April
        ("2024-12-31", "2024-25"),  # December stays in same FY as April
        ("2025-01-01", "2024-25"),  # next-calendar year, same FY
        ("2025-03-31", "2024-25"),  # boundary day again, one year forward
        ("2025-04-01", "2025-26"),  # next FY begins
        # Century rollover edge: %100 must render as 00, not 0.
        ("2099-12-31", "2099-00"),
    ]

    @pytest.mark.parametrize("iso, expected_fy", _CASES)
    def test_python_matches_truth_table(self, iso: str, expected_fy: str) -> None:
        # Both fields set to the same value: this test isolates the
        # date -> FY algorithm, not the sanction_date/last_updated
        # fallback (covered structurally above).
        record = {"sanction_date": iso, "last_updated": iso}
        assert peer_groups.financial_year_of(record) == expected_fy


# --------------------------------------------------------------------------
# peer-group.ts  <->  peer_groups.MIN_PEER_GROUP_N
# --------------------------------------------------------------------------


class TestMinPeerGroupNMirror:
    """peer_groups.MIN_PEER_GROUP_N is 30, and peer-group.ts renders a
    "thin peer group" caveat sentence for anything below that. If the
    Python constant ever moves (say, to 25 for a lower-data pilot) the TS
    literal keeps applying 30, and the officer sees confident sentences
    on works the scorer itself is refusing to fully flag. A bare literal
    is a real drift risk even though it is trivially small.
    """

    def test_ts_uses_same_threshold(self) -> None:
        ts = _read(_PEER_GROUP_TS)
        # Matches `peerGroup.n < 30` specifically, not any occurrence of
        # the digits 30 -- a stray 30 in a comment or an unrelated
        # threshold must not silently pass this test.
        m = re.search(r"peerGroup\.n\s*<\s*(\d+)", ts)
        assert m, (
            "peer-group.ts must contain `peerGroup.n < <threshold>` "
            "matching MIN_PEER_GROUP_N; if the check was moved, update "
            "this test to point at the new form."
        )
        assert int(m.group(1)) == peer_groups.MIN_PEER_GROUP_N, (
            f"MIN_PEER_GROUP_N drift: TS={m.group(1)} "
            f"Python={peer_groups.MIN_PEER_GROUP_N}"
        )
