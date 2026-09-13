import Image from "next/image";
import Link from "next/link";
import { Suspense } from "react";
import eye from "@/assets/brand/nidhinetra-eye.png";
import { STRINGS } from "@/lib/strings";
import { NavTabs } from "./NavTabs";
import { HeaderSearch } from "./HeaderSearch";
import { OfficerMenu } from "./OfficerMenu";
import { PresenterBadge } from "./PresenterControls";
import styles from "./AppHeader.module.css";

const brand = STRINGS.brand;

/**
 * The site header from the pinned reference (NidhiNetra_Vidhi.png): the
 * Government of India text mark, the tricolour eye with the wordmark, five
 * tabs, search, the Viksit Bharat mark and the officer's initials.
 *
 * A Server Component; only the parts that read the route or storage are
 * client islands. The State Emblem is left out on purpose: its use is
 * restricted by law (contracts/strings.json brand._note).
 */
export function AppHeader() {
  return (
    <header className={styles.header}>
      <div className={`page ${styles.inner}`}>
        <div className={styles.gov}>
          <span lang="hi" className={styles.govHi}>
            {brand.gov_hi}
          </span>
          <span className={styles.govEn}>{brand.gov_en}</span>
        </div>
        <span className={styles.divider} aria-hidden="true" />
        <Link href="/" className={styles.brand}>
          {/* Decorative here: the wordmark beside it already names the link. */}
          <Image src={eye} alt="" className={styles.logo} sizes="120px" preload />
          <span className={styles.brandText}>
            <span className={styles.wordmark}>{brand.name}</span>
            <span className={styles.ministry}>{brand.ministry}</span>
          </span>
        </Link>
        <NavTabs />
        <div className={styles.tools}>
          <Suspense fallback={<div className={styles.searchFallback} aria-hidden="true" />}>
            <HeaderSearch />
          </Suspense>
          <div className={styles.viksit} lang="hi">
            <span className={styles.flagBar} aria-hidden="true" />
            <span className={styles.viksitText}>
              <span>{brand.viksit_line_1}</span>
              <span>{brand.viksit_line_2}</span>
            </span>
          </div>
          <PresenterBadge />
          <OfficerMenu />
        </div>
      </div>
    </header>
  );
}
