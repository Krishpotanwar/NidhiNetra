---
name: NidhiNetra
description: The Ministry's inspection instrument for MPLADS works, under the tricolour eye.
colors:
  ink-navy: "#0F1B33"
  ink-secondary: "#334262"
  ink-muted: "#56617D"
  ink-faint: "#5E6983"
  netra-slate: "#3B4C67"
  paper-cool: "#F4F7FA"
  surface-white: "#FFFFFF"
  surface-sunken: "#F1F4F8"
  row-hover: "#F6F8FC"
  hairline: "#E3E9EF"
  hairline-strong: "#D3DCE6"
  control-border: "#C5CFDB"
  chakra-blue: "#1B4FD6"
  chakra-blue-deep: "#163FAD"
  chakra-blue-wash: "#E7EEFD"
  nav-pill: "#DFE5F3"
  tricolour-saffron: "#FF9933"
  tricolour-white: "#FFFFFF"
  tricolour-lower: "#138808"
  risk-highest: "#C81E1E"
  risk-highest-ink: "#B42318"
  risk-highest-wash: "#FDE8E8"
  risk-high: "#D4540F"
  risk-high-ink: "#B23F0B"
  risk-high-wash: "#FDEDE3"
  risk-moderate: "#C9760F"
  risk-moderate-ink: "#92560A"
  risk-moderate-wash: "#FCF1DF"
  risk-low: "#A8842A"
  risk-low-ink: "#7A6414"
  risk-low-wash: "#F6F0DC"
  risk-none-wash: "#EEF1F5"
  kpi-works: "#1B4FD6"
  kpi-works-tile: "#E1ECFE"
  kpi-flagged: "#D9480F"
  kpi-flagged-tile: "#FFEBDC"
  kpi-value: "#BE123C"
  kpi-value-tile: "#FCE7EC"
  kpi-idle: "#5B3FD1"
  kpi-idle-tile: "#EEE9FE"
typography:
  display:
    fontFamily: "Source Serif 4, Iowan Old Style, Georgia, serif"
    fontSize: "clamp(2.75rem, 1.55rem + 2.95vw, 4.75rem)"
    fontWeight: 700
    lineHeight: 1.02
    letterSpacing: "-0.028em"
  headline:
    fontFamily: "Source Serif 4, Iowan Old Style, Georgia, serif"
    fontSize: "2.177rem"
    fontWeight: 700
    lineHeight: 1.15
    letterSpacing: "-0.012em"
  figure:
    fontFamily: "Source Serif 4, Iowan Old Style, Georgia, serif"
    fontSize: "1.814rem"
    fontWeight: 700
    lineHeight: 1.15
    fontFeature: "\"tnum\" 1, \"lnum\" 1"
  title:
    fontFamily: "Geist, system-ui, sans-serif"
    fontSize: "1.26rem"
    fontWeight: 500
    lineHeight: 1.3
    letterSpacing: "-0.012em"
  body:
    fontFamily: "Geist, system-ui, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 400
    lineHeight: 1.5
  note:
    fontFamily: "Geist, system-ui, sans-serif"
    fontSize: "0.799rem"
    fontWeight: 400
    lineHeight: 1.5
  label:
    fontFamily: "Geist, system-ui, sans-serif"
    fontSize: "0.729rem"
    fontWeight: 600
    lineHeight: 1.3
    letterSpacing: "0.06em"
  data:
    fontFamily: "Geist Mono, ui-monospace, monospace"
    fontSize: "0.875rem"
    fontWeight: 500
    lineHeight: 1.3
    fontFeature: "\"tnum\" 1"
  devanagari:
    fontFamily: "Noto Sans Devanagari, Kohinoor Devanagari, Nirmala UI, sans-serif"
    fontSize: "0.938rem"
    fontWeight: 600
    lineHeight: 1.25
rounded:
  control: "8px"
  card: "12px"
  tile: "12px"
  panel: "16px"
  pill: "999px"
spacing:
  "1": "4px"
  "2": "8px"
  "3": "12px"
  "4": "16px"
  "5": "20px"
  "6": "24px"
  "8": "32px"
  "10": "40px"
  "12": "48px"
  "16": "64px"
components:
  button-primary:
    backgroundColor: "{colors.chakra-blue}"
    textColor: "{colors.surface-white}"
    rounded: "{rounded.control}"
    padding: "8px 16px"
  button-primary-hover:
    backgroundColor: "{colors.chakra-blue-deep}"
  button-secondary:
    backgroundColor: "{colors.surface-white}"
    textColor: "{colors.ink-navy}"
    rounded: "{rounded.control}"
    padding: "8px 14px"
  nav-tab:
    textColor: "{colors.ink-secondary}"
    rounded: "{rounded.control}"
    padding: "10px 14px"
  nav-tab-active:
    backgroundColor: "{colors.nav-pill}"
    textColor: "{colors.ink-navy}"
    rounded: "{rounded.control}"
    padding: "10px 16px"
  segmented-active:
    backgroundColor: "{colors.chakra-blue-wash}"
    textColor: "{colors.chakra-blue-deep}"
    rounded: "{rounded.control}"
    padding: "6px 14px"
  input:
    backgroundColor: "{colors.surface-white}"
    textColor: "{colors.ink-navy}"
    rounded: "{rounded.control}"
    padding: "8px 12px"
  card:
    backgroundColor: "{colors.surface-white}"
    rounded: "{rounded.card}"
    padding: "20px 24px"
  pill-highest:
    backgroundColor: "{colors.risk-highest-wash}"
    textColor: "{colors.risk-highest-ink}"
    rounded: "{rounded.pill}"
    padding: "4px 10px"
---

# Design System: NidhiNetra

## Overview

**Creative North Star: "The Watchful Ledger"**

A government register kept under the tricolour eye. The page reads like a well-set ministry report that happens to be live: cool paper, white ledger cards, ink-navy type, and the national colours used as identity, never as data. The masthead carries the one atmospheric image, the tricolour wave with the Ashoka Chakra and India Gate, and everything below it is quiet, tabular and exact.

Density follows the task. The Dashboard opens with one composed scene (identity, four figures, the quota, the top of the queue) so a jury grasps the product in a single screen; the Inspection List below it is a dense, keyboard-first working table. The pinned reference is `NidhiNetra_Vidhi.png`; the earlier Swiss-paper build and its hover dot field are retired.

**Key Characteristics:**
- Serif identity and figures, sans interface, monospaced money.
- White cards with hairline borders and soft navy-tinted shadows on cool paper.
- One interactive blue. A warm ramp for risk. The tricolour for identity only.
- Every number tabular and Indian-grouped; every colour paired with a number or a word.

## Colors

Ink on cool paper, one blue that means "you can act", a warm ramp that means "look here first", and the tricolour that means "India".

### Primary
- **Chakra Blue** (#1B4FD6): the only interactive colour. Links, the active segment, focus rings, primary buttons, the selected row wash. Deepens to Chakra Blue Deep (#163FAD) on hover and press.

### Neutral
- **Ink Navy** (#0F1B33): titles, figures, work names, table money.
- **Secondary Ink** (#334262): labels, column headers, inactive navigation.
- **Muted Ink** (#56617D): reason lines, context lines, captions.
- **Faint Ink** (#5E6983): placeholders and tertiary metadata; still 4.5:1 or better on paper.
- **Netra Slate** (#3B4C67): the second half of the wordmark only.
- **Cool Paper** (#F4F7FA) under **Surface White** (#FFFFFF) cards; **Sunken** (#F1F4F8) for explainer boxes and tracks; **Hairline** (#E3E9EF) for borders and row rules.

### Tricolour
- **Saffron** (#FF9933), **White**, and the **Lower band** (#138808): rules under the wordmark and captions, the vertical mark beside the Hindi slogan, and the logo. Nowhere else.

### Risk ramp
- **Highest** (#C81E1E, text #B42318, wash #FDE8E8), **High** (#D4540F, text #B23F0B), **Moderate** (#C9760F, text #92560A), **Low** (#A8842A, text #7A6414). Unflagged uses muted ink on a neutral wash. The quota bar runs the ramp from red to amber along rank.

### KPI tiles
- Works (blue on #E1ECFE), flagged (saffron-orange #D9480F on #FFEBDC), sanctioned under flagged works (rose #BE123C on #FCE7EC), unspent (violet #5B3FD1 on #EEE9FE). Pastel tile, saturated icon, one per figure.

### Named Rules
**The Tricolour Is Identity Rule.** Saffron, white and the flag's lower band appear only in brand marks and rules. The lower band's colour never encodes risk, status or data, because in this product it would read as "verified clean".

**The Warm Means Look Rule.** Warm colour marks inspection priority and nothing else. The cool blue marks interaction and nothing else. An officer must never confuse "clickable" with "risky".

## Typography

**Display Font:** Source Serif 4 (with Iowan Old Style, Georgia)
**Body Font:** Geist (with system-ui)
**Data Font:** Geist Mono (with ui-monospace)
**Devanagari:** Noto Sans Devanagari (with Kohinoor Devanagari, Nirmala UI)

**Character:** A sturdy transitional serif gives the wordmark and the headline figures the weight of a printed government report; Geist keeps every control plain and legible; Geist Mono makes columns of rupees line up to the digit.

### Hierarchy
- **Display** (700, clamp 2.75rem to 4.75rem, 1.02): the NidhiNetra wordmark on the Dashboard only.
- **Headline** (700, 2.177rem, 1.15): inner page titles.
- **Figure** (700, 1.814rem, tabular lining): KPI figures.
- **Title** (500, 1.26rem): section titles, the hero tagline.
- **Body** (400, 0.875rem, 1.5): table cells, controls, detail panel text.
- **Note** (400, 0.799rem, 1.5): reason lines and context lines, capped at 62ch.
- **Label** (600, 0.729rem, uppercase, 0.06em): column headers, field labels, KPI labels.

### Named Rules
**The Tabular Rule.** Every number on screen uses tabular figures and Indian grouping (1,72,961). Money in tables is monospaced and right aligned; money in KPI figures is serif and compacted to crore.

## Layout

A centred column up to 100rem wide with gutters of clamp(1rem, 2.4vw, 2.5rem); never full-bleed except the header, the masthead image and the footer. The header is 76px, white, and sticky. The Dashboard masthead image runs full-bleed behind the title and fades into paper under the KPI row, which overlaps it. Cards stack with 16px gaps; sections breathe at 24 to 32px. Four KPI cards collapse to two columns under 1200px and one under 640px; the table scrolls horizontally inside its card under 1280px, with the rank and work columns kept readable.

## Elevation & Depth

Light lifts, colour never does. Paper is the ground, white cards sit on it with a hairline and a soft navy-tinted shadow, and floating layers (the sticky filter bar, popovers, the detail panel) get progressively larger, softer shadows. No glass, no blur, no glow.

### Shadow Vocabulary
- **Card** (`0 1px 2px rgb(15 27 51 / 0.04), 0 6px 20px -4px rgb(15 27 51 / 0.06)`): every resting card.
- **Raised** (`0 2px 8px rgb(15 27 51 / 0.06), 0 16px 40px -8px rgb(15 27 51 / 0.12)`): sticky filter bar, menus, popovers.
- **Panel** (`0 12px 32px rgb(15 27 51 / 0.10), 0 40px 80px -16px rgb(15 27 51 / 0.18)`): the detail panel.
- **Header** (`0 1px 0 rgb(15 27 51 / 0.06), 0 8px 24px -12px rgb(15 27 51 / 0.12)`): the sticky header.

### Named Rules
**The Light Lifts Rule.** A floating surface is brighter than what it floats over and carries a larger shadow; it never changes hue.

## Shapes

Gently rounded and consistent: controls 8px, cards and icon tiles 12px, the detail panel 16px on its free edge, status pills and the avatar fully round. Borders are 1px hairlines; no coloured side borders on cards or rows.

## Components

### Header
- **Structure:** Government text mark (भारत सरकार over GOVERNMENT OF INDIA), a hairline divider, the eye logo with the NidhiNetra wordmark and ministry name, five navigation tabs, search, the Viksit Bharat mark with a vertical tricolour bar, and the officer initials button.
- **State:** Sticky, white, header shadow. Collapses search to an icon under 1180px and navigation to a menu under 960px.

### Navigation
- **Style:** Label-size sans, secondary ink. The active tab sits on a Nav Pill (#DFE5F3) with ink-navy text and its icon; the pill slides between tabs.
- **Icon weight:** the active tab's icon is filled, every other tab's is regular weight (or absent, in the desktop tab row, until it activates) — weight itself marks "you are here", not an added badge or colour.

### Buttons
- **Shape:** 8px.
- **Primary:** Chakra Blue fill, white text, 8px by 16px.
- **Secondary:** white fill, control border, ink text.
- **Hover / Focus:** 120ms colour transition; 2px Chakra Blue focus ring offset 2px; press scales to 0.98.

### Cards
- **Corner Style:** 12px. **Background:** white. **Shadow:** Card. **Border:** 1px hairline. **Padding:** 20px by 24px.

### KPI card
- Pastel icon tile (52px, 12px radius) at left holding a 23px icon; serif figure, uppercase label, one or two muted context lines. Card is 8.25rem tall minimum, so all four stay level regardless of context-line length. No trend chips unless a time series exists.

### Quota bar
- The whole filtered population as one track; the filled segment is exactly the quota's share, painted with the risk ramp; a lighter warm segment shows flagged works past the cutoff; a navy tick and label mark the cutoff rank. An explainer box on the Sunken ground states the numbers in a sentence.

### Inputs and filters
- **Style:** white fill, control border (#C5CFDB), 8px radius, caret icon. Label above in Label style with a leading icon.
- **Focus:** 2px Chakra Blue ring. **Segmented controls:** active segment on Chakra Blue Wash with Chakra Blue Deep text and border.

### Inspection table
- Two-line rows: work name in body 600, reason line beneath in Note, muted. Constituency and agency in secondary ink; money in Geist Mono; days stale in the row's risk text colour when the stall flag fired; the score in bold risk ink; a band pill at the end. Hairline between rows, no zebra, no vertical rules. The quota cutoff appears as a labelled divider row where it falls.

### Band pill
- Fully round, wash background, risk text colour, uppercase label size. Always a word, never colour alone.

### Detail panel
- Slides in from the right on a critically damped spring, no scrim. White, Panel shadow, 16px radius on the free edge. Score and breakdown first, then the peer group on Sunken, then the record, then actions.

## Do's and Don'ts

### Do:
- **Do** keep every figure real: from the API, with its population named.
- **Do** pair every warm colour with a number or a word.
- **Do** use the tricolour only for identity: the logo, the rules, the Viksit Bharat mark.
- **Do** mark every Devanagari string with `lang="hi"`.

### Don't:
- **Don't** use the flag's lower-band colour for risk, status, success or data.
- **Don't** show trend deltas or sparklines; there is one snapshot and no time series.
- **Don't** use glass, blur, glow, gradient text, or a page-wide pointer-following effect. The one exception: a fixed dot-grid texture confined to an already-empty card (an error state, an empty result, the fund-flow graph with nothing to draw) may brighten near the cursor, so it never reads as bare white space; it never leaves that card's own edges and never sits behind live content.
- **Don't** use the State Emblem of India; its use is restricted by law.
- **Don't** put an em dash anywhere in the interface.
