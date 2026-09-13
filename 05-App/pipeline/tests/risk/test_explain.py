"""Tests for risk/explain.py: template rendering, max_len handling, and the
lint against contracts/strings.json's own banned-token list.

Includes the requirement from this agent's brief: a why_flagged sentence
must never contain a token from strings.json's lint.banned_literal or
lint.banned_derived lists.
"""

from __future__ import annotations

import pytest
from nidhinetra_pipeline.risk.explain import TemplateError, render


def _all_banned_tokens(strings_contract: dict) -> set[str]:
    lint = strings_contract["lint"]
    return {*lint["banned_literal"], *lint["banned_derived"]}


def test_render_default_cost_outlier_matches_reference_example() -> None:
    sentence = render("cost_outlier", "default", {"multiple": 3.2, "category": "Road"})
    assert sentence == "Cost is 3.2x the median for road works in this state."


def test_render_stalled_work_zero_spend_reference_example() -> None:
    sentence = render("stalled_work", "zero_spend", {"months": 14})
    assert sentence == "Sanctioned 14 months ago, zero expenditure recorded."


def test_render_multiple_over_100_has_no_decimal() -> None:
    sentence = render("cost_outlier", "default", {"multiple": 140.4, "category": "Road"})
    assert "140x" in sentence
    assert "140.4x" not in sentence


def test_render_unknown_variant_raises_template_error_not_ad_hoc_prose() -> None:
    with pytest.raises(TemplateError):
        render("cost_outlier", "not_a_real_variant", {"multiple": 1.0, "category": "Road"})


def test_render_missing_param_raises() -> None:
    with pytest.raises(TemplateError):
        render("cost_outlier", "default", {"category": "Road"})  # missing multiple


def test_render_truncates_an_overlong_category_instead_of_raising() -> None:
    # "Community Infrastructure" lowercases to 25 chars, over the
    # category param's max_len of 14, and has no explicit entry in
    # strings.json's category_phrase map -- exercises the fallback +
    # truncate-on-word-boundary path together.
    sentence = render(
        "cost_outlier", "default", {"multiple": 2.0, "category": "Community Infrastructure"}
    )
    assert sentence.endswith(".")
    assert "community infrastructure" not in sentence.lower()


@pytest.mark.parametrize(
    ("flag", "variant", "params"),
    [
        ("cost_outlier", "default", {"multiple": 3.2, "category": "Road"}),
        ("cost_outlier", "no_multiple", {"category": "Health"}),
        ("stalled_work", "zero_spend", {"months": 14}),
        ("stalled_work", "part_spend", {"months": 8, "percent_spent": 4}),
        ("stalled_work", "no_update", {"months": 9}),
        ("expenditure_mismatch", "over_sanction", {"percent_over": 12}),
        ("expenditure_mismatch", "full_spend_open", {}),
        ("agency_concentration", "mps", {"mp_count": 6}),
        ("agency_concentration", "districts_and_mps", {"district_count": 5, "mp_count": 6}),
        ("agency_concentration", "vendor", {"district_count": 4}),
    ],
)
def test_every_variant_this_engine_uses_renders_a_clean_sentence(
    flag, variant, params, strings_contract
) -> None:
    sentence = render(flag, variant, params)
    assert sentence.endswith(".")
    # NOTE: not asserting "contains a digit" here -- cost_outlier.no_multiple
    # and expenditure_mismatch.full_spend_open are frozen templates that
    # legitimately carry no number (see explain.py's _lint docstring note).

    banned = _all_banned_tokens(strings_contract)
    lowered = sentence.lower()
    hit = [w for w in banned if w in lowered]
    assert not hit, f"{sentence!r} contains banned token(s) {hit}"

    for banned_char in ("—", "―", "⸺", "⸻"):
        assert banned_char not in sentence
