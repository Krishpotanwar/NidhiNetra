import { describe, expect, it } from "vitest";
import { graphTotals, realVendorId } from "./graph-data";
import type { FundFlowGraph } from "./graph-data";

function node(id: string, type: "MP" | "Agency" | "Vendor"): FundFlowGraph["nodes"][number] {
  return { id, type, label: id, risk_weight: 0 };
}

function edge(source: string, target: string, total_amount_inr: number): FundFlowGraph["edges"][number] {
  return { source, target, work_count: 1, total_amount_inr, flagged_work_count: 0, work_ids: ["W1"] };
}

describe("graphTotals", () => {
  it("counts nodes by type and sums only Agency -> Vendor edges, not MP -> Agency", () => {
    const graph: FundFlowGraph = {
      nodes: [node("mp-1", "MP"), node("agency-1", "Agency"), node("vendor-1", "Vendor")],
      edges: [edge("mp-1", "agency-1", 1_000_000), edge("agency-1", "vendor-1", 700_000)],
    };

    const totals = graphTotals(graph);

    expect(totals).toEqual({ flowInr: 700_000, mpCount: 1, agencyCount: 1, vendorCount: 1 });
  });
});

describe("realVendorId (inverse of build_graph.py's _vendor_node_id)", () => {
  it("strips the vendor_ prefix", () => {
    expect(realVendorId("vendor_10005")).toBe("10005");
  });

  it("percent-decodes a source id containing characters quote() would encode", () => {
    // Python's quote("V/01 #2", safe="") -> "V%2F01%20%232".
    expect(realVendorId("vendor_V%2F01%20%232")).toBe("V/01 #2");
  });

  it("passes through an id with no vendor_ prefix unchanged", () => {
    expect(realVendorId("10005")).toBe("10005");
  });
});
