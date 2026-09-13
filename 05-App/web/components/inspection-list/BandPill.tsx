import { riskLabel } from "@/lib/format";
import type { RiskBand } from "@/lib/types";
import styles from "./BandPill.module.css";

/**
 * The band as a word on a wash, never colour alone (design brief section 6:
 * "Every colour-coded element also carries a number or a word"). Band 0 is
 * "Not currently flagged", never "Clear" or "Clean".
 */
export function BandPill({ band }: { band: RiskBand }) {
  return (
    <span className={styles.pill} data-band={band}>
      {riskLabel(band)}
    </span>
  );
}
