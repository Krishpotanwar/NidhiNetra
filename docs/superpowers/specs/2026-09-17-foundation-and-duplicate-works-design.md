# Design: work descriptions, and hybrid duplicate-work detection

Status: APPROVED by the user section by section, 2026-09-15 to 2026-09-17, after two external
review rounds. Author: Opus. Scope: Phase 0 and Phase 1 of the AI roadmap below.

## Why

SIH26102 asks, in its own words, for "duplicate works", "predictive insights", "early warning
mechanisms" and "easy-to-understand... insights". NidhiNetra today scores every work with four
explainable rules capped at 80 points plus an IsolationForest/LOF ensemble capped at 20. A judge
asked what the AI actually does, and the honest answer was thin: an unsupervised ensemble worth a
fifth of the score.

Meanwhile the portal's own free-text `WORK_DESCRIPTION` reaches `data/raw/` on all 79,068 works and
the pipeline throws it away. That single field is what makes duplicate-work detection possible.

## The roadmap this spec sits in

| Phase | What | Changes the score? |
|---|---|---|
| 0 Foundation | Carry three source fields through to the app | No |
| 1 Duplicates | Hybrid duplicate and split-work detection | No |
| 2 Delay | Put `scripts/delay_model.py` into the app as early warning | No |
| 3 Scoring v2 | Item-type comparison groups, stalled works freed from the peer gate, the 75-day sanction note, honest contamination comment | Yes, in one release, with every figure regenerated once |
| 4 Our own model | Fine-tune a small CrossEncoder on panel-labelled and officer-reviewed pairs | No |

This spec covers Phases 0 and 1 only. Anything that moves the 0 to 100 score waits for Phase 3 so
the deck, README and pitch figures are regenerated exactly once.

## Principles, carried from the review rounds

1. **Unique texts are the unit of candidate generation, but a text-level decision is not
   automatically a work-level duplicate decision when multiple works share either text.**
2. Code finds candidates; the model reads a pair; code verifies the model's evidence; the officer
   decides. The model is never asked about fraud or intent, and its output format has no field for it.
3. Identical description does not mean identical work. 52 works described "35 nag solar street lights
   ka insttalation" may be 52 real installations.
4. The app never calls a model. Answers are computed once offline, checked, stamped with model,
   provider and prompt version, and committed, so the demo works offline and repeats exactly.
5. Nothing in Phase 1 changes any work's score, rank or flags.
6. Facts are stated neutrally. "Each work is below Rs 15 lakh; the combined sanctioned value of this
   group exceeds Rs 25 lakh" is a fact. "Threshold evasion" is an accusation the data cannot support.

## Phase 0: carry the portal's own values into the work record

Three fields, added in one contract change rather than three:

| Field | From | Mapping | First consumer |
|---|---|---|---|
| `work_description` | `WORK_DESCRIPTION` | `_clean(...)` | Phase 1, detail panel, search |
| `activity_name` | `ACTIVITY_NAME` | `_clean(activity_of(...))` | Phase 1 judge context; Phase 3 comparison groups |
| `recommendation_date` | `RECOMMENDATION_DATE` | `_parse_ddmmmyyyy(...)` | Phase 3's 75-day note |

`activity_of()` returns `""` for an empty activity, so `_clean()` wraps it to produce null.
`_clean()` only replaces tabs, collapses repeated spaces and trims; it never changes letters, so the
app can honestly say "as published, spacing tidied". `WORK_DESCRIPTION` never passes through
`activity_of()`: descriptions carry no work-reference prefix.

Contract: all three are **required keys with nullable values**, following `vendor_name` and
`sanction_date`. A missing key means the adapter broke and must fail validation; a null means the
portal had no value. The record goes from 15 fields to 18 (15 already includes F-01's `vendor_id`).

- `normalize.py`: add to `_REQUIRED_FIELDS` and `_map_one`, and correct its stale "14-key" docstring.
- `build_snapshot.py`: no change. Parquet columns come from the schema.
- API: `_MERGED_SELECT` lists columns explicitly, so all three are added there; `_SEARCH_COLUMNS`
  gains `work_description` and `activity_name`, so an officer can search "high mast", "anganwadi" or
  a village name. The existing parameterised `strpos(lower(...))` needs no change.
- Web: `workTitle()` keeps composing the short title; the description appears verbatim beneath it,
  labelled and sourced, with an explicit empty state. `activity_name` and `recommendation_date` join
  the existing "Record as published" list. All labels live in `strings.json`
  (`detail_panel.record_fields`) with an amendment-log entry.
- `web/lib/types.ts` is hand-mirrored, not generated (`make contracts` exists but is unused), so it is
  updated by hand and `test_web_mirror_drift.py` gains an assertion that `NormalizedRecord`'s keys
  match the schema.
- `PRODUCT.md`'s line "Work descriptions are not in the source data yet" is wrong and is corrected.

Tests, written first: text cleaning including tab padding; the activity prefix stripped; null for
empty; date parsing; the three parquet columns and their nullable dtype; the API returning and
searching them; the panel's empty state.

**Two guarantees the tests must prove:**

- **Ranking equivalence.** For every scored work, `risk_score`, `inspection_rank`, `flags`,
  `why_flagged` and `peer_group` are byte-identical before and after. Both builds must pin the same
  reference date, because `build_snapshot()` scores against the day it runs; comparing against the
  committed snapshot without pinning would show changes Phase 0 did not cause. `deck_figures.py` is
  then re-run as a second, weaker check.
- **Source completeness.** The build prints present, missing and unreadable counts for all three
  fields and fails if more than 1% of non-empty dates cannot be parsed. `_parse_ddmmmyyyy` returns
  null for any format it does not know, including a plain `2024-07-08`, so a portal format change
  would otherwise blank every date in silence. One odd row must not block a refresh; a format change
  must not pass.

## Phase 1, Stage A: candidate generation (deterministic, no AI)

**`canonical_description_v1`, frozen:** NFKC normalise, casefold, every run of non-alphanumeric
characters becomes one space, collapse spaces. Digits are kept. No stemming, no spell-correction, no
stopword removal. The original text is stored separately. Any change to this rule becomes `v2`,
because the same data under a different rule produces different "identical" groups.

Three internal concepts, never conflated, measured on the 2026-09-04 capture:

| Concept | Count |
|---|---|
| `exact_source_text_group` (byte-identical, same constituency) | 1,080 groups / 7,830 works |
| `canonical_v1_text_group` | 1,176 groups / 8,576 works |
| `threshold_crossing_batch` (every work under Rs 15 lakh, group total at or above Rs 25 lakh) | 271 groups / 5,424 works / Rs 204.5 crore |
| `near_copy_candidate` (text pairs, same constituency) | 40,304 |

Officer-facing wording for the first two: "Works sharing the same portal description".

**Finder 1, identical batches.** No AI. Code attaches work count, amount range, group total, sanction
dates and agency, and the `threshold_crossing_batch` flag with the neutral clause 4.4.2 sentence.
Clause 4.4.2 (Guidelines 2023) makes third-party inspection compulsory at Rs 25 lakh and above and
requires 50% coverage between Rs 15 and 25 lakh, which is why those two numbers are the ones stated.

**Finder 2, near-copy pairs,** between distinct canonical texts in the same constituency, which is a
blocking rule and not a claim that works cannot duplicate across constituencies. Two cheap channels,
unioned, both computed over the full within-block pair space (9,065,219 comparisons, largest block
1,371 texts, one block at a time):

- character similarity (TF-IDF over 3 to 5 character n-grams, cosine at or above 0.80), which catches
  typos and spelling variants such as "high mask" for "high mast";
- meaningful-token overlap (our own Jaccard over content tokens with digits preserved, at or above
  0.75 on at least three tokens), which catches reordered phrasing. We do not use an off-the-shelf
  `token_set_ratio`: it returns a perfect score when one string is a subset of another, and the extra
  words are often the most important information in the sentence.

Numbers count as tokens: "community hall no 3" and "no 4" in one ward are sibling works, not copies.

Each pair carries the tokens present on only one side, which sorts it into one of three groups:

| Group | Pairs | Example |
|---|---|---|
| Reworded match | 453 | the same road "to killo balaram house at devarapali village", worded twice |
| One-sided detail | 3,083 | "cremation ground at village" against "...at village chak dana" |
| Conflicting detail | 35,427 | "gram **gairlekh**..." against "gram **jinkhola**..." |

Group names describe what the code knows, not what it suspects.

Those three counts were measured on a run that ignored single-digit tokens, so they sum to 38,963
rather than the 40,304 above. Counting digits moves pairs between groups, mostly out of "reworded
match" and into "conflicting detail", because "hall no 3" and "hall no 4" stop looking identical.
Stage D re-measures all three under the final tokenizer.

**Finder 3, a quiet district audit pass:** same District Authority, different constituency, exact
plus character similarity at or above 0.90. It found 4 identical groups and 11 near-copy pairs, so it
stays stored and unfeatured rather than widening the main search.

Thresholds are `candidate_generation_v0`. Stage D sets them from measured yield.

**Artifact:** `duplicate_candidates.json`, staged and committed with the other snapshot files, all or
none. Every candidate carries a deterministic identity (`scope`, both text fingerprints,
`finder_version`), which finder hits matched, both similarity scores, the shared and one-sided tokens,
the work ids on each side, and per-side amount, date, activity, agency and status summaries.

## Phase 1, Stage B: the pair judge

**What it sees:** the two descriptions as published, each side's portal activity, and the
constituency. Not amounts, dates, agencies or work counts. Those are work-level facts, and keeping
them out is what makes one answer reusable across every work behind a text.

**Five answers:** `same_asset_same_place`, `same_place_different_asset`, `same_asset_different_place`,
`not_enough_detail`, `unrelated`. Abstaining is a first-class answer and its rate is reported: a judge
that never abstains on "Construction of Mandap" is failing.

**Evidence, checked by code:** for each text, the asset words and the place-or-institution words,
quoted verbatim or null. Either "same place" answer must quote the shared identifier from both texts.
Code rejects any answer whose quotes are not literally present, counts the rejection, and leaves the
pair unjudged rather than showing an invented quote. No model prose ever reaches an officer: the
screen renders fixed sentences from `strings.json` plus the quoted spans.

**Running it:** one command, never the build. Strict JSON schema (Hugging Face Inference Providers
support `strict: true` on `openai/gpt-oss-120b`, `gpt-oss-20b` and `qwen`), 10 to 20 pairs per
request, temperature 0. Answers land in `data/judgments/text_pair_judgments.parquet`, stamped with
model, provider, prompt version, schema version and date, and committed. `data/judgments/` is covered
by no ignore rule, unlike `data/outcomes/`, which is deliberately local: one is a bought computation,
the other a human record. A dollar budget cap, resumable, with prices in config rather than code
comments. Judging all 40,304 pairs costs about 1 to 2 dollars at `gpt-oss-120b` rates (DeepInfra
$0.04 in / $0.17 out per million tokens).

**Model choice is decided by Stage D,** among `openai/gpt-oss-120b`, `openai/gpt-oss-20b`,
`google/gemma-3-27b-it` and `sarvamai/sarvam-m` (Indic scripts and romanised Hindi, via Featherless;
strict-JSON support unverified, so it may need JSON mode plus retries).

## From a text answer to a work-level candidate (code, not AI)

40,304 text pairs sit over 121,165 work pairs. Only 620 pairs (1.5%) imply more than 25 work pairs;
the largest implies 2,904.

- At 25 work pairs or fewer, code pairs the works and attaches each pair's amounts, dates and gap,
  agency, activity and status.
- Above that, the candidate stays group-to-group with summaries only, so a 246-work batch never
  becomes 12,000 rows.
- Labels: same place and asset with close amounts and dates gives `duplicate_candidate`; same place
  and asset but numbered or same-day gives `split_or_phase_candidate`; same place, different asset
  gives `sibling_candidate`; different place or unrelated gives `separate_work`; not enough detail
  gives `unclear`.
- The text answer is cached once. Work-level labels are recomputed every build, being deterministic.

**What reaches the officer:** only `duplicate_candidate` or `split_or_phase_candidate`, and only when
at least one discriminating fact is quoted from both records: a place, an institution, road endpoints,
a building or an asset identifier. The rule is source-grounded, not place-specific, because
"boundary wall at Govt Girls High School Rampur" identifies its asset by institution.

## Phase 1, Stage C: the review surface

Mirrors R-06 exactly. A new `duplicate_store.py` beside `alias_store.py` in the same `outcomes.db`;
`store.py` untouched. `duplicate_candidates` holds frozen identity, unique on scope plus both text
fingerprints plus finder version, so a rebuild updates evidence instead of resurfacing a decided
pair. `duplicate_reviews` is append-only with `reviewed_by` self-reported (the same known weakness as
`inspector_id`, F-10) and a `supersedes` column. Two new contracts, checked by `validate.py` with a
negative case in its self-test.

A new `duplicates` router beside `entity_aliases`: a paginated list that resolves evidence works in
one query, a review endpoint, and `duplicate_context` on the work detail endpoint. The detail panel
gains a "Works with the same or similar description" section with the shared words marked; the queue
renders inline on the Inspection List page with a count; nav stays at four tabs; the empty state uses
`DotCanvas`. Copy lives in one new `strings.json` block modelled on `entity_alias_review`, reusing its
actions "These are the same" and "These are different". "Duplicate" never appears as a verdict.

## Stage D: the test set and the model bake-off

300 seeded, stratified text pairs: 60 reworded, 80 one-sided, 60 conflicting with one differing token
each side, 50 conflicting with more, and **50 from below the cut-off** (character 0.65 to 0.80),
generated for the sample only. Without that last stratum we cannot say what the finder misses.

Two labellers from different companies, blind to each other and to the judge: a Claude Opus subagent,
and GPT via the user's Codex app or ChatGPT (the Codex CLI is not installed locally, so this is a file
handoff). Both follow the judge's own rubric, so the rubric is under test too. Agreement becomes the
reference label; disagreements are marked ambiguous, excluded from the headline figure and counted,
because a pair two strong models read differently is one an officer should decide. Agreement is
reported per answer type, and no figure is published for a type the labellers rarely agree on.

Per model: agreement with the reference by stratum and weighted to the population; abstention
behaviour; **false same-place claims reported separately**, since that is the error that sends an
officer to the wrong village; rejected outputs; cost per 1,000 pairs from the API's own token counts.
The selection rule is fixed in advance: fewest false same-place claims first, then the cheaper model
among those within a small margin.

Thresholds are then chosen from measured yield per band, so the claim is "we chose 0.80 because below
it candidate volume rose sharply while confirmed pairs barely moved".

Wording, in public and in the app: never "accuracy". "On 300 pairs labelled independently by two
frontier models, the judge matched the reference on N% and made M false same-place claims", with the
caveat that the reference is model-made, not human-made. `strings.json` bans "accuracy",
"confidence" and "probability", so the Reports page says "agrees with an independent two-model
reference on N of 300 pairs".

Every artifact is committed and re-runnable from one script, as `deck_figures.py` already is.

## Sequencing and risks

F-01 and R-06 landed first (`ccfa488`, `4b29469`, 2026-09-17), because Phase 0 touches the same files.
T06 and the gated data rebuild T07 still sit ahead of implementation.

- Free-tier and provider terms change without notice, so the judge is provider-agnostic, resumable and
  budget-capped, and its answers are committed once bought.
- A judge that over-claims "same place" is the dangerous failure, which is why it is measured on its
  own and why the queue demands quotes from both records.
- Officer queue noise, not cost, decides how wide the net is; Stage D sets that.
- Semantic embeddings are deliberately absent from v1. They rate "RO plant at Madugula" and "RO plant
  at Madugula Koduru" as near-identical, and place words are the deciding evidence here. They return
  in Phase 4 as an extra recall channel, measured before adoption.

## Open items for the user

1. Confirm the Hugging Face credit balance, its expiry, and that it counts as compute credit.
2. Gate G1 for T07 is still closed; the UI change from F-01 only becomes visible on real data after it.
3. Whether Phase 2 should also produce Hindi inspection briefs, which would need its own section.
