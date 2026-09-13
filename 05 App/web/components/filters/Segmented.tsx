"use client";

import { useRef } from "react";
import styles from "./Segmented.module.css";

interface SegmentedProps<T extends string> {
  labelId: string;
  value: T;
  options: { value: T; label: string }[];
  onChange: (next: T) => void;
}

/**
 * A radio group that looks like the reference's segmented control. Real radio
 * semantics, so a keyboard user moves through it with the arrow keys and a
 * screen reader announces "2 of 3" rather than reading three unrelated
 * buttons.
 */
export function Segmented<T extends string>({ labelId, value, options, onChange }: SegmentedProps<T>) {
  const ref = useRef<HTMLDivElement>(null);

  const onKeyDown = (event: React.KeyboardEvent<HTMLDivElement>) => {
    const keys = ["ArrowRight", "ArrowDown", "ArrowLeft", "ArrowUp"];
    if (!keys.includes(event.key)) return;
    event.preventDefault();
    const step = event.key === "ArrowRight" || event.key === "ArrowDown" ? 1 : -1;
    const index = options.findIndex((option) => option.value === value);
    const next = options[(index + step + options.length) % options.length];
    onChange(next.value);
    const buttons = ref.current?.querySelectorAll<HTMLButtonElement>("[role='radio']");
    buttons?.[options.indexOf(next)]?.focus();
  };

  return (
    <div ref={ref} role="radiogroup" aria-labelledby={labelId} className={styles.group} onKeyDown={onKeyDown}>
      {options.map((option) => {
        const checked = option.value === value;
        return (
          <button
            key={option.value}
            type="button"
            role="radio"
            aria-checked={checked}
            tabIndex={checked ? 0 : -1}
            className={styles.segment}
            onClick={() => onChange(option.value)}
          >
            {option.label}
          </button>
        );
      })}
    </div>
  );
}
