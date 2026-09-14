"use client";

import { useEffect, useRef, useState } from "react";
import type Sigma from "sigma";
import { STRINGS } from "@/lib/strings";
import type { FundFlowGraph, GraphNodeType } from "@/lib/graph-data";
import { DotCanvas } from "@/components/shared/DotCanvas";
import { createSigmaElements, type GraphPalette } from "./sigma-graph";
import styles from "./GraphView.module.css";

const s = STRINGS.fund_flow;

const COLUMN_ORDER: GraphNodeType[] = ["MP", "Agency", "Vendor"];
const COLUMN_LABEL: Record<GraphNodeType, string> = {
  MP: s.column_mp,
  Agency: s.column_agency,
  Vendor: s.column_vendor,
};

const FALLBACK_PALETTE: GraphPalette = {
  ink: "#0f1b33",
  ink2: "#334262",
  hairline: "#e3e9ef",
  hairlineStrong: "#d3dce6",
  risk3: "#d4540f",
  risk4: "#c81e1e",
};

function graphPalette(element: HTMLElement): GraphPalette {
  const computed = getComputedStyle(element);
  const token = (name: string, fallback: string) => computed.getPropertyValue(name).trim() || fallback;
  return {
    ink: token("--ink", FALLBACK_PALETTE.ink),
    ink2: token("--ink-2", FALLBACK_PALETTE.ink2),
    hairline: token("--hairline", FALLBACK_PALETTE.hairline),
    hairlineStrong: token("--hairline-strong", FALLBACK_PALETTE.hairlineStrong),
    risk3: token("--risk-3", FALLBACK_PALETTE.risk3),
    risk4: token("--risk-4", FALLBACK_PALETTE.risk4),
  };
}

interface TooltipState {
  text: string;
  x: number;
  y: number;
  horizontal: "left" | "center" | "right";
  vertical: "above" | "below";
}

type RendererState = "loading" | "ready" | "failed";

interface GraphViewProps {
  graph: FundFlowGraph;
  /** Renders this vendor's path in the risk colour; everything else recedes. */
  highlightVendorId?: string;
}

export function GraphView({ graph, highlightVendorId }: GraphViewProps) {
  const mountRef = useRef<HTMLDivElement>(null);
  const [tooltip, setTooltip] = useState<TooltipState | null>(null);
  const [rendererState, setRendererState] = useState<RendererState>("loading");

  useEffect(() => {
    const mount = mountRef.current;
    if (!mount || graph.nodes.length === 0) return;
    const container = mount;

    let disposed = false;
    let renderer: Sigma | null = null;
    setTooltip(null);
    setRendererState("loading");

    async function initialise() {
      const [{ MultiDirectedGraph }, { default: SigmaRenderer }] = await Promise.all([
        import("graphology"),
        import("sigma"),
      ]);
      if (disposed) return;

      const elements = createSigmaElements(graph, highlightVendorId, graphPalette(container));
      const sigmaGraph = new MultiDirectedGraph();
      for (const node of elements.nodes) {
        sigmaGraph.addNode(node.id, node.attributes);
      }
      for (const edge of elements.edges) {
        sigmaGraph.addEdgeWithKey(edge.id, edge.source, edge.target, edge.attributes);
      }

      renderer = new SigmaRenderer(sigmaGraph, container, {
        enableEdgeEvents: true,
        hideEdgesOnMove: true,
        hideLabelsOnMove: true,
        labelColor: { attribute: "labelColor", color: FALLBACK_PALETTE.ink2 },
        labelFont: getComputedStyle(container).fontFamily,
        labelRenderedSizeThreshold: 5,
        labelSize: 11,
        labelWeight: "500",
        renderEdgeLabels: false,
        renderLabels: true,
        stagePadding: 24,
        zIndex: true,
      });
      setRendererState("ready");

      const showTooltip = (text: string, x: number, y: number) => {
        const horizontal = x < container.clientWidth / 3
          ? "right"
          : x > (container.clientWidth * 2) / 3
            ? "left"
            : "center";
        const vertical = y < container.clientHeight / 2 ? "below" : "above";
        setTooltip({ text, x, y, horizontal, vertical });
      };
      renderer.on("enterNode", ({ node, event }) => {
        showTooltip(String(sigmaGraph.getNodeAttribute(node, "fullLabel")), event.x, event.y);
      });
      renderer.on("leaveNode", () => setTooltip(null));
      renderer.on("enterEdge", ({ edge, event }) => {
        showTooltip(String(sigmaGraph.getEdgeAttribute(edge, "label")), event.x, event.y);
      });
      renderer.on("leaveEdge", () => setTooltip(null));
    }

    void initialise().catch((error: unknown) => {
      if (disposed) return;
      console.error("Fund-flow renderer failed to initialise.", error);
      setRendererState("failed");
    });
    return () => {
      disposed = true;
      renderer?.kill();
    };
  }, [graph, highlightVendorId]);

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
        <div
          ref={mountRef}
          role="img"
          aria-label={s.subtitle}
          className={styles.canvas}
          data-graph-renderer="sigma"
          data-render-state={rendererState}
        />
        {tooltip && (
          <span
            role="tooltip"
            className={styles.tooltip}
            style={{ left: tooltip.x, top: tooltip.y }}
            data-horizontal={tooltip.horizontal}
            data-vertical={tooltip.vertical}
          >
            {tooltip.text}
          </span>
        )}
      </div>
    </div>
  );
}
