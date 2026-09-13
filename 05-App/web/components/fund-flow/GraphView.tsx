"use client";

import { useMemo } from "react";
import { renderTemplate, STRINGS } from "@/lib/strings";
import { displayName, formatCurrencyFull, formatIndianInt } from "@/lib/format";
import type { FundFlowGraph, GraphNode, GraphNodeType } from "@/lib/graph-data";
import { highlightedNodeIds } from "@/lib/vendor-concentration";
import { DotCanvas } from "@/components/shared/DotCanvas";
import styles from "./GraphView.module.css";

const s = STRINGS.fund_flow;

/**
 * A tiered layout, not a force simulation: the domain fixes the geometry
 * (money moves MP -> Agency -> Vendor, always), so three columns and curved
 * edges say everything a spring layout would approximate, deterministically.
 */
const COLUMN_ORDER: GraphNodeType[] = ["MP", "Agency", "Vendor"];
const COLUMN_LABEL: Record<GraphNodeType, string> = {
  MP: s.column_mp,
  Agency: s.column_agency,
  Vendor: s.column_vendor,
};

const NODE_R_MIN = 5;
const NODE_R_MAX = 12;
const ROW_HEIGHT = 30;
const COLUMN_GAP = 300;
const PADDING_X = 210;
const PADDING_Y = 28;
const LABEL_MAX = 30;

interface Positioned extends GraphNode {
  x: number;
  y: number;
  r: number;
}

function truncate(label: string): string {
  const clean = displayName(label);
  return clean.length > LABEL_MAX ? `${clean.slice(0, LABEL_MAX - 1)}…` : clean;
}

function layout(graph: FundFlowGraph) {
  const maxWeight = Math.max(1, ...graph.nodes.map((n) => n.risk_weight));
  const byColumn = COLUMN_ORDER.map((type) => graph.nodes.filter((n) => n.type === type));
  const maxRows = Math.max(1, ...byColumn.map((column) => column.length));
  const height = PADDING_Y * 2 + maxRows * ROW_HEIGHT;

  const positioned: Positioned[] = [];
  byColumn.forEach((column, columnIndex) => {
    const x = PADDING_X + columnIndex * COLUMN_GAP;
    const columnHeight = column.length * ROW_HEIGHT;
    const startY = (height - columnHeight) / 2 + ROW_HEIGHT / 2;
    column.forEach((node, rowIndex) => {
      const r = NODE_R_MIN + (NODE_R_MAX - NODE_R_MIN) * (node.risk_weight / maxWeight);
      positioned.push({ ...node, x, y: startY + rowIndex * ROW_HEIGHT, r });
    });
  });

  return { positioned, width: PADDING_X * 2 + (COLUMN_ORDER.length - 1) * COLUMN_GAP, height };
}

interface GraphViewProps {
  graph: FundFlowGraph;
  /** Renders this vendor's path in the risk colour; everything else recedes. */
  highlightVendorId?: string;
}

export function GraphView({ graph, highlightVendorId }: GraphViewProps) {
  const { positioned, width, height } = useMemo(() => layout(graph), [graph]);
  const byId = useMemo(() => new Map(positioned.map((node) => [node.id, node])), [positioned]);
  const highlighted = useMemo(
    () => (highlightVendorId ? highlightedNodeIds(graph, highlightVendorId) : null),
    [graph, highlightVendorId],
  );

  if (graph.nodes.length === 0) {
    return (
      <DotCanvas className={styles.empty}>
        <p className={styles.emptyTitle}>{s.empty}</p>
        <p className={styles.emptyBody}>{s.empty_body}</p>
      </DotCanvas>
    );
  }

  return (
    <div>
      <div className={styles.legend}>
        {COLUMN_ORDER.map((type) => (
          <span key={type}>{COLUMN_LABEL[type]}</span>
        ))}
      </div>
      <div className={styles.scroller}>
        <svg
          viewBox={`0 0 ${width} ${height}`}
          width={width}
          height={height}
          role="img"
          aria-label={s.subtitle}
          className={styles.canvas}
        >
          {graph.edges.map((edge, index) => {
            const from = byId.get(edge.source);
            const to = byId.get(edge.target);
            if (!from || !to) return null; // referential integrity is enforced server-side
            const flagged = edge.flagged_work_count > 0;
            const onPath = highlighted ? highlighted.has(edge.source) && highlighted.has(edge.target) : false;
            const midX = (from.x + to.x) / 2;
            return (
              <path
                key={index}
                d={`M ${from.x} ${from.y} C ${midX} ${from.y}, ${midX} ${to.y}, ${to.x} ${to.y}`}
                fill="none"
                className={styles.edge}
                data-state={onPath ? "path" : flagged ? "flagged" : "plain"}
                data-dimmed={highlighted && !onPath ? "" : undefined}
                strokeWidth={Math.min(7, 1.5 + Math.log2(edge.work_count + 1))}
              >
                <title>
                  {renderTemplate(s.edge_label, {
                    work_count: formatIndianInt(edge.work_count),
                    amount: formatCurrencyFull(edge.total_amount_inr),
                  })}
                </title>
              </path>
            );
          })}

          {positioned.map((node) => {
            const onPath = highlighted?.has(node.id) ?? false;
            return (
              <g key={node.id} opacity={highlighted && !onPath ? 0.35 : 1}>
                <circle
                  cx={node.x}
                  cy={node.y}
                  r={onPath ? node.r + 1.5 : node.r}
                  className={styles.node}
                  data-state={onPath ? "path" : node.risk_weight > 0 ? "flagged" : "plain"}
                >
                  <title>{displayName(node.label)}</title>
                </circle>
                <text
                  x={node.type === "Agency" ? node.x : node.type === "Vendor" ? node.x + node.r + 9 : node.x - node.r - 9}
                  y={node.type === "Agency" ? node.y - node.r - 7 : node.y}
                  textAnchor={node.type === "Agency" ? "middle" : node.type === "Vendor" ? "start" : "end"}
                  dominantBaseline={node.type === "Agency" ? "auto" : "middle"}
                  className={styles.label}
                  data-strong={onPath || undefined}
                >
                  {truncate(node.label)}
                </text>
              </g>
            );
          })}
        </svg>
      </div>
    </div>
  );
}
