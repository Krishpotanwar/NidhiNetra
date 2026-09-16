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


__all__ = ["QUOTA_PERCENT", "UNDER_IMPLEMENTATION", "quota_by_group", "quota_for"]
