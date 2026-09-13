# NidhiNetra: Design Brief

SIH 2026 · Problem statement SIH26102 · Ministry of Statistics and Programme Implementation

**Part A** is the prompt. Copy it whole into the design tool and change nothing. **Part B** is the resource pack: attach it, or paste as a follow-up. **Part C** is engineering reference, not for the design tool.

---

# PART A. THE PROMPT

> Copy from the line below to END PROMPT.

---BEGIN PROMPT---

Design a desktop web application called **NidhiNetra**.

## 1. What it is

NidhiNetra is an oversight instrument for India's Ministry of Statistics and Programme Implementation. It monitors MPLADS, a scheme under which every Member of Parliament directs roughly 5 crore rupees a year into local public works: roads, school buildings, water systems, health centres. Thousands of works, thousands of contractors, tens of thousands of crores.

One fact drives the entire interface. Under the scheme's own guidelines, **District Authorities must physically inspect at least 10 percent of works under implementation every year.** Nothing tells them which 10 percent to choose, so the selection is effectively arbitrary, and around 90 percent of works are never physically inspected at all.

NidhiNetra ranks the works by risk and hands the officer a prioritised inspection list.

**It never accuses anyone of fraud.** It says: these are the ones worth looking at first, and here is exactly why. Every design decision below serves that distinction. It is not a disclaimer, it is the product.

## 2. Who is looking at it

A senior civil servant at the Ministry. Career official, reads dense documents all day, personally answerable if a Parliamentary Question or a national audit report names this scheme.

They are not impressed by decoration. They are impressed by a screen that tells them what to do on Monday morning.

This is an instrument of government, not a consumer analytics product. Authority over friendliness. No illustrations, no mascots, no emoji, no startup energy.

## 3. The design thesis

**Swiss for content. Apple for chrome.**

Two traditions, each doing what it is genuinely good at:

**Everything on the page is Swiss editorial.** Off-white paper. Hairline rules, never boxes or cards. No shadows. No borders drawn around things. Typography, alignment and whitespace carry the whole hierarchy. This is the tradition that exists specifically to make dense tabular information readable, which is exactly the problem here.

**Anything that floats is Apple light.** The detail panel, modals, tooltips, the filter bar once it becomes sticky. These get a true white surface, a soft tinted shadow, and a gentle radius. Swiss has no vocabulary for "this is above the page"; Apple's material language does.

Note the inversion from dark interfaces: in light, an elevated surface is **brighter** than the page. So the page is off-white and floating surfaces are pure white. Elevation reads as light, not as grey. Never invert this.

**No frosted glass anywhere.** Translucency depends on contrast with what sits behind it, and white on white has none. Depth here comes from elevation and hairlines, which actually work in light.

The overall feeling: a beautifully set annual report that happens to be interactive. Quiet, confident, unhurried, expensive. Every value on the page deliberate and defensible.

## 4. Layout

### Page structure
A single centred column, maximum 90rem, with generous outer gutters. Never full-bleed: a table stretched across a 2560px monitor is unreadable.

Vertical order, top to bottom, separated by generous whitespace rather than dividers:
1. **Title block.** The product name, then the premise as a real sentence, not a tagline.
2. **Summary strip.** Four figures in a row: works under implementation, flagged for inspection, total rupees under flagged works, rupees idle beyond twelve months. Big numerals, small labels beneath. No boxes around them. Separated by whitespace alone.
3. **Filter bar.** State, year, work category, flag type. Becomes sticky on scroll, and only then does it gain the floating treatment from section 3.
4. **The table.**

### The table, which is the product

Use **two-line rows.** Do not cram eight columns onto one line.

- **Line one:** rank, work name, district, implementing agency, sanctioned amount, spent amount, risk score.
- **Line two:** the plain-language reason, indented to align under the work name, in muted ink at one step down in size, constrained to a comfortable reading measure of roughly 46 characters.

The reason is the most important element on the entire page. Giving it its own line rather than a cramped column is the single most consequential layout decision here. It is the product's voice.

Column rules:
- Rank is narrow, fixed width, tabular numerals, muted. It orders the page; it does not shout.
- Text columns align left. All numeric columns align right. No exceptions.
- **No vertical rules at all.** Alignment does the separating.
- One hairline between rows. No zebra striping, no fills.
- Sticky header. Where the scrolling content passes under it, fade a short gradient mask instead of drawing a border.
- Row height is derived from line height plus padding, never a fixed pixel value.

### The detail panel
Slides in from the right, roughly 32rem wide or 38 percent of the viewport, whichever is smaller.

**No dimming scrim.** This is a parallel surface, not a blocking task: the officer is comparing this work against the list behind it and must keep that context. Reserve scrims for genuinely blocking actions.

It contains the full record, and then the two things that matter:

**The risk breakdown.** Each contributing factor on its own line with its own weight, so the score is never a black box.

**The peer group, stated plainly.** One canonical sentence, frozen: "Compared against 1,72,961 road works in Bihar, 2023-24." Category, then state, then year, in that order, with the count in Indian numbering. An earlier draft of this brief said "in this state for this year" while the PRD said "Bihar, 2023-24"; the explicit form wins because a judge reading a screenshot has no other way to know which state and year the comparison used. The template lives in `contracts/strings.json`, not in a component. Give it real visual weight. Do not bury it as a caption. This single element answers the strongest objection anyone can raise against the whole product, which is that a road through hills genuinely costs more than a road across plains. Showing the comparison set proves the comparison was fair.

From here, an entry point into the fund-flow view.

### The fund-flow view
A network diagram. Nodes are MPs, implementing agencies, and vendors. Edges are money.

Its purpose is to surface a vendor or agency receiving work from an unusual number of different MPs or districts, a pattern that is invisible in any row-by-row view.

It must be readable, not a hairball. Filter aggressively by default and expand on demand. Bring one cluster into focus and let everything else recede. Controls float over the canvas using the Apple light treatment.

## 5. Type

Use **Geist** for the interface and **Geist Mono** for every number.

**Anchor the scale to the table cell**, because it is the most frequent size on the page, and derive every other size from it by a consistent ratio of about 1.2. Do not pick sizes one at a time.

**Tracking is size-specific.** A single letter-spacing value is wrong somewhere. Large text reads too loose as it grows and needs negative tracking. Small uppercase labels need positive tracking. Body sits at zero.

**Leading runs inversely to size.** Tight on the title block, comfortable on the reason text.

Build hierarchy from weight, size and leading together, never from size alone. Weight adds presence without consuming space, which is what a dense page needs.

**Tabular numerals are mandatory** on every numeric column and on the rank. Proportional numerals in a ranked table look amateur immediately.

**All rupee amounts use Indian numbering.** Write 1,72,961 and not 172,961. Getting this wrong reads as a foreign product built by people who did not check.

Set optical sizing to automatic. Express sizes in relative units so the layout scales with the reader's own text-size setting rather than breaking.

## 6. Colour

Light, restrained, and almost monochrome. Colour is a scarce resource spent only where it carries meaning.

- **Paper:** off-white, very faintly cool. Not pure white, because pure white leaves no room for elevation to read.
- **Floating surfaces:** pure white.
- **Ink:** a near-black with a trace of blue. Never pure black.
- **Hairlines:** light enough to organise without drawing attention.
- **One accent only,** cool in tone, used exclusively for interactive elements. It never appears decoratively.

**The risk scale, and this rule is absolute: never use green.**

Green means verified clean. Nothing here is verified clean, only unflagged. Green is a claim we cannot support and a knowledgeable viewer will catch it.

Use a single warm ramp running from muted ink through amber to a deep red at the top. In light mode these must be **darker and more saturated** than their dark-mode equivalents to hold contrast against white. Keep them institutional rather than alarmist. These are recommendations to look, not alarms.

The risk ramp is warm and the interactive accent is cool. That separation is deliberate: it stops the officer confusing "this is clickable" with "this is risky."

Rank and position carry most of the signal. Colour reinforces and never carries meaning alone. Every colour-coded element also carries a number or a word.

## 7. Icons

Phosphor Icons, one weight throughout, chosen once and never mixed. Never draw icon paths by hand.

## 8. Motion

Purposeful, never decorative. The interface should feel like a physical object that responds instantly and can be redirected at any moment.

**Feedback fires on pointer down, never on release.** A row responds the instant it is pressed. Waiting for the click to complete feels dead.

**Use springs, not durations.** Think in two parameters: damping, where 1.0 settles with no overshoot, and response, meaning how quickly it reaches the target. Add bounce **only when a gesture carried momentum into it.** Overshoot on a panel opened by a click is wrong. Overshoot on something the user flicked is right.

- The detail panel opens from a click, so it is critically damped with no bounce, and a response near 0.3 seconds.
- The graph settling after a pan or a flick carries momentum, so it takes a little bounce.

**Every animation is interruptible.** A closing panel that the user grabs again follows immediately, rather than finishing and then reopening. Animate from the current on-screen value, never from the logical target, or the interruption produces a visible jump.

**Spatial symmetry.** What enters from the right leaves to the right. Anchor the panel's transform origin toward the row that opened it.

**Boundaries resist, they do not stop dead.** At the end of the table and at the edges of the graph canvas, apply progressive resistance. A hard stop reads as frozen.

**Nothing loops.** No ambient animation, no parallax, no scroll effects. Anything still moving after it has arrived is a bug. Animate only transform and opacity.

## 9. Accessibility, three independent signals

Reduced motion does not mean no feedback. It means a gentler equivalent. Handle all three, not just the first:

- **Reduced motion:** replace springs and slides with short opacity cross-fades. Drop all overshoot. Keep colour and opacity changes that aid comprehension.
- **Reduced transparency:** any translucency becomes fully opaque.
- **Increased contrast:** near-solid surfaces with a defined, contrasting border on every floating element.

WCAG AA minimum on all text, including placeholder text, helper text and focus rings. Visible keyboard focus on every interactive element, and the table must be fully keyboard navigable.

## 10. Words

The framing discipline is a UI constraint. One overclaiming label in a screenshot undoes the entire product.

| Never write | Write instead |
|---|---|
| Fraud detected | Flagged for inspection |
| Suspicious work | High priority for review |
| Corruption risk | Risk score, or Inspection priority |
| Verified clean, or No issues | Not currently flagged |
| Confirmed anomaly | Statistical outlier against peer group |

Every flag is a recommendation to look. Never a finding.

**No em-dash characters anywhere in the interface.** Not in headings, labels, buttons, body text, tooltips, empty states or alt text. Use a comma, a full stop, or restructure the sentence.

## 11. Nothing is hardcoded

Two meanings, both binding.

**Values.** Define a type scale and a spacing scale, each derived from a single anchor by a consistent ratio. Every size, gap, padding and row height is expressed in terms of those scales. No stray hex codes, no stray pixel values scattered through components. Someone should be able to change the ratio in one place and have the whole page reshape coherently.

**Content.** No figure, label, count or name is baked into a component. Every value on screen arrives as data. That means designing the states that follow from it, and they are part of this deliverable, not an afterthought:

- **Loading:** skeleton rows matching the real row geometry, never a spinner.
- **Empty:** a filter combination returning nothing, composed properly, saying what to do next.
- **Missing fields:** vendor unknown, date absent, amount not yet recorded. Government data is incomplete and the design must expect it rather than break on it.
- **Long values:** a work name running to three lines, an agency name longer than its column.

## 12. Do not ship

Purple or blue gradients. Any glow. Cards with drop shadows and icon circles, which is the default dashboard look. Green anywhere. Traffic-light colour coding. Stock illustrations, 3D shapes, decorative blobs. Frosted glass. A hairball network graph. Charts that fill space rather than answer a question. Any number without tabular figures. Hand-drawn icons. Pure black or pure white text. Version stamps, scroll cues, decorative status dots, locale or weather strips. Vertical rules in the table. Zebra striping.

## 13. Constraints

Desktop first, because the real user is at a desk. Must hold up on a projector at 1920 by 1080 and stay legible from the back of a room, so run base sizes above typical web defaults. Light is the only theme required; if a dark variant is offered it must obey the same rules with elevation inverted. Must render fully from local data with no network.

## 14. Deliver

1. **The inspection list, fully realised.** Including hover, keyboard focus, loading, empty, and missing-field states. This one matters more than the rest combined.
2. **The detail panel,** showing the risk breakdown and the stated peer group.
3. **The fund-flow view.**
4. **A specimen sheet:** the derived type scale with its size-specific tracking, the spacing scale, the colour set, and the elevation levels.

---END PROMPT---

---

# PART B. RESOURCE PACK

## B1. Scales, derived from two anchors

Change the two anchors and the entire system reshapes. This is what "no hardcoding" means in practice.

```css
:root {
  /* ---------- The only two numbers chosen by hand ---------- */
  --font-base:  0.875rem;   /* the table cell: most frequent size = the anchor */
  --ratio:      1.2;        /* minor third; tight enough for dense UI */
  --space-unit: 0.25rem;

  /* ---------- Type scale, derived ---------- */
  --font-2xs: calc(var(--font-base) / var(--ratio) / var(--ratio));
  --font-xs:  calc(var(--font-base) / var(--ratio));
  --font-sm:  var(--font-base);
  --font-md:  calc(var(--font-base) * var(--ratio));
  --font-lg:  calc(var(--font-md)   * var(--ratio));
  --font-xl:  calc(var(--font-lg)   * var(--ratio));
  --font-2xl: calc(var(--font-xl)   * var(--ratio));

  /* ---------- Leading, inverse to size ---------- */
  --leading-tight:  1.1;
  --leading-snug:   1.3;
  --leading-normal: 1.55;

  /* ---------- Tracking, size-specific ---------- */
  --track-display: -0.022em;
  --track-heading: -0.012em;
  --track-body:     0em;
  --track-micro:    0.04em;   /* small uppercase labels only */

  /* ---------- Space scale, derived ---------- */
  --space-1:  var(--space-unit);
  --space-2:  calc(var(--space-unit) *  2);
  --space-3:  calc(var(--space-unit) *  3);
  --space-4:  calc(var(--space-unit) *  4);
  --space-6:  calc(var(--space-unit) *  6);
  --space-8:  calc(var(--space-unit) *  8);
  --space-12: calc(var(--space-unit) * 12);
  --space-16: calc(var(--space-unit) * 16);
  --space-24: calc(var(--space-unit) * 24);

  /* ---------- Layout metrics, derived not magic ---------- */
  --row-height:     calc(var(--font-sm) * var(--leading-snug) + var(--space-3) * 2);
  --page-max:       90rem;
  --page-gutter:    var(--space-8);
  --panel-width:    min(32rem, 38vw);
  --measure-reason: 46ch;
  --radius-control: calc(var(--space-unit) * 1.5);
  --radius-panel:   calc(var(--space-unit) * 3);
}
```

## B2. Colour, light

`oklch` keeps the risk ramp perceptually even, which a hex ramp will not.

```css
:root {
  /* Surfaces. Elevation reads BRIGHTER than the page in light mode. */
  --paper:           oklch(99%   0.002 250);  /* the page */
  --surface:         oklch(100%  0     0  );  /* floating: panel, modal, tooltip */
  --sunken:          oklch(97.5% 0.003 250);  /* sticky header strip */
  --hairline:        oklch(92%   0.004 250);
  --hairline-strong: oklch(85%   0.005 250);

  /* Ink. Never pure black. */
  --ink:       oklch(21% 0.012 265);
  --ink-muted: oklch(48% 0.010 265);   /* the reason line */
  --ink-faint: oklch(64% 0.008 265);   /* rank, labels */

  /* One accent. Cool. Interactive only, never decorative. */
  --accent:      oklch(52% 0.16  255);
  --accent-wash: oklch(96% 0.03  255);

  /* Risk ramp. Warm. Darker than a dark-mode ramp so it holds on white.
     NO GREEN AT ANY STEP. Green would claim "verified clean". */
  --risk-0: var(--ink-faint);          /* not currently flagged */
  --risk-1: oklch(66% 0.11 75);        /* low */
  --risk-2: oklch(60% 0.14 55);        /* moderate */
  --risk-3: oklch(54% 0.16 38);        /* high */
  --risk-4: oklch(46% 0.17 28);        /* highest priority */

  /* Elevation. Tinted to the ink hue, never pure black. Two levels only. */
  --shadow-raised: 0 1px 2px oklch(21% 0.012 265 / .06),
                   0 4px 12px oklch(21% 0.012 265 / .06);
  --shadow-panel:  0 2px 4px oklch(21% 0.012 265 / .05),
                   0 16px 48px oklch(21% 0.012 265 / .12);
}
```

## B3. Type roles and the sticky-header mask

```css
:root { font-optical-sizing: auto; font-synthesis: none; }

.t-title   { font-size: var(--font-2xl); font-weight: 600; letter-spacing: var(--track-display); line-height: var(--leading-tight); }
.t-figure  { font-size: var(--font-xl);  font-weight: 550; letter-spacing: var(--track-heading); line-height: var(--leading-tight); font-variant-numeric: tabular-nums; }
.t-work    { font-size: var(--font-sm);  font-weight: 500; letter-spacing: var(--track-body);    line-height: var(--leading-snug); }
.t-reason  { font-size: var(--font-xs);  font-weight: 400; letter-spacing: var(--track-body);    line-height: var(--leading-normal); color: var(--ink-muted); max-width: var(--measure-reason); }
.t-colhead { font-size: var(--font-2xs); font-weight: 600; letter-spacing: var(--track-micro);   line-height: var(--leading-snug); text-transform: uppercase; color: var(--ink-faint); }

/* Every numeric cell. Both properties, not one. */
.t-num {
  font-family: 'Geist Mono', ui-monospace, monospace;
  font-variant-numeric: tabular-nums;
  font-size: var(--font-sm);
  line-height: var(--leading-snug);
  text-align: right;
}

/* Sticky header: fade the content under it. Never a 1px divider. */
.table-head-mask {
  height: var(--space-3);
  background: linear-gradient(to bottom, var(--paper), transparent);
}

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation-duration: .01ms !important; transition-duration: 120ms !important; }
  .panel { transform: none !important; }   /* cross-fade, never slide */
}
@media (prefers-contrast: more) {
  .panel, .tooltip { border: 1px solid var(--hairline-strong); box-shadow: none; }
}
```

## B4. Fonts and icons, licensing confirmed

| Asset | Licence | Verified |
|---|---|---|
| Geist, Geist Mono | **SIL Open Font License 1.1** | Commercial use, self-hosting, subsetting and embedding all permitted. Ship the licence file with the fonts. |
| Phosphor Icons | **MIT** | Free for commercial use. |

`https://vercel.com/font` · `npm i geist` · `https://phosphoricons.com` · `npm i @phosphor-icons/react`

Apple's SF Symbols is licensed for Apple platforms only and cannot ship on the web, which is why Phosphor is the substitute rather than a compromise.

## B5. Build stack

| Layer | Choice | Why |
|---|---|---|
| Data grid | **TanStack Table** | Headless. Sorting, virtualisation and column sizing already solved. The ranked table is the product; do not hand-roll it. |
| Primitives | Radix UI | Accessible dialog, popover, tooltip, select, unstyled |
| Styling | Tailwind v4, with B1 and B2 as the token layer | |
| Motion | Motion, from `motion/react` | Spring API maps to damping and response; `useReducedMotion` built in |
| Graph | Cytoscape.js or react-force-graph | Both handle filtering and clustering properly |
| Icons | `@phosphor-icons/react` | |

---

# PART C. ENGINEERING REFERENCE

Not for the design tool. This is for whoever builds the data layer.

## C1. The MPLADS dashboard has a public REST API

**Verified live on 2026-08-31 by inspecting the dashboard's own network traffic.** This overturns the earlier assumption in the plan that no bulk API exists.

Base: `https://mplads.mospi.gov.in`

| Endpoint | Verified |
|---|---|
| `POST /rest/PreLoginDashboardData/getStateData` | Returns clean JSON. 36 states with numeric `STATE_ID`. |
| `POST /rest/PreLoginDashboardData/getTenureData` | 200 OK |
| `POST /rest/PreLoginDashboardData/getTilesData` | Called on load |
| `POST /rest/PreLoginCitizenWorkRcmdRest/getAttachmentById` | Work-level attachments |
| `getMpNameByStates`, `getReviewDetailsByWork`, `getAttachmentDataForTileReports` | Referenced in the dashboard's own client code |

**No authentication.** All calls are `POST`, `Content-Type: application/json`, with a JSON body.

Sample response from `getStateData`:
```json
[{"STATE_NAME":"Andhra Pradesh","STATE_ID":2},{"STATE_NAME":"Bihar","STATE_ID":6}]
```

The presence of `PreLoginCitizenWorkRcmdRest` and `getReviewDetailsByWork` means **work-level records and their uploaded attachments are publicly reachable**, not just state aggregates. That is what the product needs.

**Two cautions, both mandatory.**

The dashboard's JavaScript is deliberately obfuscated: strings are unicode-escaped and some are stored reversed. That is a signal the operators would rather people did not script against it. The data is public, unauthenticated, and published for public consumption, so reading it is legitimate. But be a good citizen: **rate-limit hard, cache the first successful pull to disk immediately, and never re-fetch during a demo.** Getting the team's IP blocked by a government server mid-hackathon would be unrecoverable.

Second: these are undocumented internal endpoints. They can change without notice. The cached snapshot is not an optimisation, it is the thing the demo actually runs on.

## C2. Backup and enrichment sources

- **data.gov.in** carries several MPLADS datasets from MoSPI, each offering Download, Preview, Export and a **Data API**. Verified present. They are aggregate and historical, covering periods such as 2014-15 to 2017-18 and 2016-17 to 2019-20, so they are good for trend context and backfill rather than current work-level detail.
- **dataful.in** lists more granular MPLADS datasets including work-level lists by year, state and MP. Commercial platform, so check access terms before depending on it.
- **empoweredindian.in/mplads** is an existing public MPLADS visualisation. Worth studying, and worth naming in the pitch as prior art you go beyond.

## C3. Facts verified for the pitch

- **The 10 percent rule is confirmed.** District Authorities must inspect at least 10 percent of works under implementation every year, and involve the MP in inspections where feasible. It appears in the scheme guidelines, in a dedicated MoSPI circular on mandatory inspection, and it has been examined in UPSC civil-service papers, so it is settled, well-known fact rather than an obscure reading.
- **A detail worth using:** projects implemented through societies and trusts are subject to **full inspection, not the 10 percent sample.** The scheme already treats a higher-risk category differently. That is precedent for exactly what NidhiNetra does, and it is a strong answer to any judge who suggests risk-based targeting is a novel imposition.
- Roughly 1,729 crore rupees currently sits unspent with district authorities. In 2023-24, MPs recommended about 6,383 crore of work against about 4,805 crore actually spent.
- National audit has previously found a case of about 5.93 crore rupees of one MP's funds paid to a cooperative society whose members belonged to that MP's own party. That is a fund-flow-graph-shaped pattern and it is the strongest available hero example for the graph view.

Re-confirm each figure against its primary source before it appears on a slide.

## C4. What to do next

1. Run Part A through the design tool with Part B attached.
2. Generate variants and compare before committing to one.
3. Build with `design-taste-frontend` and `high-end-visual-design`, checking the result against section 12.
4. Give Part C to whoever owns the data layer. The API finding in C1 is the single biggest change to the build plan.
5. Record the chosen direction in `04 Prototype/Logbook.md`.
