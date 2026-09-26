import { afterEach, beforeEach, describe, expect, test } from "vitest";
import rawStrings from "../../contracts/strings.json";
import rawStringsHi from "../../contracts/strings.hi.json";
import { STRINGS, renderTemplate, setLocale, translateReason } from "./strings";

describe("setLocale (T11A overlay)", () => {
  beforeEach(() => {
    setLocale("en");
  });
  afterEach(() => {
    setLocale("en");
  });

  test('"hi" overwrites STRINGS.nav.dashboard from the Hindi overlay', () => {
    expect(STRINGS.nav.dashboard).toBe("Dashboard");
    setLocale("hi");
    expect(STRINGS.nav.dashboard).toBe("डैशबोर्ड");
  });

  test("a key strings.hi.json does not cover falls back to English", () => {
    setLocale("hi");
    // brand.name is deliberately never overlaid (T11B): "NidhiNetra" is a
    // proper noun, not translated, so it always falls back to English.
    expect(STRINGS.brand.name).toBe("NidhiNetra");
  });

  test('"en" restores the English value after a switch to "hi"', () => {
    setLocale("hi");
    expect(STRINGS.nav.dashboard).toBe("डैशबोर्ड");
    setLocale("en");
    expect(STRINGS.nav.dashboard).toBe("Dashboard");
  });

  test("does not translate the number_format block (locale-invariant formatting rules)", () => {
    const before = STRINGS.number_format.date.display;
    setLocale("hi");
    expect(STRINGS.number_format.date.display).toBe(before);
  });
});

describe("translateReason (T11B)", () => {
  afterEach(() => {
    setLocale("en");
  });

  test("returns a sentence that matches no why_flagged template unchanged", () => {
    setLocale("hi");
    const sentence = "This sentence was never rendered from a why_flagged template.";
    expect(translateReason(sentence)).toBe(sentence);
  });

  test('under "en", round-trips every template back to itself (a safe no-op)', () => {
    const english = (rawStrings as { why_flagged: Record<string, unknown> }).why_flagged;
    for (const flagKey of Object.keys(english)) {
      if (flagKey.startsWith("_")) continue;
      const variants = (english[flagKey] as { variants: Record<string, { text: string }> }).variants;
      for (const variantKey of Object.keys(variants)) {
        const enText = variants[variantKey].text;
        const params = sampleParamsFor(enText);
        const sentence = renderTemplate(enText, params);
        expect(translateReason(sentence)).toBe(sentence);
      }
    }
  });

  test('under "hi", every why_flagged template round-trips: an English sentence built from the template with sample params becomes the Hindi template rendered with the same params', () => {
    setLocale("hi");
    const english = (rawStrings as { why_flagged: Record<string, unknown> }).why_flagged;
    const hindi = (rawStringsHi as { why_flagged?: Record<string, unknown> }).why_flagged ?? {};
    let checked = 0;
    for (const flagKey of Object.keys(english)) {
      if (flagKey.startsWith("_")) continue;
      const enVariants = (english[flagKey] as { variants: Record<string, { text: string }> }).variants;
      const hiVariants = (hindi[flagKey] as { variants?: Record<string, { text: string }> } | undefined)
        ?.variants;
      for (const variantKey of Object.keys(enVariants)) {
        const enText = enVariants[variantKey].text;
        const hiText = hiVariants?.[variantKey]?.text;
        expect(hiText, `strings.hi.json is missing why_flagged.${flagKey}.variants.${variantKey}.text`).toBeTruthy();
        const params = sampleParamsFor(enText);
        const englishSentence = renderTemplate(enText, params);
        const expectedHindiSentence = renderTemplate(hiText as string, params);
        expect(translateReason(englishSentence)).toBe(expectedHindiSentence);
        checked += 1;
      }
    }
    // Guards against the loop above silently checking nothing.
    expect(checked).toBeGreaterThan(0);
  });
});

/** Distinct, digit-only sample values for every {param} in a template --
 * safe against the non-greedy (.+?) regex translateReason builds, since
 * none of these templates' literal text contains bare digits. */
function sampleParamsFor(template: string): Record<string, string> {
  const params: Record<string, string> = {};
  let n = 2;
  for (const match of template.matchAll(/\{(\w+)\}/g)) {
    params[match[1]] = String(n);
    n += 1;
  }
  return params;
}
