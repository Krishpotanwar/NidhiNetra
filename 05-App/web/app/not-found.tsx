import Link from "next/link";
import { PageMasthead } from "@/components/page-shell/PageMasthead";
import { Str } from "@/components/shell/Str";
import styles from "@/components/page-shell/SystemPage.module.css";

export default function NotFound() {
  return (
    <>
      <PageMasthead eyebrow={<Str k="brand.ministry" />} title={<Str k="system_pages.not_found_title" />} />
      <div className={`page ${styles.body}`}>
        <p className={styles.text}>
          <Str k="system_pages.not_found_body" />
        </p>
        <Link href="/" className={styles.action}>
          <Str k="system_pages.not_found_action" />
        </Link>
      </div>
    </>
  );
}
