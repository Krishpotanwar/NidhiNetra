/**
 * Every user-visible string in this app comes from contracts/strings.json.
 * This module is the only place that imports the raw contract; everything
 * else imports STRINGS from here. contracts/ is frozen and read-only to A5
 * (see 05-App/README.md) -- this file only reads and renders it, never edits it.
 */
import rawStrings from "../../contracts/strings.json";
import rawStringsHi from "../../contracts/strings.hi.json";

export const STRINGS = rawStrings;

export type Locale = "en" | "hi";

// A snapshot of the English tree, taken once before setLocale can mutate
// STRINGS in place. "en" restores from this; "hi" falls back to it wherever
// strings.hi.json has no matching key -- Hindi is an overlay, not a second
// contract (D9): a missing translation shows English, never a blank or a
// raw dotted key.
const ENGLISH_STRINGS = structuredClone(rawStrings);

// Authoring metadata and locale-invariant formatting rules, not copy -- the
// same top-level blocks contracts/validate.py's lint_strings skips.
// "_meta"/"_measure" are already skipped by the leading-underscore rule
// below; these two are not.
const OVERLAY_SKIP_TOP_LEVEL = new Set(["lint", "number_format"]);

type Tree = Record<string, unknown>;

function applyOverlay(target: Tree, english: Tree, source: Tree | null, topLevel: boolean): void {
  for (const key of Object.keys(english)) {
    if (key.startsWith("_")) continue;
    if (topLevel && OVERLAY_SKIP_TOP_LEVEL.has(key)) continue;
    const englishValue = english[key];
    if (Array.isArray(englishValue)) continue;
    if (typeof englishValue === "string") {
      const overrideValue = source ? source[key] : undefined;
      target[key] = typeof overrideValue === "string" ? overrideValue : englishValue;
    } else if (englishValue && typeof englishValue === "object") {
      const sourceChild = source ? (source[key] as Tree | undefined) : undefined;
      applyOverlay(target[key] as Tree, englishValue as Tree, sourceChild ?? null, false);
    }
  }
}

/**
 * Switches every string leaf of the live STRINGS object between English and
 * the Hindi overlay (contracts/strings.hi.json), in place. Components read
 * STRINGS.x.y directly at render time, so nothing needs to re-import
 * anything; they just need to render again after this runs, which
 * LocaleRoot's key={locale} remount does.
 */
export function setLocale(locale: Locale): void {
  applyOverlay(
    STRINGS as unknown as Tree,
    ENGLISH_STRINGS as unknown as Tree,
    locale === "hi" ? (rawStringsHi as unknown as Tree) : null,
    true,
  );
}

/**
 * Fills a `{param}` template from contracts/strings.json with values.
 * Throws in development if a param the template declares is missing, so a
 * silently-blank placeholder in production copy is never introduced.
 */
export function renderTemplate(template: string, params: Record<string, string | number>): string {
  return template.replace(/\{(\w+)\}/g, (match, key: string) => {
    if (!(key in params)) {
      if (process.env.NODE_ENV !== "production") {
        throw new Error(`renderTemplate: missing param "${key}" for template "${template}"`);
      }
      return match;
    }
    return String(params[key]);
  });
}
