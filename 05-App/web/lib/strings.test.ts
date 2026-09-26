import { afterEach, beforeEach, describe, expect, test } from "vitest";
import { STRINGS, setLocale } from "./strings";

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
    // reports is not part of T11A's seed (nav and brand only).
    expect(STRINGS.reports.title).toBe("Reports");
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
