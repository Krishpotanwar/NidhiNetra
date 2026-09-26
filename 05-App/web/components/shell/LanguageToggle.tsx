"use client";

import { STRINGS } from "@/lib/strings";
import { useLocale } from "./LocaleRoot";
import styles from "./LanguageToggle.module.css";

const language = STRINGS.language;

/**
 * A real <button>, not a link: switching locale is an in-place UI action,
 * not navigation (GIGW 3.0 Hindi/English requirement, T11A). Shows the
 * OTHER language's name -- the one a click switches to -- so the label
 * itself is never run through the Hindi overlay (contracts/strings.json
 * language block).
 */
export function LanguageToggle() {
  const { locale, change } = useLocale();
  const isHindi = locale === "hi";
  return (
    <button
      type="button"
      className={styles.toggle}
      aria-label={language.toggle_aria}
      onClick={() => change(isHindi ? "en" : "hi")}
    >
      {isHindi ? language.english_label : <span lang="hi">{language.hindi_label}</span>}
    </button>
  );
}
