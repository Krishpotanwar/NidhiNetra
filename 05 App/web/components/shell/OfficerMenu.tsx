"use client";

import { useId, useState } from "react";
import * as Popover from "@radix-ui/react-popover";
import { UserCircle } from "@phosphor-icons/react";
import { STRINGS } from "@/lib/strings";
import { officerInitials, useOfficerInitials } from "@/lib/preferences";
import styles from "./OfficerMenu.module.css";

const nav = STRINGS.nav;
const MAX_INITIALS = 12;

/**
 * Where the reference shows a signed-in user, this shows the officer's
 * self-reported initials: the same value the inspection form attaches to a
 * recorded outcome. No sign-in exists in this prototype, and the popover
 * says so rather than implying an account.
 */
export function OfficerMenu() {
  const initials = useOfficerInitials();
  const [open, setOpen] = useState(false);

  return (
    <Popover.Root open={open} onOpenChange={setOpen}>
      <Popover.Trigger
        className={styles.trigger}
        aria-label={`${nav.officer_button}: ${initials || nav.officer_none}`}
      >
        {initials ? (
          <span className={styles.initials}>{initials.slice(0, 3).toUpperCase()}</span>
        ) : (
          <UserCircle size={26} aria-hidden="true" />
        )}
      </Popover.Trigger>
      <Popover.Portal>
        <Popover.Content className={styles.content} align="end" sideOffset={10} collisionPadding={12}>
          {open && <OfficerForm initial={initials} onDone={() => setOpen(false)} />}
        </Popover.Content>
      </Popover.Portal>
    </Popover.Root>
  );
}

function OfficerForm({ initial, onDone }: { initial: string; onDone: () => void }) {
  const [value, setValue] = useState(initial);
  const id = useId();
  const hintId = useId();

  return (
    <form
      onSubmit={(event) => {
        event.preventDefault();
        officerInitials.set(value.trim().slice(0, MAX_INITIALS));
        onDone();
      }}
    >
      <p className={styles.title}>{nav.officer_title}</p>
      <p id={hintId} className={styles.body}>
        {nav.officer_body}
      </p>
      <label htmlFor={id} className={`t-label ${styles.label}`}>
        {nav.officer_field}
      </label>
      <input
        id={id}
        value={value}
        onChange={(event) => setValue(event.target.value)}
        maxLength={MAX_INITIALS}
        autoComplete="off"
        aria-describedby={hintId}
        className={styles.input}
        autoFocus
      />
      <div className={styles.actions}>
        <button
          type="button"
          className={styles.secondary}
          onClick={() => {
            officerInitials.set("");
            onDone();
          }}
        >
          {nav.officer_clear}
        </button>
        <button type="submit" className={styles.primary}>
          {nav.officer_save}
        </button>
      </div>
    </form>
  );
}
