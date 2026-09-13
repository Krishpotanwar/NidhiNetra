"use client";

import { useEffect } from "react";
import { STRINGS } from "@/lib/strings";
import styles from "@/components/page-shell/SystemPage.module.css";

const copy = STRINGS.system_pages;

export default function GlobalError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => {
    // Logged, never rendered: an exception message is not contract copy.
    console.error("Unhandled error in a view", error);
  }, [error]);

  return (
    <div className={`page ${styles.body}`}>
      <h1 className={styles.title}>{copy.error_title}</h1>
      <p className={styles.text}>{copy.error_body}</p>
      <button type="button" onClick={reset} className={styles.action}>
        {copy.error_action}
      </button>
    </div>
  );
}
