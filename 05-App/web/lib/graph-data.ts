import { fetchEnvelope } from "./api-client";

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

/**
 * Wraps GET /api/graph, matching contracts/fund_flow_graph.schema.json.
 * agency/vendor filter by node label, matching the query params
 * contracts/openapi.yaml declares for this endpoint.
 */
export async function fetchFundFlowGraph(
  filter?: { agency?: string; vendor?: string },
  signal?: AbortSignal,
): Promise<FundFlowGraph> {
  const params = new URLSearchParams();
  if (filter?.agency) params.set("agency", filter.agency);
  if (filter?.vendor) params.set("vendor", filter.vendor);
  const qs = params.toString();
  return fetchEnvelope<FundFlowGraph>(`/api/graph${qs ? `?${qs}` : ""}`, { signal });
}
