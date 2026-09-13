import { STRINGS } from "@/lib/strings";
import styles from "./AppFooter.module.css";

const brand = STRINGS.brand;

/**
 * The reference's footer, minus two things it showed: a Government of India
 * copyright line (this prototype is not a government publication) and a
 * version stamp (design brief section 12 bans them, and there is no release).
 */
export function AppFooter() {
  return (
    <footer className={styles.footer}>
      <div className={`page ${styles.inner}`}>
        <p className={styles.credit}>
          <span>{brand.footer_credit}</span>
          <span className={styles.sep} aria-hidden="true" />
          <span>{brand.footer_event}</span>
        </p>
        <div className={styles.right}>
          <span lang="hi" className={styles.motto}>
            {brand.motto}
          </span>
          <span className={styles.rule} aria-hidden="true" />
          <span className={styles.tagline}>{brand.footer_tagline}</span>
        </div>
      </div>
    </footer>
  );
}
