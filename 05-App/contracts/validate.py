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
 12. Every copy string in strings.json passes strings.json's own lint block
     (banned words, banned characters) -- see lint_strings()
"""

import argparse
import json
import re
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


LINT_SKIP_TOP_LEVEL = {"lint", "_meta", "_measure", "number_format"}
LINT_SKIP_KEYS = {"never", "authority"}


def _iter_lint_leaves(node, path: str):
    """Yield (dotted.path, value) for every string leaf under `node`.

    Applies strings.json's own skip rules: any key starting with `_`; the
    top-level lint/_meta/_measure/number_format blocks; and any key named
    never/authority (authoring rules, not copy) at any depth.
    """
    if isinstance(node, dict):
        for key, value in node.items():
            if key.startswith("_") or key in LINT_SKIP_KEYS:
                continue
            if not path and key in LINT_SKIP_TOP_LEVEL:
                continue
            yield from _iter_lint_leaves(value, f"{path}.{key}" if path else key)
    elif isinstance(node, list):
        for i, value in enumerate(node):
            yield from _iter_lint_leaves(value, f"{path}[{i}]")
    elif isinstance(node, str):
        yield path, node


def lint_strings(
    strings: dict,
    banned_terms: list[str],
    banned_chars: dict,
    exemptions: set[str],
) -> list[str]:
    """Lint every copy string in `strings` against strings.json's own lint block.

    This is what makes lint._note's claim -- "validate.py reads this block
    so the rules and the strings have one source of truth" -- true. Returns
    one message per hit: "<dotted.key.path>: <term or char name> in
    "<first 60 chars>"". warn_chars is out of scope; only banned_chars and
    banned_terms (banned_literal + banned_derived) are enforced here.
    """
    term_patterns = [
        (term, re.compile(rf"(?<![a-z]){re.escape(term.lower())}(?![a-z])"))
        for term in banned_terms
    ]
    char_names = {
        value: name
        for name, value in banned_chars.items()
        if not name.startswith("_") and isinstance(value, str)
    }
    emoji_ranges = []
    for entry in banned_chars.get("emoji_ranges", []):
        lo_hex, _, hi_hex = entry.partition("-")
        lo = int(lo_hex, 16)
        emoji_ranges.append((lo, int(hi_hex, 16) if hi_hex else lo))

    hits: list[str] = []
    for path, text in _iter_lint_leaves(strings, ""):
        if text in exemptions:
            continue
        snippet = text[:60]
        lowered = text.lower()
        for term, pattern in term_patterns:
            if pattern.search(lowered):
                hits.append(f'{path}: {term} in "{snippet}"')
        for ch in text:
            if ch in char_names:
                hits.append(f'{path}: {char_names[ch]} in "{snippet}"')
            elif any(lo <= ord(ch) <= hi for lo, hi in emoji_ranges):
                hits.append(f'{path}: emoji U+{ord(ch):04X} in "{snippet}"')

    return hits


_PLACEHOLDER = re.compile(r"\{(\w+)\}")
_MISSING = object()


def _lookup_path(node: object, path: str) -> object:
    """Walks a dotted path as _iter_lint_leaves yields it (e.g. "nav.dashboard")
    into a nested dict. Returns _MISSING if any segment is absent.
    """
    for part in path.split("."):
        if not isinstance(node, dict) or part not in node:
            return _MISSING
        node = node[part]
    return node


def check_hi_against_en(hi_strings: dict, en_strings: dict) -> list[str]:
    """Cross-checks strings.hi.json (the Hindi overlay, D9) against
    strings.json: every hi key path must resolve to a real English string
    leaf -- a stray or renamed key would otherwise silently fall back to
    English (lib/strings.ts setLocale) instead of failing loudly here --
    and every translated leaf's {placeholder} set must match its English
    counterpart exactly, or a dropped/renamed param renders literally
    (e.g. "{date}") while the other silently drops a value.
    """
    errors: list[str] = []
    for path, hi_text in _iter_lint_leaves(hi_strings, ""):
        en_value = _lookup_path(en_strings, path)
        if en_value is _MISSING or not isinstance(en_value, str):
            errors.append(f"strings.hi.json key '{path}' has no matching string in strings.json")
            continue
        hi_params = set(_PLACEHOLDER.findall(hi_text))
        en_params = set(_PLACEHOLDER.findall(en_value))
        if hi_params != en_params:
            errors.append(
                f"strings.hi.json key '{path}': placeholders {sorted(hi_params)} "
                f"do not match strings.json's {sorted(en_params)}"
            )
    return errors


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

    print("\nSelf-test 6: the two Stage C review-store contracts ...")
    good_candidate = {
        "finder": "identical_batch",
        "scope": "C1",
        "fingerprint_a": "1111111111111111",
        "fingerprint_b": "1111111111111111",
        "finder_version": "candidate_generation_v0",
        "threshold_crossing_batch": True,
        "text": "PCC Road, near Ram House",
        "work_ids": ["W1", "W2"],
    }
    good_review = {
        "review_id": 1,
        "candidate_id": 1,
        "status": "confirmed_same",
        "reviewed_by": "RK",
        "reviewed_at": "2026-09-22T08:30:00Z",
        "reviewer_note": "",
        "supersedes": None,
    }
    candidate_schema = json.loads((HERE / "duplicate_candidate.schema.json").read_text())
    review_schema = json.loads((HERE / "duplicate_review.schema.json").read_text())
    good_errors = list(jsonschema.Draft7Validator(candidate_schema).iter_errors(good_candidate))
    good_errors += list(jsonschema.Draft7Validator(review_schema).iter_errors(good_review))
    if good_errors:
        print(f"  FAIL: a well-formed candidate/review was rejected: {good_errors[0].message}")
        return 1
    broken_candidate = {**good_candidate, "work_ids": ["only-one"]}
    broken_review = {**good_review, "status": "duplicate"}
    candidate_errors = list(
        jsonschema.Draft7Validator(candidate_schema).iter_errors(broken_candidate)
    )
    review_errors = list(jsonschema.Draft7Validator(review_schema).iter_errors(broken_review))
    if not candidate_errors:
        print("  FAIL: validator did not catch a one-work-id duplicate candidate")
        return 1
    if not review_errors:
        print("  FAIL: validator did not catch an unknown duplicate-review status")
        return 1
    print(
        f"  PASS: caught {len(candidate_errors)} candidate and {len(review_errors)} review error(s)"
    )

    print("\nSelf-test 7: lint_strings enforces strings.json's own banned-word/char rules ...")
    strings_data = load(HERE / "strings.json")
    lint_block = strings_data["lint"]
    banned_terms = lint_block["banned_literal"] + lint_block["banned_derived"]
    banned_chars = lint_block["banned_chars"]
    exemptions = set(lint_block["negation_exemptions"])

    cases = [
        ({"x": "Fraud found"}, True, "a banned word ('fraud')"),
        ({"x": "text — dash"}, True, "a banned em dash"),
        ({"x": "\U0001f642"}, True, "a banned emoji"),
        (
            {"never": "fraud is not shown to officers"},
            False,
            "a 'never' key (authoring rule, not copy)",
        ),
        (
            {"x": "Flags are recommendations to inspect, not findings."},
            False,
            "an exact negation_exemptions entry",
        ),
        ({"x": "safely"}, False, "'safely', which is not 'safe' on a letter boundary"),
    ]
    for fixture, want_hit, description in cases:
        hits = lint_strings(fixture, banned_terms, banned_chars, exemptions)
        if bool(hits) != want_hit:
            verdict = "missed" if want_hit else "wrongly flagged"
            print(f"  FAIL: {verdict} {description}: {hits}")
            return 1
    print(f"  PASS: all {len(cases)} lint_strings cases behave as specified")

    print("\nSelf-test 8: the real strings.json lints clean under its own rules ...")
    real_hits = lint_strings(strings_data, banned_terms, banned_chars, exemptions)
    if real_hits:
        print(f"  FAIL: {len(real_hits)} lint hit(s) in strings.json: {real_hits[:5]}")
        return 1
    print("  PASS: strings.json has zero lint hits")

    print("\nSelf-test 9: the real strings.hi.json lints clean and matches strings.json ...")
    hi_data = load(HERE / "strings.hi.json")
    banned_hi = lint_block["banned_hi"]
    real_hi_hits = lint_strings(hi_data, banned_hi, banned_chars, set())
    if real_hi_hits:
        print(f"  FAIL: {len(real_hi_hits)} lint hit(s) in strings.hi.json: {real_hi_hits[:5]}")
        return 1
    real_cross_errors = check_hi_against_en(hi_data, strings_data)
    if real_cross_errors:
        print(f"  FAIL: {len(real_cross_errors)} cross-check error(s): {real_cross_errors[:5]}")
        return 1
    print("  PASS: strings.hi.json is clean and every key matches strings.json")

    print(
        "\nSelf-test 10: lint_strings catches a banned Hindi word (Devanagari has no case, "
        "so banned_hi matches as a plain substring) ..."
    )
    hi_hits = lint_strings({"x": "यह घोटाला है"}, banned_hi, banned_chars, set())
    if not hi_hits:
        print("  FAIL: a banned Hindi word ('घोटाला') was not caught")
        return 1
    print(f"  PASS: caught {len(hi_hits)} hit(s), e.g. {hi_hits[0]}")

    print("\nSelf-test 11: check_hi_against_en catches an unknown hi key path ...")
    unknown_key_errors = check_hi_against_en({"nav": {"not_a_real_key": "x"}}, strings_data)
    if not unknown_key_errors:
        print("  FAIL: an unknown strings.hi.json key path was not caught")
        return 1
    print(f"  PASS: caught {len(unknown_key_errors)} error(s), e.g. {unknown_key_errors[0]}")

    print("\nSelf-test 12: check_hi_against_en catches a {placeholder} mismatch ...")
    placeholder_errors = check_hi_against_en({"nav": {"dashboard": "{oops} डैशबोर्ड"}}, strings_data)
    if not placeholder_errors:
        print("  FAIL: a placeholder mismatch against strings.json was not caught")
        return 1
    print(f"  PASS: caught {len(placeholder_errors)} error(s), e.g. {placeholder_errors[0]}")

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

    strings_data = load(HERE / "strings.json")
    lint_block = strings_data["lint"]
    errors += lint_strings(
        strings_data,
        lint_block["banned_literal"] + lint_block["banned_derived"],
        lint_block["banned_chars"],
        set(lint_block["negation_exemptions"]),
    )

    hi_strings = load(HERE / "strings.hi.json")
    errors += lint_strings(hi_strings, lint_block["banned_hi"], lint_block["banned_chars"], set())
    errors += check_hi_against_en(hi_strings, strings_data)

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
        f"{aliases_n} alias candidates. strings.json lint clean. All checks passed."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
