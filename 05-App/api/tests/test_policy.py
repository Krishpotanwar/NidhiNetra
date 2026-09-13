"""api/src/nidhinetra_api/policy.py -- no dedicated test file existed
before this pass (/plan-eng-review, 2026-09-14, Test review finding).
"""

from __future__ import annotations

from nidhinetra_api.policy import quota_by_group, quota_for


def test_quota_for_rounds_up_to_at_least_ten_percent() -> None:
    # "At least ten percent" is a floor: 10% of 14 is 1.4, which must round
    # UP to 2, never down to 1.
    assert quota_for(14) == 2


def test_quota_for_floors_a_small_population_at_one() -> None:
    # 10% of 3 is 0.3, which still owes at least one inspection -- a
    # District Authority with only 3 works under implementation cannot
    # satisfy clause 4.5.2 by inspecting zero of them.
    assert quota_for(3) == 1


def test_quota_for_is_zero_for_an_empty_population() -> None:
    # A district with no works under implementation owes no inspections --
    # "1 of 0 works" was a real bug, found 2026-09-02 (module docstring).
    assert quota_for(0) == 0
    assert quota_for(-1) == 0


def test_quota_for_never_rounds_a_float_product_up_by_one() -> None:
    # 44810 * 0.10 == 4481.0 exactly, but float error must never push the
    # ceiling to 4482. Integer arithmetic in quota_for is what guarantees
    # this; this test would catch a future rewrite that switched to floats.
    assert quota_for(44_810) == 4_481


def test_quota_by_group_applies_quota_for_independently_per_group() -> None:
    # The whole point of F-03: five districts, each cleared against its own
    # population, must each clear their own floor of 1 -- summing to 5, not
    # the 2 a single national quota_for(14) would require. A concentrated
    # national top-2 pick could satisfy the national figure while leaving
    # three of these five districts with zero inspections all year.
    populations = {
        "Zilla Parishad Works Dept": 5,
        "Municipal Corporation Works Cell": 3,
        "PWD Division 7": 3,
        "State Electricity Board Civil Wing": 2,
        "Rural Engineering Services": 0,
    }
    assert quota_by_group(populations) == {
        "Zilla Parishad Works Dept": 1,
        "Municipal Corporation Works Cell": 1,
        "PWD Division 7": 1,
        "State Electricity Board Civil Wing": 1,
        "Rural Engineering Services": 0,
    }


def test_quota_by_group_of_empty_mapping_is_empty() -> None:
    assert quota_by_group({}) == {}
