# Design: Fund Flow as an honest Sankey, rebuilt to the reference

Status: APPROVED by the user section by section, 2026-09-19. Author: Opus. Scope: the Fund Flow tab
(`05-App/web/components/fund-flow/`) and one API endpoint (`GET /api/graph/cluster`).

## Why

The reference is `hi.png`: three columns (Members of Parliament, implementing agencies, vendor) joined
by ribbons whose width is money, with a cluster panel and a ranked vendor list beside it. The deployed
tab (`implemented3.png`) does not read, and the causes are mechanical, not cosmetic:

1. Ribbons and names are positioned from different starting points. Each gutter SVG starts at the top of the
   column header while the rows start below it, so every ribbon sits about 24px too high (the red bar
   beside "IMPLEMENTING AGENCIES").
2. Ribbons live in a 72px gutter about 200px from the names they belong to, inside an SVG stretched with
   `preserveAspectRatio="none"`, which distorts curves and widths.
3. Ribbons are stroked lines on a log scale (1.5 to 12px), not stacked bands. Widths do not add up, so
   "width is money" is not true on screen.
4. Rows collapsed into "+N more" drop their ribbons, so money disappears.
5. The data overstates the MP side. `subgraph_for` keeps whole MP to agency edges, which carry the MP's
   entire spend through that agency. Measured on the live snapshot: SRI NELCO ₹7.65 Cr drawn against ₹0.72
   Cr paid to the vendor; Gyan Ganga ₹18.47 Cr against ₹6.60 Cr; Khalsa Exports ₹5.34 Cr against ₹1.56 Cr.
   Restricted to the works each agency paid to the vendor, the MP side equals the vendor total exactly for
   all 25 most concentrated vendors (each work has exactly one MP, one agency and one vendor).
6. The KPI tiles print raw rupees in Geist Mono through `t-num`, which also right-aligns them
   (`₹25,80,15,24,793`), against DESIGN.md's rule that KPI money is serif and compacted to crore.

## Decisions (user, 2026-09-19)

- Fix the data on the server (option chosen over a browser-side aggregation of `/api/works`, and over
  leaving the MP side overstated).
- Build our own three-column Sankey layout in SVG. No new dependency (d3-sankey and ECharts were
  considered and rejected: lockfile churn across the Mac and VM installs, general DAG layout we do not
  need, canvas rendering and config styling that fight the reference and accessibility).
- Page layout, copy changes and verification as below.

## 1. API: `GET /api/graph/cluster` returns balanced flows

- New pure function `graph_analysis.restrict_to_vendor_works(subgraph, facts)`. For every MP to agency
  edge it keeps only the `work_ids` that agency paid to the cluster's vendor, and recomputes `work_count`,
  `total_amount_inr` (sum of `sanctioned_amount_inr`, `or 0`, rounded to paise) and `flagged_work_count`
  (works whose scored `flags` list is non-empty). These are the same rules `build_graph.py` uses. Agency to
  vendor edges and all nodes pass through unchanged. `subgraph_for` and its TypeScript parity port are not
  touched.
- `routers/graph.py` `get_cluster` collects the vendor's work ids from the subgraph, reads
  `(sanctioned_amount_inr, flags)` for exactly those ids in one DuckDB query over `works LEFT JOIN scored`
  (connection closed with `contextlib.closing`, as F-23 requires), decodes `flags` with
  `db.decode_scored_json`, and returns the restricted subgraph. A work id missing from the tables counts
  as ₹0 and unflagged, matching `build_graph.py`'s treatment of a missing scored record.
- The response shape (fund_flow_graph schema) is unchanged; the endpoint docstring states the new meaning
  of MP to agency edges inside a cluster.
- Invariant: for every agency in a cluster, the sum of MP to agency amounts equals the agency to vendor
  amount, to the paisa after rounding.
- `GET /api/graph` (the `?agency=` deep link) is unchanged. There the agency's inflow can exceed its
  outflow by works with no recorded vendor; the chart tolerates unequal sides (see 2).

## 2. Chart: `sankey-layout.ts` (pure) and `SankeyChart.tsx`

These replace `ribbon-layout.ts` and `RibbonView.tsx`, whose files and tests are deleted.

**Columns.** MP, Agency, Vendor. Links are MP to Agency and Agency to Vendor. A node's value is
`max(inflow, outflow)` in sanctioned rupees.

**Collapse.** At most 7 rows per column. With more than 7 nodes, the 6 largest by value stay and the rest
merge into one "+N more" node per column. Links to merged nodes are merged per counterpart, so money is
preserved and the merged node keeps its ribbons. Column headings count every node, before collapse.

**Order.** Largest value first, then two rounds of value-weighted barycenter sweeps (forward and
backward) to reduce crossings, with a stable sort so ties keep their order. "+N more" stays last.

**Scale.** One scale `k` (px per rupee) for the whole chart, so a rupee is equally thick on both hops.
`k = min(TARGET_BAR_PX / busiestColumnTotal, kFit)`, where `kFit` is the largest `k` whose tallest column
(boxes plus gaps) fits `PLOT_MAX_PX`, found by bisection. `k` never drops below
`MIN_BAR_PX / busiestColumnTotal`; the plot grows taller instead. Starting values, each a named
calibration constant: `TARGET_BAR_PX 280`, `PLOT_MAX_PX 460`, `MIN_BAR_PX 160`, row gap 10px.

**Nodes.** Each node is a label box (reference style) with a 6px bar on its left edge.
- Bar height = `max(sum of in-link widths, sum of out-link widths)`, centred in the box.
- Box height = `max(bar height, minimum)`. The minimum is MP 44px (one-line name plus amount), agency and
  vendor 58px (two-line name plus amount).
- Columns are centred vertically in the plot.
- Box widths are `clamp(width × 0.21, 170px, 250px)`. The two ribbon gaps share the remaining width.

**Links.** Each link is a filled band between two cubic curves with control points at the horizontal
midpoint. Its thickness is `amount × k`, linear, with a 1.5px floor only for flows too thin to see.
- In-links end at the bar's left edge. Out-links start at the box's right edge.
- Bands stack from the top of the bar's span, sorted by the other end's position, so none cross at a node.
- Colour comes from the link's own flagged share: no works flagged is blue (`--accent`), some flagged is
  amber (`--risk-3`), all flagged is red (`--risk-4`), at low opacity. They are drawn blue first, then
  amber, then red.
- The vendor box takes the wash and bar colour of its own tier. "+N more" uses a neutral bar and a sunken
  box.

**Rendering.**
- One container measured by `ResizeObserver`, with a 720px minimum width. Below that the chart scrolls
  sideways inside its card.
- One SVG draws the bars and bands. The label boxes are HTML, absolutely positioned from the same layout
  numbers, so labels and ribbons cannot drift apart.
- Column headings are placed the same way: "Members of Parliament (7)", "Implementing agencies (8)",
  "Vendor (1)", or "Vendors (n)" when there is more than one.

**Box content.**
- MP: name on one line with an ellipsis, then the amount.
- Agency: a bank icon, the name (up to two lines), then the amount.
- Vendor: a briefcase icon, the name (up to two lines), then "amount · N works".
- The full name is always in the tooltip.
- Chart amounts use the threshold-scaled `formatCurrency` (₹ / L / Cr), which exists for exactly this
  compact use.

**Interaction.**
- Each box is a `<button>`. Hovering or focusing a box, or hovering a band, brings that node's bands (or
  that band) to full strength and dims the rest.
- An HTML tooltip gives source and target names, the sanctioned amount, the work count and the
  `cluster_risk_flag_note` sentence.

**Accessibility.**
- The SVG is `aria-hidden`.
- A visually hidden table lists every flow: from, to, sanctioned amount, works, flagged works.

**Motion.** When the focused vendor changes, the band group reveals left to right with a `clip-path` inset
over about 480ms, easing out. It is disabled under `prefers-reduced-motion`.

## 3. Page layout, top to bottom

1. **Masthead.** The shared `PageMasthead`, unchanged.
2. **KPI row** (`StatTiles`, restyled to DESIGN.md's KPI card). Each card has a 52px pastel icon tile, a
   sentence-case label and a serif tabular figure.
   - Flow represented: `formatCroreParts`, as in "₹2,580.15" with a small "Cr".
   - Members of Parliament.
   - Implementing agencies.
   - Vendors.
   - Icons are Database, UsersThree, Bank and Briefcase. The tiles are blue for the first three and violet
     for vendors.
   - While loading, the four cards show skeletons so the page does not shift.
3. **Toolbar card** (`ConcentrationFilter`, restyled into one row that wraps on narrow screens):
   - the minimum Members stepper;
   - the search field;
   - "{shown} of {matching} matching vendors shown";
   - Reset (a secondary button with an icon, disabled at the defaults).
4. **Main row.** The chart card takes the remaining width; the sidebar is 26rem and drops below the chart
   under 75rem.
   - **Chart card.**
     - A header with the vendor name (serif `h2`) and a "{count} MPs" pill.
     - The Sankey.
     - A legend strip on the sunken ground: three swatches with the existing tier labels, and on the right
       the existing `ribbon_info_note`.
   - **Cluster in focus card** (`ClusterInFocus`).
     - The vendor name, then four stat tiles (Members, Agencies, Works, and Sanctioned value, the last on
       the rose tile).
     - When any linked work is flagged, a risk box on `--risk-4-wash` with a warning icon: the
       `cluster_risk_flag_note` line, then `framing.standing_note` ("Flags are recommendations to inspect,
       not findings.", an exact-match lint exemption).
     - The primary "View linked works" button with an arrow, linking to `/inspections?vendor_id=...` as
       today.
   - **Most concentrated vendors card.** A table (#, Vendor, MPs) showing 5 rows, with the selected row on
     `--accent-wash`. "View all {count}" expands the list in place and "Show fewer" collapses it. Rows are
     buttons that focus a vendor.
5. **Deep link (`?agency=`).** No KPI row, toolbar or sidebar. The chart runs full width under the agency
   name, with the existing `back_to_clusters` link. Vendors collapse to 6 + "+N more".
6. **Below.** `AliasReviewQueue` and the `scale_caveat` line, unchanged.

**States.** These are kept, laid out in the new cards:
- the loading skeletons (no spinner, no text, per the design brief);
- `api_unreachable` with retry;
- `rebuild_required`;
- the empty filter (`empty`, `empty_body`) in the chart card and the list.

## 4. Copy (`contracts/strings.json`, `fund_flow`, with a dated `_meta` changelog entry)

- `subtitle` becomes "Trace concentrated MP, agency and vendor relationships in the MPLADS record."
- `search_label` and `search_placeholder` become "Search vendors". The search matches vendor names only,
  so the current "vendor or agency" claims something the search does not do.
- New keys:
  - `toolbar_count` "{shown} of {matching} matching vendors shown";
  - `members_pill` "{count} MPs";
  - `view_all` "View all {count}";
  - `show_fewer` "Show fewer";
  - `flow_table_caption` "Every flow in this chart";
  - `flow_table_from` "From";
  - `flow_table_to` "To";
  - `flow_table_amount` "Sanctioned";
  - `flow_table_works` "Works";
  - `flow_table_flagged` "Flagged works".
- Keys no longer shown stay in the contract, since nothing checks for unused keys (`contracts/validate.py`
  checks data files, and the banned-word lint runs only on risk reasons in `explain.py`):
  `concentration_filter_description`, `cluster_median_note`, `clusters_note`. The "Selected cluster"
  eyebrow from the reference is not built (Impeccable craft floor), because the highlighted list row
  already marks the selection.

## 5. Verification

- **API:**
  - pytest: a unit test for `restrict_to_vendor_works` on a hand-built graph (an MP with two works at one
    agency, only one paid to the vendor);
  - an endpoint test that every agency in a fixture cluster balances and that every MP edge's `work_ids`
    are a subset of that agency's paid works;
  - the existing suite;
  - `uvx ruff` on the changed files only.
- **Web (vitest):** `sankey-layout` invariants:
  - bands fill each bar span exactly, without overflow;
  - a balanced input gives equal agency sides;
  - "+N more" preserves totals and link counts merge;
  - boxes in a column never overlap;
  - the output is identical for shuffled input;
  - widths are linear in amount above the floor;
  - unequal deep-link sides do not overflow.
- **Web (components and gates):**
  - `SankeyChart` render tests: headings with counts, labels, legend, hidden table rows, hover highlighting;
  - `FundFlowClient` and `StatTiles` tests updated;
  - tsc, eslint and `next build` through `web-gates` in the VM mirror.
- **Visual:**
  - the real API and web app on the committed snapshot, screenshotted at 1920×1080, 1440×900 and 390px
    wide with headless Chromium;
  - compared against `hi.png`, followed by one batched fix round;
  - Impeccable's `detect` run once on the changed files.
- **Not done without asking:** push or deploy. Pushing `main` redeploys Vercel and Render.
