"""F-19 (nemotronreview.md): no make target may delete data/raw/.

data/raw/ holds the original MPLADS dashboard captures (the three tiles,
including the truncated expenditure capture and its salvaged copy). They are
gitignored, so they exist on one disk only, and they may not be
re-downloadable. They are audit evidence, not a cache.
"""

from __future__ import annotations

from pathlib import Path

# pipeline/tests/test_makefile_safety.py -> parents[2] is "05-App/"
_MAKEFILE = Path(__file__).resolve().parents[2] / "Makefile"


def _recipe_lines(target: str) -> list[str]:
    lines = _MAKEFILE.read_text(encoding="utf-8").splitlines()
    recipe: list[str] = []
    inside = False
    for line in lines:
        if line.startswith(f"{target}:"):
            inside = True
            continue
        if not inside:
            continue
        if line.startswith("\t"):
            recipe.append(line.strip())
        elif line.strip() == "" or line.lstrip().startswith("#"):
            continue
        else:
            break
    return recipe


def test_clean_exists_and_never_touches_the_raw_captures() -> None:
    recipe = _recipe_lines("clean")
    assert recipe, "Makefile has no clean recipe; update this test if it was renamed"
    assert not any("data/raw" in line for line in recipe), recipe


def test_no_make_recipe_deletes_the_raw_captures() -> None:
    offending = [
        line.strip()
        for line in _MAKEFILE.read_text(encoding="utf-8").splitlines()
        if line.startswith("\t") and "rm " in line and "data/raw" in line
    ]
    assert offending == []
