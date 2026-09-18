import { fetchEnvelopeWithMeta } from "./api-client";
import type { VendorConcentration } from "./vendor-concentration";

export type GraphNodeType = "MP" | "Agency" | "Vendor";

export interface GraphNode {
  id: string;
  type: GraphNodeType;
  label: string;
  risk_weight: number;
}

export interface GraphEdge {
  source: string;
  target: string;
  work_count: number;
  total_amount_inr: number;
  flagged_work_count: number;
  /**
   * Every real work_id backing this edge (F-02, fixed 2026-09-14). Adjacency
   * between an MP->Agency edge and an Agency->Vendor edge is NOT evidence of
   * a real fund-flow path -- only a work_id shared by both edges' work_ids
   * is. See vendor-concentration.ts, the one place that two-hop walk happens.
   */
  work_ids: string[];
}

export interface FundFlowGraph {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

const VENDOR_NODE_PREFIX = "vendor_";

/**
 * Recovers the real works.vendor_id from a Vendor node's graph id.
 * build_graph.py's `_vendor_node_id` encodes it as `vendor_` + percent-
 * encoding (`urllib.parse.quote(vendor_id, safe="")`) precisely so the node
 * id and the source identifier are never confused for each other; this is
 * that encoding's inverse, for the one place (linking to the Inspection
 * List's vendor_id filter) that needs the source identifier back.
 */
export function realVendorId(vendorNodeId: string): string {
  const encoded = vendorNodeId.startsWith(VENDOR_NODE_PREFIX)
    ? vendorNodeId.slice(VENDOR_NODE_PREFIX.length)
    : vendorNodeId;
  try {
    return decodeURIComponent(encoded);
  } catch {
    return encoded;
  }
}

export interface GraphTotals {
  flowInr: number;
  mpCount: number;
  agencyCount: number;
  vendorCount: number;
}

/**
 * Whole-graph totals for the page's stat-tile row. `flowInr` sums only the
 * Agency -> Vendor edges (the same tier vendor-concentration.ts's own
 * `paidInr` sums for one vendor) -- summing every edge, MP -> Agency
 * included, would double-count the same sanctioned works once for the
 * MP's recommendation and again for the agency's payment.
 */
export function graphTotals(graph: FundFlowGraph): GraphTotals {
  const byId = new Map<string, GraphNode>(graph.nodes.map((n) => [n.id, n]));
  let mpCount = 0;
  let agencyCount = 0;
  let vendorCount = 0;
  for (const node of graph.nodes) {
    if (node.type === "MP") mpCount++;
    else if (node.type === "Agency") agencyCount++;
    else vendorCount++;
  }
  const flowInr = graph.edges
    .filter((edge) => byId.get(edge.source)?.type === "Agency")
    .reduce((sum, edge) => sum + edge.total_amount_inr, 0);
  return { flowInr, mpCount, agencyCount, vendorCount };
}

/**
 * GET /api/graph's answer. `rebuildRequired` is true when the API holds back a
 * graph.json built before F-01 (its middle tier would be District Authorities
 * under the "Implementing agency" label) or before F-02 (edges without work
 * IDs cannot be checked for a real shared work). The API then sends an empty
 * graph with meta.graph_status = "rebuild_required".
 */
export interface FundFlowGraphResult {
  graph: FundFlowGraph;
  rebuildRequired: boolean;
}

/**
 * Wraps GET /api/graph, matching contracts/fund_flow_graph.schema.json.
 * agency/vendor filter by node label, matching the query params
 * contracts/openapi.yaml declares for this endpoint.
 */
export async function fetchFundFlowGraph(
  filter?: { agency?: string; vendor?: string },
  signal?: AbortSignal,
): Promise<FundFlowGraphResult> {
  const params = new URLSearchParams();
  if (filter?.agency) params.set("agency", filter.agency);
  if (filter?.vendor) params.set("vendor", filter.vendor);
  const qs = params.toString();
  const result = await fetchEnvelopeWithMeta<FundFlowGraph>(`/api/graph${qs ? `?${qs}` : ""}`, {
    signal,
  });
  return { graph: result.data, rebuildRequired: result.meta?.graph_status === "rebuild_required" };
}

interface RawVendorConcentration {
  vendor_id: string;
  vendor_label: string;
  member_count: number;
  agency_count: number;
  work_count: number;
  sanctioned_inr: number;
  flagged_work_count: number;
}

interface RawGraphTotals {
  flow_inr: number;
  mp_count: number;
  agency_count: number;
  vendor_count: number;
}

interface RawConcentrationsResponse {
  vendors: RawVendorConcentration[];
  matching_count: number;
  total_vendor_count: number;
  median_member_count: number;
  totals: RawGraphTotals | null;
}

function toVendorConcentration(raw: RawVendorConcentration): VendorConcentration {
  return {
    vendorId: raw.vendor_id,
    vendorLabel: raw.vendor_label,
    memberCount: raw.member_count,
    agencyCount: raw.agency_count,
    workCount: raw.work_count,
    paidInr: raw.sanctioned_inr,
    flaggedWorkCount: raw.flagged_work_count,
  };
}

function toGraphTotals(raw: RawGraphTotals): GraphTotals {
  return {
    flowInr: raw.flow_inr,
    mpCount: raw.mp_count,
    agencyCount: raw.agency_count,
    vendorCount: raw.vendor_count,
  };
}

export interface VendorConcentrationsResult {
  vendors: VendorConcentration[];
  matchingCount: number;
  totalVendorCount: number;
  medianMemberCount: number;
  totals: GraphTotals | null;
  rebuildRequired: boolean;
}

/**
 * GET /api/graph/concentrations (T17/F-17b): the server-ranked top vendors,
 * plus the whole-graph totals the stat tiles need, so the non-deep-link
 * Fund Flow view no longer downloads the national graph just to rank
 * vendors and sum totals. `limit` is deliberately requested at the
 * endpoint's own maximum (100), not the 25 actually displayed -- FundFlowClient's
 * own text search filters vendor names client-side over whatever comes back,
 * and searching only the displayed 25 would make a real, more-concentrated
 * match outside the top 25 unfindable. This is the fixed design's own stated
 * bound, not a new server capability.
 */
export async function fetchVendorConcentrations(
  minMembers: number,
  limit: number,
  signal?: AbortSignal,
): Promise<VendorConcentrationsResult> {
  const params = new URLSearchParams({ min_members: String(minMembers), limit: String(limit) });
  const result = await fetchEnvelopeWithMeta<RawConcentrationsResponse>(
    `/api/graph/concentrations?${params.toString()}`,
    { signal },
  );
  return {
    vendors: result.data.vendors.map(toVendorConcentration),
    matchingCount: result.data.matching_count,
    totalVendorCount: result.data.total_vendor_count,
    medianMemberCount: result.data.median_member_count,
    totals: result.data.totals ? toGraphTotals(result.data.totals) : null,
    rebuildRequired: result.meta?.graph_status === "rebuild_required",
  };
}

/**
 * GET /api/graph/cluster (T17/F-17b): one vendor's own evidence-backed
 * subgraph, fetched on demand instead of narrowed client-side out of an
 * already-downloaded national graph.
 */
export async function fetchVendorCluster(vendorId: string, signal?: AbortSignal): Promise<FundFlowGraphResult> {
  const params = new URLSearchParams({ vendor_id: vendorId });
  const result = await fetchEnvelopeWithMeta<FundFlowGraph>(`/api/graph/cluster?${params.toString()}`, { signal });
  return { graph: result.data, rebuildRequired: result.meta?.graph_status === "rebuild_required" };
}
