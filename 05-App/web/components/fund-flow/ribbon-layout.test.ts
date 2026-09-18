import { describe, expect, it } from "vitest";
import type { FundFlowGraph } from "@/lib/graph-data";
import { buildRibbonLayout, MAX_ROWS_PER_COLUMN, ROW_HEIGHT } from "./ribbon-layout";

function node(id: string, type: "MP" | "Agency" | "Vendor", label = id): FundFlowGraph["nodes"][number] {
  return { id, type, label, risk_weight: 0 };
}

function edge(
  source: string,
  target: string,
  overrides: Partial<FundFlowGraph["edges"][number]> = {},
): FundFlowGraph["edges"][number] {
  return {
    source,
    target,
    work_count: 1,
    total_amount_inr: 0,
    flagged_work_count: 0,
    work_ids: ["W1"],
    ...overrides,
  };
}

describe("buildRibbonLayout", () => {
  it("places rows top-down in label order at a fixed row height", () => {
    const graph: FundFlowGraph = {
      nodes: [node("mp_b", "MP", "Beta"), node("mp_a", "MP", "Alpha")],
      edges: [],
    };

    const layout = buildRibbonLayout(graph, undefined);

    expect(layout.columns.MP.rows.map((r) => r.label)).toEqual(["Alpha", "Beta"]);
    expect(layout.columns.MP.rows[0].y).toBe(ROW_HEIGHT / 2);
    expect(layout.columns.MP.rows[1].y).toBe(ROW_HEIGHT + ROW_HEIGHT / 2);
  });

  it("caps a column at MAX_ROWS_PER_COLUMN and reports the rest as overflow", () => {
    const nodes = Array.from({ length: MAX_ROWS_PER_COLUMN + 3 }, (_, i) => node(`mp_${i}`, "MP", `MP ${i}`));
    const graph: FundFlowGraph = { nodes, edges: [] };

    const layout = buildRibbonLayout(graph, undefined);

    expect(layout.columns.MP.rows).toHaveLength(MAX_ROWS_PER_COLUMN);
    expect(layout.columns.MP.overflowCount).toBe(3);
  });

  it("marks an edge into a collapsed row as undrawable rather than pointing nowhere", () => {
    const nodes = Array.from({ length: MAX_ROWS_PER_COLUMN + 1 }, (_, i) => node(`mp_${i}`, "MP", `MP ${i}`));
    nodes.push(node("agency_1", "Agency"));
    const overflowMpId = `mp_${MAX_ROWS_PER_COLUMN}`; // sorted last, so it's the one collapsed
    const graph: FundFlowGraph = { nodes, edges: [edge(overflowMpId, "agency_1")] };

    const layout = buildRibbonLayout(graph, undefined);

    expect(layout.mpAgencyRibbons).toHaveLength(0);
  });

  it("colours an edge by its real share of flagged works, not by cluster selection", () => {
    const graph: FundFlowGraph = {
      nodes: [
        node("agency_1", "Agency"),
        node("vendor_1", "Vendor"),
        node("vendor_2", "Vendor"),
        node("vendor_3", "Vendor"),
      ],
      edges: [
        edge("agency_1", "vendor_1", { work_count: 4, flagged_work_count: 4 }), // all flagged
        edge("agency_1", "vendor_2", { work_count: 4, flagged_work_count: 1 }), // some flagged
        edge("agency_1", "vendor_3", { work_count: 4, flagged_work_count: 0 }), // none flagged
      ],
    };

    const layout = buildRibbonLayout(graph, undefined);
    const stateFor = (id: string) => layout.agencyVendorRibbons.find((r) => r.id.startsWith(id))?.state;

    expect(stateFor("agency_1->vendor_1")).toBe("high");
    expect(stateFor("agency_1->vendor_2")).toBe("elevated");
    expect(stateFor("agency_1->vendor_3")).toBe("plain");
  });

  it("widens a ribbon with the sanctioned amount, not the work count", () => {
    const graph: FundFlowGraph = {
      nodes: [node("agency_1", "Agency"), node("vendor_1", "Vendor"), node("vendor_2", "Vendor")],
      edges: [
        // vendor_1's edge has far fewer works but a far larger sanctioned amount.
        edge("agency_1", "vendor_1", { work_count: 1, total_amount_inr: 50_00_00_000 }),
        edge("agency_1", "vendor_2", { work_count: 50, total_amount_inr: 10_000 }),
      ],
    };

    const layout = buildRibbonLayout(graph, undefined);
    const widthFor = (id: string) => layout.agencyVendorRibbons.find((r) => r.id.startsWith(id))?.strokeWidth ?? 0;

    expect(widthFor("agency_1->vendor_1")).toBeGreaterThan(widthFor("agency_1->vendor_2"));
  });

  it("normalises width across the whole layout, so the largest amount always reads widest", () => {
    const graph: FundFlowGraph = {
      nodes: [node("mp_1", "MP"), node("agency_1", "Agency"), node("vendor_1", "Vendor")],
      edges: [
        edge("mp_1", "agency_1", { total_amount_inr: 100 }),
        edge("agency_1", "vendor_1", { total_amount_inr: 100_000_000 }),
      ],
    };

    const layout = buildRibbonLayout(graph, undefined);

    expect(layout.agencyVendorRibbons[0].strokeWidth).toBeGreaterThan(layout.mpAgencyRibbons[0].strokeWidth);
  });

  it("marks only the vendor passed as highlightVendorId as selected", () => {
    const graph: FundFlowGraph = {
      nodes: [node("vendor_1", "Vendor"), node("vendor_2", "Vendor")],
      edges: [],
    };

    const layout = buildRibbonLayout(graph, "vendor_2");

    const byId = new Map(layout.columns.Vendor.rows.map((r) => [r.id, r.selected]));
    expect(byId.get("vendor_1")).toBe(false);
    expect(byId.get("vendor_2")).toBe(true);
  });

  it("sizes height off the tallest column's slots, including its own overflow row", () => {
    const nodes = [
      ...Array.from({ length: MAX_ROWS_PER_COLUMN + 2 }, (_, i) => node(`mp_${i}`, "MP", `MP ${i}`)),
      node("agency_1", "Agency"),
    ];
    const graph: FundFlowGraph = { nodes, edges: [] };

    const layout = buildRibbonLayout(graph, undefined);

    // MAX_ROWS_PER_COLUMN shown rows + one "+N more" slot.
    expect(layout.height).toBe((MAX_ROWS_PER_COLUMN + 1) * ROW_HEIGHT);
  });
});
