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

function sortedNodesOfType(graph: FundFlowGraph, type: GraphNodeType): GraphNode[] {
  return graph.nodes.filter((n) => n.type === type).sort((a, b) => a.label.localeCompare(b.label));
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
  const mp = buildColumn("MP", sortedNodesOfType(graph, "MP"), highlightVendorId);
  const agency = buildColumn("Agency", sortedNodesOfType(graph, "Agency"), highlightVendorId);
  const vendor = buildColumn("Vendor", sortedNodesOfType(graph, "Vendor"), highlightVendorId);

  const slots = (c: RibbonColumn) => c.rows.length + (c.overflowCount > 0 ? 1 : 0);
  const totalRows = Math.max(1, slots(mp.column), slots(agency.column), slots(vendor.column));

  const byId = new Map<string, GraphNode>(graph.nodes.map((n) => [n.id, n]));
  const mpEdges = graph.edges.filter((e) => byId.get(e.source)?.type === "MP");
  const agencyVendorEdges = graph.edges.filter((e) => byId.get(e.source)?.type === "Agency");
  const widthFor = widthScale([...mpEdges, ...agencyVendorEdges]);

  return {
    columns: { MP: mp.column, Agency: agency.column, Vendor: vendor.column },
    height: totalRows * ROW_HEIGHT,
    mpAgencyRibbons: ribbonsBetween(mpEdges, mp.yById, agency.yById, widthFor),
    agencyVendorRibbons: ribbonsBetween(agencyVendorEdges, agency.yById, vendor.yById, widthFor),
  };
}
