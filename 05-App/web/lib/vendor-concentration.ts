import type { FundFlowGraph, GraphEdge, GraphNode } from "./graph-data";

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
 * True when a and b share at least one element. Iterates the smaller set
 * first (a lightweight optimization, not load-bearing at today's scale) so
 * the check is at worst O(min(|a|, |b|)).
 */
function hasSharedWork(a: Set<string>, b: Set<string>): boolean {
  const [smaller, larger] = a.size <= b.size ? [a, b] : [b, a];
  for (const workId of smaller) {
    if (larger.has(workId)) return true;
  }
  return false;
}

/**
 * One entry per Vendor node in the graph, regardless of any threshold --
 * filtering by threshold is the caller's job (matchingVendors below), so
 * this stays the one place the two-hop walk happens.
 *
 * F-02 (nemotronreview.md), fixed 2026-09-14: an MP is credited to a vendor
 * only when a real work_id backs BOTH hops -- the MP's own edge into the
 * agency, and that agency's edge into the vendor. Before this fix, every MP
 * touching an agency was credited to every vendor that agency paid, whether
 * or not a single real work connected them; the audit measured this
 * false-path rate at 97.8%. Sharing only an agency, with no work in common,
 * is not a fund-flow path.
 */
export function allVendorConcentrations(graph: FundFlowGraph): VendorConcentration[] {
  const byId = new Map<string, GraphNode>(graph.nodes.map((n) => [n.id, n]));

  // agency id -> (MP id -> that MP's own work_ids into this agency).
  const mpWorkIdsOfAgency = new Map<string, Map<string, Set<string>>>();
  // vendor id -> every Agency -> Vendor edge into it. Built once, so each
  // vendor below reads only its own edges instead of rescanning the whole
  // edge list (F-17: the rescan was vendors x edges, about 437 million checks
  // on the rebuilt national graph).
  const agencyEdgesIntoVendor = new Map<string, GraphEdge[]>();
  for (const edge of graph.edges) {
    const source = byId.get(edge.source);
    const target = byId.get(edge.target);
    if (source?.type === "MP" && target?.type === "Agency") {
      const byMp = mpWorkIdsOfAgency.get(edge.target) ?? new Map<string, Set<string>>();
      byMp.set(edge.source, new Set(edge.work_ids));
      mpWorkIdsOfAgency.set(edge.target, byMp);
    } else if (source?.type === "Agency") {
      const into = agencyEdgesIntoVendor.get(edge.target) ?? [];
      into.push(edge);
      agencyEdgesIntoVendor.set(edge.target, into);
    }
  }

  const result: VendorConcentration[] = [];
  for (const vendor of graph.nodes) {
    if (vendor.type !== "Vendor") continue;
    const members = new Set<string>();
    let workCount = 0;
    let paidInr = 0;
    for (const edge of agencyEdgesIntoVendor.get(vendor.id) ?? []) {
      workCount += edge.work_count;
      paidInr += edge.total_amount_inr;

      const agencyVendorWorkIds = new Set(edge.work_ids);
      for (const [mpId, mpWorkIds] of mpWorkIdsOfAgency.get(edge.source) ?? []) {
        if (hasSharedWork(mpWorkIds, agencyVendorWorkIds)) members.add(mpId);
      }
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
 *
 * F-02, fixed 2026-09-14: an MP is kept only if a work_id it shares with
 * the agency is one of the SAME work_ids that agency used to reach one of
 * `vendorIds` -- not merely any MP touching an agency that happens to also
 * pay one of these vendors via unrelated works. Same false-path fix as
 * allVendorConcentrations above, applied to the highlighted subgraph
 * instead of the concentration count.
 */
export function subgraphFor(graph: FundFlowGraph, vendorIds: Set<string>): FundFlowGraph {
  const byId = new Map<string, GraphNode>(graph.nodes.map((n) => [n.id, n]));

  // agency id -> the union of work_ids on this agency's edges into any of
  // vendorIds specifically -- not every work_id touching the agency, which
  // would let an MP whose own work has nothing to do with these vendors
  // ride along on the agency's unrelated business.
  const relevantWorkIdsOfAgency = new Map<string, Set<string>>();
  for (const edge of graph.edges) {
    const source = byId.get(edge.source);
    if (source?.type === "Agency" && vendorIds.has(edge.target)) {
      const set = relevantWorkIdsOfAgency.get(edge.source) ?? new Set<string>();
      for (const workId of edge.work_ids) set.add(workId);
      relevantWorkIdsOfAgency.set(edge.source, set);
    }
  }
  const keepAgencies = new Set(relevantWorkIdsOfAgency.keys());

  const keepMps = new Set<string>();
  for (const edge of graph.edges) {
    const target = byId.get(edge.target);
    if (target?.type !== "Agency" || !keepAgencies.has(edge.target)) continue;
    const relevant = relevantWorkIdsOfAgency.get(edge.target) ?? new Set<string>();
    if (hasSharedWork(new Set(edge.work_ids), relevant)) keepMps.add(edge.source);
  }

  const keepNodes = new Set<string>([...vendorIds, ...keepAgencies, ...keepMps]);
  return {
    nodes: graph.nodes.filter((n) => keepNodes.has(n.id)),
    edges: graph.edges.filter((edge) => {
      if (!keepNodes.has(edge.source) || !keepNodes.has(edge.target)) return false;

      // A Member can survive because of a valid path through one agency,
      // while another kept agency has only an unrelated work from that same
      // Member. Filtering by endpoint alone would redraw that cross-branch
      // edge and visually recreate F-02's false path inside the subgraph.
      const source = byId.get(edge.source);
      const target = byId.get(edge.target);
      if (source?.type === "MP" && target?.type === "Agency") {
        const relevant = relevantWorkIdsOfAgency.get(edge.target);
        return relevant ? hasSharedWork(new Set(edge.work_ids), relevant) : false;
      }

      return true;
    }),
  };
}
