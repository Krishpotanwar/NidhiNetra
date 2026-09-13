"use client";

import { useEffect, useId, useRef, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { MagnifyingGlass } from "@phosphor-icons/react";
import { STRINGS } from "@/lib/strings";
import { MAX_QUERY_LENGTH } from "@/lib/filters";
import styles from "./HeaderSearch.module.css";

interface HeaderSearchProps {
  variant?: "bar" | "menu";
  onSubmitted?: () => void;
}

/**
 * Searches the inspection list (GET /api/works?q=, a plain-text match over
 * work ID, constituency, agency, MP, state and vendor). Submitting always
 * lands on the Inspection List; from there the current filters are kept and
 * only the page resets. Press "/" anywhere to focus it.
 */
export function HeaderSearch({ variant = "bar", onSubmitted }: HeaderSearchProps) {
  const pathname = usePathname();
  const params = useSearchParams();
  const urlQuery = pathname === "/inspections" ? (params.get("q") ?? "") : "";
  // Keyed on the address bar's query, so the field resets when navigation
  // changes it rather than drifting out of step with what the list shows.
  return <SearchForm key={urlQuery} initial={urlQuery} variant={variant} onSubmitted={onSubmitted} />;
}

function SearchForm({
  initial,
  variant,
  onSubmitted,
}: {
  initial: string;
  variant: "bar" | "menu";
  onSubmitted?: () => void;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const [value, setValue] = useState(initial);
  const inputRef = useRef<HTMLInputElement>(null);
  const id = useId();

  useEffect(() => {
    if (variant !== "bar") return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key !== "/" || event.metaKey || event.ctrlKey || event.altKey) return;
      const target = event.target as HTMLElement | null;
      if (target && (target.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName))) return;
      event.preventDefault();
      inputRef.current?.focus();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [variant]);

  const submit = (event: React.FormEvent) => {
    event.preventDefault();
    const q = value.trim().slice(0, MAX_QUERY_LENGTH);
    const next = new URLSearchParams(pathname === "/inspections" ? params.toString() : "");
    next.delete("page");
    if (q) next.set("q", q);
    else next.delete("q");
    const qs = next.toString();
    router.push(qs ? `/inspections?${qs}` : "/inspections");
    inputRef.current?.blur();
    onSubmitted?.();
  };

  return (
    <form role="search" onSubmit={submit} className={variant === "bar" ? styles.bar : styles.menu}>
      <label htmlFor={id} className="sr-only">
        {STRINGS.nav.search_label}
      </label>
      <MagnifyingGlass aria-hidden="true" size={18} className={styles.icon} />
      <input
        ref={inputRef}
        id={id}
        type="search"
        name="q"
        value={value}
        onChange={(event) => setValue(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === "Escape") {
            setValue("");
            inputRef.current?.blur();
          }
        }}
        placeholder={STRINGS.nav.search_placeholder}
        maxLength={MAX_QUERY_LENGTH}
        autoComplete="off"
        enterKeyHint="search"
        className={styles.input}
      />
      {variant === "bar" && (
        <kbd className={styles.kbd} title={STRINGS.nav.search_shortcut}>
          /
        </kbd>
      )}
      <button type="submit" className="sr-only">
        {STRINGS.nav.search_submit}
      </button>
    </form>
  );
}
