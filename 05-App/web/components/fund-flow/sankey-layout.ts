import { displayName, formatIndianInt } from "@/lib/format";
import type { FundFlowGraph, GraphNodeType } from "@/lib/graph-data";
import { renderTemplate, STRINGS } from "@/lib/strings";

const s = STRINGS.fund_flow;

/**
 * Pure layout for the three-column MP -> Agency -> Vendor Sankey. No React and no
 * DOM, so every position can be tested. SankeyChart.tsx draws exactly these
 * numbers: the bars and bands in one SVG, the label boxes as HTML at the same
 * coordinates, so a name can never drift away from its money.
 *
 * Width is money. One scale (px per rupee) serves both hops, and a band is that
 * many px thick, linear, so the bands leaving a node add up to the bar they
 * leave from. The single deviation is a floor for flows too thin to see.
 */

const COLUMNS: GraphNodeType[] = ["MP", "Agency", "Vendor"];

// Calibration constants. The maths below is fixed; these are what to tune
// against the reference.
export const MAX_ROWS = 7; // rows per column, the "+N more" row included
export const MIN_WIDTH = 720;
const TARGET_BAR_PX = 280; // the busiest column's bars, in total, when everything fits
const PLOT_MAX_PX = 460; // the tallest column (boxes and gaps) tries to stay under this
const MIN_BAR_PX = 160; // the busiest column's bars never get thinner than this, in total
const ROW_GAP = 10;
const MIN_BOX_PX: Record<GraphNodeType, number> = { MP: 44, Agency: 58, Vendor: 58 };
const MIN_BAND_PX = 1.5;
const BOX_WIDTH_RATIO = 0.21;
const BOX_WIDTH_MIN = 170;
const BOX_WIDTH_MAX = 250;
const RELAXATION_ROUNDS = 2;

export type SankeyTier = "plain" | "elevated" | "high";

export interface SankeyNode {
  id: string;
  type: GraphNodeType;
  label: string;
  isMore: boolean;
  /** Sanctioned rupees through this node: the larger of what arrives and what leaves. */
  amount: number;
  /** Works arriving at this node. The vendor box prints it. */
  workCount: number;
  /** The flagged share of the works arriving here. Colours the vendor box. */
  tier: SankeyTier;
  /** The label box. */
  x: number;
  y: number;
  width: number;
  height: number;
  /** The bar on the box's left edge, centred vertically in the box. */
  barY: number;
  barHeight: number;
}

export interface SankeyLink {
  id: string;
  source: string;
  target: string;
  sourceLabel: string;
  targetLabel: string;
  amount: number;
  workCount: number;
  flaggedCount: number;
  tier: SankeyTier;
  /** Band thickness in px. */
  width: number;
  /** The band's outline, for an SVG path. */
  d: string;
}

export interface SankeyColumn {
  type: GraphNodeType;
  /** Every node of this type in the graph, before "+N more" collapses any. */
  count: number;
  x: number;
  width: number;
}

export interface SankeyLayout {
  width: number;
  height: number;
  /** Pixels per rupee. */
  scale: number;
  columns: SankeyColumn[];
  nodes: SankeyNode[];
  links: SankeyLink[];
}

interface Flow {
  source: string;
  target: string;
  amount: number;
  workCount: number;
  flaggedCount: number;
}

interface Draft {
  id: string;
  type: GraphNodeType;
  label: string;
  isMore: boolean;
}

type Neighbours = Map<string, Array<{ id: string; weight: number }>>;

const byCode = (a: string, b: string) => (a < b ? -1 : a > b ? 1 : 0);
// Whole-pixel precision is noise in an SVG path; two decimals keep it short.
const px = (value: number) => Math.round(value * 100) / 100;

export function tierOf(flagged: number, works: number): SankeyTier {
  if (works <= 0 || flagged <= 0) return "plain";
  return flagged >= works ? "high" : "elevated";
}

/** MP -> Agency and Agency -> Vendor edges only, in a fixed order so that summing them never depends on input order. */
function readFlows(graph: FundFlowGraph): Flow[] {
  const typeOf = new Map(graph.nodes.map((n) => [n.id, n.type]));
  const flows: Flow[] = [];
  for (const edge of graph.edges) {
    const from = typeOf.get(edge.source);
    const to = typeOf.get(edge.target);
    if (!from || !to || COLUMNS.indexOf(to) !== COLUMNS.indexOf(from) + 1) continue;
    flows.push({
      source: edge.source,
      target: edge.target,
      amount: Math.max(0, edge.total_amount_inr),
      workCount: edge.work_count,
      flaggedCount: edge.flagged_work_count,
    });
  }
  return flows.sort((a, b) => byCode(a.source, b.source) || byCode(a.target, b.target));
}

function groupBy(flows: Flow[], key: (f: Flow) => string): Map<string, Flow[]> {
  const groups = new Map<string, Flow[]>();
  for (const f of flows) {
    const list = groups.get(key(f));
    if (list) list.push(f);
    else groups.set(key(f), [f]);
  }
  return groups;
}

function throughput(flows: Flow[]) {
  const inflow = new Map<string, number>();
  const outflow = new Map<string, number>();
  for (const f of flows) {
    outflow.set(f.source, (outflow.get(f.source) ?? 0) + f.amount);
    inflow.set(f.target, (inflow.get(f.target) ?? 0) + f.amount);
  }
  return { inflow, outflow };
}

function foldFlows(flows: Flow[], fold: Map<string, string>): Flow[] {
  const merged = new Map<string, Flow>();
  for (const f of flows) {
    const source = fold.get(f.source) ?? f.source;
    const target = fold.get(f.target) ?? f.target;
    const key = `${source}\u0000${target}`;
    const into = merged.get(key);
    if (into) {
      into.amount += f.amount;
      into.workCount += f.workCount;
      into.flaggedCount += f.flaggedCount;
    } else {
      merged.set(key, { source, target, amount: f.amount, workCount: f.workCount, flaggedCount: f.flaggedCount });
    }
  }
  return [...merged.values()];
}

/** Largest first, the six biggest kept and the rest folded into one "+N more" node per column. */
function collapse(graph: FundFlowGraph, flows: Flow[]) {
  const { inflow, outflow } = throughput(flows);
  const fold = new Map<string, string>();
  const counts = {} as Record<GraphNodeType, number>;
  const columns = {} as Record<GraphNodeType, Draft[]>;
  for (const type of COLUMNS) {
    const sorted = graph.nodes
      .filter((n) => n.type === type)
      .map((n) => ({ id: n.id, label: displayName(n.label), value: Math.max(inflow.get(n.id) ?? 0, outflow.get(n.id) ?? 0) }))
      .sort((a, b) => b.value - a.value || byCode(a.label, b.label) || byCode(a.id, b.id));
    counts[type] = sorted.length;
    const shown = sorted.length > MAX_ROWS ? sorted.slice(0, MAX_ROWS - 1) : sorted;
    const folded = sorted.slice(shown.length);
    columns[type] = shown.map(({ id, label }) => ({ id, type, label, isMore: false }));
    if (folded.length > 0) {
      const id = `more:${type}`;
      for (const d of folded) fold.set(d.id, id);
      const label = renderTemplate(s.ribbon_more_note, { count: formatIndianInt(folded.length) });
      columns[type].push({ id, type, label, isMore: true });
    }
  }
  return { counts, columns, flows: fold.size > 0 ? foldFlows(flows, fold) : flows };
}

function neighbours(flows: Flow[]) {
  const feeders: Neighbours = new Map();
  const sinks: Neighbours = new Map();
  const add = (map: Neighbours, key: string, id: string, weight: number) => {
    const list = map.get(key);
    if (list) list.push({ id, weight });
    else map.set(key, [{ id, weight }]);
  };
  for (const f of flows) {
    // +1 so a flow with no recorded amount still pulls on its neighbours.
    add(feeders, f.target, f.source, f.amount + 1);
    add(sinks, f.source, f.target, f.amount + 1);
  }
  return { feeders, sinks };
}

/** One barycenter pass: each node moves to the money-weighted average row of the nodes it trades with. Ties keep their order. */
function sweep(column: Draft[], against: Draft[], links: Neighbours): Draft[] {
  const row = new Map(against.map((d, i) => [d.id, i]));
  const score = (d: Draft) => {
    let sum = 0;
    let weight = 0;
    for (const n of links.get(d.id) ?? []) {
      const at = row.get(n.id);
      if (at !== undefined) {
        sum += at * n.weight;
        weight += n.weight;
      }
    }
    return weight > 0 ? sum / weight : Infinity;
  };
  const scored = column.filter((d) => !d.isMore).map((d) => ({ d, at: score(d) }));
  scored.sort((a, b) => (a.at === b.at ? 0 : a.at < b.at ? -1 : 1));
  return [...scored.map((x) => x.d), ...column.filter((d) => d.isMore)];
}

export function buildSankeyLayout(graph: FundFlowGraph, chartWidth: number): SankeyLayout {
  const collapsed = collapse(graph, readFlows(graph));
  const { flows, counts } = collapsed;
  const { feeders, sinks } = neighbours(flows);

  let { MP: mp, Agency: agency, Vendor: vendor } = collapsed.columns;
  for (let round = 0; round < RELAXATION_ROUNDS; round++) {
    agency = sweep(agency, mp, feeders);
    vendor = sweep(vendor, agency, feeders);
    agency = sweep(agency, vendor, sinks);
    mp = sweep(mp, agency, sinks);
  }
  const order = { MP: mp, Agency: agency, Vendor: vendor };

  // What each node moves, by direction, and the scale that turns it into pixels.
  const { inflow, outflow } = throughput(flows);
  const into = groupBy(flows, (f) => f.target);
  const outOf = groupBy(flows, (f) => f.source);
  const amountOf = (id: string) => Math.max(inflow.get(id) ?? 0, outflow.get(id) ?? 0);
  const band = (amount: number, k: number) => Math.max(amount * k, MIN_BAND_PX);
  const barPx = (id: string, k: number) =>
    Math.max(
      (into.get(id) ?? []).reduce((sum, f) => sum + band(f.amount, k), 0),
      (outOf.get(id) ?? []).reduce((sum, f) => sum + band(f.amount, k), 0),
    );
  const boxPx = (d: Draft, k: number) => Math.max(barPx(d.id, k), MIN_BOX_PX[d.type]);
  const columnPx = (col: Draft[], k: number) =>
    col.reduce((sum, d) => sum + boxPx(d, k), 0) + ROW_GAP * Math.max(0, col.length - 1);
  const tallest = (k: number) => Math.max(...COLUMNS.map((t) => columnPx(order[t], k)));

  const busiest = Math.max(...COLUMNS.map((t) => order[t].reduce((sum, d) => sum + amountOf(d.id), 0)));
  let scale = 0;
  if (busiest > 0) {
    const target = TARGET_BAR_PX / busiest;
    let fit = target;
    if (tallest(target) > PLOT_MAX_PX) {
      let lo = 0;
      let hi = target;
      for (let i = 0; i < 40; i++) {
        const mid = (lo + hi) / 2;
        if (tallest(mid) <= PLOT_MAX_PX) lo = mid;
        else hi = mid;
      }
      fit = lo;
    }
    scale = Math.max(MIN_BAR_PX / busiest, fit);
  }

  // Boxes: columns centred vertically in a plot as tall as the tallest column.
  const width = Math.max(MIN_WIDTH, chartWidth);
  const boxWidth = Math.min(BOX_WIDTH_MAX, Math.max(BOX_WIDTH_MIN, width * BOX_WIDTH_RATIO));
  const gutter = (width - COLUMNS.length * boxWidth) / (COLUMNS.length - 1);
  const height = tallest(scale);
  const nodes: SankeyNode[] = [];
  COLUMNS.forEach((type, c) => {
    let y = (height - columnPx(order[type], scale)) / 2;
    for (const d of order[type]) {
      const bar = barPx(d.id, scale);
      const boxHeight = Math.max(bar, MIN_BOX_PX[type]);
      const arriving = into.get(d.id) ?? [];
      const works = arriving.reduce((sum, f) => sum + f.workCount, 0);
      const flagged = arriving.reduce((sum, f) => sum + f.flaggedCount, 0);
      nodes.push({
        id: d.id,
        type,
        label: d.label,
        isMore: d.isMore,
        amount: amountOf(d.id),
        workCount: works,
        tier: tierOf(flagged, works),
        x: c * (boxWidth + gutter),
        y,
        width: boxWidth,
        height: boxHeight,
        barY: y + (boxHeight - bar) / 2,
        barHeight: bar,
      });
      y += boxHeight + ROW_GAP;
    }
  });

  // Every flow joins two placed nodes, so these lookups cannot miss.
  const placed = new Map(nodes.map((n) => [n.id, n]));
  const at = (id: string) => placed.get(id)!;
  const centre = (id: string) => at(id).y + at(id).height / 2;

  // Bands stack down each bar in the order of the node at their other end, so none cross at a node.
  const above = (end: "source" | "target") => (a: Flow, b: Flow) =>
    centre(a[end]) - centre(b[end]) || byCode(a[end], b[end]);
  const leaves = new Map<Flow, number>();
  const arrives = new Map<Flow, number>();
  const stack = (n: SankeyNode, flows: Flow[], end: "source" | "target", tops: Map<Flow, number>) => {
    let y = n.barY;
    for (const f of [...flows].sort(above(end))) {
      tops.set(f, y);
      y += band(f.amount, scale);
    }
  };
  for (const n of nodes) {
    stack(n, outOf.get(n.id) ?? [], "target", leaves);
    stack(n, into.get(n.id) ?? [], "source", arrives);
  }

  const links: SankeyLink[] = [];
  for (const n of nodes) {
    for (const f of [...(outOf.get(n.id) ?? [])].sort(above("target"))) {
      const to = at(f.target);
      const thick = band(f.amount, scale);
      const x0 = n.x + n.width;
      const x1 = to.x;
      const xm = (x0 + x1) / 2;
      const y0 = leaves.get(f) ?? n.barY;
      const y1 = arrives.get(f) ?? to.barY;
      links.push({
        id: `${f.source}->${f.target}`,
        source: f.source,
        target: f.target,
        sourceLabel: n.label,
        targetLabel: to.label,
        amount: f.amount,
        workCount: f.workCount,
        flaggedCount: f.flaggedCount,
        tier: tierOf(f.flaggedCount, f.workCount),
        width: thick,
        d:
          `M${px(x0)},${px(y0)} C${px(xm)},${px(y0)} ${px(xm)},${px(y1)} ${px(x1)},${px(y1)} ` +
          `L${px(x1)},${px(y1 + thick)} C${px(xm)},${px(y1 + thick)} ${px(xm)},${px(y0 + thick)} ${px(x0)},${px(y0 + thick)} Z`,
      });
    }
  }

  return {
    width,
    height,
    scale,
    columns: COLUMNS.map((type, c) => ({ type, count: counts[type], x: c * (boxWidth + gutter), width: boxWidth })),
    nodes,
    links,
  };
}
