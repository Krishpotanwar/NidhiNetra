import { describe, expect, it } from "vitest";
import type { FundFlowGraph } from "./graph-data";
import { allVendorConcentrations, subgraphFor } from "./vendor-concentration";

function node(id: string, type: "MP" | "Agency" | "Vendor", label = id): FundFlowGraph["nodes"][number] {
  return { id, type, label, risk_weight: 0 };
}

function edge(
  source: string,
  target: string,
  work_ids: string[],
): FundFlowGraph["edges"][number] {
  return { source, target, work_count: work_ids.length, total_amount_inr: 0, flagged_work_count: 0, work_ids };
}

describe("allVendorConcentrations (F-02: two unrelated works sharing only an agency cannot form a path)", () => {
  it("does not credit an MP to a vendor when they share only an agency, not a work", () => {
    // MP A funds Shared Agency via W1. MP B funds Shared Agency via W2, a
    // completely different work. Shared Agency pays V1, but ONLY via W1.
    // There is no real path from MP B to V1 -- W2 never touched V1 -- even
    // though MP B and V1 both connect to Shared Agency.
    const graph: FundFlowGraph = {
      nodes: [node("mp_a", "MP"), node("mp_b", "MP"), node("agency_shared", "Agency"), node("vendor_v1", "Vendor")],
      edges: [
        edge("mp_a", "agency_shared", ["W1"]),
        edge("mp_b", "agency_shared", ["W2"]),
        edge("agency_shared", "vendor_v1", ["W1"]),
      ],
    };

    const [v1] = allVendorConcentrations(graph).filter((v) => v.vendorId === "vendor_v1");

    expect(v1.memberCount).toBe(1);
  });

  it("does credit an MP to a vendor when a real work_id backs both hops", () => {
    const graph: FundFlowGraph = {
      nodes: [node("mp_a", "MP"), node("agency_shared", "Agency"), node("vendor_v1", "Vendor")],
      edges: [edge("mp_a", "agency_shared", ["W1"]), edge("agency_shared", "vendor_v1", ["W1"])],
    };

    const [v1] = allVendorConcentrations(graph);

    expect(v1.memberCount).toBe(1);
  });

  it("credits each qualifying MP independently when several works legitimately share a vendor", () => {
    // W1 (MP A) and W2 (MP B) are different works, but BOTH happen to pay
    // V1 through Shared Agency -- a real, evidence-backed concentration of
    // two members, not the pre-fix bug of crediting everyone on the agency.
    const graph: FundFlowGraph = {
      nodes: [node("mp_a", "MP"), node("mp_b", "MP"), node("agency_shared", "Agency"), node("vendor_v1", "Vendor")],
      edges: [
        edge("mp_a", "agency_shared", ["W1"]),
        edge("mp_b", "agency_shared", ["W2"]),
        edge("agency_shared", "vendor_v1", ["W1", "W2"]),
      ],
    };

    const [v1] = allVendorConcentrations(graph);

    expect(v1.memberCount).toBe(2);
  });

  it("still sums workCount and paidInr over every Agency->Vendor edge regardless of the member fix", () => {
    const graph: FundFlowGraph = {
      nodes: [node("mp_a", "MP"), node("agency_shared", "Agency"), node("vendor_v1", "Vendor")],
      edges: [
        { ...edge("mp_a", "agency_shared", ["W1"]) },
        { ...edge("agency_shared", "vendor_v1", ["W1"]), work_count: 1, total_amount_inr: 500_000 },
      ],
    };

    const [v1] = allVendorConcentrations(graph);

    expect(v1.workCount).toBe(1);
    expect(v1.paidInr).toBe(500_000);
  });
});

describe("subgraphFor (F-02: the highlighted cluster must not include an unrelated MP)", () => {
  it("excludes an MP that shares only the agency with the target vendor, not a work", () => {
    const graph: FundFlowGraph = {
      nodes: [node("mp_a", "MP"), node("mp_b", "MP"), node("agency_shared", "Agency"), node("vendor_v1", "Vendor")],
      edges: [
        edge("mp_a", "agency_shared", ["W1"]),
        edge("mp_b", "agency_shared", ["W2"]),
        edge("agency_shared", "vendor_v1", ["W1"]),
      ],
    };

    const sub = subgraphFor(graph, new Set(["vendor_v1"]));

    const keptIds = new Set(sub.nodes.map((n) => n.id));
    expect(keptIds.has("mp_a")).toBe(true);
    expect(keptIds.has("mp_b")).toBe(false);
    expect(keptIds.has("agency_shared")).toBe(true);
  });

  it("keeps an agency's other real vendor relationships out when only one vendor is targeted", () => {
    // Shared Agency pays both V1 (via W1, MP A) and V2 (via W3, MP C).
    // Targeting only V1 must not pull in MP C, who has nothing to do with
    // V1 even though both MPs route through the same agency.
    const graph: FundFlowGraph = {
      nodes: [
        node("mp_a", "MP"),
        node("mp_c", "MP"),
        node("agency_shared", "Agency"),
        node("vendor_v1", "Vendor"),
        node("vendor_v2", "Vendor"),
      ],
      edges: [
        edge("mp_a", "agency_shared", ["W1"]),
        edge("mp_c", "agency_shared", ["W3"]),
        edge("agency_shared", "vendor_v1", ["W1"]),
        edge("agency_shared", "vendor_v2", ["W3"]),
      ],
    };

    const sub = subgraphFor(graph, new Set(["vendor_v1"]));
    const keptIds = new Set(sub.nodes.map((n) => n.id));

    expect(keptIds.has("mp_a")).toBe(true);
    expect(keptIds.has("mp_c")).toBe(false);
    expect(keptIds.has("vendor_v2")).toBe(false);
  });

  it("excludes a cross-branch MP edge that has no work in common with the target vendor", () => {
    // MP A reaches V1 legitimately through Agency A on W1. Agency B also
    // reaches V1, but on W2; MP A's separate edge into Agency B is W3.
    // Keeping MP A because of its valid Agency A path must not make W3 look
    // like a second path to V1 merely because both endpoint nodes survive.
    const graph: FundFlowGraph = {
      nodes: [
        node("mp_a", "MP"),
        node("agency_a", "Agency"),
        node("agency_b", "Agency"),
        node("vendor_v1", "Vendor"),
      ],
      edges: [
        edge("mp_a", "agency_a", ["W1"]),
        edge("agency_a", "vendor_v1", ["W1"]),
        edge("mp_a", "agency_b", ["W3"]),
        edge("agency_b", "vendor_v1", ["W2"]),
      ],
    };

    const sub = subgraphFor(graph, new Set(["vendor_v1"]));

    expect(sub.edges).toContain(graph.edges[0]);
    expect(sub.edges).not.toContain(graph.edges[2]);
  });
});

describe("allVendorConcentrations at national scale (F-17)", () => {
  it("summarises a graph the size of the rebuilt snapshot in well under a second", () => {
    const MPS = 536;
    const AGENCIES = 5_856;
    const VENDORS = 17_455;
    const nodes: FundFlowGraph["nodes"] = [];
    const edges: FundFlowGraph["edges"] = [];
    for (let m = 0; m < MPS; m++) nodes.push(node(`mp_${m}`, "MP"));
    for (let a = 0; a < AGENCIES; a++) {
      nodes.push(node(`agency_${a}`, "Agency"));
      edges.push(edge(`mp_${a % MPS}`, `agency_${a}`, [`W${a}`]));
    }
    for (let v = 0; v < VENDORS; v++) {
      nodes.push(node(`vendor_${v}`, "Vendor"));
      edges.push(edge(`agency_${v % AGENCIES}`, `vendor_${v}`, [`W${v % AGENCIES}`]));
    }

    const started = performance.now();
    const result = allVendorConcentrations({ nodes, edges });
    const elapsed = performance.now() - started;

    expect(result).toHaveLength(VENDORS);
    expect(result.every((vendor) => vendor.memberCount === 1)).toBe(true);
    expect(elapsed).toBeLessThan(1000);
  });
});
