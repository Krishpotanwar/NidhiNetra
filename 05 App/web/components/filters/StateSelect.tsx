"use client";

import { useId, useState } from "react";
import * as Popover from "@radix-ui/react-popover";
import { CaretDown, MagnifyingGlass } from "@phosphor-icons/react";
import { renderTemplate, STRINGS } from "@/lib/strings";
import { formatIndianInt } from "@/lib/format";
import type { FacetOption } from "@/lib/types";
import styles from "./controls.module.css";
import own from "./StateSelect.module.css";

const filters = STRINGS.filters;

interface StateSelectProps {
  labelId: string;
  value: string[];
  options: FacetOption[];
  onChange: (next: string[]) => void;
}

/**
 * States, multi-select: the reference shows three at once ("Bihar, Odisha,
 * Jharkhand"), and comparing a handful of states is the real task. Thirty six
 * options is too many for a plain list, so it carries a find field.
 */
export function StateSelect({ labelId, value, options, onChange }: StateSelectProps) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const valueId = useId();
  const findId = useId();

  const summary =
    value.length === 0
      ? filters.all_states
      : value.length <= 3
        ? value.join(", ")
        : renderTemplate(filters.states_count, { n: formatIndianInt(value.length) });

  const needle = query.trim().toLowerCase();
  const visible = needle ? options.filter((option) => option.value.toLowerCase().includes(needle)) : options;

  const toggle = (state: string) => {
    const next = value.includes(state) ? value.filter((s) => s !== state) : [...value, state];
    next.sort((a, b) => a.localeCompare(b));
    onChange(next);
  };

  return (
    <Popover.Root
      open={open}
      onOpenChange={(next) => {
        setOpen(next);
        if (!next) setQuery("");
      }}
    >
      <Popover.Trigger className={`${styles.trigger} ${styles.wide}`} aria-labelledby={`${labelId} ${valueId}`}>
        <span id={valueId} className={styles.value}>
          {summary}
        </span>
        <CaretDown size={13} weight="bold" className={styles.caret} />
      </Popover.Trigger>
      <Popover.Portal>
        <Popover.Content className={`${styles.content} ${own.panel}`} align="start" sideOffset={6} collisionPadding={12}>
          <div className={own.find}>
            <MagnifyingGlass size={15} aria-hidden="true" className={own.findIcon} />
            <input
              id={findId}
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder={filters.state_find}
              aria-label={filters.state_find}
              className={own.findInput}
              autoComplete="off"
            />
          </div>
          <div className={own.list} role="group" aria-labelledby={labelId}>
            {visible.map((option) => (
              <label key={option.value} className={own.option}>
                <input
                  type="checkbox"
                  className={own.checkbox}
                  checked={value.includes(option.value)}
                  onChange={() => toggle(option.value)}
                />
                <span className={own.optionLabel}>{option.value}</span>
                <span className={styles.count}>{formatIndianInt(option.count)}</span>
              </label>
            ))}
            {visible.length === 0 && <p className={own.none}>{filters.state_none_found}</p>}
          </div>
          <div className={own.footer}>
            <button type="button" className={own.clear} onClick={() => onChange([])} disabled={value.length === 0}>
              {filters.selection_clear}
            </button>
            <Popover.Close className={own.done}>{filters.done}</Popover.Close>
          </div>
        </Popover.Content>
      </Popover.Portal>
    </Popover.Root>
  );
}
