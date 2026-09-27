# NidhiNetra Finale Demo Script (T14/T15)

SIH26102, MPLADS inspection targeting, for the MoSPI jury. Data as of **4 September 2026**
(committed snapshot): 44,810 works under implementation, Rs 2,496.73 cr, 729 District
Authorities, 535 constituencies. Say the population and the date beside every number.
Never say fraud, detect, anomaly, verified, confirmed, compliant, finding, accuracy,
confidence, probability, likelihood, investigate or caught; no em dash; a score orders,
it never predicts one work.

## 10-minute path (Dashboard, then Inspection List for the role lenses)

| # | Time | Screen / click | Say |
|---|---|---|---|
| 1 | 0:00 | Dashboard loads | "44,810 works under implementation, Rs 2,496.73 crore, as of 4 September 2026. Every number on this screen comes from that one snapshot." |
| 2 | 0:45 | Point at the three pendency cards | "The Ministry reviews three timelines every month. 33,204 of 44,810 works, 74.1 percent, were sanctioned more than 45 days after the MP's recommendation, median 90 days. 10,856 are open past one year. 17,441 show no payment after 90 days. We never combine these into one count; each is its own check." |
| 3 | 1:45 | Annual inspection quota bar | "The list's own 10 percent line falls at rank 4,481 of 44,810." |
| 4 | 2:15 | Open Inspection List, View as: Ministry (default) | "Each District Authority owes its own 10 percent, rounded up. Across 729 authorities that is 4,820 inspections this year." |
| 5 | 2:45 | View as: State Nodal Authority | "A state sees its third-party duty: 986 works of Rs 25 lakh or more, plus half of 1,739 between Rs 15 and 25 lakh, 1,856 in all." |
| 6 | 3:30 | View as: District Authority, choose Jaunpur | "Jaunpur holds 813 works under implementation; its own 10 percent is 82. The list below is ordered for that." |
| 7 | 4:15 | Click Print this list | "One click, and a District Authority has a paper list for the field, ranked, with today's snapshot date on it." |
| 8 | 4:45 | View as: Member of Parliament, choose a constituency | "The same duty sentence, for that MP's own constituency: how many of their works were sanctioned late, how many are open past a year." |
| 9 | 5:30 | Back to Ministry. Timeline filter, choose "At risk of running late" | "3,396 works sanctioned in the last year are on this watch list." |
| 10 | 6:00 | Open a flagged row's detail panel | "Early warning: among the tenth of recent works that a model trained on earlier sanctions ranks most at risk of staying open past one year. It orders; it says nothing certain about this one work." |
| 11 | 6:45 | Close that panel. Clear the Timeline filter. Scroll to the duplicate review queue | "An open model read 39,093 near-identical description pairs, about $1.43 in total, and code checked every quoted word it used. 1,265 work-level candidates came out of that: 1,103 possible duplicates, 162 possible splits or phases. 5.8 percent were left unclear, 6.3 percent had a quoted word the code rejected." |
| 12 | 7:45 | Search work 293635 in the header, open its detail panel | "This work carries both quoted spans side by side, for the officer to check, not a verdict. It also shows why: Stage on the portal, Completed on and Documents on the public dashboard are wired end to end but carry no values in this snapshot, so they read not recorded. The pre-finale data refresh populates them." |
| 13 | 8:45 | Header toggle to Hindi | "One toggle switches every interface string, English or Hindi, per GIGW 3.0. The numbers themselves stay exactly as published, in the same digits." |
| 14 | 9:15 | Reports page, early-warning method line | "Trained on 5,292 sanctioned works, checked on a later 8,738. Held-out ROC-AUC 0.692. Its top tenth held about twice the average share of works still open on that later set." |
| 15 | 9:50 | Close | "Flags are recommendations to inspect, not findings." |

## 3-minute cut

Rows 1, 2, 6, 7, 10, 12, 13 only: Dashboard premise and pendency cards; District Authority
lens with its duty line and Print this list; the early-warning detail line; work 293635's
judged near-copy quotes; the Hindi toggle. Skip State/MP lenses, the queue's own rates note
and the Reports page.

## Offline fallback

On the presenter's laptop, from `05-App/`: `make demo` (present in `05-App/Makefile`;
it runs the API on port 8000 and the web app on port 3000 together, against the committed
snapshot, `Ctrl+C` stops both). Open `http://localhost:3000`. Then turn Wi-Fi off and reload:
the page keeps working end to end, because both servers are local and the header/body fonts
(`next/font/google`) are self-hosted at build time, never fetched from Google at runtime. The
app itself never calls out except to its own local API; the header's own "Offline. Showing
snapshot from 4 Sep 2026. 79,068 records. No live connection in use." line is the honest,
built-in state for exactly this, not a demo trick.

## Q&A additions

- **"74% sanctioned after 45 days?"** The median is 90 days, a systemic delay, so it is shown
  per authority rather than as a work flag.
- **"4,481 vs 4,820?"** One is the list's 10 percent line; the other is each authority's own
  10 percent, rounded up.
- **"Why logistic regression?"** 5,292 labelled works and 5 features (sanctioned amount, the
  agency's prior record, sanction month, category, state); it beat gradient boosting; its
  coefficients explain.
- **"Is 0.69 good?"** It orders, it does not predict any one work. Its top tenth held about
  twice the average share of works still open on a later, unseen set of sanctions.

## Slide text for H5 (3 bullets per new feature; paste into the PPTX, check in PowerPoint)

**Pendency timelines**
- 33,204 of 44,810 works under implementation (74.1%) were sanctioned more than 45 days after
  the MP's recommendation; median 90 days.
- 10,856 works are open past one year (Rs 596.24 cr); 17,441 show no payment after 90 days
  (Rs 906.87 cr).
- Three separate MoSPI checks, each shown on its own, never combined into one count.

**Role lenses**
- One preset scope plus one duty sentence, for Ministry, State Nodal Authority, District
  Authority and Member of Parliament; no new nav tab.
- A District Authority sees its own 10 percent, rounded up (4,820 nationally across 729
  authorities), and can print that exact list.
- A State Nodal Authority sees its third-party duty: 986 works of Rs 25 lakh or more plus half
  of 1,739 between Rs 15 and 25 lakh, 1,856 in all.

**Early warning**
- A logistic regression trained on 5,292 sanctioned works, checked on a later 8,738; held-out
  ROC-AUC 0.692.
- Its top tenth held about twice the average share of works still open on that later set.
- It adds one filter and one line of context to a work; it never states a per-work chance.

**Near-copy duplicates**
- An open model read 39,093 near-identical description pairs (about $1.43 in total); code
  checked every quoted word.
- 1,265 work-level candidates: 1,103 possible duplicates, 162 possible splits or phases.
- Every judged row carries the model's own quoted words from each description, for an officer
  to check.

**Hindi interface**
- One header toggle switches every interface string, meeting GIGW 3.0's Hindi and English
  requirement.
- Data values stay exactly as published; numerals stay in the international form (Constitution
  Art. 343(1)).
- Reasons and the early-warning line are translated too, not only labels.

## T15: 36-hour finale build menu (six increments, each under 2 hours, each visible in the demo)

1. **A state league table** from `GET /api/pendency?group_by=state` on Reports. The endpoint
   already returns per-state counts and quotas; this is a table component, no backend change.
2. **A District Authority league table** (top 20 by open past one year), same endpoint with
   `group_by=district_authority`, sorted and capped client-side.
3. **The top 3 logistic-regression coefficients** behind a work's early warning. The model
   already fits them; store them alongside the metrics in `early_warning.json` and show them
   next to the detail line.
4. **A Hindi print view** (if T11). The print-only header already exists; carry the Hindi
   overlay into it.
5. **One jury-requested filter.** Whatever they ask for, added to `FilterPanel.tsx`'s existing
   `SelectControl` pattern.
6. **The T13 live pull on stage**, if the venue network allows. `POST /api/refresh` is already
   wired to the "Refresh now" button.

## Assets

- Video: `docs/demo/walkthrough.webm` (1920x1080, silent, follows the 10-minute path above).
- Screenshots: `docs/screenshots/{dashboard,inspection-list,fund-flow,pendency,district-lens,hindi}.png`.
