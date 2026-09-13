"use client";

import { useEffect, useRef } from "react";
import type { ReactNode } from "react";
import styles from "./DotCanvas.module.css";

interface DotCanvasProps {
  /** The empty or error state's own class (e.g. styles.state), kept so
   *  every caller's existing padding and max-width are untouched. */
  className: string;
  children: ReactNode;
  /** Some callers are a landmark (`section` with `aria-label`); the
   *  texture must not downgrade that to an unlabelled div. */
  as?: "div" | "section";
  "aria-label"?: string;
}

/**
 * A quiet dot-grid texture for the app's genuinely empty spaces (error
 * cards, empty results, the fund-flow graph with nothing to draw), with a
 * small circular highlight that brightens the dots nearest the cursor.
 *
 * This is not the reference's removed DotField: that was a page-wide
 * pointer-following field behind live content. This is a fixed grid
 * confined to one already-empty card; only which dots read brighter
 * moves, and only inside that card's own edges (DESIGN.md, "Named
 * Rules" -- the confined-texture exception to the pointer-following ban).
 *
 * Position is written straight to CSS custom properties on the element,
 * not React state: a continuous pointer value re-rendering the tree on
 * every move would be the exact mistake the coding rules single out.
 */
export function DotCanvas({ className, children, as: Tag = "div", ...rest }: DotCanvasProps) {
  const ref = useRef<HTMLElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

    const handleMove = (event: PointerEvent) => {
      const rect = el.getBoundingClientRect();
      el.style.setProperty("--dot-x", `${event.clientX - rect.left}px`);
      el.style.setProperty("--dot-y", `${event.clientY - rect.top}px`);
    };
    el.addEventListener("pointermove", handleMove);
    return () => el.removeEventListener("pointermove", handleMove);
  }, []);

  return (
    // A callback ref, not the object ref directly: `Tag` is a union of
    // intrinsic elements, and only a ref that accepts the wider
    // HTMLElement (not one tag's own, narrower element type) satisfies
    // every branch of that union.
    <Tag ref={(node: HTMLElement | null) => { ref.current = node; }} className={`${styles.canvas} ${className}`} {...rest}>
      {children}
    </Tag>
  );
}
