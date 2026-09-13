"""Regenerates every quantitative claim in the SIH round-2 deck from the committed
snapshot, so any figure on a slide can be re-derived in front of a reviewer.

Run from `05-App/`:
    uv run python scripts/deck_figures.py

Nothing here is cached or hand-entered. If a number in the deck disagrees with this
script's output, the deck is wrong.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

SNAPSHOT = Path(__file__).resolve().parent.parent / "data" / "snapshot"
# Clause 4.5.2 of the MPLADS Guidelines (April 2023) sets the quota against "works
# under implementation", not against every work on the portal -- so the denominator
# below is deliberately narrower than the full record count.
UNDER_IMPLEMENTATION = ("In Progress", "Sanctioned")
STATUTORY_QUOTA_FRACTION = 0.10


def load() -> pd.DataFrame:
    works = pd.read_parquet(SNAPSHOT / "works.parquet")
    scored = pd.read_parquet(SNAPSHOT / "scored.parquet")
    frame = works.merge(scored, on="work_id")
    frame["flag_count"] = frame["flags"].map(lambda f: len(json.loads(f)) if f else 0)
    frame["is_flagged"] = frame["flag_count"] > 0
    return frame


def scheme_totals(frame: pd.DataFrame) -> None:
    sanctioned = frame["sanctioned_amount_inr"].sum()
    spent = frame["expenditure_amount_inr"].sum()
    print("SLIDE 2 -- scheme scale")
    print(f"  works                {len(frame):>12,}")
    print(f"  under implementation {frame.completion_status.isin(UNDER_IMPLEMENTATION).sum():>12,}")
    print(f"  sanctioned           Rs {sanctioned / 1e7:>10,.0f} crore")
    print(f"  spent                Rs {spent / 1e7:>10,.0f} crore")
    print(f"  unspent              Rs {(sanctioned - spent) / 1e7:>10,.0f} crore "
          f"({100 * (sanctioned - spent) / sanctioned:.1f}%)")


def detector_counts(frame: pd.DataFrame) -> None:
    counts: dict[str, int] = {}
    for raw in frame["flags"].fillna(""):
        for flag in (json.loads(raw) if raw else []):
            counts[flag] = counts.get(flag, 0) + 1
    print("\nSLIDE 11 -- detector firing counts")
    for flag, n in sorted(counts.items(), key=lambda kv: -kv[1]):
        print(f"  {flag:<24}{n:>8,}")
    print(f"  {'>=1 flag':<24}{frame.is_flagged.sum():>8,} "
          f"({100 * frame.is_flagged.mean():.1f}%)")


def targeting_performance(frame: pd.DataFrame) -> None:
    """The lift numbers on slides 5 and 15, computed on the statutory base."""
    pool = frame[frame.completion_status.isin(UNDER_IMPLEMENTATION)].sort_values("inspection_rank")
    quota = round(len(pool) * STATUTORY_QUOTA_FRACTION)
    top = pool.head(quota)
    at_risk = (pool.sanctioned_amount_inr - pool.expenditure_amount_inr).sum()
    at_risk_top = (top.sanctioned_amount_inr - top.expenditure_amount_inr).sum()
    print("\nSLIDES 5 & 15 -- targeting the statutory quota")
    print(f"  pool (under implementation)     {len(pool):>10,}")
    print(f"  statutory 10% quota             {quota:>10,}")
    print(f"  base rate flagged in pool       {100 * pool.is_flagged.mean():>9.1f}%")
    print(f"  precision inside the quota      {100 * top.is_flagged.mean():>9.1f}%")
    print(f"  lift vs random                  {top.is_flagged.mean() / pool.is_flagged.mean():>9.2f}x")
    print(f"  multi-flag works captured       "
          f"{(top.flag_count >= 2).sum():,} of {(pool.flag_count >= 2).sum():,}")
    print(f"  rupees inside quota             Rs {top.sanctioned_amount_inr.sum() / 1e7:,.0f} cr "
          f"of Rs {pool.sanctioned_amount_inr.sum() / 1e7:,.0f} cr "
          f"({100 * top.sanctioned_amount_inr.sum() / pool.sanctioned_amount_inr.sum():.1f}%)")
    print(f"  unspent-at-risk inside quota    Rs {at_risk_top / 1e7:,.0f} cr of "
          f"Rs {at_risk / 1e7:,.0f} cr ({100 * at_risk_top / at_risk:.1f}%)")


def peer_group_coverage(frame: pd.DataFrame) -> None:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pipeline" / "src"))
    from nidhinetra_pipeline.risk.peer_groups import MIN_PEER_GROUP_N, build_peer_index

    records = frame.to_dict("records")
    for record in records:
        for key in ("sanction_date", "last_updated", "implementing_agency", "vendor_name"):
            value = record.get(key)
            if value is not None and not isinstance(value, str):
                record[key] = None if pd.isna(value) else str(value)
    index = build_peer_index(records)
    clearing = {k: g for k, g in index.items() if g.n >= MIN_PEER_GROUP_N}
    covered = sum(g.n for g in clearing.values())
    print("\nSLIDES 3 & 11 -- peer groups")
    print(f"  groups formed                   {len(index):>10,}")
    print(f"  clearing the n>={MIN_PEER_GROUP_N} floor          {len(clearing):>10,}")
    print(f"  works covered                   {covered:>10,} ({100 * covered / len(records):.1f}%)")


def graph_structure() -> None:
    """Slide 16. Two different vendor-concentration counts are printed deliberately:
    the deck quotes both and says which one it means."""
    from collections import defaultdict

    graph = json.loads((SNAPSHOT / "graph.json").read_text())
    nodes = {n["id"]: n for n in graph["nodes"]}
    agency_mps: dict[str, set[str]] = defaultdict(set)
    agency_vendors: dict[str, set[str]] = defaultdict(set)
    for edge in graph["edges"]:
        source_type = nodes[edge["source"]]["type"]
        target_type = nodes[edge["target"]]["type"]
        if source_type == "MP" and target_type == "Agency":
            agency_mps[edge["target"]].add(edge["source"])
        elif source_type == "Agency" and target_type == "Vendor":
            agency_vendors[edge["source"]].add(edge["target"])
    vendor_mps: dict[str, set[str]] = defaultdict(set)
    for agency, vendors in agency_vendors.items():
        for vendor in vendors:
            vendor_mps[vendor] |= agency_mps[agency]

    by_type: dict[str, int] = {}
    for node in graph["nodes"]:
        by_type[node["type"]] = by_type.get(node["type"], 0) + 1
    print("\nSLIDE 16 -- fund-flow graph")
    print(f"  nodes {len(graph['nodes']):,}  edges {len(graph['edges']):,}  {by_type}")
    print(f"  agencies spanning >=3 MPs (direct)              "
          f"{sum(1 for m in agency_mps.values() if len(m) >= 3):>6,}")
    print(f"  vendors reachable from >=3 MPs (two-hop)        "
          f"{sum(1 for m in vendor_mps.values() if len(m) >= 3):>6,}")


if __name__ == "__main__":
    data = load()
    scheme_totals(data)
    detector_counts(data)
    targeting_performance(data)
    peer_group_coverage(data)
    graph_structure()
