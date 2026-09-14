import { displayName, formatCurrencyFull, formatIndianInt } from "@/lib/format";
import type { FundFlowGraph, GraphNode, GraphNodeType } from "@/lib/graph-data";
import { renderTemplate, STRINGS } from "@/lib/strings";
import { subgraphFor } from "@/lib/vendor-concentration";

const COLUMN_X: Record<GraphNodeType, number> = {
  MP: 0,
  Agency: 0.5,
  Vendor: 1,
};

const LABEL_MAX = 30;
const NODE_SIZE_MIN = 5;
const NODE_SIZE_MAX = 12;

export interface GraphPalette {
  ink: string;
  ink2: string;
  hairline: string;
  hairlineStrong: string;
  risk3: string;
  risk4: string;
}

export type GraphVisualState = "path" | "flagged" | "plain";

export interface SigmaNodeAttributes {
  x: number;
  y: number;
  size: number;
  label: string;
  fullLabel: string;
  color: string;
  labelColor: string;
  nodeType: GraphNodeType;
  visualState: GraphVisualState;
  dimmed: boolean;
  zIndex: number;
}

export interface SigmaEdgeAttributes {
  size: number;
  label: string;
  color: string;
  visualState: GraphVisualState;
  dimmed: boolean;
  zIndex: number;
}

export interface SigmaNodeDescriptor {
  id: string;
  attributes: SigmaNodeAttributes;
}

export interface SigmaEdgeDescriptor {
  id: string;
  source: string;
  target: string;
  attributes: SigmaEdgeAttributes;
}

export interface SigmaElements {
  nodes: SigmaNodeDescriptor[];
  edges: SigmaEdgeDescriptor[];
}

function truncate(label: string): string {
  return label.length > LABEL_MAX ? `${label.slice(0, LABEL_MAX - 1)}…` : label;
}

function compareNodeIds(a: GraphNode, b: GraphNode): number {
  return a.id < b.id ? -1 : a.id > b.id ? 1 : 0;
}

function nodeYPositions(nodes: GraphNode[]): Map<string, number> {
  const result = new Map<string, number>();
  for (const type of Object.keys(COLUMN_X) as GraphNodeType[]) {
    const column = nodes.filter((node) => node.type === type).sort(compareNodeIds);
    column.forEach((node, index) => {
      result.set(node.id, column.length === 1 ? 0.5 : index / Math.max(1, column.length - 1));
    });
  }
  return result;
}

function rgba(color: string, alpha: number): string {
  const hex = color.trim().match(/^#([\da-f]{3}|[\da-f]{6})$/i)?.[1];
  if (hex) {
    const expanded = hex.length === 3 ? [...hex].map((digit) => digit + digit).join("") : hex;
    const channels = [0, 2, 4].map((offset) => Number.parseInt(expanded.slice(offset, offset + 2), 16));
    return `rgba(${channels[0]}, ${channels[1]}, ${channels[2]}, ${alpha})`;
  }

  const rgb = color.trim().match(/^rgba?\(\s*(\d+(?:\.\d+)?)\s*,\s*(\d+(?:\.\d+)?)\s*,\s*(\d+(?:\.\d+)?)/i);
  if (rgb) return `rgba(${rgb[1]}, ${rgb[2]}, ${rgb[3]}, ${alpha})`;

  return color;
}

function nodeColor(
  state: GraphVisualState,
  dimmed: boolean,
  palette: GraphPalette,
): string {
  if (dimmed) return rgba(palette.hairlineStrong, 0.35);
  if (state === "path") return palette.risk4;
  if (state === "flagged") return palette.risk3;
  return palette.hairline;
}

function edgeColor(
  state: GraphVisualState,
  dimmed: boolean,
  palette: GraphPalette,
): string {
  if (dimmed) return rgba(palette.hairlineStrong, 0.14);
  if (state === "path") return palette.risk4;
  if (state === "flagged") return rgba(palette.risk3, 0.5);
  return rgba(palette.hairlineStrong, 0.55);
}

export function createSigmaElements(
  graph: FundFlowGraph,
  highlightVendorId: string | undefined,
  palette: GraphPalette,
): SigmaElements {
  const maxRisk = Math.max(1, ...graph.nodes.map((node) => node.risk_weight));
  const yById = nodeYPositions(graph.nodes);
  const highlightedGraph = highlightVendorId
    ? subgraphFor(graph, new Set([highlightVendorId]))
    : undefined;
  const highlighted = highlightedGraph
    ? new Set(highlightedGraph.nodes.map((node) => node.id))
    : undefined;
  const highlightedEdges = highlightedGraph ? new Set(highlightedGraph.edges) : undefined;

  const nodes = graph.nodes.map((node): SigmaNodeDescriptor => {
    const onPath = highlighted?.has(node.id) ?? false;
    const dimmed = highlighted !== undefined && !onPath;
    const visualState: GraphVisualState = onPath ? "path" : node.risk_weight > 0 ? "flagged" : "plain";
    const fullLabel = displayName(node.label);
    const boundedRisk = Math.min(maxRisk, Math.max(0, node.risk_weight));

    return {
      id: node.id,
      attributes: {
        x: COLUMN_X[node.type],
        y: yById.get(node.id) ?? 0.5,
        size: NODE_SIZE_MIN + (NODE_SIZE_MAX - NODE_SIZE_MIN) * (boundedRisk / maxRisk),
        label: truncate(fullLabel),
        fullLabel,
        color: nodeColor(visualState, dimmed, palette),
        labelColor: dimmed ? rgba(palette.ink2, 0.35) : onPath ? palette.ink : palette.ink2,
        nodeType: node.type,
        visualState,
        dimmed,
        zIndex: onPath ? 2 : visualState === "flagged" ? 1 : 0,
      },
    };
  });

  const nodeIds = new Set(graph.nodes.map((node) => node.id));
  const edges = graph.edges.flatMap((edge, index): SigmaEdgeDescriptor[] => {
    if (!nodeIds.has(edge.source) || !nodeIds.has(edge.target)) return [];

    const onPath = highlightedEdges?.has(edge) ?? false;
    const dimmed = highlighted !== undefined && !onPath;
    const visualState: GraphVisualState = onPath ? "path" : edge.flagged_work_count > 0 ? "flagged" : "plain";

    return [{
      id: `edge-${index}`,
      source: edge.source,
      target: edge.target,
      attributes: {
        size: Math.min(7, 1.5 + Math.log2(edge.work_count + 1)),
        label: renderTemplate(STRINGS.fund_flow.edge_label, {
          work_count: formatIndianInt(edge.work_count),
          amount: formatCurrencyFull(edge.total_amount_inr),
        }),
        color: edgeColor(visualState, dimmed, palette),
        visualState,
        dimmed,
        zIndex: onPath ? 2 : visualState === "flagged" ? 1 : 0,
      },
    }];
  });

  return { nodes, edges };
}
