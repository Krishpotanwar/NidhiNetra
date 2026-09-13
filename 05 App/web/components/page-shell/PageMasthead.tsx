import Image from "next/image";
import hero from "@/assets/brand/hero-tricolour.jpg";
import styles from "./PageMasthead.module.css";

interface PageMastheadProps {
  eyebrow: string;
  title: string;
  lede?: string;
}

/**
 * The inner pages carry the same tricolour band as the Dashboard, at a
 * quarter of the height: enough to say "same instrument", not enough to
 * spend a working screen on.
 */
export function PageMasthead({ eyebrow, title, lede }: PageMastheadProps) {
  return (
    <section className={styles.masthead}>
      <div className={styles.media}>
        <Image src={hero} alt="" fill sizes="100vw" placeholder="blur" className={styles.image} preload />
        <div className={styles.veil} />
      </div>
      <div className={`page ${styles.content}`}>
        <p className={`t-eyebrow ${styles.eyebrow}`}>{eyebrow}</p>
        <h1 className={styles.title}>{title}</h1>
        <span className={styles.rule} aria-hidden="true" />
        {lede && <p className={styles.lede}>{lede}</p>}
      </div>
    </section>
  );
}
