import type { FundFlowGraph, GraphNode } from "./graph-data";

/**
 * Vendor concentration: how many distinct Members of Parliament, through
 * however many agencies, ultimately pay a given vendor. New 2026-09-03,
 * reference-fidelity pass -- the reference's Fund Flow view has a live
 * "minimum Members per vendor" filter and a "cluster in focus" panel;
 * this module is the pure computation behind both, kept apart from the
 * components so it can be reasoned about (and tested) without React.
 *
 * fund_flow_graph.schema.json's edges are MP -> Agency and Agency ->
 * Vendor, flat in one array with no notion of a path -- reachability has
 * to be walked in two hops, not read off a single edge.
 *
 * What this deliberately does NOT compute, and why: the reference's mockup
 * also shows a "Districts" count per vendor, distinct from "Members".
 * build_graph.py's own docstring says why that is not available here: "the
 * graph carries no separate district node -- an MP's constituency stands
 * in for district here," and MP nodes are keyed by mp_name, not
 * constituency (one node per distinct MP, not per distinct district).
 * Inventing a Districts figure would mean either fabricating a field that
 * does not exist or quietly redefining it as something else and labelling
 * it the same -- both are exactly the mistake this project's Logbook
 * already caught once today with the PPT's fabricated flag types. Left
 * out; a real Districts figure would need the inspection list's own rows
 * (which do carry constituency) joined in by mp_name, which is a real
 * option for later, not attempted in this pass.
 */

export interface VendorConcentration {
  vendorId: string;
  vendorLabel: string;
  /** Distinct MPs reachable via any agency this vendor is paid through. */
  memberCount: number;
  /** Sum of work_count across every Agency -> Vendor edge into this vendor. */
  workCount: number;
  /** Sum of total_amount_inr across the same edges. */
  paidInr: number;
}

/**
 * One entry per Vendor node in the graph, regardless of any threshold --
 * filtering by threshold is the caller's job (matchingVendors below), so
 * this stays the one place the two-hop walk happens.
 */
export function allVendorConcentrations(graph: FundFlowGraph): VendorConcentration[] {
  const byId = new Map<string, GraphNode>(graph.nodes.map((n) => [n.id, n]));

  // agency id -> set of MP ids with a direct MP -> Agency edge into it.
  const mpsOfAgency = new Map<string, Set<string>>();
  for (const edge of graph.edges) {
    const source = byId.get(edge.source);
    const target = byId.get(edge.target);
    if (source?.type === "MP" && target?.type === "Agency") {
      const set = mpsOfAgency.get(edge.target) ?? new Set<string>();
      set.add(edge.source);
      mpsOfAgency.set(edge.target, set);
    }
  }

  const result: VendorConcentration[] = [];
  for (const vendor of graph.nodes) {
    if (vendor.type !== "Vendor") continue;
    const members = new Set<string>();
    let workCount = 0;
    let paidInr = 0;
    for (const edge of graph.edges) {
      const source = byId.get(edge.source);
      if (source?.type !== "Agency" || edge.target !== vendor.id) continue;
      workCount += edge.work_count;
      paidInr += edge.total_amount_inr;
      for (const mpId of mpsOfAgency.get(edge.source) ?? []) members.add(mpId);
    }
    result.push({ vendorId: vendor.id, vendorLabel: vendor.label, memberCount: members.size, workCount, paidInr });
  }
  return result;
}

/** Vendors meeting `threshold`, ranked by member count descending -- the
 *  reference's own ordering ("6 of 214 vendors... match"), ties broken by
 *  label so the ranking is stable rather than depending on node order. */
export function matchingVendors(all: VendorConcentration[], threshold: number): VendorConcentration[] {
  return all
    .filter((v) => v.memberCount >= threshold)
    .sort((a, b) => b.memberCount - a.memberCount || a.vendorLabel.localeCompare(b.vendorLabel));
}

/** The middle value of a non-empty list of member counts, for "the median
 *  vendor in this filter is paid on works from {n} Member(s)". Even-length
 *  lists average their two middle values, then round -- a fractional
 *  Member count has no honest meaning here. */
export function medianMemberCount(vendors: VendorConcentration[]): number {
  if (vendors.length === 0) return 0;
  const sorted = [...vendors].map((v) => v.memberCount).sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  const median = sorted.length % 2 === 0 ? (sorted[mid - 1] + sorted[mid]) / 2 : sorted[mid];
  return Math.round(median);
}

/**
 * The node ids on the path into a single vendor: itself, every agency
 * with a direct edge into it, and every MP with a direct edge into one of
 * those agencies. Used to colour the "cluster in focus" vendor's own path
 * distinctly from the rest of a multi-vendor filtered view -- the same
 * reachability walk as subgraphFor below, but returning node ids for one
 * vendor rather than filtering the graph for a whole set.
 */
export function highlightedNodeIds(graph: FundFlowGraph, vendorId: string): Set<string> {
  const subgraph = subgraphFor(graph, new Set([vendorId]));
  return new Set(subgraph.nodes.map((n) => n.id));
}

/**
 * The subgraph reachable from `vendorIds`: those vendors, every agency
 * with a direct edge into one of them, and every MP with a direct edge
 * into one of those agencies. "Everything else is held back so the
 * cluster reads" (reference copy) -- this is that holding-back, applied
 * to the graph data itself rather than dimming nodes in place, so a
 * held-back MP or agency that happens to also feed a matching vendor via
 * a different path is correctly kept, not dropped.
 */
export function subgraphFor(graph: FundFlowGraph, vendorIds: Set<string>): FundFlowGraph {
  const byId = new Map<string, GraphNode>(graph.nodes.map((n) => [n.id, n]));
  const keepAgencies = new Set<string>();
  for (const edge of graph.edges) {
    const source = byId.get(edge.source);
    if (source?.type === "Agency" && vendorIds.has(edge.target)) keepAgencies.add(edge.source);
  }
  const keepMps = new Set<string>();
  for (const edge of graph.edges) {
    const target = byId.get(edge.target);
    if (target?.type === "Agency" && keepAgencies.has(edge.target)) keepMps.add(edge.source);
  }
  const keepNodes = new Set<string>([...vendorIds, ...keepAgencies, ...keepMps]);
  return {
    nodes: graph.nodes.filter((n) => keepNodes.has(n.id)),
    edges: graph.edges.filter((e) => keepNodes.has(e.source) && keepNodes.has(e.target)),
  };
}
