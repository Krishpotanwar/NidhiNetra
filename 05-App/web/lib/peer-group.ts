/**
 * Composes the frozen peer-group sentence from contracts/strings.json.
 *
 * The scored fixture gives peer_group as { label, n }, where label is
 * already assembled as "Category works, State, Year" (e.g. "Drinking Water
 * works, Jharkhand, 2023-24") per the design brief's "category, then state,
 * then year" rule. normalized_record has no independent fiscal-year field
 * (tenure is the five-year MP term, not the financial year), so year only
 * exists inside that label string -- there is nowhere else to source it.
 * This parses the label back into its three parts so the *explicit* template
 * can be rendered properly, with the category correctly lowercased through
 * number_format.category_phrase (the label itself keeps the record's title
 * case, which is right for a standalone label but wrong mid-sentence).
 */
import { renderTemplate, STRINGS } from "./strings";
import { categoryPhrase, formatIndianInt } from "./format";
import type { PeerGroup } from "./types";

interface ParsedPeerGroup {
  category: string;
  state: string;
  year: string;
}

function parseLabel(label: string): ParsedPeerGroup | null {
  const parts = label.split(", ");
  if (parts.length !== 3) return null;
  const [categoryWorks, state, year] = parts;
  const category = categoryWorks.replace(/\s+works$/i, "");
  return { category, state, year };
}

/**
 * Renders the design brief section 4 peer-group sentence, "explicit" form
 * (category, state and year spelled out) -- the form the brief itself says
 * to use "anywhere the state and year are not otherwise visible, and in any
 * exported or screenshotted view," which the detail panel is.
 */
export function peerGroupSentence(peerGroup: PeerGroup): string {
  const parsed = parseLabel(peerGroup.label);
  const peer_n = formatIndianInt(peerGroup.n);

  if (!parsed) {
    // Defensive fallback: label didn't match the frozen "X works, Y, Z" shape.
    return renderTemplate(STRINGS.peer_group.variants.thin.text, {
      peer_n,
      category: peerGroup.label,
    });
  }

  if (peerGroup.n < 30) {
    return renderTemplate(STRINGS.peer_group.variants.thin.text, {
      peer_n,
      category: categoryPhrase(parsed.category),
    });
  }

  return renderTemplate(STRINGS.peer_group.variants.explicit.text, {
    peer_n,
    category: categoryPhrase(parsed.category),
    state: parsed.state,
    year: parsed.year,
  });
}
