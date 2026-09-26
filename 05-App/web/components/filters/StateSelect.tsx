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
  /** T6: a single choice (District Authority, MP constituency) instead of
   *  the States field's multi-select. Choosing an option replaces `value`
   *  with just that option and closes the popover, rather than toggling it
   *  into a growing set. Defaults to false, which keeps every existing
   *  caller's behaviour exactly as it was. */
  single?: boolean;
  /** Summary/option-list text for "nothing chosen yet". Defaults to
   *  today's "All states" wording. */
  allLabel?: string;
  /** How one option's row -- and, when the value is found among `options`,
   *  the closed trigger's summary -- is labelled. Defaults to the option's
   *  raw value, as today. */
  optionLabel?: (option: FacetOption) => string;
}

/**
 * States, multi-select: the reference shows three at once ("Bihar, Odisha,
 * Jharkhand"), and comparing a handful of states is the real task. Thirty six
 * options is too many for a plain list, so it carries a find field.
 *
 * T6 (D10) generalizes this same popover into the District Authority and MP
 * constituency pickers via `single`/`allLabel`/`optionLabel`: same find
 * field, same list, same "Clear selection", just one choice instead of many.
 */
export function StateSelect({
  labelId,
  value,
  options,
  onChange,
  single = false,
  allLabel = filters.all_states,
  optionLabel,
}: StateSelectProps) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const valueId = useId();
  const findId = useId();
  const radioName = useId();

  const optionText = optionLabel ?? ((option: FacetOption) => option.value);
  // Identical to the raw value when optionLabel is not given (optionText(o)
  // === o.value whenever `found`), so the default multi-select summary is
  // byte-identical to before this prop existed.
  const labelFor = (raw: string) => {
    const found = options.find((option) => option.value === raw);
    return found ? optionText(found) : raw;
  };

  const summary =
    value.length === 0
      ? allLabel
      : value.length <= 3
        ? value.map(labelFor).join(", ")
        : renderTemplate(filters.states_count, { n: formatIndianInt(value.length) });

  const needle = query.trim().toLowerCase();
  const visible = needle ? options.filter((option) => option.value.toLowerCase().includes(needle)) : options;

  const choose = (chosen: string) => {
    if (single) {
      onChange([chosen]);
      setOpen(false);
      return;
    }
    const next = value.includes(chosen) ? value.filter((s) => s !== chosen) : [...value, chosen];
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
          <div className={own.list} role={single ? "radiogroup" : "group"} aria-labelledby={labelId}>
            {visible.map((option) => (
              <label key={option.value} className={own.option}>
                <input
                  type={single ? "radio" : "checkbox"}
                  name={single ? radioName : undefined}
                  className={own.checkbox}
                  checked={value.includes(option.value)}
                  onChange={() => choose(option.value)}
                />
                <span className={own.optionLabel}>{optionText(option)}</span>
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
