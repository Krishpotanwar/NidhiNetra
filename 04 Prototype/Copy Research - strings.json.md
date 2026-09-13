Since you pasted the text inline (no filepath), here's the compressed output directly. All code blocks, inline backticks, URLs, headings, paths, and blockquoted source citations are preserved verbatim; only surrounding prose is compressed.

---

```markdown
---
tags: [sih2026, contracts, copy, cp0]
ps: SIH26102
solution_name: NidhiNetra
date: 2026-09-01
status: recommendation
---

# CP0 and copy: should `contracts/strings.json` be frozen?

Research answer for the six-agent parallel build. Sources read: `NIDHINETRA-DESIGN-BRIEF.md` (sections 4, 5, 10, 11, 12, Part B1), `04 Prototype/PRD.md`, `04 Prototype/Execution Plan.md` section 3.2, `04 Prototype/Checkpoints.md`, `.claude/plan/nidhinetra-app-build.md` for CP0 + folder definitions.

---

## 1. Recommendation

**Freeze all user-visible copy in `contracts/strings.json` at CP0, alongside the three JSON schemas. Not just the flag sentences.**

Six reasons, each grounded in a specific written line.

### 1.1 The design brief already made this decision. It is section 11.

Section 11, titled "Nothing is hardcoded", has two halves. Second half not about numbers:

> **Content.** No figure, label, count or name is baked into a component. Every value on screen arrives as data.

The word **label** is in that sentence. Under the brief as written, a component containing the literal string `"No results found"` is a violation, exactly as a component containing `#F5F5F5` is. Section 11 does not name the file labels arrive from. `contracts/strings.json` is that file. Freezing it is not an addition to the brief, it is the missing half of a rule the brief already states.

The brief then lists what must be designed, the same list this file must fill:

> - **Loading:** skeleton rows matching the real row geometry, never a spinner.
> - **Empty:** a filter combination returning nothing, composed properly, saying what to do next.
> - **Missing fields:** vendor unknown, date absent, amount not yet recorded.
> - **Long values:** a work name running to three lines, an agency name longer than its column.

Note the last bullet. "Long values" is a copy problem before a layout problem, solvable only if the maximum length of each string is known in advance. It cannot be known if the strings are written last.

### 1.2 The agent who writes the sentences is not the agent who is gated on them

Decisive argument, and a defect in the current plan, not an opinion.

Execution Plan section 1 assigns prose to A2:

> **A2 Risk Engine** | Isolation Forest / LOF / peer-group z-scores, composite score, **plain-language reasons**

Checkpoints puts the copy gate on A5:

> ## CP5 - The Inspection List is live
> **Owner:** A5
> - [ ] **Copy audit passed:** no "fraud detected", no green anywhere, no em-dashes

So A2 authors the sentences, ships them through the section 3.2 payload, A4 passes them untouched, and **A5 is held responsible at CP5 for words A5 did not write and cannot change.** A5's only remedies then: fail the checkpoint, or rewrite strings in the render layer, which forks the copy and violates section 11. The seam between "who writes it" and "who is judged on it" is where a frozen contract belongs. Same argument section 3 makes for the data shapes:

> six agents work on six pieces at once instead of one agent doing everything in order. That only works if everyone agrees up front on the exact shape of the data passed between them. That agreement is section 3. Skip it and the pieces will not fit at the end.

Copy crosses three agents. Passed between them. Currently no agreed shape.

### 1.3 Drift has already started, in the source documents themselves

The peer group sentence exists in two forms in two frozen planning documents.

Design brief section 4:

> A line reading, for example, "Compared against 289 road works in this state for this year."

PRD, must-ship item M3:

> The stated peer group ("compared against 289 road works, Bihar, 2023-24") is not optional

Same element, same example data, two sentences, two capitalisations. Neither is wrong. But if two carefully written documents by the same author diverge on the single most load-bearing sentence in the product, six agents working in parallel will diverge further and faster. Direct evidence, not a hypothetical. Both forms are frozen below as named variants with a stated rule for which context uses which.

### 1.4 There are required strings nobody is currently assigned to write

Execution Plan section 2, rung 5 of the acquisition ladder:

> Hand-curated seed dataset from published CAG reports and dashboard exports, **clearly labelled in the UI as a demo dataset** ... Honest labelling is mandatory. A demo on labelled sample data is respectable; a demo on unlabelled fake data that a judge catches is fatal.

That is a mandatory user-visible string. It is specified in the **data acquisition** section, owned by **A1**, and would be rendered by **A5**, who has no reason to ever read section 2. Under "leave copy to the agents", this string does not get written, and the failure mode named in that same paragraph is the word "fatal". A frozen strings file is the only artifact both agents read.

Same holds for the offline and cached states. PRD section 4:

> **Offline-safe.** Judging-day wifi failure must not be able to kill the demo.

If wifi dies during judging, the string a judge reads is a status message that, under the current plan, would be improvised by whichever agent hit the error path first.

### 1.5 The 46 character measure is only enforceable against templates

Design brief section 4:

> **Line two:** the plain-language reason ... constrained to a comfortable reading measure of roughly 46 characters.

Part B1 makes it a token: `--measure-reason: 46ch;`

A free-prose sentence generated at runtime by A2 cannot be checked against this before it renders. A template with declared parameters and declared maximum parameter lengths **can** be checked at CP0, by arithmetic, before a single component exists. That converts a visual review into a test, which is what Execution Plan section 5 demands of everything else:

> **Contract violations are auto-reject.** If output does not validate against section 3, it goes back without discussion. Write the validator on Day 1.

One clarification the measurement produced, and it matters. The two frozen examples in section 3.2 are 53 and 52 characters long. Both wrap to two lines at a 46ch measure. **46ch is the wrap width, not a length cap**, and the intended normal is two lines. A lint that fails anything over 46 characters would reject the project's own reference examples. The correct rule is a worst case render of 92 characters, two lines at the measure. Every template below was measured against its longest plausible parameter values and holds at two lines.

### 1.6 The stakes are asymmetric, and both documents say so in the same words

Design brief section 10:

> The framing discipline is a UI constraint. One overclaiming label in a screenshot undoes the entire product.

PRD section 4:

> **Framing discipline is a UI constraint, not a slide footnote.**

Design brief section 1:

> **It never accuses anyone of fraud.** ... Every design decision below serves that distinction. It is not a disclaimer, it is the product.

Distributing authorship of the product's defining constraint across six agents, then checking it once at CP5 by reading the screen, is a review strategy with a single point of failure and no automated backstop. Freezing the strings costs a few hours at CP0 and makes the constraint testable in CI from Day 1.

### 1.7 What freezing does not mean

Stating this precisely matters: an over-broad rule produces a lint that fires on `detectors.py` and gets switched off within a day.

- **A2 keeps everything that is actually A2's job.** Detection thresholds, which flag fires, on what evidence, with what parameter values, and the composite score. A2 chooses the sentence and supplies the numbers. A2 does not choose the words. `template_id` plus `params` is a richer output than a string, not a poorer one.
- **A5 keeps typography, wrapping, truncation, casing and layout.** Strings are stored in sentence case; uppercase micro labels get their casing from `text-transform`, never from the JSON.
- **Scope is user-visible text only.** Code identifiers, module names, log lines, docstrings, test names, commit messages and the problem statement title ("MPLADS Anomaly Detection") are out of scope and out of lint range.
- **It is amendable, not immutable.** An agent that needs a string it cannot find raises it with A6, it lands in the file, and it goes in the Logbook, per Execution Plan section 8. Forbidden: patching copy inside a component.

### 1.8 The contract amendment this implies

Section 3.2 currently ships a rendered sentence:

```json
"why_flagged": {
  "cost_outlier": "Cost is 3.2x the median for road works in this state."
}
```

Keep that field. It makes the API and the committed snapshot readable by a judge without a render step, worth a lot. **Add a parallel field** so the sentence is reproducible and lintable:

```json
"why_flagged": {
  "cost_outlier": "Cost is 3.2x the median for road works in this state."
},
"why_flagged_ref": {
  "cost_outlier": {
    "template_id": "cost_outlier.default",
    "params": { "multiple": 3.2, "category": "road" }
  }
}
```

`validate.py` then asserts that `render(strings[template_id], params) == why_flagged[flag]`. Any agent editing prose in place is caught mechanically instead of by eye. Cheapest possible change at CP0, expensive after A2 ships.

### 1.9 Scheduling note

The Design Review dated 2026-09-01 chose Approach A, which halts all streams pending the data spike, and defers `contracts/validate.py` to Wave 0. `strings.json` is the one CP0 artifact with **zero dependency on the spike outcome**, because no string in it changes based on which acquisition rung succeeds. The single exception is the rung 5 demo dataset label, drafted below as a conditional. Whether to write it during the spike or in Wave 0 is your call as arbiter, but it commits no engineering and blocks nothing.

### 1.10 The alternatives, and why they lose

| Option | What it costs | Why it fails |
|---|---|---|
| Leave copy to the agents | Nothing up front | Violates design brief section 11 as literally written. Puts the CP5 copy gate on an agent who cannot fix what it is gated on. Loses the rung 5 label and the offline states entirely. |
| Freeze only the flag sentences | Roughly an hour | Leaves the highest risk string in the product unfrozen. The empty state is where a developer most naturally types "No issues found", which design brief section 10 bans by name. The flag sentences are the strings agents are already thinking carefully about. The unwatched states are where the accusation slips in. |
| **Freeze all user-visible copy** | A few hours at CP0, plus the 3.2 amendment in 1.8 | None found. |

---

## 2. `contracts/strings.json`

Draft, ready to land at `05-App/contracts/strings.json`. Every string was measured. No em-dash characters, no en dashes, no emoji, no banned vocabulary.

```json
{
  "_meta": {
    "contract": "strings",
    "version": "1.0.0",
    "status": "FROZEN AT CP0",
    "owner": "A6",
    "locale": "en-IN",
    "authority": "NIDHINETRA-DESIGN-BRIEF.md sections 4, 5, 10, 11, 12. PRD section 4. Execution Plan section 3.2.",
    "rule": "No user-visible string exists anywhere except this file. A2 selects a template_id and supplies params. A4 passes both through. A5 renders. No agent writes prose.",
    "scope": "User-visible text only. Code identifiers, log lines, docstrings, test names and document titles are out of scope.",
    "casing": "Strings are stored in sentence case. Uppercase micro labels get their casing from text-transform in CSS, never from this file.",
    "amendment": "Raise with A6, land it here, append to Logbook.md. Never patch copy inside a component."
  },

  "_measure": {
    "reason_wrap_ch": 46,
    "note": "46ch is the wrap measure from --measure-reason in design brief B1. It is not a truncation cap. The two reference examples in Execution Plan 3.2 are 53 and 52 characters and both wrap to two lines, so two lines is the intended normal.",
    "reason_worst_case_max": 92,
    "reason_hard_fail": 138,
    "rule": "A template passes if its render at the declared maximum parameter lengths is 92 characters or fewer."
  },

  "why_flagged": {
    "_rules": [
      "State the measurement. Never state the inference.",
      "Every reason carries at least one number, because the product promise in design brief section 1 is 'here is exactly why'.",
      "Every reason ends in a full stop, matching both reference examples.",
      "No verb of judgement. The reference examples use 'is' and 'recorded'.",
      "Where a dash is wanted, use a comma. The reference example 'Sanctioned 14 months ago, zero expenditure recorded.' already demonstrates this."
    ],

    "cost_outlier": {
      "params": {
        "multiple": { "type": "multiple", "required": true, "max_len": 5 },
        "category": { "type": "category_phrase", "required": true, "max_len": 14 },
        "state": { "type": "state_display", "required": false, "max_len": 20 }
      },
      "variants": {
        "default": {
          "text": "Cost is {multiple}x the median for {category} works in this state.",
          "use_when": "Always, in the table reason line. This is the reference example from Execution Plan 3.2.",
          "worst_case_len": 65
        },
        "named_state": {
          "text": "Cost is {multiple}x the median for {category} works in {state}.",
          "use_when": "Detail panel only, where the measure is wider and the state may not be on screen.",
          "worst_case_len": 75,
          "caution": "Do not use for states whose display name exceeds 20 characters. See number_format.state_display."
        },
        "no_multiple": {
          "text": "Cost is above the usual range for {category} works here.",
          "use_when": "The peer median is unavailable or zero, so a multiple cannot be computed honestly.",
          "worst_case_len": 60
        }
      }
    },

    "stalled_work": {
      "params": {
        "months": { "type": "integer", "required": true, "max_len": 3 },
        "percent_spent": { "type": "percent", "required": false, "max_len": 3 }
      },
      "variants": {
        "zero_spend": {
          "text": "Sanctioned {months} months ago, zero expenditure recorded.",
          "use_when": "Expenditure is exactly zero. This is the reference example from Execution Plan 3.2.",
          "worst_case_len": 53
        },
        "part_spend": {
          "text": "Sanctioned {months} months ago, {percent_spent} percent spent.",
          "use_when": "Expenditure is above zero but below the stall threshold.",
          "worst_case_len": 45
        },
        "no_update": {
          "text": "No expenditure update in {months} months.",
          "use_when": "sanction_date is missing but last_updated is present. Never render a missing sanction date as a computed age.",
          "worst_case_len": 36
        }
      }
    },

    "expenditure_mismatch": {
      "params": {
        "percent_over": { "type": "percent", "required": false, "max_len": 4 },
        "spent": { "type": "currency_compact", "required": false, "max_len": 14 },
        "sanctioned": { "type": "currency_compact", "required": false, "max_len": 14 }
      },
      "variants": {
        "over_sanction": {
          "text": "Expenditure is {percent_over} percent above sanction.",
          "use_when": "expenditure_amount_inr exceeds sanctioned_amount_inr.",
          "worst_case_len": 43
        },
        "amounts": {
          "text": "{spent} spent against {sanctioned} sanctioned.",
          "use_when": "Detail panel, where the absolute figures are more useful than the ratio.",
          "worst_case_len": 55
        },
        "full_spend_open": {
          "text": "Full amount spent, work still under implementation.",
          "use_when": "expenditure equals sanction while completion_status is not Completed.",
          "worst_case_len": 51
        }
      }
    },

    "agency_concentration": {
      "params": {
        "mp_count": { "type": "integer", "required": false, "max_len": 3 },
        "district_count": { "type": "integer", "required": false, "max_len": 3 },
        "percent_share": { "type": "percent", "required": false, "max_len": 3 }
      },
      "variants": {
        "mps": {
          "text": "Agency holds works from {mp_count} different MPs.",
          "use_when": "Default. Concentration measured across MPs.",
          "worst_case_len": 42
        },
        "districts_and_mps": {
          "text": "Agency holds works in {district_count} districts, {mp_count} MPs.",
          "use_when": "Both spans are unusual and the fund flow view is reachable from this row.",
          "worst_case_len": 45
        },
        "vendor": {
          "text": "Vendor appears in {district_count} districts this year.",
          "use_when": "The concentrated node is a vendor rather than an implementing agency.",
          "worst_case_len": 42
        },
        "share": {
          "text": "Agency holds {percent_share} percent of works in this district.",
          "use_when": "Share of a single district rather than a span across many.",
          "worst_case_len": 51
        }
      },
      "_note": "Neutral verb is 'holds'. 'Controls', 'dominates', 'captured', 'cornered' and 'monopolises' are banned. See lint.banned_derived."
    }
  },

  "peer_group": {
    "_note": "Design brief section 4 requires real visual weight here, not a caption. Two forms exist in the source documents; both are frozen with a stated rule for which to use.",
    "params": {
      "peer_n": { "type": "count", "required": true, "max_len": 6 },
      "category": { "type": "category_phrase", "required": true, "max_len": 14 },
      "state": { "type": "state_display", "required": false, "max_len": 20 },
      "year": { "type": "financial_year", "required": false, "max_len": 7 }
    },
    "variants": {
      "contextual": {
        "text": "Compared against {peer_n} {category} works in this state for this year.",
        "use_when": "Table row and detail panel, where the active state and year filters are already on screen.",
        "source": "Design brief section 4, verbatim form.",
        "worst_case_len": 73
      },
      "explicit": {
        "text": "Compared against {peer_n} {category} works, {state}, {year}.",
        "use_when": "Anywhere the state and year are not otherwise visible, and in any exported or screenshotted view.",
        "source": "PRD must-ship item M3, verbatim form.",
        "worst_case_len": 76
      },
      "thin": {
        "text": "Compared against {peer_n} {category} works, a small group.",
        "use_when": "peer_n is below 30. Saying the group is small is an honesty requirement, not a hedge.",
        "worst_case_len": 60
      }
    },
    "label": "Peer group",
    "missing": "Peer group not available for this work."
  },

  "risk_labels": {
    "_source": "Design brief B2, the comments on the --risk-0 through --risk-4 tokens.",
    "0": "Not currently flagged",
    "1": "Low",
    "2": "Moderate",
    "3": "High",
    "4": "Highest priority",
    "score_label": "Risk score",
    "score_caption": "An ordering device, not a likelihood.",
    "_note": "Level 0 is 'Not currently flagged' and never 'Clear', 'Clean', 'OK' or 'Verified'. Design brief section 6: nothing here is verified clean, only unflagged."
  },

  "framing": {
    "premise": "District Authorities must inspect at least 10 percent of works under implementation each year. This list ranks which 10 percent to inspect first.",
    "premise_note": "Title block sentence. The 46ch reason measure does not apply here; --measure-reason governs .t-reason only.",
    "standing_note": "Flags are recommendations to inspect, not findings.",
    "standing_note_placement": "Persistent, below the table, in muted ink. Not a modal, not a dismissible banner.",
    "method_link": "How the ranking is built",
    "unflagged_caveat": "Unflagged does not mean inspected or verified."
  },

  "quota_meter": {
    "label": "Annual inspection quota",
    "value": "{quota_n} of {total_n} works, the 10 percent minimum.",
    "cutoff_marker": "Quota cutoff at rank {cutoff_rank}",
    "beyond_cutoff": "Beyond the annual quota",
    "params": {
      "quota_n": { "type": "count", "required": true },
      "total_n": { "type": "count", "required": true },
      "cutoff_rank": { "type": "count", "required": true }
    }
  },

  "summary_strip": {
    "works_under_implementation": "Works under implementation",
    "flagged_for_inspection": "Flagged for inspection",
    "value_under_flagged": "Value under flagged works",
    "idle_beyond_12_months": "Idle beyond 12 months",
    "_note": "Design brief section 4 names these four figures. All four render in crore so they compare at a glance. See number_format.currency.summary_strip_override."
  },

  "table": {
    "columns": {
      "rank": "Rank",
      "work": "Work",
      "district": "District",
      "agency": "Agency",
      "sanctioned": "Sanctioned",
      "spent": "Spent",
      "risk": "Risk"
    },
    "column_tooltips": {
      "agency": "Implementing agency",
      "risk": "Inspection priority, 0 to 100"
    },
    "row_action_hint": "Open the full record",
    "sorted_by": "Sorted by inspection priority",
    "result_count": "{shown_n} of {total_n} works"
  },

  "detail_panel": {
    "title": "Work record",
    "breakdown_title": "What contributed to this rank",
    "breakdown_row": "{factor}, {weight} points",
    "close": "Close",
    "fund_flow_entry": "View fund flow",
    "record_fields": {
      "work_id": "Work ID",
      "mp_name": "Member of Parliament",
      "constituency": "Constituency",
      "agency": "Implementing agency",
      "vendor": "Vendor",
      "category": "Category",
      "sanctioned": "Sanctioned",
      "spent": "Spent",
      "sanction_date": "Sanction date",
      "status": "Status",
      "last_updated": "Last updated",
      "source": "Source"
    }
  },

  "fund_flow": {
    "title": "Fund flow",
    "subtitle": "MPs, implementing agencies and vendors. Edges are money.",
    "legend_mp": "Member of Parliament",
    "legend_agency": "Implementing agency",
    "legend_vendor": "Vendor",
    "edge_label": "{work_count} works, {amount}",
    "expand": "Expand this cluster",
    "collapse": "Collapse",
    "reset": "Reset view",
    "empty": "No connections in this filter.",
    "empty_body": "Widen the filter or select a different agency.",
    "scale_caveat": "Concentration patterns are only meaningful across many districts."
  },

  "filters": {
    "state": "State",
    "year": "Year",
    "category": "Work category",
    "flag": "Flag type",
    "all": "All",
    "clear": "Clear all filters",
    "flag_names": {
      "cost_outlier": "Cost outlier",
      "stalled_work": "Stalled work",
      "expenditure_mismatch": "Expenditure mismatch",
      "agency_concentration": "Agency concentration"
    }
  },

  "actions": {
    "flag_for_inspection": "Flag for inspection",
    "retry": "Retry",
    "try_again": "Try again",
    "clear_filters": "Clear all filters",
    "_note": "PRD section 4: buttons say 'Flag for inspection', never 'Report fraud'. 'Investigate', 'Report' and 'Escalate' are banned as button verbs."
  },

  "data_states": {
    "loading": {
      "visible_text": null,
      "screen_reader": "Loading the inspection list.",
      "render": "Skeleton rows matching the real row geometry. Design brief section 11: never a spinner.",
      "never": "Do not render a visible 'Loading...' label, a spinner, a progress percentage or a time estimate."
    },

    "empty_after_filter": {
      "title": "No works match these filters.",
      "body": "Widen the state, year or category filter.",
      "action": "Clear all filters",
      "render": "Composed in the table body at the same measure as a reason line, not centred in a large void.",
      "never": "Do not write 'No issues found', 'All clear', 'Nothing to report' or 'You are all caught up'. Design brief section 10 bans 'No issues' by name.",
      "no_flags_variant": {
        "use_when": "The filter returns works, but none of them are flagged. Distinct from returning no works at all.",
        "title": "No works in this filter are currently flagged.",
        "body": "Unflagged does not mean inspected or verified."
      }
    },

    "api_unreachable": {
      "title": "Cannot reach the data service.",
      "body": "Check that the service is running, then retry.",
      "action": "Retry",
      "render": "Replaces the table body. The filter bar and summary strip stay in place so the officer keeps their context.",
      "never": "No 'Oops', no 'Something went wrong', no exclamation mark, no stack trace, no HTTP status code in the visible text. Log the status code instead.",
      "precedence": "If a cached snapshot is available, render showing_cached_data instead of this state."
    },

    "showing_cached_data": {
      "label": "Offline. Showing snapshot from {date}.",
      "detail": "{record_count} records. No live connection in use.",
      "render": "A single muted line above the filter bar. Provenance, not decoration.",
      "params": {
        "date": { "type": "date", "required": true },
        "record_count": { "type": "count", "required": true }
      },
      "note": "Design brief section 12 bans version stamps and locale strips as decoration. This line is functional provenance required by PRD M6 and CP6, and is not covered by that ban.",
      "demo_dataset_variant": {
        "use_when": "source_rung is 5, the hand-curated seed dataset.",
        "label": "Demo dataset. Not live MPLADS data.",
        "detail": "Curated from published reports for demonstration.",
        "render": "Same position, but always visible and never dismissible.",
        "authority": "Execution Plan section 2, rung 5: clearly labelled in the UI as a demo dataset. Honest labelling is mandatory."
      }
    },

    "refresh_in_progress": {
      "label": "Refreshing. Showing the previous results.",
      "screen_reader": "Refreshing the inspection list.",
      "render": "The existing table stays fully visible and readable. A muted label in the filter bar only.",
      "never": "Do not blank the table, do not overlay a scrim, do not show a spinner, do not disable the filters."
    },

    "refresh_failed": {
      "label": "Refresh failed. Showing results from {time}.",
      "body": "The previous results are still on screen.",
      "action": "Try again",
      "params": { "time": { "type": "time", "required": true } },
      "render": "The stale table stays. The label sits where refresh_in_progress sat.",
      "never": "Do not clear the table on a failed refresh. Stale data with an honest timestamp beats an empty screen."
    }
  },

  "missing_fields": {
    "_authority": "Design brief section 11: vendor unknown, date absent, amount not yet recorded.",
    "vendor": "Vendor not recorded",
    "date": "Date not recorded",
    "amount": "Amount not yet recorded",
    "agency": "Agency not recorded",
    "generic": "Not recorded",
    "render": "Muted ink, one step down, left aligned even inside a numeric column, because it is text and not a number.",
    "never": "A missing amount never renders as zero, as a dash, or as N/A. Rendering a missing amount as zero would make stalled_work appear to fire on absent data."
  },

  "number_format": {
    "locale": "en-IN",

    "grouping": {
      "system": "indian",
      "rule": "Last three digits, then pairs.",
      "example": "1,72,961",
      "never": "172,961",
      "authority": "Design brief section 5: All rupee amounts use Indian numbering. Write 1,72,961 and not 172,961. Getting this wrong reads as a foreign product built by people who did not check.",
      "applies_to": "Every integer on screen, including counts and peer_n, not only currency."
    },

    "currency": {
      "symbol": "₹",
      "space_after_symbol": false,
      "thresholds": [
        { "up_to": 99999, "form": "full", "decimals": 0, "example": "₹87,500" },
        { "up_to": 9999999, "form": "lakh", "suffix": " L", "decimals": 2, "example": "₹12.40 L" },
        { "up_to": null, "form": "crore", "suffix": " Cr", "decimals": 2, "example": "₹1,729.61 Cr" }
      ],
      "trailing_zeros": "Always kept, never trimmed. A right aligned column of tabular figures breaks visually if the decimal count varies between rows.",
      "integer_part": "The integer part keeps Indian grouping inside the compact form. Write 1,729.61 Cr and not 1729.61 Cr.",
      "summary_strip_override": "All four summary figures render in crore regardless of magnitude, so the four values compare directly.",
      "prose_form": "Inside a sentence, spell the unit: 12.40 lakh, 1,729.61 crore. Abbreviate to L and Cr only in table cells, the summary strip and the detail panel.",
      "never_zero_for_missing": "A null amount renders missing_fields.amount. Never ₹0."
    },

    "multiple": {
      "decimals": 1,
      "always_show_decimal": true,
      "suffix": "x",
      "space_before_suffix": false,
      "examples": ["3.2x", "3.0x", "12.4x"],
      "over_100": "Round to a whole number, for example 140x. One decimal at that magnitude is false precision.",
      "authority": "Execution Plan 3.2 reference example: Cost is 3.2x the median.",
      "never": "Do not write 3x for a value of 3.0. Do not write 3.24x. Do not put a space before the x."
    },

    "percent": {
      "decimals": 0,
      "in_sentences": "Spell the word percent.",
      "in_numeric_columns": "Use the symbol with no space.",
      "authority": "The design brief writes 10 percent, 38 percent and 90 percent in prose throughout."
    },

    "risk_score": {
      "range": "0 to 100",
      "decimals": 0,
      "suffix": "none",
      "never": "Never append a percent sign. Never label it confidence, probability, likelihood or accuracy. It orders a queue, it does not estimate a chance.",
      "authority": "PRD section 4: Explainability beats accuracy theatre."
    },

    "rank": {
      "decimals": 0,
      "prefix": "none",
      "never": "No hash symbol, no 'Rank 1' inside the cell.",
      "authority": "Design brief section 4: Rank is narrow, fixed width, tabular numerals, muted. It orders the page; it does not shout."
    },

    "date": {
      "display": "12 Aug 2026",
      "months": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
      "never": "Never 12/08/2026 or 08/12/2026. A slash date is ambiguous between Indian and American order.",
      "financial_year": "2023-24, plain hyphen. Never an en dash, never an em dash."
    },

    "time": {
      "display": "09:14",
      "note": "24 hour, IST, no seconds, no timezone suffix in the interface."
    },

    "category_phrase": {
      "_note": "Categories arrive from contract 3.1 in title case. Mid-sentence they render lowercase from this map. A1 extends the map when the real category list lands; unmapped values fall back to lowercasing the raw value.",
      "Road": "road",
      "Drinking Water": "drinking water",
      "School": "school building",
      "Health": "health centre"
    },

    "state_display": {
      "rule": "Use the official state name as it arrives from contract 3.1.",
      "max_len_for_reason_line": 20,
      "open_item": "Two union territory names exceed 20 characters and have no agreed short form here. A1 confirms the official abbreviation before the named_state variant is used for them. Until then those rows use the default variant."
    },

    "tabular": {
      "rule": "Every rendered number sits in a tabular figure font. No exception.",
      "authority": "Design brief section 12 do-not-ship list: Any number without tabular figures."
    }
  },

  "lint": {
    "_note": "validate.py reads this block so the rules and the strings have one source of truth. Scope is this file plus text nodes in web/components. It does not scan code identifiers, log lines, docstrings, test names or markdown documents.",
    "banned_literal": [
      "fraud", "fraudulent", "detected", "detect", "detection",
      "suspicious", "suspect", "corruption", "corrupt",
      "verified clean", "verified", "no issues", "confirmed anomaly", "confirmed",
      "anomaly", "anomalous"
    ],
    "banned_derived": [
      "guilty", "culprit", "offender", "violator", "wrongdoing", "misuse",
      "misutilisation", "embezzlement", "siphoned", "diverted", "kickback",
      "scam", "bogus", "ghost work", "fake", "irregularity", "irregular",
      "questionable", "dubious", "proven", "conclusive", "established",
      "guaranteed", "certified", "evidence of", "finding", "findings",
      "controls", "dominates", "captured", "cornered", "monopolises",
      "clean", "all clear", "cleared", "safe", "healthy", "compliant",
      "passed", "no problems", "looks good", "green",
      "investigate", "report fraud", "escalate", "prosecute", "penalise",
      "oops", "uh oh", "whoops", "sorry", "something went wrong",
      "hang tight", "just a sec", "we found", "our ai", "the model says",
      "algorithm found", "accuracy", "confidence", "probability", "likelihood"
    ],
    "banned_chars": {
      "em_dash": "\u2014",
      "horizontal_bar": "\u2015",
      "two_em_dash": "\u2E3A",
      "three_em_dash": "\u2E3B",
      "_why_escaped": "Stored as escapes so this config file never contains the character it bans, and a repo wide grep for the em dash has no permanent false positive in its own rule file.",
      "emoji_ranges": ["1F300-1FAFF", "2600-27BF", "FE0F", "1F1E6-1F1FF"]
    },
    "warn_chars": {
      "en_dash": "\u2013",
      "double_hyphen": "--",
      "exclamation": "!"
    },
    "allowed_terms": [
      "flagged", "flag", "not currently flagged", "unflagged",
      "risk score", "inspection priority", "statistical outlier",
      "high priority for review", "flag for inspection", "peer group",
      "outlier", "under implementation", "recommendation"
    ],
    "negation_exemptions": [
      "Flags are recommendations to inspect, not findings.",
      "Unflagged does not mean inspected or verified.",
      "An ordering device, not a likelihood."
    ],
    "_negation_note": "Found by running this lint against this file. A banned word used to deny a claim is the opposite of an overclaim, and these three strings are among the most load bearing in the product. Exempt them by exact whole string match, never by relaxing the word rule, so a new negated phrase has to be added here deliberately.",
    "structural": {
      "reason_worst_case_max_chars": 92,
      "reason_hard_fail_chars": 138,
      "reason_must_end_with_full_stop": true,
      "reason_must_contain_a_number": true,
      "every_declared_param_must_appear_in_its_template": true,
      "every_placeholder_must_be_declared": true,
      "no_string_may_be_empty": true,
      "no_uppercase_only_strings": "Casing is presentation. Store sentence case."
    }
  }
}
```

---

## 3. Banned words and patterns for the lint

Every entry traces to a line in the source documents. Three tiers, because a lint that cannot distinguish a hard rule from a tone preference gets argued with and then switched off.

### Tier 1. Literal, taken from the text

From design brief section 10, the "Never write" column:

| Banned token | Source line | Approved replacement |
|---|---|---|
| `fraud`, `fraudulent` | "Fraud detected" | "Flagged for inspection" |
| `detected`, `detect`, `detection` | "Fraud detected" | "Flagged for inspection" |
| `suspicious`, `suspect` | "Suspicious work" | "High priority for review" |
| `corruption`, `corrupt` | "Corruption risk" | "Risk score", "Inspection priority" |
| `verified clean`, `verified` | "Verified clean, or No issues" | "Not currently flagged" |
| `no issues` | "Verified clean, or No issues" | "Not currently flagged" |
| `confirmed`, `confirmed anomaly` | "Confirmed anomaly" | "Statistical outlier against peer group" |
| `anomaly`, `anomalous` | "Confirmed anomaly" | "Statistical outlier against peer group" |

From other explicit lines:

| Banned | Source |
|---|---|
| U+2014 em dash, anywhere | Section 10: "No em-dash characters anywhere in the interface. Not in headings, labels, buttons, body text, tooltips, empty states or alt text." |
| Emoji, any codepoint | Section 2: "No illustrations, no mascots, no emoji, no startup energy." |
| `Report fraud` as button text | PRD section 4: "Buttons say 'Flag for inspection,' never 'Report fraud.'" |
| The word `green` in any risk label | Section 6: "never use green ... Green means verified clean." |
| Any number rendered without tabular figures | Section 12: "Any number without tabular figures." |

### Tier 2. Derived, each from a stated principle

These do not appear as banned words in the brief. Each is banned because it asserts something a stated principle forbids asserting. The citation is what makes each defensible in review.

**From section 1, "It never accuses anyone of fraud":**
`guilty`, `culprit`, `offender`, `violator`, `wrongdoing`, `misuse`, `misutilisation`, `embezzlement`, `siphoned`, `diverted`, `kickback`, `scam`, `bogus`, `ghost work`, `fake`.

**From section 10, "Every flag is a recommendation to look. Never a finding":**
`finding`, `findings`, `irregularity`, `irregular`, `proven`, `conclusive`, `established`, `evidence of`, `guaranteed`, `certified`. Audit vocabulary. CAG produces findings; NidhiNetra produces a queue. The PRD's own comparison table depends on that difference holding.

**From section 6, "Nothing here is verified clean, only unflagged":**
`clean`, `all clear`, `cleared`, `safe`, `healthy`, `compliant`, `passed`, `no problems`, `looks good`. Same claim as green, made in words instead of colour. The colour is banned; the claim must be banned with it, or the ban is cosmetic.

**From section 4, "surface a vendor or agency receiving work from an unusual number of different MPs":**
`controls`, `dominates`, `captured`, `cornered`, `monopolises` as verbs for concentration. The neutral verb is `holds`. Concentration is a count, not a motive.

**From PRD scope, "a supervised fraud classifier (no labels exist; claiming one is a credibility failure)" and "Explainability beats accuracy theatre":**
`our AI`, `the model says`, `algorithm found`, `we found`, plus `accuracy`, `confidence`, `probability` and `likelihood` attached to a score. The risk score is an ordering device. Presenting it as a likelihood claims a calibration that no ground truth supports.

**From section 2, "Authority over friendliness. No illustrations, no mascots, no emoji, no startup energy":**
`Oops`, `Uh oh`, `Whoops`, `Sorry`, `Something went wrong`, `Hang tight`, `Just a sec`. Warn tier, plus the exclamation mark. Register, not safety; report separately so a genuine safety failure is never buried in tone noise.

**From PRD section 4, "Buttons say 'Flag for inspection'":**
`Investigate`, `Report`, `Escalate`, `Prosecute`, `Penalise` as action verbs. The officer inspects. Every other verb names a process this product has no authority to start.

### Tier 3. Structural patterns, not words

| Rule | Source |
|---|---|
| Reason worst case render over 92 characters fails; over 138 is a hard fail | Section 4, "roughly 46 characters", read correctly as a wrap measure. The reference examples are 53 and 52 characters. |
| Reason must end in a full stop | Both reference examples in Execution Plan 3.2. |
| Reason must contain at least one number | Section 1, "here is exactly why". A reason with no figure is an assertion. |
| Every placeholder declared, every declared param used | Execution Plan section 5, "Contract violations are auto-reject." |
| No string stored in uppercase only | Section 5, tracking and casing are size-specific presentation concerns. |
| U+2013 en dash and `--` as punctuation | Warn tier. Section 10 bans the em dash by name only. A double hyphen is an em dash typed in ASCII and should be caught. A plain hyphen in `2023-24` is correct and must not warn. |

### Scope and false positive control

A lint that fires on the project's own filenames will be disabled within a day, so the scope must be written down with the rules.

**In scope:** `contracts/strings.json`, text nodes and string literals inside `web/components/`, `aria-label` and `alt` attributes, and any `why_flagged` value in the committed snapshot.

**Out of scope, and never reported:** Python and TypeScript identifiers, module and file names, log messages, docstrings, comments, test names, commit messages, and every markdown document in the vault. The problem statement is literally titled "MPLADS Anomaly Detection" and the pipeline directory is `risk/detectors.py`. Both are correct. Both would fail a naively scoped lint.

**Word boundary matching, not substring matching.** `detect` as a substring hits `detectors`. Match whole words, case insensitively.

**Negated use needs an exemption list, and this was found by running the lint against the draft above.** Three strings use a banned word in order to deny it: "Flags are recommendations to inspect, not findings.", "Unflagged does not mean inspected or verified." and "An ordering device, not a likelihood." A word boundary lint rejects all three, and they are among the most load bearing strings in the product. Exempt them by **exact whole string match** in `lint.negation_exemptions`, never by weakening the word rules. That way a new negated phrase has to be added deliberately by a human rather than slipping through a loosened pattern.

**Two exit codes.** Tier 1 and Tier 2 fail the build. Tier 3 warn entries report without failing. Mixing them means a real accusation slips past inside a wall of tone warnings.

---

## 4. What this changes at CP0

Four additions to the CP0 checklist in `04 Prototype/Checkpoints.md`, for A6:

- [ ] `contracts/strings.json` exists and every user-visible string in the product is in it
- [ ] `validate.py` runs the lint in section 3 and fails on a deliberately banned word
- [ ] `validate.py` proves every `why_flagged` template renders within 92 characters at its declared maximum parameter lengths
- [ ] Contract 3.2 amended with `why_flagged_ref` as in section 1.8, and `validate.py` asserts the rendered sentence matches the template

One amendment to CP5, for A5:

> Current: "**Copy audit passed:** no 'fraud detected', no green anywhere, no em-dashes"
>
> Proposed: "**Copy audit passed:** the lint exits zero, and no user-visible string exists outside `contracts/strings.json`"

The current wording asks A5 to eyeball three specific mistakes. The proposed wording is a script, matching Execution Plan section 5, which already refuses eyeballing everywhere else: "**A schema validator script exists and runs.** Not eyeballing. A script."

---

## 5. Open items for the human

1. **Two peer group sentences exist in the frozen documents** (section 1.3 above). Both are drafted as named variants. Confirm the split, or pick one and delete the other from whichever document loses.
2. **Lakh and crore abbreviation.** This draft freezes `L` and `Cr` in cells and the spelled words in prose. The Design Review wrote `cr` lowercase and Part C3 wrote `crore` in full. Pick one and it propagates from `number_format`.
3. **Two union territory names exceed the reason line measure** and have no agreed short form. Flagged as an open item inside `state_display` rather than invented here. A1 confirms when real state values land.
4. **Timing.** `strings.json` has no dependency on the data spike outcome. Written during the spike or in Wave 0 is your call as arbiter under the Design Review's Approach A.
```