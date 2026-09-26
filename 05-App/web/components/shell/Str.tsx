"use client";

import { STRINGS } from "@/lib/strings";

/**
 * Renders the string at a dotted STRINGS path (e.g. "nav.dashboard") at
 * render time. Exists so visible copy in a Server Component page -- which
 * renders once on the server and would otherwise freeze at whatever
 * STRINGS held then -- can instead re-read the live, overlay-switchable
 * STRINGS object: a Client Component boundary remounts (LocaleRoot's
 * key={locale}) and re-reads it, where a bare server-rendered string
 * cannot. Renders nothing for a path that resolves to no string, rather
 * than throwing on a typo or a since-renamed key.
 */
export function Str({ k }: { k: string }) {
  const value: unknown = k.split(".").reduce<unknown>((node, part) => {
    if (node && typeof node === "object" && part in node) {
      return (node as Record<string, unknown>)[part];
    }
    return undefined;
  }, STRINGS);
  return typeof value === "string" ? value : null;
}
