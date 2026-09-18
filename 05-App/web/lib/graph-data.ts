import { fetchEnvelopeWithMeta } from "./api-client";

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
