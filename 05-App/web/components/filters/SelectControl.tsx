"use client";

import * as Select from "@radix-ui/react-select";
import { CaretDown, Check } from "@phosphor-icons/react";
import { formatIndianInt } from "@/lib/format";
import type { SelectOption } from "@/lib/filters";
import styles from "./controls.module.css";

interface SelectControlProps {
  labelId: string;
  value: string;
  options: SelectOption[];
  onValueChange: (value: string) => void;
  width?: "narrow" | "default" | "wide";
}

/**
 * A single-choice filter. A real listbox (Radix Select) rather than the
 * reference mockup's click-to-cycle control, which gives no way to see the
 * options before committing, skip one, or operate it from a keyboard.
 */
export function SelectControl({ labelId, value, options, onValueChange, width = "default" }: SelectControlProps) {
  const current = options.find((option) => option.value === value) ?? options[0];
  const widthClass = width === "narrow" ? styles.narrow : width === "wide" ? styles.wide : "";

  return (
    <Select.Root value={value} onValueChange={onValueChange}>
      <Select.Trigger className={`${styles.trigger} ${widthClass}`} aria-labelledby={labelId}>
        <Select.Value className={styles.value}>{current?.label}</Select.Value>
        <Select.Icon className={styles.caret}>
          <CaretDown size={13} weight="bold" />
        </Select.Icon>
      </Select.Trigger>
      <Select.Portal>
        <Select.Content className={styles.content} position="popper" sideOffset={6}>
          <Select.Viewport>
            {options.map((option) => (
              <Select.Item key={option.value} value={option.value} className={styles.item}>
                <Select.ItemIndicator className={styles.check}>
                  <Check size={13} weight="bold" />
                </Select.ItemIndicator>
                <Select.ItemText>{option.label}</Select.ItemText>
                {option.count !== undefined && <span className={styles.count}>{formatIndianInt(option.count)}</span>}
              </Select.Item>
            ))}
          </Select.Viewport>
        </Select.Content>
      </Select.Portal>
    </Select.Root>
  );
}
