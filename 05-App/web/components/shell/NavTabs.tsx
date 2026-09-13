"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Suspense, useState } from "react";
import * as Popover from "@radix-ui/react-popover";
import { motion, useReducedMotion } from "motion/react";
import { ClipboardText, FlowArrow, House, List, ListNumbers, X } from "@phosphor-icons/react";
import { STRINGS } from "@/lib/strings";
import { HeaderSearch } from "./HeaderSearch";
import styles from "./NavTabs.module.css";

const nav = STRINGS.nav;

export const TABS = [
  { href: "/", label: nav.dashboard, Icon: House },
  { href: "/inspections", label: nav.inspection_list, Icon: ListNumbers },
  { href: "/fund-flow", label: nav.fund_flow, Icon: FlowArrow },
  { href: "/reports", label: nav.reports, Icon: ClipboardText },
] as const;

export function isActiveTab(pathname: string, href: string): boolean {
  return href === "/" ? pathname === "/" : pathname === href || pathname.startsWith(`${href}/`);
}

// Critically damped: the pill follows a click, which carries no momentum,
// so it settles without overshoot (design brief section 8).
const PILL_SPRING = { type: "spring" as const, stiffness: 520, damping: 46 };

/**
 * The five tabs from the reference. The active tab sits on a pill with its
 * icon; the pill slides to the next tab on navigation rather than jumping,
 * which is the one piece of motion the header has, and it reads as "you
 * moved here". Collapses to a menu on narrow screens.
 */
export function NavTabs() {
  const pathname = usePathname();
  const reduce = useReducedMotion();

  return (
    <>
      <nav aria-label={nav.primary_label} className={styles.nav}>
        <ul className={styles.tabs}>
          {TABS.map(({ href, label, Icon }) => {
            const active = isActiveTab(pathname, href);
            return (
              <motion.li key={href} layout={reduce ? false : "position"} transition={PILL_SPRING}>
                <Link href={href} aria-current={active ? "page" : undefined} className={styles.tab}>
                  {active && (
                    <motion.span
                      layoutId="nav-active-pill"
                      className={styles.pill}
                      transition={reduce ? { duration: 0 } : PILL_SPRING}
                    />
                  )}
                  {active && <Icon aria-hidden="true" size={17} weight="fill" className={styles.icon} />}
                  <span className={styles.label}>{label}</span>
                </Link>
              </motion.li>
            );
          })}
        </ul>
      </nav>
      <MobileMenu pathname={pathname} />
    </>
  );
}

function MobileMenu({ pathname }: { pathname: string }) {
  const [open, setOpen] = useState(false);
  return (
    <Popover.Root open={open} onOpenChange={setOpen}>
      <Popover.Trigger className={styles.menuButton} aria-label={open ? nav.menu_close : nav.menu_open}>
        {open ? <X size={20} aria-hidden="true" /> : <List size={20} aria-hidden="true" />}
      </Popover.Trigger>
      <Popover.Portal>
        <Popover.Content className={styles.menu} align="end" sideOffset={12} collisionPadding={12}>
          <Suspense fallback={null}>
            <HeaderSearch variant="menu" onSubmitted={() => setOpen(false)} />
          </Suspense>
          <nav aria-label={nav.primary_label}>
            <ul className={styles.menuList}>
              {TABS.map(({ href, label, Icon }) => {
                const active = isActiveTab(pathname, href);
                return (
                  <li key={href}>
                    <Link
                      href={href}
                      aria-current={active ? "page" : undefined}
                      className={styles.menuItem}
                      onClick={() => setOpen(false)}
                    >
                      <Icon aria-hidden="true" size={18} weight={active ? "fill" : "regular"} />
                      <span className={styles.label}>{label}</span>
                    </Link>
                  </li>
                );
              })}
            </ul>
          </nav>
        </Popover.Content>
      </Popover.Portal>
    </Popover.Root>
  );
}
