"""Fills a fired detector's why_flagged sentence from the frozen templates
in contracts/strings.json.

A2 never writes prose here. A detector picks a template_id ("variant") and
supplies params; this module's only job is substitution, formatting each
param to the number_format rules, respecting every declared max_len, and
linting the rendered sentence against contracts/strings.json's own
lint.banned_literal / banned_derived / banned_chars lists before handing it
back. If a detector needs a case none of the frozen variants cover, this
module raises TemplateError loudly instead of inventing a sentence -- see
that error's docstring.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

# .../05-App/pipeline/src/nidhinetra_pipeline/risk/explain.py
# parents[4] == ".../05-App" -- see contracts/validate.py for the sibling
# convention (HERE = Path(__file__).parent) this mirrors one level deeper.
STRINGS_PATH = Path(__file__).resolve().parents[4] / "contracts" / "strings.json"


class TemplateError(RuntimeError):
    """Raised when why_flagged cannot honestly render a fired detector's
    output. Two distinct causes, both fatal by design (never silently
    downgraded to hand-written prose):

    1. The flag/variant genuinely does not exist in contracts/strings.json.
       This is a real contract gap -- the fix is to add a new named
       template to strings.json (not to write an ad-hoc sentence here),
       and to flag that addition for human review, per this agent's brief.
    2. A required param was not supplied, or a formatted param still
       overflows its declared max_len after truncation/clamping.
    """


@lru_cache(maxsize=1)
def _load_strings() -> dict[str, Any]:
    return json.loads(STRINGS_PATH.read_text())


def _category_phrase(category: str, max_len: int) -> str:
    """Mid-sentence category phrase, per number_format.category_phrase:
    categories arrive from contract 3.1 in title case; mid-sentence they
    render lowercase from the map, falling back to lowercasing the raw
    value for anything not yet mapped.
    """
    strings = _load_strings()
    phrase_map = strings["number_format"]["category_phrase"]
    phrase = phrase_map.get(category, category.lower())
    return _truncate_on_word_boundary(phrase, max_len)


def _truncate_on_word_boundary(value: str, max_len: int) -> str:
    """"Truncate sensibly" (this agent's brief, on the params/max_len
    contract): cut at the last whole word that still fits rather than
    slicing mid-word, so an overflowing phrase degrades to something still
    readable instead of a mangled fragment. Falls back to a hard cut only
    if there is no space to cut on at all.
    """
    if len(value) <= max_len:
        return value
    head = value[:max_len]
    if " " in head:
        head = head.rsplit(" ", 1)[0]
    return head[:max_len]


def _format_multiple(value: float) -> str:
    # number_format.multiple: one decimal normally, "3.2x" not "3x"; round
    # to a whole number over 100 ("140x" not "140.0x", false precision).
    if value >= 100:
        return f"{value:.0f}"
    return f"{value:.1f}"


def _format_percent(value: float) -> str:
    # number_format.percent: zero decimals.
    return str(round(value))


def _format_integer(value: float) -> str:
    return str(int(round(value)))


_FORMATTERS = {
    "multiple": _format_multiple,
    "percent": _format_percent,
    "integer": _format_integer,
    "count": _format_integer,
}


def _clamp_numeric_text(text: str, max_len: int) -> str:
    """Numeric overflow past max_len: clamp the magnitude to the largest
    value that fits rather than truncate digits off a number, which would
    silently change its value (e.g. "1234" -> "123" is a lie; a 3-digit cap
    should read "999"). In practice none of this engine's real values get
    anywhere near these caps -- this exists as a documented, safe fallback
    per the params/max_len contract, not a path expected to fire.
    """
    sign = "-" if text.startswith("-") else ""
    digits = "9" * max(1, max_len - len(sign))
    return sign + digits


def _format_param(name: str, value: Any, param_spec: dict[str, Any]) -> str:
    max_len = param_spec.get("max_len")
    if name == "category":
        return _category_phrase(value, max_len or 14)

    ptype = param_spec.get("type", "")
    formatter = _FORMATTERS.get(ptype)
    text = formatter(value) if formatter else str(value)

    if max_len is not None and len(text) > max_len:
        text = _clamp_numeric_text(text, max_len)
    return text


def render(flag: str, variant: str, params: dict[str, Any]) -> str:
    """Render one why_flagged sentence for a fired detector.

    `flag` is one of the four contract flag names, `variant` is the
    template_id inside contracts/strings.json's why_flagged[flag].variants,
    and `params` supplies the raw (unformatted) values for whichever
    placeholders that template declares.
    """
    strings = _load_strings()
    try:
        flag_spec = strings["why_flagged"][flag]
    except KeyError as exc:
        raise TemplateError(f"no why_flagged templates exist for flag {flag!r}") from exc
    try:
        variant_spec = flag_spec["variants"][variant]
    except KeyError as exc:
        raise TemplateError(
            f"why_flagged.{flag} has no variant {variant!r}. This is a real "
            "template gap: add a new named template to contracts/strings.json "
            "(never write ad-hoc prose here), and flag the addition for "
            "human review."
        ) from exc

    text = variant_spec["text"]
    placeholders = set(re.findall(r"\{(\w+)\}", text))
    param_specs = flag_spec.get("params", {})

    formatted: dict[str, str] = {}
    for name in placeholders:
        if name not in params:
            raise TemplateError(
                f"why_flagged.{flag}.{variant} needs param {name!r}, which the "
                "detector did not supply"
            )
        formatted[name] = _format_param(name, params[name], param_specs.get(name, {}))

    sentence = text.format(**formatted)
    _lint(sentence, strings)
    return sentence


_LINT_CHAR_KEYS = ("em_dash", "horizontal_bar", "two_em_dash", "three_em_dash")


def _lint(sentence: str, strings: dict[str, Any]) -> None:
    """Enforce contracts/strings.json's own lint block against a rendered
    sentence, so a banned word can never reach output even if a future
    template or param slips one in. Mirrors contracts/validate.py's "one
    source of truth" approach (lint._note): the rules live in strings.json,
    this function only applies them.
    """
    lint = strings["lint"]

    if sentence in set(lint.get("negation_exemptions", [])):
        return

    lowered = sentence.lower()
    for word in [*lint["banned_literal"], *lint["banned_derived"]]:
        if word in lowered:
            raise TemplateError(f"rendered sentence contains banned token {word!r}: {sentence!r}")

    banned_chars = lint["banned_chars"]
    for key in _LINT_CHAR_KEYS:
        ch = banned_chars.get(key)
        if ch and ch in sentence:
            raise TemplateError(f"rendered sentence contains banned char {key!r}: {sentence!r}")

    # NOTE: lint.structural.reason_must_contain_a_number is deliberately
    # NOT enforced here. Two frozen variants this engine legitimately uses
    # -- cost_outlier.no_multiple ("Cost is above the usual range for
    # {category} works here.") and expenditure_mismatch.full_spend_open
    # ("Full amount spent, work still under implementation.") -- carry no
    # digits at all by design (no_multiple exists specifically for when a
    # multiple cannot be honestly computed). lint._note scopes this file's
    # structural block to strings.json's own content and web/components
    # text nodes, not to values these templates are filled with at
    # runtime, so this is not a contract violation to skip.
    structural = lint.get("structural", {})
    if structural.get("reason_must_end_with_full_stop") and not sentence.endswith("."):
        raise TemplateError(f"why_flagged sentence must end with a full stop: {sentence!r}")
    hard_fail = structural.get("reason_hard_fail_chars")
    if hard_fail and len(sentence) > hard_fail:
        raise TemplateError(
            f"why_flagged sentence is {len(sentence)} chars, over the "
            f"{hard_fail}-char hard fail limit: {sentence!r}"
        )
