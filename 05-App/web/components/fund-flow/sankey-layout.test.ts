import { describe, expect, it } from "vitest";
import type { FundFlowGraph } from "@/lib/graph-data";
import { renderTemplate, STRINGS } from "@/lib/strings";
import { buildSankeyLayout, MAX_ROWS, MIN_WIDTH, tierOf, type SankeyLayout } from "./sankey-layout";

type Type = "MP" | "Agency" | "Vendor";

function node(id: string, type: Type, label = id): FundFlowGraph["nodes"][number] {
  return { id, type, label, risk_weight: 0 };
}

function edge(
  source: string,
  target: string,
  amount: number,
  overrides: Partial<FundFlowGraph["edges"][number]> = {},
): FundFlowGraph["edges"][number] {
  return {
    source,
    target,
    work_count: 1,
    total_amount_inr: amount,
    flagged_work_count: 0,
    work_ids: ["W1"],
    ...overrides,
  };
}

/** Two Members and two agencies, all paying one vendor: every agency balances. */
const balanced: FundFlowGraph = {
  nodes: [
    node("mp_a", "MP", "Member A"),
    node("mp_b", "MP", "Member B"),
    node("ag_x", "Agency", "Agency X"),
    node("ag_y", "Agency", "Agency Y"),
    node("v_1", "Vendor", "Vendor One"),
  ],
  edges: [
    edge("mp_a", "ag_x", 6_000_000),
    edge("mp_b", "ag_x", 4_000_000),
    edge("mp_b", "ag_y", 10_000_000),
    edge("ag_x", "v_1", 10_000_000),
    edge("ag_y", "v_1", 10_000_000),
  ],
};

const at = (layout: SankeyLayout, id: string) => {
  const found = layout.nodes.find((n) => n.id === id);
  if (!found) throw new Error(`no node ${id}`);
  return found;
};
const arriving = (layout: SankeyLayout, id: string) =>
  layout.links.filter((l) => l.target === id).reduce((sum, l) => sum + l.width, 0);
const leaving = (layout: SankeyLayout, id: string) =>
  layout.links.filter((l) => l.source === id).reduce((sum, l) => sum + l.width, 0);

/** A graph with `count` Members paying one agency that pays one vendor. */
function crowd(count: number): FundFlowGraph {
  const mps = Array.from({ length: count }, (_, i) => node(`mp_${i}`, "MP", `Member ${i}`));
  return {
    nodes: [...mps, node("ag_1", "Agency"), node("v_1", "Vendor")],
    edges: [
      ...mps.map((m, i) => edge(m.id, "ag_1", (i + 1) * 1_000_000, { flagged_work_count: i % 2 })),
      edge("ag_1", "v_1", (count * (count + 1) * 1_000_000) / 2),
    ],
  };
}

describe("buildSankeyLayout", () => {
  it("fills each bar with exactly the bands that leave and arrive", () => {
    const layout = buildSankeyLayout(balanced, 1100);

    for (const n of layout.nodes) {
      const larger = Math.max(arriving(layout, n.id), leaving(layout, n.id));
      expect(n.barHeight).toBeCloseTo(larger, 6);
      expect(arriving(layout, n.id)).toBeLessThanOrEqual(n.barHeight + 1e-6);
      expect(leaving(layout, n.id)).toBeLessThanOrEqual(n.barHeight + 1e-6);
    }
  });

  it("gives an agency equal sides when its money balances", () => {
    const layout = buildSankeyLayout(balanced, 1100);

    for (const id of ["ag_x", "ag_y"]) {
      expect(arriving(layout, id)).toBeCloseTo(leaving(layout, id), 6);
    }
  });

  it("keeps the bar as tall as the larger side when a deep link is unbalanced", () => {
    // 10 Cr reached the agency, but only 7 Cr of it went to a vendor on record.
    const graph: FundFlowGraph = {
      nodes: [node("mp_a", "MP"), node("ag_x", "Agency"), node("v_1", "Vendor")],
      edges: [edge("mp_a", "ag_x", 100_000_000), edge("ag_x", "v_1", 70_000_000)],
    };

    const layout = buildSankeyLayout(graph, 1100);
    const agency = at(layout, "ag_x");

    expect(agency.barHeight).toBeCloseTo(arriving(layout, "ag_x"), 6);
    expect(leaving(layout, "ag_x")).toBeCloseTo(agency.barHeight * 0.7, 6);
    expect(leaving(layout, "ag_x")).toBeLessThan(agency.barHeight);
  });

  it("folds everything past the sixth node into one '+N more' node that keeps its money", () => {
    const graph = crowd(12);

    const layout = buildSankeyLayout(graph, 1100);
    const members = layout.nodes.filter((n) => n.type === "MP");
    const more = members[members.length - 1];

    expect(members).toHaveLength(MAX_ROWS);
    expect(more.isMore).toBe(true);
    expect(more.label).toBe(renderTemplate(STRINGS.fund_flow.ribbon_more_note, { count: "6" }));
    // The six smallest MPs paid 1 to 6 million.
    expect(more.amount).toBe(21_000_000);
    expect(members.reduce((sum, n) => sum + n.amount, 0)).toBe(78_000_000);
    // Six kept links plus one merged link, carrying the folded works and flags.
    const intoAgency = layout.links.filter((l) => l.target === "ag_1");
    expect(intoAgency).toHaveLength(MAX_ROWS);
    const merged = intoAgency.find((l) => l.source === more.id);
    expect(merged?.amount).toBe(21_000_000);
    expect(merged?.workCount).toBe(6);
    expect(merged?.flaggedCount).toBe(3);
    // The heading still counts every Member.
    expect(layout.columns[0].count).toBe(12);
  });

  it("keeps the folded node last and does not fold a column of exactly seven", () => {
    const seven = buildSankeyLayout(crowd(MAX_ROWS), 1100);
    expect(seven.nodes.filter((n) => n.type === "MP").some((n) => n.isMore)).toBe(false);

    const eight = buildSankeyLayout(crowd(MAX_ROWS + 1), 1100);
    const members = eight.nodes.filter((n) => n.type === "MP");
    expect(members[members.length - 1].isMore).toBe(true);
    expect(members.slice(0, -1).some((n) => n.isMore)).toBe(false);
  });

  it("never overlaps two boxes in a column", () => {
    for (const graph of [balanced, crowd(3), crowd(12)]) {
      const layout = buildSankeyLayout(graph, 1100);
      for (const type of ["MP", "Agency", "Vendor"] as const) {
        const column = layout.nodes.filter((n) => n.type === type).sort((a, b) => a.y - b.y);
        column.slice(1).forEach((n, i) => expect(n.y).toBeGreaterThanOrEqual(column[i].y + column[i].height));
        for (const n of column) {
          expect(n.y).toBeGreaterThanOrEqual(0);
          expect(n.y + n.height).toBeLessThanOrEqual(layout.height + 1e-6);
        }
      }
    }
  });

  it("lays out the same graph the same way whatever order it arrives in", () => {
    const graph = crowd(12);
    // A fixed shuffle, so the test cannot flake.
    const shuffled: FundFlowGraph = {
      nodes: graph.nodes.map((_, i, all) => all[(i * 5 + 3) % all.length]),
      edges: graph.edges.map((_, i, all) => all[(i * 7 + 2) % all.length]),
    };
    expect(new Set(shuffled.nodes).size).toBe(graph.nodes.length);
    expect(new Set(shuffled.edges).size).toBe(graph.edges.length);

    expect(buildSankeyLayout(shuffled, 1100)).toEqual(buildSankeyLayout(graph, 1100));
  });

  it("makes a band's thickness linear in its amount", () => {
    const graph: FundFlowGraph = {
      nodes: [node("ag_1", "Agency"), node("v_1", "Vendor"), node("v_2", "Vendor")],
      edges: [edge("ag_1", "v_1", 10_000_000), edge("ag_1", "v_2", 30_000_000)],
    };

    const layout = buildSankeyLayout(graph, 1100);
    const width = (target: string) => layout.links.find((l) => l.target === target)?.width ?? 0;

    expect(width("v_2") / width("v_1")).toBeCloseTo(3, 6);
    expect(width("v_1")).toBeCloseTo(10_000_000 * layout.scale, 6);
  });

  it("draws a flow too thin to see as a hairline instead of dropping it", () => {
    const graph: FundFlowGraph = {
      nodes: [node("ag_1", "Agency"), node("v_1", "Vendor"), node("v_2", "Vendor")],
      edges: [edge("ag_1", "v_1", 100_000_000), edge("ag_1", "v_2", 1)],
    };

    const layout = buildSankeyLayout(graph, 1100);

    expect(layout.links.find((l) => l.target === "v_2")?.width).toBe(1.5);
  });

  it("orders each column largest first", () => {
    const graph: FundFlowGraph = {
      nodes: [node("mp_a", "MP", "A"), node("mp_b", "MP", "B"), node("mp_c", "MP", "C"), node("ag_1", "Agency")],
      edges: [edge("mp_a", "ag_1", 10), edge("mp_b", "ag_1", 50), edge("mp_c", "ag_1", 30)],
    };

    const layout = buildSankeyLayout(graph, 1100);

    expect(layout.nodes.filter((n) => n.type === "MP").map((n) => n.id)).toEqual(["mp_b", "mp_c", "mp_a"]);
  });

  it("sits an agency beside the Members that feed it, not only by its own size", () => {
    // Size alone would put ag_p (6 Cr) on top. But it is fed only by the second Member,
    // while ag_q and ag_z are fed by the first, who sits above.
    const graph: FundFlowGraph = {
      nodes: [
        node("mp_1", "MP"),
        node("mp_2", "MP"),
        node("ag_p", "Agency"),
        node("ag_q", "Agency"),
        node("ag_z", "Agency"),
      ],
      edges: [
        edge("mp_1", "ag_q", 50_000_000),
        edge("mp_1", "ag_z", 50_000_000),
        edge("mp_2", "ag_p", 60_000_000),
      ],
    };

    const layout = buildSankeyLayout(graph, 1100);

    expect(layout.nodes.filter((n) => n.type === "MP").map((n) => n.id)).toEqual(["mp_1", "mp_2"]);
    expect(layout.nodes.filter((n) => n.type === "Agency").map((n) => n.id)).toEqual(["ag_q", "ag_z", "ag_p"]);
  });

  it("centres a short column against the tallest one", () => {
    const layout = buildSankeyLayout(crowd(5), 1100);
    const vendor = at(layout, "v_1");

    expect(vendor.y).toBeCloseTo((layout.height - vendor.height) / 2, 6);
  });

  it("scales the busiest column to the target, and never thinner than the minimum", () => {
    const small = buildSankeyLayout(crowd(2), 1100);
    const barsOf = (layout: SankeyLayout, type: Type) =>
      layout.nodes.filter((n) => n.type === type).reduce((sum, n) => sum + n.barHeight, 0);
    expect(barsOf(small, "MP")).toBeCloseTo(280, 3);

    // Seven agencies force tall boxes, so the plot grows instead of the bands thinning below 160px.
    const agencies = Array.from({ length: 7 }, (_, i) => node(`ag_${i}`, "Agency"));
    const wide: FundFlowGraph = {
      nodes: [node("mp_1", "MP"), ...agencies, node("v_1", "Vendor")],
      edges: [
        ...agencies.map((a) => edge("mp_1", a.id, 10_000_000)),
        ...agencies.map((a) => edge(a.id, "v_1", 10_000_000)),
      ],
    };
    const layout = buildSankeyLayout(wide, 1100);
    expect(barsOf(layout, "Agency")).toBeGreaterThanOrEqual(160 - 1e-6);
    expect(layout.height).toBeGreaterThan(460);
  });

  it("clamps the box width and shares what is left between two equal gutters", () => {
    const wide = buildSankeyLayout(balanced, 1600);
    const [mp, agency, vendor] = wide.columns;

    expect(mp.width).toBe(250);
    expect(agency.x - (mp.x + mp.width)).toBeCloseTo(vendor.x - (agency.x + agency.width), 6);
    expect(vendor.x + vendor.width).toBeCloseTo(1600, 6);

    const narrow = buildSankeyLayout(balanced, 400);
    expect(narrow.width).toBe(MIN_WIDTH);
    expect(narrow.columns[0].width).toBe(170);
  });

  it("has nothing to draw for an empty graph, and ignores an edge that skips a column", () => {
    const empty = buildSankeyLayout({ nodes: [], edges: [] }, 1100);
    expect(empty.nodes).toEqual([]);
    expect(empty.links).toEqual([]);
    expect(empty.height).toBe(0);

    const skipping: FundFlowGraph = {
      nodes: [node("mp_1", "MP"), node("v_1", "Vendor")],
      edges: [edge("mp_1", "v_1", 5_000_000)],
    };
    expect(buildSankeyLayout(skipping, 1100).links).toEqual([]);
  });

  it("tiers a band by the share of its works that carry a flag", () => {
    expect(tierOf(0, 4)).toBe("plain");
    expect(tierOf(1, 4)).toBe("elevated");
    expect(tierOf(4, 4)).toBe("high");
    expect(tierOf(0, 0)).toBe("plain");
  });

  it("gives a vendor its own tier and the works that reach it", () => {
    const graph: FundFlowGraph = {
      nodes: [node("ag_1", "Agency"), node("ag_2", "Agency"), node("v_1", "Vendor")],
      edges: [
        edge("ag_1", "v_1", 4_000_000, { work_count: 4, flagged_work_count: 4 }),
        edge("ag_2", "v_1", 6_000_000, { work_count: 6, flagged_work_count: 2 }),
      ],
    };

    const vendor = at(buildSankeyLayout(graph, 1100), "v_1");

    expect(vendor.workCount).toBe(10);
    expect(vendor.tier).toBe("elevated");
    expect(vendor.amount).toBe(10_000_000);
  });
});
