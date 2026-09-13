/**
 * Number, currency and date formatting. Every rule here is taken from
 * contracts/strings.json's `number_format` block -- nothing is a local
 * guess about how a number should look. Import this rather than formatting
 * a number inline in a component; the design brief calls out Indian
 * numbering as "a real, testable formatting rule, not a suggestion."
 */
import { STRINGS } from "./strings";
import type { FlagType, RiskBand, WorkCategory } from "./types";

/** Indian digit grouping: last three digits, then pairs. 172961 -> "1,72,961". */
export function formatIndianInt(value: number): string {
  const negative = value < 0;
  const digits = Math.trunc(Math.abs(value)).toString();

  if (digits.length <= 3) {
    return (negative ? "-" : "") + digits;
  }

  const last3 = digits.slice(-3);
  let rest = digits.slice(0, -3);
  const groups: string[] = [];
  while (rest.length > 2) {
    groups.unshift(rest.slice(-2));
    rest = rest.slice(0, -2);
  }
  if (rest.length > 0) {
    groups.unshift(rest);
  }
  return (negative ? "-" : "") + groups.join(",") + "," + last3;
}

function formatIndianDecimal(value: number, decimals: number): string {
  const negative = value < 0;
  const fixed = Math.abs(value).toFixed(decimals);
  const [intPart, decPart] = fixed.split(".");
  const groupedInt = formatIndianInt(Number(intPart));
  return (negative ? "-" : "") + groupedInt + (decPart ? "." + decPart : "");
}

/**
 * Rupee amount, threshold-scaled per strings.json number_format.currency:
 * full below 1 lakh, lakh below 1 crore, crore above. Trailing zeros are
 * always kept so a column of tabular figures does not jump decimal width
 * row to row.
 */
export function formatCurrency(amountInr: number): string {
  const abs = Math.abs(amountInr);
  const { symbol } = STRINGS.number_format.currency;
  if (abs <= 99999) {
    return symbol + formatIndianInt(Math.round(amountInr));
  }
  if (abs <= 9999999) {
    return symbol + formatIndianDecimal(amountInr / 1e5, 2) + " L";
  }
  return symbol + formatIndianDecimal(amountInr / 1e7, 2) + " Cr";
}

/**
 * Always renders in crore, per number_format.currency.summary_strip_override:
 * "All four summary figures render in crore regardless of magnitude, so the
 * four values compare directly."
 *
 * Superseded 2026-09-02 by formatCurrencyFull below, per direct request:
 * lakh/crore abbreviation traded comparability for compactness, and the
 * request was specifically to remove that trade -- two amounts differing
 * in the thousands are much easier to compare as "1,53,91,404" vs
 * "1,72,04,900" than as "1.54 Cr" vs "1.72 Cr" when the reader has to
 * subtract in their head either way. Kept, unused, rather than deleted:
 * contracts/strings.json's number_format.currency thresholds are still the
 * frozen contract for anywhere a compact form is deliberately wanted
 * later (a legend, a chart axis), so the function that implements them
 * stays available without another rewrite.
 */
export function formatCurrencyCrore(amountInr: number): string {
  const { symbol } = STRINGS.number_format.currency;
  return symbol + formatIndianDecimal(amountInr / 1e7, 2) + " Cr";
}

/**
 * The full rupee amount, Indian-grouped, no lakh/crore abbreviation.
 * Replaces formatCurrency/formatCurrencyCrore at every call site
 * 2026-09-02 -- see formatCurrencyCrore's docstring for why. Rounds to
 * whole rupees: paise-level precision does not change which of two works
 * cost more, and a column of whole-rupee tabular figures is easier to
 * scan than one with two extra decimal digits doing no comparative work.
 */
export function formatCurrencyFull(amountInr: number): string {
  const { symbol } = STRINGS.number_format.currency;
  return symbol + formatIndianInt(Math.round(amountInr));
}

/** 3.2x, 3.0x (decimal always shown); 140x above 100x, where a decimal is false precision. */
export function formatMultiple(value: number): string {
  if (Math.abs(value) >= 100) {
    return Math.round(value) + "x";
  }
  return value.toFixed(1) + "x";
}

/** Numeric-column form: "38%". Sentence form spells the word: "38 percent". */
export function formatPercent(value: number, form: "symbol" | "word" = "symbol"): string {
  const rounded = Math.round(value);
  return form === "word" ? `${rounded} percent` : `${rounded}%`;
}

/** Risk score: 0-100, no decimals, no suffix -- it orders a queue, not a probability. */
export function formatRiskScore(score: number): string {
  return String(Math.round(score));
}

/** 2026-08-15 -> "15 Aug 2026". Never a slash date (ambiguous Indian/American order). */
export function formatDate(dateStr: string): string {
  const [year, month, day] = dateStr.split("-").map(Number);
  const months = STRINGS.number_format.date.months;
  return `${day} ${months[month - 1]} ${year}`;
}

/**
 * Whole days between `lastUpdated` (a record's own last_updated, the only
 * per-work freshness field normalized_record.schema.json has -- there is
 * no separate "last progress entry" date) and `asOf` (the snapshot's own
 * data_as_of, never the browser's real-world today: two officers looking
 * at the same cached snapshot on different days must see the same number).
 * New 2026-09-03, reference-fidelity pass -- the Days stale column.
 * Floored at 0 so a record updated after the snapshot's own as-of instant
 * (should not happen, but a snapshot rebuilt mid-render is not impossible)
 * never displays a negative age.
 */
export function daysStale(lastUpdated: string, asOf: string): number {
  const from = new Date(lastUpdated).getTime();
  const to = new Date(asOf).getTime();
  return Math.max(0, Math.round((to - from) / (24 * 60 * 60 * 1000)));
}

/**
 * ISO 8601 UTC timestamp (the API's own data_as_of / manifest.generated_at
 * shape, e.g. "2026-09-01T19:37:02Z") -> "01:07", per
 * number_format.time: 24 hour, IST, no seconds, no timezone suffix.
 * New 2026-09-02, wiring the refresh control -- refresh_failed's "{time}"
 * placeholder is the first caller that needed a clock time rather than a
 * calendar date, and none of formatDate's string-splitting approach works
 * for it (a full timestamp, a timezone conversion, no year/month/day to
 * split on the same way).
 */
export function formatTimeIst(isoTimestamp: string): string {
  const formatted = new Intl.DateTimeFormat("en-GB", {
    timeZone: "Asia/Kolkata",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(new Date(isoTimestamp));
  // en-GB with hour12:false already gives 24-hour "HH:mm"; some ICU
  // implementations render midnight as "24:00" instead of "00:00" -- guard
  // it explicitly rather than trust every runtime's ICU data to agree.
  return formatted === "24:00" ? "00:00" : formatted;
}

/** Mid-sentence category form, lowercase, per number_format.category_phrase. */
export function categoryPhrase(category: WorkCategory | string): string {
  const map = STRINGS.number_format.category_phrase as Record<string, string>;
  return map[category] ?? category.toLowerCase();
}

export const FLAG_LABELS: Record<FlagType, string> = STRINGS.filters.flag_names;

/**
 * Risk band, 0 (unflagged) through 4 (highest priority). The contract fixes
 * risk_score as a continuous 0-100 ordering device and risk_labels as the
 * five band names, but leaves banding thresholds to the renderer -- A2's
 * contract does not emit a band. flags.length === 0 always forces band 0
 * regardless of score, matching "Empty array means unflagged, not clean."
 * The interior cut points (25/50/75) are an even quartile split; there is no
 * contract-specified alternative to defer to.
 */
export function riskBand(score: number, flags: FlagType[]): RiskBand {
  if (flags.length === 0) return 0;
  if (score > 75) return 4;
  if (score > 50) return 3;
  if (score > 25) return 2;
  return 1;
}

export function riskLabel(band: RiskBand): string {
  return STRINGS.risk_labels[String(band) as "0" | "1" | "2" | "3" | "4"];
}

export function riskColorVar(band: RiskBand): string {
  return `var(--risk-${band})`;
}

/**
 * Display casing for names the source publishes in capitals, for example
 * "AZAMGARH(DISTRICT MAGISTRATE AZAMGARH_IDA)" becomes "Azamgarh (District
 * Magistrate Azamgarh IDA)". Display only: the detail panel's record section
 * still shows the exact published string. Words the source already wrote in
 * mixed case are left alone, dotted initials and single letters stay as they
 * are, and the acronyms below (sampled from the real agency names,
 * 2026-09-11) stay in capitals. An unknown acronym degrades to title case,
 * which is still readable; it is never changed in meaning.
 */
const KEEP_UPPER = new Set([
  "IDA", "DC", "DM", "SDM", "SDO", "BDO", "CEO", "DRDA", "PWD", "ZP", "SC", "ST",
  "UT", "NCT", "MPLADS", "MLA", "MP", "IAS", "PHED", "RWD", "NDMC", "MCD", "GHMC", "BBMP",
]);
const LOWER_WORDS = new Set(["of", "and", "the", "for", "in", "at", "to", "by", "on", "cum", "with"]);

function caseWord(word: string, isFirst: boolean): string {
  if (/[a-z]/.test(word) || word.includes(".") || word.length === 1 || KEEP_UPPER.has(word)) {
    return word;
  }
  const lower = word.toLowerCase();
  if (!isFirst && LOWER_WORDS.has(lower)) return lower;
  return lower.replace(/(^|[-'])([a-z])/g, (_, sep: string, ch: string) => sep + ch.toUpperCase());
}

export function displayName(raw: string): string {
  const spaced = raw
    .replace(/_/g, " ")
    .replace(/\s*\(\s*/g, " (")
    .replace(/\s*\)/g, ")")
    .replace(/\)(?=\S)/g, ") ")
    .replace(/\s+/g, " ")
    .trim();
  let index = 0;
  return spaced.replace(/[A-Za-z][A-Za-z.'-]*/g, (word) => caseWord(word, index++ === 0));
}

/** Rank as the reference sets it: two digits below ten ("01"), Indian grouping above. */
export function formatRank(rank: number): string {
  return rank < 10 ? `0${rank}` : formatIndianInt(rank);
}

/**
 * A crore amount split into its figure and its unit, so a KPI can set the
 * unit smaller than the figure. Same rounding and grouping as
 * formatCurrencyCrore: "Rs 1,155.87" plus "Cr".
 */
export function formatCroreParts(amountInr: number): { value: string; unit: string } {
  const { symbol, thresholds } = STRINGS.number_format.currency;
  const unit = (thresholds[thresholds.length - 1].suffix ?? " Cr").trim();
  return { value: symbol + formatIndianDecimal(amountInr / 1e7, 2), unit };
}
