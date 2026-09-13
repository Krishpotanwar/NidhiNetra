import Image from "next/image";
import hero from "@/assets/brand/hero-tricolour.jpg";
import { STRINGS } from "@/lib/strings";
import styles from "./DashboardHero.module.css";

const brand = STRINGS.brand;

/**
 * The masthead from the pinned reference: the tricolour wave with the Ashoka
 * Chakra and India Gate, the wordmark set in two tones, and the premise in
 * three short sentences. A Server Component, so the one large image on the
 * page is in the initial HTML and carries the LCP.
 *
 * The image is decorative (alt=""): every fact it carries is in the text
 * beside it. A veil holds the text above 4.5:1 wherever the ribbon runs.
 */
export function DashboardHero() {
  return (
    <section className={styles.hero} aria-labelledby="dashboard-title">
      <div className={styles.media}>
        <Image src={hero} alt="" fill sizes="100vw" placeholder="blur" className={styles.image} preload />
        <div className={styles.veil} />
      </div>
      <div className={`page ${styles.content}`}>
        <p className={`t-eyebrow ${styles.eyebrow}`}>{brand.ministry}</p>
        <h1 id="dashboard-title" className={styles.wordmark}>
          <span>{brand.name_part_1}</span>
          <span className={styles.netra}>{brand.name_part_2}</span>
        </h1>
        <span className={styles.rule} aria-hidden="true" />
        <p className={styles.tagline}>{brand.tagline}</p>
        <p className={styles.body}>{brand.hero_body}</p>
        <p className={styles.caption}>
          <span>{brand.hero_caption_1}</span>
          <span>{brand.hero_caption_2}</span>
          <span className={styles.captionRule} aria-hidden="true" />
        </p>
      </div>
    </section>
  );
}
