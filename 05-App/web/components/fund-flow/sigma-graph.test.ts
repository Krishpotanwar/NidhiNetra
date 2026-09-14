import { describe, expect, test } from "vitest";
import type { FundFlowGraph } from "@/lib/graph-data";
import { createSigmaElements, type GraphPalette } from "./sigma-graph";

const palette: GraphPalette = {
  ink: "#0f1b33",
  ink2: "#334262",
  hairline: "#e3e9ef",
  hairlineStrong: "#d3dce6",
  risk3: "#d4540f",
  risk4: "#c81e1e",
};

const graph: FundFlowGraph = {
  nodes: [
    { id: "mp-1", type: "MP", label: "MEMBER_ONE", risk_weight: 0 },
    { id: "agency-1", type: "Agency", label: "AGENCY_ONE", risk_weight: 5 },
    { id: "vendor-1", type: "Vendor", label: "VENDOR_ONE", risk_weight: 10 },
    { id: "vendor-2", type: "Vendor", label: "VENDOR_TWO", risk_weight: 0 },
  ],
  edges: [
    {
      source: "mp-1",
      target: "agency-1",
      work_count: 1,
      total_amount_inr: 1_000_000,
      flagged_work_count: 0,
      work_ids: ["WORK-1"],
    },
    {
      source: "agency-1",
      target: "vendor-1",
      work_count: 4,
      total_amount_inr: 1_000_000,
      flagged_work_count: 2,
      work_ids: ["WORK-1"],
    },
    {
      source: "agency-1",
      target: "vendor-2",
      work_count: 2,
      total_amount_inr: 500_000,
      flagged_work_count: 0,
      work_ids: ["WORK-2"],
    },
    {
      source: "agency-1",
      target: "missing-vendor",
      work_count: 1,
      total_amount_inr: 1,
      flagged_work_count: 0,
      work_ids: ["WORK-MISSING"],
    },
  ],
};

describe("createSigmaElements", () => {
  test("preserves the tiered layout and keeps every coordinate bounded", () => {
    const manyVendors = Array.from({ length: 1_000 }, (_, index) => ({
      id: `vendor-${index}`,
      type: "Vendor" as const,
      label: `Vendor ${index}`,
      risk_weight: 0,
    }));
    const elements = createSigmaElements(
      {
        nodes: [
          { id: "mp", type: "MP", label: "Member", risk_weight: 0 },
          { id: "agency", type: "Agency", label: "Agency", risk_weight: 0 },
          ...manyVendors,
        ],
        edges: [],
      },
      undefined,
      palette,
    );

    const mp = elements.nodes.find((node) => node.id === "mp");
    const agency = elements.nodes.find((node) => node.id === "agency");
    const vendors = elements.nodes.filter((node) => node.attributes.nodeType === "Vendor");
    expect(mp?.attributes.x).toBeLessThan(agency?.attributes.x ?? 0);
    expect(agency?.attributes.x).toBeLessThan(vendors[0].attributes.x);
    expect(elements.nodes.every((node) => node.attributes.y >= 0 && node.attributes.y <= 1)).toBe(true);
  });

  test("maps node risk, edge magnitude, labels, and evidence-backed highlighting", () => {
    const elements = createSigmaElements(graph, "vendor-1", palette);
    const byId = new Map(elements.nodes.map((node) => [node.id, node.attributes]));
    const edges = new Map(elements.edges.map((edge) => [edge.id, edge.attributes]));

    expect(byId.get("mp-1")).toMatchObject({
      label: "Member One",
      fullLabel: "Member One",
      size: 5,
      color: palette.risk4,
      visualState: "path",
    });
    expect(byId.get("agency-1")?.size).toBe(8.5);
    expect(byId.get("vendor-1")).toMatchObject({ size: 12, color: palette.risk4, visualState: "path" });
    expect(byId.get("vendor-2")).toMatchObject({
      color: "rgba(211, 220, 230, 0.35)",
      visualState: "plain",
      dimmed: true,
    });

    expect(edges.get("edge-0")).toMatchObject({ color: palette.risk4, visualState: "path" });
    expect(edges.get("edge-1")).toMatchObject({
      label: "4 works, ₹10,00,000 sanctioned",
      size: Math.min(7, 1.5 + Math.log2(5)),
      color: palette.risk4,
      visualState: "path",
    });
    expect(edges.get("edge-2")).toMatchObject({
      color: "rgba(211, 220, 230, 0.14)",
      dimmed: true,
    });
    expect(elements.edges).toHaveLength(3);
  });

  test("uses the flagged state when no path is focused", () => {
    const elements = createSigmaElements(graph, undefined, palette);
    const agency = elements.nodes.find((node) => node.id === "agency-1");
    const flaggedEdge = elements.edges.find((edge) => edge.id === "edge-1");

    expect(agency?.attributes).toMatchObject({ color: palette.risk3, visualState: "flagged", dimmed: false });
    expect(flaggedEdge?.attributes).toMatchObject({
      color: "rgba(212, 84, 15, 0.5)",
      visualState: "flagged",
      dimmed: false,
    });
  });

  test("does not highlight an endpoint-only cross-branch edge as evidence", () => {
    const crossBranchGraph: FundFlowGraph = {
      nodes: [
        { id: "mp", type: "MP", label: "Member", risk_weight: 0 },
        { id: "agency-a", type: "Agency", label: "Agency A", risk_weight: 0 },
        { id: "agency-b", type: "Agency", label: "Agency B", risk_weight: 0 },
        { id: "vendor", type: "Vendor", label: "Vendor", risk_weight: 0 },
      ],
      edges: [
        { ...graph.edges[0], source: "mp", target: "agency-a", work_ids: ["W1"] },
        { ...graph.edges[0], source: "agency-a", target: "vendor", work_ids: ["W1"] },
        { ...graph.edges[0], source: "mp", target: "agency-b", work_ids: ["W3"] },
        { ...graph.edges[0], source: "agency-b", target: "vendor", work_ids: ["W2"] },
      ],
    };

    const elements = createSigmaElements(crossBranchGraph, "vendor", palette);

    expect(elements.edges[0].attributes.visualState).toBe("path");
    expect(elements.edges[2].attributes).toMatchObject({ dimmed: true, visualState: "plain" });
  });
});
