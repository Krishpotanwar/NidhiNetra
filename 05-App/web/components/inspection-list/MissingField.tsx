import { STRINGS } from "@/lib/strings";

type MissingKey = "vendor" | "date" | "amount" | "agency" | "generic";

/**
 * Renders one of contracts/strings.json's missing_fields strings. Per that
 * contract: "Muted ink, one step down, left aligned even inside a numeric
 * column, because it is text and not a number." A missing amount is never
 * rendered as zero, a dash, or N/A -- see missing_fields.never.
 */
export function MissingField({ field }: { field: MissingKey }) {
  return (
    <span
      style={{
        color: "var(--ink-faint)",
        fontFamily: "var(--font-geist-sans)",
        fontVariantNumeric: "normal",
        textAlign: "left",
        fontStyle: "normal",
        fontSize: "var(--font-xs)",
      }}
    >
      {STRINGS.missing_fields[field]}
    </span>
  );
}
