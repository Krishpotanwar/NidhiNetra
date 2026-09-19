"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import type { PointerEvent } from "react";
import { ArrowRight, Bank, Briefcase, Info } from "@phosphor-icons/react";
import { DotCanvas } from "@/components/shared/DotCanvas";
import { formatCurrency, formatCurrencyFull, formatIndianInt } from "@/lib/format";
import type { FundFlowGraph } from "@/lib/graph-data";
import { renderTemplate, STRINGS } from "@/lib/strings";
import {
  buildSankeyLayout,
  MIN_WIDTH,
  type SankeyColumn,
  type SankeyLink,
  type SankeyNode,
  type SankeyTier,
} from "./sankey-layout";
import styles from "./SankeyChart.module.css";

const s = STRINGS.fund_flow;

// What the chart assumes until the first ResizeObserver report (and where none exists, as in jsdom).
const DEFAULT_WIDTH = 960;
const BAR_WIDTH = 6;
// Drawn back to front, so a thin flagged band is never buried under a thick ordinary one.
const TIER_RANK: Record<SankeyTier, number> = { plain: 0, elevated: 1, high: 2 };
const TIER_CLASS: Record<SankeyTier, string> = {
  plain: styles.plain,
  elevated: styles.elevated,
  high: styles.high,
};

// A tier class only sets the colour variables its element then reads; "+N more" goes neutral.
const toneOf = (node: SankeyNode) =>
  node.isMore ? styles.more : node.type === "Vendor" ? TIER_CLASS[node.tier] : styles.plain;

type Focus = { kind: "node" | "link"; id: string } | null;
type Tip = { link: SankeyLink; x: number; y: number };

function headingOf(column: SankeyColumn): string {
  const name =
    column.type === "MP"
      ? s.column_mp
      : column.type === "Agency"
        ? s.column_agency
        : column.count === 1
          ? s.column_vendor
          : s.totals_vendor_label;
  return `${name} (${formatIndianInt(column.count)})`;
}

/**
 * The three-column MP -> Agency -> Vendor Sankey. Every position comes from
 * sankey-layout.ts: one SVG draws the bars and bands, and the label boxes are HTML
 * at the same coordinates, so a name cannot drift away from its money.
 */
export function SankeyChart({ graph }: { graph: FundFlowGraph }) {
  if (graph.nodes.length === 0) {
    return (
      <DotCanvas className={styles.empty}>
        <p className={styles.emptyTitle}>{s.empty}</p>
        <p className={styles.emptyBody}>{s.empty_body}</p>
      </DotCanvas>
    );
  }
  return <Chart graph={graph} />;
}

// Split from SankeyChart so the measuring effect mounts together with the element it measures.
function Chart({ graph }: { graph: FundFlowGraph }) {
  const frame = useRef<HTMLDivElement>(null);
  const plot = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(DEFAULT_WIDTH);
  const [focus, setFocus] = useState<Focus>(null);
  const [tip, setTip] = useState<Tip | null>(null);

  useEffect(() => {
    const element = frame.current;
    if (!element || typeof ResizeObserver === "undefined") return;
    const watch = new ResizeObserver(([entry]) => setWidth(entry.contentRect.width));
    watch.observe(element);
    return () => watch.disconnect();
  }, []);

  const layout = useMemo(() => buildSankeyLayout(graph, width), [graph, width]);
  const drawn = useMemo(
    () => [...layout.links].sort((a, b) => TIER_RANK[a.tier] - TIER_RANK[b.tier]),
    [layout.links],
  );
  // A different set of vendors is a different picture: remount the SVG so its reveal plays again.
  const revealKey = layout.nodes
    .filter((n) => n.type === "Vendor")
    .map((n) => n.id)
    .join("|");

  const stateOf = (link: SankeyLink) => {
    if (!focus) return undefined;
    const on = focus.kind === "link" ? focus.id === link.id : link.source === focus.id || link.target === focus.id;
    return on ? "on" : "dim";
  };
  const showTip = (link: SankeyLink, event: PointerEvent) => {
    const box = plot.current?.getBoundingClientRect();
    if (!box) return;
    setFocus({ kind: "link", id: link.id });
    setTip({ link, x: event.clientX - box.left, y: event.clientY - box.top });
  };
  const clear = () => {
    setFocus(null);
    setTip(null);
  };

  return (
    <div className={styles.chart}>
      <div className={styles.scroller}>
        <div ref={frame} className={styles.frame} style={{ minWidth: MIN_WIDTH }}>
          <div className={styles.headings}>
            {layout.columns.map((column) => (
              <h3 key={column.type} className={styles.heading} style={{ left: column.x }}>
                {headingOf(column)}
              </h3>
            ))}
          </div>

          <div ref={plot} className={styles.plot} style={{ height: layout.height }}>
            {layout.nodes.map((node) => (
              <NodeBox
                key={node.id}
                node={node}
                onFocus={() => setFocus({ kind: "node", id: node.id })}
                onBlur={clear}
              />
            ))}

            <svg key={revealKey} className={styles.bands} width={layout.width} height={layout.height} aria-hidden="true">
              {drawn.map((link) => (
                <path
                  key={link.id}
                  d={link.d}
                  className={`${styles.band} ${TIER_CLASS[link.tier]}`}
                  data-tier={link.tier}
                  data-state={stateOf(link)}
                  onPointerEnter={(event) => showTip(link, event)}
                  onPointerMove={(event) => showTip(link, event)}
                  onPointerLeave={clear}
                />
              ))}
              {layout.nodes.map((node) => (
                <rect
                  key={node.id}
                  x={node.x}
                  y={node.barY}
                  width={BAR_WIDTH}
                  height={node.barHeight}
                  rx={2}
                  className={`${styles.bar} ${toneOf(node)}`}
                />
              ))}
            </svg>

            {tip && <Tooltip tip={tip} limit={layout.width} />}
          </div>
        </div>
      </div>

      {/* In a clipped wrapper: a table ignores width and overflow on itself, so a bare one would lay out at
          its natural width and make the whole page scroll sideways on a narrow screen. */}
      <div className="sr-only">
        <table>
          <caption>{s.flow_table_caption}</caption>
          <thead>
            <tr>
              <th scope="col">{s.flow_table_from}</th>
              <th scope="col">{s.flow_table_to}</th>
              <th scope="col">{s.flow_table_amount}</th>
              <th scope="col">{s.flow_table_works}</th>
              <th scope="col">{s.flow_table_flagged}</th>
            </tr>
          </thead>
          <tbody>
            {layout.links.map((link) => (
              <tr key={link.id}>
                <td>{link.sourceLabel}</td>
                <td>{link.targetLabel}</td>
                <td>{formatCurrencyFull(link.amount)}</td>
                <td>{formatIndianInt(link.workCount)}</td>
                <td>{formatIndianInt(link.flaggedCount)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className={styles.legend}>
        <ul className={styles.swatches}>
          <li>
            <span className={`${styles.swatch} ${styles.plain}`} aria-hidden="true" />
            {s.ribbon_legend_plain}
          </li>
          <li>
            <span className={`${styles.swatch} ${styles.elevated}`} aria-hidden="true" />
            {s.ribbon_legend_elevated}
          </li>
          <li>
            <span className={`${styles.swatch} ${styles.high}`} aria-hidden="true" />
            {s.ribbon_legend_high}
          </li>
        </ul>
        <p className={styles.note}>
          <Info size={16} aria-hidden="true" />
          {s.ribbon_info_note}
        </p>
      </div>
    </div>
  );
}

function NodeBox({ node, onFocus, onBlur }: { node: SankeyNode; onFocus: () => void; onBlur: () => void }) {
  const Glyph = node.type === "Agency" ? Bank : node.type === "Vendor" ? Briefcase : null;
  const amount = formatCurrency(node.amount);
  const detail =
    node.type === "Vendor"
      ? `${amount} · ${renderTemplate(s.works_count, { count: formatIndianInt(node.workCount) })}`
      : amount;
  return (
    <button
      type="button"
      className={`${styles.box} ${styles[`box${node.type}`]} ${toneOf(node)}`}
      style={{ left: node.x, top: node.y, width: node.width, height: node.height }}
      title={node.label}
      onPointerEnter={onFocus}
      onPointerLeave={onBlur}
      onFocus={onFocus}
      onBlur={onBlur}
    >
      {Glyph && !node.isMore && (
        <span className={styles.glyph} aria-hidden="true">
          <Glyph size={16} weight="fill" />
        </span>
      )}
      <span className={styles.text}>
        <span className={styles.name}>{node.label}</span>
        <span className={styles.amount}>{detail}</span>
      </span>
    </button>
  );
}

function Tooltip({ tip, limit }: { tip: Tip; limit: number }) {
  const { link } = tip;
  return (
    <div
      className={styles.tip}
      role="tooltip"
      style={{ left: Math.max(0, Math.min(tip.x + 14, limit - 260)), top: tip.y + 14 }}
    >
      <p className={styles.tipRoute}>
        {link.sourceLabel}
        <ArrowRight size={12} aria-hidden="true" />
        {link.targetLabel}
      </p>
      <p className={styles.tipLine}>
        {renderTemplate(s.edge_label, {
          work_count: formatIndianInt(link.workCount),
          amount: formatCurrencyFull(link.amount),
        })}
      </p>
      {link.flaggedCount > 0 && (
        <p className={styles.tipFlag}>
          {renderTemplate(s.cluster_risk_flag_note, {
            flagged: formatIndianInt(link.flaggedCount),
            total: formatIndianInt(link.workCount),
          })}
        </p>
      )}
    </div>
  );
}
