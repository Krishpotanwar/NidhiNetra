"""Peer-group construction for the NidhiNetra risk engine.

A peer group is the comparison set a work is judged against: works sharing
the same (work_category, state, financial_year). Every statistical claim in
why_flagged is only as honest as the group it is measured against -- see
`Understanding NidhiNetra.html` part 6 ("a hill road genuinely costs more").
That is why the key is this specific (category AND state AND year, not any
one alone), and why groups below the eng-review minimum of 30 are excluded
from flagging entirely rather than flagged with a caveat, and never widened
to a broader category just to clear the floor. Widening would destroy the
exact specificity that makes the comparison defensible (Execution Plan 3.2,
Checkpoints CP2).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from statistics import mean, pstdev, quantiles
from typing import Any

# Eng review rule (Checkpoints CP2, risk_scored_record.schema.json
# peer_group.n minimum). Never lower this. Never "fix" a low-n group by
# widening its key instead -- see module docstring.
MIN_PEER_GROUP_N = 30

PeerGroupKey = tuple[str, str, str]  # (work_category, state, financial_year)


def financial_year_of(record: dict[str, Any]) -> str | None:
    """Indian financial year label for a record, e.g. "2023-24" (Apr-Mar).

    Prefers sanction_date, since that is when the work actually entered its
    peer cohort's spending year. Falls back to last_updated when
    sanction_date is null -- normalized_record.schema.json marks
    sanction_date "degradable", and last_updated is always required and
    non-null, so this fallback means a record only loses its peer group
    when both dates are literally unusable, not merely when the more
    specific one is missing.
    """
    raw = record.get("sanction_date") or record.get("last_updated")
    if not raw:
        return None
    try:
        d = date.fromisoformat(raw)
    except ValueError:
        return None
    start_year = d.year if d.month >= 4 else d.year - 1
    return f"{start_year}-{(start_year + 1) % 100:02d}"


def peer_group_key(record: dict[str, Any]) -> PeerGroupKey | None:
    """The (category, state, financial_year) grouping key, or None when the
    record lacks enough information to place it in any peer group at all.
    A record with no key never gets a peer group and therefore never gets
    flagged, by construction (see engine.py).
    """
    category = record.get("work_category")
    state = record.get("state")
    if not category or not state:
        return None
    fy = financial_year_of(record)
    if fy is None:
        return None
    return (category, state, fy)


@dataclass(frozen=True)
class PeerGroup:
    """Group statistics for one (work_category, state, financial_year)
    cohort. Only ever handed to a detector once its `n` has already been
    checked against MIN_PEER_GROUP_N by `peer_group_for` -- detectors do
    not re-check this themselves, by design, so there is exactly one place
    in the codebase that can get the eng-review rule wrong.
    """

    key: PeerGroupKey
    label: str
    n: int
    mean_cost: float
    std_cost: float
    median_cost: float
    q1_cost: float
    q3_cost: float
    mean_ratio: float  # expenditure / sanctioned, averaged over the group
    std_ratio: float
    work_ids: frozenset[str] = field(default_factory=frozenset)

    @property
    def iqr_cost(self) -> float:
        return self.q3_cost - self.q1_cost

    def as_contract(self) -> dict[str, Any]:
        """The exact shape risk_scored_record.schema.json's peer_group
        expects: label and n, nothing else. Internal stats (mean_cost,
        std_cost, ...) are for detectors only and never leave this module.
        """
        return {"label": self.label, "n": self.n}


def _stats(values: list[float]) -> tuple[float, float, float, float, float]:
    """mean, std (population), median, q1, q3 -- guarded for small n."""
    if not values:
        return 0.0, 0.0, 0.0, 0.0, 0.0
    m = mean(values)
    s = pstdev(values) if len(values) > 1 else 0.0
    if len(values) >= 2:
        # method="exclusive" (the default) matches the conventional
        # "quartile of a sample" definition used in stats textbooks and in
        # spreadsheets' QUARTILE.EXC -- appropriate here since a peer group
        # is a sample of works, not the full population of all possible
        # works of that kind.
        qs = quantiles(values, n=4)
        q1, med, q3 = qs[0], qs[1], qs[2]
    else:
        q1 = med = q3 = values[0]
    return m, s, med, q1, q3


def build_peer_index(
    records: list[dict[str, Any]],
) -> dict[PeerGroupKey, PeerGroup]:
    """Groups every record by (work_category, state, financial_year) and
    computes the statistics detectors need. Computed for every group
    regardless of size -- the MIN_PEER_GROUP_N floor is enforced only at
    lookup time in `peer_group_for`, so a small group's stats exist (e.g.
    for tests and diagnostics) but `peer_group_for` never hands them out
    for use in a flag.
    """
    groups: dict[PeerGroupKey, list[dict[str, Any]]] = {}
    for record in records:
        key = peer_group_key(record)
        if key is None:
            continue
        groups.setdefault(key, []).append(record)

    index: dict[PeerGroupKey, PeerGroup] = {}
    for key, members in groups.items():
        category, state, fy = key
        costs = [
            float(m["sanctioned_amount_inr"])
            for m in members
            if m.get("sanctioned_amount_inr") is not None
        ]
        ratios = [
            float(m["expenditure_amount_inr"]) / float(m["sanctioned_amount_inr"])
            for m in members
            if m.get("sanctioned_amount_inr") not in (None, 0)
            and m.get("expenditure_amount_inr") is not None
        ]
        mean_cost, std_cost, median_cost, q1_cost, q3_cost = _stats(costs)
        mean_ratio, std_ratio, *_ = _stats(ratios) if ratios else (0.0, 0.0, 0.0, 0.0, 0.0)

        index[key] = PeerGroup(
            key=key,
            # Category, then state, then year -- the frozen order from
            # NIDHINETRA-DESIGN-BRIEF.md section 4 ("Compared against
            # 1,72,961 road works in Bihar, 2023-24") and the PRD M3
            # verbatim explicit form in strings.json's peer_group.explicit
            # variant. The other historical form (peer_group.contextual,
            # "in this state for this year") elides the state and year for
            # on-screen contexts where filters are already visible; that is
            # a rendering choice for the frontend to make from n/label, not
            # something this label itself should ever omit, because the
            # label is stored data an API consumer might show with no
            # filters on screen at all (e.g. an export or a screenshot).
            label=f"{category} works, {state}, {fy}",
            n=len(members),
            mean_cost=mean_cost,
            std_cost=std_cost,
            median_cost=median_cost,
            q1_cost=q1_cost,
            q3_cost=q3_cost,
            mean_ratio=mean_ratio,
            std_ratio=std_ratio,
            work_ids=frozenset(m["work_id"] for m in members),
        )
    return index


def peer_group_for(
    record: dict[str, Any],
    all_records: list[dict[str, Any]],
    index: dict[PeerGroupKey, PeerGroup] | None = None,
) -> PeerGroup | None:
    """The one function that decides whether a record is even eligible to
    be flagged. Returns None whenever:
      - the record cannot be placed in any peer group (missing category,
        state, or both dates), or
      - its true peer group has fewer than MIN_PEER_GROUP_N members.

    None here must propagate all the way to "flags = [], peer_group =
    null" in engine.py, with no detector ever running on this record. See
    the CRITICAL test in tests/risk for the assertion that this holds even
    for an arbitrarily extreme record.
    """
    key = peer_group_key(record)
    if key is None:
        return None
    idx = index if index is not None else build_peer_index(all_records)
    group = idx.get(key)
    if group is None or group.n < MIN_PEER_GROUP_N:
        return None
    return group
