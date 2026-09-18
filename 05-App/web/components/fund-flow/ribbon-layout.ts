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
 * Colour is two real, already-collected signals, not an invented
 * "concentration tier": whether an edge carries any flagged work
 * (edge.flagged_work_count, from the server's own risk scoring) and whether
 * a node is the vendor currently in focus (highlightVendorId, the page's own
 * selection state). Nothing here approximates a number the graph does not
 * actually have.
 */

export const ROW_HEIGHT = 32;
export const MAX_ROWS_PER_COLUMN = 8;
const LABEL_MAX = 34;

export type RibbonEdgeState = "plain" | "flagged";

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

function ribbonsBetween(
  edges: GraphEdge[],
  sourceY: Map<string, number>,
  targetY: Map<string, number>,
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
      state: edge.flagged_work_count > 0 ? "flagged" : "plain",
      strokeWidth: Math.min(10, 2 + Math.log2(edge.work_count + 1) * 2),
      title: renderTemplate(s.edge_label, {
        work_count: formatIndianInt(edge.work_count),
        amount: formatCurrencyFull(edge.total_amount_inr),
      }),
    });
  });
  // Flagged ribbons render on top of plain ones, so a thin flagged ribbon is
  // never hidden under a thicker ordinary one.
  return paths.sort((a, b) => (a.state === b.state ? 0 : a.state === "flagged" ? 1 : -1));
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

  return {
    columns: { MP: mp.column, Agency: agency.column, Vendor: vendor.column },
    height: totalRows * ROW_HEIGHT,
    mpAgencyRibbons: ribbonsBetween(mpEdges, mp.yById, agency.yById),
    agencyVendorRibbons: ribbonsBetween(agencyVendorEdges, agency.yById, vendor.yById),
  };
}
