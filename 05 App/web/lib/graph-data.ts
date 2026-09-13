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
