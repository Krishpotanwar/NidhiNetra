"use client";

import { useEffect } from "react";
import { useSearchParams } from "next/navigation";
import { X } from "@phosphor-icons/react";
import { STRINGS } from "@/lib/strings";
import { presenterMode, usePresenterMode } from "@/lib/preferences";
import styles from "./PresenterControls.module.css";

/**
 * Reads ?present=1 or ?present=0 into session storage, once per navigation.
 * Rendered in the root layout inside a Suspense boundary (useSearchParams).
 */
export function PresenterUrlSync() {
  const flag = useSearchParams().get("present");
  useEffect(() => {
    if (flag === "1") presenterMode.set(true);
    else if (flag === "0") presenterMode.set(false);
  }, [flag]);
  return null;
}

/** Visible only in presenter mode, so nobody forgets it is on. */
export function PresenterBadge() {
  const on = usePresenterMode();
  if (!on) return null;
  return (
    <span className={styles.badge}>
      <span>{STRINGS.presenter.badge}</span>
      <button
        type="button"
        className={styles.exit}
        aria-label={STRINGS.presenter.exit}
        onClick={() => presenterMode.set(false)}
      >
        <X size={12} weight="bold" aria-hidden="true" />
      </button>
    </span>
  );
}
