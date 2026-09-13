import Link from "next/link";
import { STRINGS } from "@/lib/strings";
import { PageMasthead } from "@/components/page-shell/PageMasthead";
import styles from "@/components/page-shell/SystemPage.module.css";

const copy = STRINGS.system_pages;

export default function NotFound() {
  return (
    <>
      <PageMasthead eyebrow={STRINGS.brand.ministry} title={copy.not_found_title} />
      <div className={`page ${styles.body}`}>
        <p className={styles.text}>{copy.not_found_body}</p>
        <Link href="/" className={styles.action}>
          {copy.not_found_action}
        </Link>
      </div>
    </>
  );
}
