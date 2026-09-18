import { displayName, formatCurrencyFull, formatIndianInt } from "@/lib/format";
import type { FundFlowGraph, GraphEdge, GraphNode, GraphNodeType } from "@/lib/graph-data";
import { renderTemplate, STRINGS } from "@/lib/strings";

const s = STRINGS.fund_flow;

/**
 * Pure layout math for the three-column MP -> Agency -> Vendor ribbon chart
 * (the reference's Fund Flow visual). Kept apart from RibbonView.tsx so the
 * row/ribbon positions can be reasoned about (and tested) without React or a
 * DOM -- rows sit at a fixed height, evenly stacked top-down, so a ribbon's
 * endpoints are computed from list position alone, never measured off the
 * rendered page.
 *
 * Row ORDER within each column is not alphabetical -- an early version was,
 * and it produced an unreadable tangle of crossing ribbons reported against
 * the deployed page, because alphabetical order has nothing to do with which
 * MPs actually fund which agencies. Instead each column is ordered by the
 * "barycenter" heuristic layered-graph and Sankey-diagram tools use to
 * minimise crossings: place each Agency near the average row of the MPs
 * that feed it, each Vendor near the average row of its Agencies, then sweep
 * back (re-settle MPs against the now-fixed Agency order, and so on) a
 * couple of times so it converges. Cheap here -- at most MAX_ROWS_PER_COLUMN
 * nodes a side -- and it is the actual fix for "the graph is a mess", not a
 * cosmetic tweak.
 *
 * Colour and width are both real, already-collected signals, never an
 * invented "concentration score":
 * - width scales with edge.total_amount_inr (the sanctioned amount that
 *   edge actually represents), log-normalised across every edge drawn in
 *   this one layout so the thinnest and thickest ribbons on screen are
 *   always visibly different regardless of the cluster's absolute scale.
 * - colour is the real share of that edge's works carrying a risk flag
 *   (edge.flagged_work_count / edge.work_count): none flagged (plain),
 *   some flagged (elevated), or all flagged (high) -- three honest tiers
 *   from data the graph already carries, not a fabricated "concentration"
 *   number.
 */

export const ROW_HEIGHT = 32;
export const MAX_ROWS_PER_COLUMN = 8;
const LABEL_MAX = 34;
const MIN_RIBBON_WIDTH = 1.5;
const MAX_RIBBON_WIDTH = 12;
// Barycenter relaxation rounds (forward + backward each). Node counts here
// are tiny (<= MAX_ROWS_PER_COLUMN a side), so this converges well before
// 2 rounds; more would cost nothing but buy nothing either.
const RELAXATION_ROUNDS = 2;

export type RibbonEdgeState = "plain" | "elevated" | "high";

export interface RibbonRow {
  id: string;
  label: string;
  fullLabel: string;
  selected: boolean;
  y: number;
}

export interface RibbonColumn {
  type: GraphNodeType;
  rows: RibbonRow[];
  overflowCount: number;
}

export interface RibbonPath {
  id: string;
  d: string;
  state: RibbonEdgeState;
  strokeWidth: number;
  title: string;
}

export interface RibbonLayout {
  columns: Record<GraphNodeType, RibbonColumn>;
  height: number;
  mpAgencyRibbons: RibbonPath[];
  agencyVendorRibbons: RibbonPath[];
}

function truncate(label: string): string {
  const full = displayName(label);
  return full.length > LABEL_MAX ? `${full.slice(0, LABEL_MAX - 1)}…` : full;
}

function byLabel(a: GraphNode, b: GraphNode): number {
  return a.label.localeCompare(b.label);
}

function nodesOfType(graph: FundFlowGraph, type: GraphNodeType): GraphNode[] {
  return graph.nodes.filter((n) => n.type === type);
}

function indexById(order: GraphNode[]): Map<string, number> {
  const map = new Map<string, number>();
  order.forEach((node, i) => map.set(node.id, i));
  return map;
}

function groupBy(pairs: Array<[string, string]>): Map<string, string[]> {
  const map = new Map<string, string[]>();
  for (const [key, value] of pairs) {
    const existing = map.get(key);
    if (existing) existing.push(value);
    else map.set(key, [value]);
  }
  return map;
}

/**
 * Reorders `nodes` by the average position of the neighbours each one
 * connects to (via `neighborsOf`, looked up in `neighborIndex`) -- the
 * barycenter heuristic. A node with no resolvable neighbour sorts to the
 * end (score Infinity) rather than jumping to the top, so a genuinely
 * unconnected row does not get shuffled ahead of connected ones. Ties
 * (including every node, when a column has no neighbours to score against
 * at all -- no edges yet, or a backward sweep against an empty column)
 * keep their current relative order rather than falling back to a fixed
 * tiebreak: `Array.prototype.sort` is stable, so this is just "sort by
 * score alone." That matters across the relaxation rounds below -- a
 * sweep with nothing to differentiate ties on must leave the previous
 * sweep's real progress alone, not silently reset it to alphabetical.
 * The very first call in a fresh relaxation still ties everything back to
 * label order, because the order fed in is the initial alphabetical one.
 */
function barycenterOrder(
  nodes: GraphNode[],
  neighborIndex: Map<string, number>,
  neighborsOf: (nodeId: string) => string[],
): GraphNode[] {
  const scored = nodes.map((node) => {
    const positions = neighborsOf(node.id)
      .map((id) => neighborIndex.get(id))
      .filter((p): p is number => p !== undefined);
    const score = positions.length > 0 ? positions.reduce((a, b) => a + b, 0) / positions.length : Infinity;
    return { node, score };
  });
  return scored.sort((a, b) => a.score - b.score).map((s) => s.node);
}

function buildColumn(
  type: GraphNodeType,
  nodes: GraphNode[],
  highlightId: string | undefined,
): { column: RibbonColumn; yById: Map<string, number> } {
  const shown = nodes.slice(0, MAX_ROWS_PER_COLUMN);
  const yById = new Map<string, number>();
  const rows: RibbonRow[] = shown.map((node, i) => {
    const y = i * ROW_HEIGHT + ROW_HEIGHT / 2;
    yById.set(node.id, y);
    return {
      id: node.id,
      label: truncate(node.label),
      fullLabel: displayName(node.label),
      selected: node.id === highlightId,
      y,
    };
  });
  return {
    column: { type, rows, overflowCount: Math.max(0, nodes.length - shown.length) },
    yById,
  };
}

function edgeState(edge: GraphEdge): RibbonEdgeState {
  if (edge.work_count <= 0 || edge.flagged_work_count <= 0) return "plain";
  if (edge.flagged_work_count >= edge.work_count) return "high";
  return "elevated";
}

/**
 * Log-normalises total_amount_inr across every edge this one layout draws
 * (both MP -> Agency and Agency -> Vendor together, so a rupee is the same
 * width regardless of which hop it is on), into [MIN_RIBBON_WIDTH,
 * MAX_RIBBON_WIDTH]. Log rather than linear: sanctioned amounts on a single
 * vendor's cluster commonly span two or three orders of magnitude, and a
 * linear map would flatten everything but the single largest edge down to
 * the minimum width, which reads as "every edge is the same" -- the exact
 * complaint this replaces work_count-based width to fix.
 */
function widthScale(edges: GraphEdge[]): (amountInr: number) => number {
  if (edges.length === 0) return () => MIN_RIBBON_WIDTH;
  const logAmounts = edges.map((e) => Math.log(Math.max(0, e.total_amount_inr) + 1));
  const min = Math.min(...logAmounts);
  const max = Math.max(...logAmounts);
  if (max === min) return () => (MIN_RIBBON_WIDTH + MAX_RIBBON_WIDTH) / 2;
  return (amountInr: number) => {
    const t = (Math.log(Math.max(0, amountInr) + 1) - min) / (max - min);
    return MIN_RIBBON_WIDTH + t * (MAX_RIBBON_WIDTH - MIN_RIBBON_WIDTH);
  };
}

// Draw order back-to-front, so a thinner but more severe ribbon is never
// buried under a thicker ordinary one.
const STATE_RANK: Record<RibbonEdgeState, number> = { plain: 0, elevated: 1, high: 2 };

function ribbonsBetween(
  edges: GraphEdge[],
  sourceY: Map<string, number>,
  targetY: Map<string, number>,
  widthFor: (amountInr: number) => number,
): RibbonPath[] {
  const paths: RibbonPath[] = [];
  edges.forEach((edge, index) => {
    const y1 = sourceY.get(edge.source);
    const y2 = targetY.get(edge.target);
    // A collapsed ("+N more") endpoint has no row of its own to draw into.
    if (y1 === undefined || y2 === undefined) return;
    paths.push({
      id: `${edge.source}->${edge.target}-${index}`,
      d: `M0,${y1} C33,${y1} 66,${y2} 100,${y2}`,
      state: edgeState(edge),
      strokeWidth: widthFor(edge.total_amount_inr),
      title: renderTemplate(s.edge_label, {
        work_count: formatIndianInt(edge.work_count),
        amount: formatCurrencyFull(edge.total_amount_inr),
      }),
    });
  });
  return paths.sort((a, b) => STATE_RANK[a.state] - STATE_RANK[b.state]);
}

export function buildRibbonLayout(graph: FundFlowGraph, highlightVendorId: string | undefined): RibbonLayout {
  const byId = new Map<string, GraphNode>(graph.nodes.map((n) => [n.id, n]));
  const mpEdges = graph.edges.filter((e) => byId.get(e.source)?.type === "MP");
  const agencyVendorEdges = graph.edges.filter((e) => byId.get(e.source)?.type === "Agency");

  const agencyToMps = groupBy(mpEdges.map((e): [string, string] => [e.target, e.source]));
  const mpToAgencies = groupBy(mpEdges.map((e): [string, string] => [e.source, e.target]));
  const vendorToAgencies = groupBy(agencyVendorEdges.map((e): [string, string] => [e.target, e.source]));
  const agencyToVendors = groupBy(agencyVendorEdges.map((e): [string, string] => [e.source, e.target]));

  let mpOrder = nodesOfType(graph, "MP").sort(byLabel);
  let agencyOrder = nodesOfType(graph, "Agency").sort(byLabel);
  let vendorOrder = nodesOfType(graph, "Vendor").sort(byLabel);

  for (let round = 0; round < RELAXATION_ROUNDS; round++) {
    // Forward: settle Agency against MP, then Vendor against the now-settled Agency.
    agencyOrder = barycenterOrder(agencyOrder, indexById(mpOrder), (id) => agencyToMps.get(id) ?? []);
    vendorOrder = barycenterOrder(vendorOrder, indexById(agencyOrder), (id) => vendorToAgencies.get(id) ?? []);
    // Backward: re-settle Agency against the now-settled Vendor, then MP against Agency.
    agencyOrder = barycenterOrder(agencyOrder, indexById(vendorOrder), (id) => agencyToVendors.get(id) ?? []);
    mpOrder = barycenterOrder(mpOrder, indexById(agencyOrder), (id) => mpToAgencies.get(id) ?? []);
  }

  const mp = buildColumn("MP", mpOrder, highlightVendorId);
  const agency = buildColumn("Agency", agencyOrder, highlightVendorId);
  const vendor = buildColumn("Vendor", vendorOrder, highlightVendorId);

  const slots = (c: RibbonColumn) => c.rows.length + (c.overflowCount > 0 ? 1 : 0);
  const totalRows = Math.max(1, slots(mp.column), slots(agency.column), slots(vendor.column));
  const widthFor = widthScale([...mpEdges, ...agencyVendorEdges]);

  return {
    columns: { MP: mp.column, Agency: agency.column, Vendor: vendor.column },
    height: totalRows * ROW_HEIGHT,
    mpAgencyRibbons: ribbonsBetween(mpEdges, mp.yById, agency.yById, widthFor),
    agencyVendorRibbons: ribbonsBetween(agencyVendorEdges, agency.yById, vendor.yById, widthFor),
  };
}
