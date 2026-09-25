"""The District Authority inspection policy, in one place.

MPLADS guidelines clause 4.5.2: District Authorities physically inspect at
least ten percent of works under implementation every year. Two facts follow
from that sentence, and both had drifted into separate copies: stats.py owned
the population, while inspections.py and web/lib/data.ts each re-derived the
ceiling rule. They live here now, and everything server-side imports them.
"""

from __future__ import annotations

from collections.abc import Mapping

# Recommended works are not yet sanctioned; Completed works are done. Neither
# is inspected under clause 4.5.2 (04 Prototype/Logbook.md, 2026-08-31).
UNDER_IMPLEMENTATION: tuple[str, ...] = ("Sanctioned", "In Progress")

QUOTA_PERCENT = 10

# The three checks MoSPI's monthly pendency review runs over works under
# implementation (T4). All three are separate facts (D4): none of them
# touches score, rank or flags, and D5 forbids ever combining them into one
# "any pendency" count.
SANCTION_DAYS_LIMIT = 45  # Guidelines 2023 para 3.2.4
COMPLETION_DAYS_LIMIT = 365  # Guidelines 2023 para 3.2.12, "generally not exceed one year"
NO_PAYMENT_DAYS = 90  # MoSPI monthly pendency review, PIB release 2153066 (06 Aug 2025)
PENDENCY_KINDS: tuple[str, ...] = ("late_sanction", "open_past_one_year", "no_payment_90_days")


def quota_for(population_n: int) -> int:
    """Works the quota requires out of `population_n`.

    "At least ten percent" is a floor, so it rounds up, and a non-empty
    population always owes at least one inspection. An empty one owes none:
    "1 of 0 works" was a real bug, found 2026-09-02. Integer arithmetic on
    purpose, so no float product like 44810 * 0.1 can ever round the ceiling
    up by one.
    """
    if population_n <= 0:
        return 0
    return max(1, -(-population_n * QUOTA_PERCENT // 100))


def quota_by_group(population_by_group: Mapping[str, int]) -> dict[str, int]:
    """quota_for(), applied once per District Authority instead of once
    nationally (F-03, nemotronreview.md, fixed 2026-09-14). Clause 4.5.2 is
    a per-authority obligation: a district with zero of its own works
    inspected this year is a real compliance gap even when one other
    district's surplus makes a single national quota_for() call look
    satisfied. `population_by_group` is each District Authority's own count
    of works under implementation (UNDER_IMPLEMENTATION), keyed however the
    caller identifies a district -- since F-01 that is
    `works.implementing_district_authority` (IDA_NAME).
    """
    return {group: quota_for(n) for group, n in population_by_group.items()}


def pendency_clause(kind: str, as_of: str) -> tuple[str, list[str]]:
    """A parameterised SQL WHERE fragment (over the table alias `works`) for
    one of the three MoSPI pendency checks, plus its bind params.

    D3: late_sanction is measured from the portal's recommendation date, not
    a receipt date -- the receipt date is not published. `as_of` is the
    snapshot's own data_as_of (D2), never today's date and never
    max(last_updated); callers get it from snapshot.data_as_of_date().

    Deliberately raises rather than silently matching nothing: a caller that
    typos a kind, or passes the later "early_warning" rank-based check this
    function does not know about (a later task special-cases that one in
    works.py's _where -- R6), should see an error immediately.
    """
    if kind == "late_sanction":
        return (
            "works.recommendation_date IS NOT NULL AND works.sanction_date IS NOT NULL "
            "AND date_diff('day', CAST(works.recommendation_date AS DATE), "
            f"CAST(works.sanction_date AS DATE)) > {SANCTION_DAYS_LIMIT}",
            [],
        )
    if kind == "open_past_one_year":
        return (
            "works.sanction_date IS NOT NULL AND date_diff('day', "
            f"CAST(works.sanction_date AS DATE), CAST(? AS DATE)) > {COMPLETION_DAYS_LIMIT}",
            [as_of],
        )
    if kind == "no_payment_90_days":
        return (
            "works.sanction_date IS NOT NULL AND date_diff('day', "
            f"CAST(works.sanction_date AS DATE), CAST(? AS DATE)) > {NO_PAYMENT_DAYS} "
            "AND coalesce(works.expenditure_amount_inr, 0) = 0",
            [as_of],
        )
    raise ValueError(f"unknown pendency kind: {kind!r}")


__all__ = [
    "COMPLETION_DAYS_LIMIT",
    "NO_PAYMENT_DAYS",
    "PENDENCY_KINDS",
    "QUOTA_PERCENT",
    "SANCTION_DAYS_LIMIT",
    "UNDER_IMPLEMENTATION",
    "pendency_clause",
    "quota_by_group",
    "quota_for",
]
