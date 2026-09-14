#!/usr/bin/env python3
"""CP0 validator. A script, not eyeballing.

Usage:
    python3 validate.py                        # validate the committed fixtures
    python3 validate.py --works PATH --scored PATH --graph PATH --aliases PATH
    python3 validate.py --self-test            # prove it actually rejects bad data

Checks, in order:
  1. Every works.fixture.json record matches normalized_record.schema.json
  2. Every scored.fixture.json record matches risk_scored_record.schema.json
  3. Every graph.fixture.json object matches fund_flow_graph.schema.json
  4. Cross-file: every scored.work_id has a matching works.work_id
  5. Cross-file: inspection_rank runs 1..N with no gaps, no duplicates
  6. Cross-file: peer_group.n >= 30 whenever flags is non-empty (eng review rule)
  7. Cross-file: peer_group is null whenever flags is empty
  8. Cross-file: every graph edge source/target matches a node id
  9. Cross-file: every graph edge work_id is a real works.fixture.json work_id
     (F-02, nemotronreview.md: an edge with no real work behind it, or one
     backed by a work_id that does not exist, is exactly the false-path
     failure mode this check exists to catch)
 10. Every alias candidate matches entity_alias_candidate.schema.json
 11. Cross-file: every alias evidence_work_id is a real works.fixture.json work_id
"""

import argparse
import json
import sys
from pathlib import Path

try:
    import jsonschema
except ImportError:
    print("ERROR: jsonschema not installed. Run: pip install jsonschema", file=sys.stderr)
    sys.exit(1)

HERE = Path(__file__).parent


def load(path: Path):
    return json.loads(path.read_text())


def validate_schema(records, schema, label: str, errors: list[str]) -> None:
    validator = jsonschema.Draft7Validator(schema)
    for i, record in enumerate(records):
        for err in validator.iter_errors(record):
            wid = record.get("work_id", f"index {i}")
            location = ".".join(str(part) for part in err.path) or "<root>"
            errors.append(f"[{label}] {wid}: {err.message} (at {location})")


def validate_all(
    works_path: Path,
    scored_path: Path,
    graph_path: Path,
    aliases_path: Path | None = None,
) -> list[str]:
    errors: list[str] = []
    aliases_path = aliases_path or HERE / "fixtures" / "alias_candidates.fixture.json"

    normalized_schema = load(HERE / "normalized_record.schema.json")
    scored_schema = load(HERE / "risk_scored_record.schema.json")
    graph_schema = load(HERE / "fund_flow_graph.schema.json")
    alias_schema = load(HERE / "entity_alias_candidate.schema.json")

    works = load(works_path)
    scored = load(scored_path)
    graph = load(graph_path)
    aliases = load(aliases_path)

    validate_schema(works, normalized_schema, "works", errors)
    validate_schema(scored, scored_schema, "scored", errors)
    validate_schema(aliases, alias_schema, "alias candidate", errors)

    graph_validator = jsonschema.Draft7Validator(graph_schema)
    for err in graph_validator.iter_errors(graph):
        location = ".".join(str(part) for part in err.path) or "<root>"
        errors.append(f"[graph] {err.message} (at {location})")

    # cross-file checks, only meaningful once schema checks pass
    work_ids = {w.get("work_id") for w in works if isinstance(w, dict)}
    scored_ids = [s.get("work_id") for s in scored if isinstance(s, dict)]

    for wid in scored_ids:
        if wid not in work_ids:
            errors.append(
                f"[cross-file] scored.work_id {wid!r} has no matching row in works.fixture.json"
            )

    ranks = sorted(
        s.get("inspection_rank") for s in scored if isinstance(s, dict) and "inspection_rank" in s
    )
    expected = list(range(1, len(scored) + 1))
    if ranks != expected:
        errors.append(
            "[cross-file] inspection_rank is not 1..N with no gaps: "
            f"got {ranks}, expected {expected}"
        )

    for s in scored:
        if not isinstance(s, dict):
            continue
        wid = s.get("work_id", "<unknown>")
        flags = s.get("flags", [])
        peer_group = s.get("peer_group")
        if flags and not peer_group:
            errors.append(
                f"[cross-file] {wid}: has flags {flags} but peer_group is "
                "missing/null (mandatory when flagged)"
            )
        if flags and peer_group and peer_group.get("n", 0) < 30:
            errors.append(
                f"[cross-file] {wid}: peer_group.n={peer_group.get('n')} is "
                "below the minimum of 30 (eng review rule)"
            )
        if not flags and peer_group:
            errors.append(
                f"[cross-file] {wid}: has no flags but peer_group is set "
                "(should be null when unflagged)"
            )

    node_ids = {n.get("id") for n in graph.get("nodes", []) if isinstance(n, dict)}
    for e in graph.get("edges", []):
        if not isinstance(e, dict):
            continue
        if e.get("source") not in node_ids:
            errors.append(f"[cross-file] graph edge source {e.get('source')!r} matches no node id")
        if e.get("target") not in node_ids:
            errors.append(f"[cross-file] graph edge target {e.get('target')!r} matches no node id")
        for wid in e.get("work_ids", []):
            if wid not in work_ids:
                errors.append(
                    f"[cross-file] graph edge {e.get('source')!r}->{e.get('target')!r} "
                    f"claims work_id {wid!r}, which has no matching row in works.fixture.json"
                )

    for candidate in aliases:
        if not isinstance(candidate, dict):
            continue
        for wid in candidate.get("evidence_work_ids", []):
            if wid not in work_ids:
                errors.append(
                    f"[cross-file] alias candidate "
                    f"{candidate.get('proposed_canonical_id')!r}/"
                    f"{candidate.get('alias_label')!r} claims evidence work_id "
                    f"{wid!r}, which has no matching row in works.fixture.json"
                )

    return errors


def run_self_test() -> int:
    """Prove the validator actually rejects bad data, not just accepts good data."""
    import tempfile

    good_works = load(HERE / "fixtures" / "works.fixture.json")
    print("Self-test 1: corrupt work_category with an enum violation ...")
    broken = json.loads(json.dumps(good_works))
    broken[0]["work_category"] = "Not A Real Category"
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "broken_works.json"
        p.write_text(json.dumps(broken))
        errs = validate_all(
            p,
            HERE / "fixtures" / "scored.fixture.json",
            HERE / "fixtures" / "graph.fixture.json",
        )
    if not errs:
        print("  FAIL: validator did not catch an invalid work_category enum value")
        return 1
    print(f"  PASS: caught {len(errs)} error(s), e.g. {errs[0]}")

    good_scored = load(HERE / "fixtures" / "scored.fixture.json")
    print("Self-test 2: rank gap (duplicate rank 1, missing rank N) ...")
    broken_scored = json.loads(json.dumps(good_scored))
    broken_scored[1]["inspection_rank"] = broken_scored[0]["inspection_rank"]
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "broken_scored.json"
        p.write_text(json.dumps(broken_scored))
        errs = validate_all(
            HERE / "fixtures" / "works.fixture.json",
            p,
            HERE / "fixtures" / "graph.fixture.json",
        )
    if not errs:
        print("  FAIL: validator did not catch a rank gap/duplicate")
        return 1
    print(f"  PASS: caught {len(errs)} error(s), e.g. {errs[0]}")

    print("Self-test 3: peer_group.n below the minimum of 30 ...")
    broken_scored2 = json.loads(json.dumps(good_scored))
    for s in broken_scored2:
        if s["flags"]:
            s["peer_group"]["n"] = 3
            break
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "broken_scored2.json"
        p.write_text(json.dumps(broken_scored2))
        errs = validate_all(
            HERE / "fixtures" / "works.fixture.json",
            p,
            HERE / "fixtures" / "graph.fixture.json",
        )
    if not errs:
        print("  FAIL: validator did not catch peer_group.n below minimum")
        return 1
    print(f"  PASS: caught {len(errs)} error(s), e.g. {errs[0]}")

    print("\nSelf-test 4: alias evidence names a real fixture work ...")
    broken_aliases = [
        {
            "entity_type": "vendor",
            "proposed_canonical_id": "SYNTH-V001",
            "alias_label": "Rajdhani Civil Works",
            "reason": "identifier_has_multiple_labels",
            "evidence_work_ids": ["NOT-A-REAL-WORK"],
        }
    ]
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "broken_aliases.json"
        p.write_text(json.dumps(broken_aliases))
        errs = validate_all(
            HERE / "fixtures" / "works.fixture.json",
            HERE / "fixtures" / "scored.fixture.json",
            HERE / "fixtures" / "graph.fixture.json",
            p,
        )
    if not any("NOT-A-REAL-WORK" in error for error in errs):
        print("  FAIL: validator did not catch an unknown alias evidence work_id")
        return 1
    print(f"  PASS: caught {len(errs)} error(s), e.g. {errs[0]}")

    print("\nSelf-test 5: the unmodified fixtures still pass ...")
    errs = validate_all(
        HERE / "fixtures" / "works.fixture.json",
        HERE / "fixtures" / "scored.fixture.json",
        HERE / "fixtures" / "graph.fixture.json",
    )
    if errs:
        print(f"  FAIL: {len(errs)} error(s) on the real fixtures: {errs[:3]}")
        return 1
    print("  PASS: real fixtures are clean")

    print("\nAll self-tests passed. The validator has real teeth.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--works", type=Path, default=HERE / "fixtures" / "works.fixture.json")
    ap.add_argument("--scored", type=Path, default=HERE / "fixtures" / "scored.fixture.json")
    ap.add_argument("--graph", type=Path, default=HERE / "fixtures" / "graph.fixture.json")
    ap.add_argument(
        "--aliases",
        type=Path,
        default=HERE / "fixtures" / "alias_candidates.fixture.json",
    )
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return run_self_test()

    errors = validate_all(args.works, args.scored, args.graph, args.aliases)
    if errors:
        print(f"FAILED: {len(errors)} error(s)\n")
        for e in errors:
            print(f"  - {e}")
        return 1

    works_n = len(load(args.works))
    scored_n = len(load(args.scored))
    aliases_n = len(load(args.aliases))
    graph_data = load(args.graph)
    print(
        f"OK: {works_n} works, {scored_n} scored records, "
        f"{len(graph_data['nodes'])} graph nodes, {len(graph_data['edges'])} graph edges, "
        f"{aliases_n} alias candidates. All checks passed."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
