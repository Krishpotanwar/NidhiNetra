import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, test, vi } from "vitest";
import type { FundFlowGraph } from "@/lib/graph-data";
import { renderTemplate, STRINGS } from "@/lib/strings";
import { SankeyChart } from "./SankeyChart";

const s = STRINGS.fund_flow;

const graph: FundFlowGraph = {
  nodes: [
    { id: "mp-1", type: "MP", label: "MEMBER ONE", risk_weight: 0 },
    { id: "mp-2", type: "MP", label: "Member Two", risk_weight: 0 },
    { id: "agency-1", type: "Agency", label: "Agency One", risk_weight: 1 },
    { id: "vendor-1", type: "Vendor", label: "Vendor One", risk_weight: 2 },
  ],
  edges: [
    {
      source: "mp-1",
      target: "agency-1",
      work_count: 2,
      total_amount_inr: 30_000_000,
      flagged_work_count: 0,
      work_ids: ["W1", "W2"],
    },
    {
      source: "mp-2",
      target: "agency-1",
      work_count: 1,
      total_amount_inr: 10_000_000,
      flagged_work_count: 1,
      work_ids: ["W3"],
    },
    {
      source: "agency-1",
      target: "vendor-1",
      work_count: 3,
      total_amount_inr: 40_000_000,
      flagged_work_count: 1,
      work_ids: ["W1", "W2", "W3"],
    },
  ],
};

afterEach(() => vi.unstubAllGlobals());

const paths = (container: HTMLElement) => Array.from(container.querySelectorAll("path[data-tier]"));

test("shows the existing empty state for an empty graph", () => {
  render(<SankeyChart graph={{ nodes: [], edges: [] }} />);

  expect(screen.getByText(s.empty)).toBeInTheDocument();
  expect(screen.getByText(s.empty_body)).toBeInTheDocument();
});

test("heads each column with how many nodes it holds", () => {
  render(<SankeyChart graph={graph} />);

  expect(screen.getByRole("heading", { name: `${s.column_mp} (2)` })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: `${s.column_agency} (1)` })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: `${s.column_vendor} (1)` })).toBeInTheDocument();
});

test("heads the vendor column in the plural when there is more than one", () => {
  const two: FundFlowGraph = {
    nodes: [...graph.nodes, { id: "vendor-2", type: "Vendor", label: "Vendor Two", risk_weight: 0 }],
    edges: graph.edges,
  };
  render(<SankeyChart graph={two} />);

  expect(screen.getByRole("heading", { name: `${s.totals_vendor_label} (2)` })).toBeInTheDocument();
});

test("names every node with its money, and the vendor with its works", () => {
  render(<SankeyChart graph={graph} />);
  // The names also appear in the text table, so read them off the boxes.
  const box = (name: RegExp) => within(screen.getByRole("button", { name }));

  expect(box(/Member One/).getByText("₹3.00 Cr")).toBeInTheDocument();
  expect(box(/Agency One/).getByText("₹4.00 Cr")).toBeInTheDocument();
  expect(box(/Vendor One/).getByText(`₹4.00 Cr · ${renderTemplate(s.works_count, { count: "3" })}`)).toBeInTheDocument();
});

test("explains the colours and the width in a legend", () => {
  render(<SankeyChart graph={graph} />);

  expect(screen.getByText(s.ribbon_legend_plain)).toBeInTheDocument();
  expect(screen.getByText(s.ribbon_legend_elevated)).toBeInTheDocument();
  expect(screen.getByText(s.ribbon_legend_high)).toBeInTheDocument();
  expect(screen.getByText(s.ribbon_info_note)).toBeInTheDocument();
});

test("lists every flow in a table for readers who cannot see the picture", () => {
  render(<SankeyChart graph={graph} />);

  const table = within(screen.getByRole("table", { name: s.flow_table_caption }));
  expect(table.getAllByRole("row")).toHaveLength(1 + graph.edges.length);
  expect(table.getByText("₹3,00,00,000")).toBeInTheDocument();
  expect(table.getByText("₹4,00,00,000")).toBeInTheDocument();
  for (const heading of [s.flow_table_from, s.flow_table_to, s.flow_table_amount, s.flow_table_works, s.flow_table_flagged]) {
    expect(table.getByRole("columnheader", { name: heading })).toBeInTheDocument();
  }
});

test("draws the plain bands first and the flagged ones last", () => {
  const { container } = render(<SankeyChart graph={graph} />);

  expect(paths(container).map((p) => p.getAttribute("data-tier"))).toEqual(["plain", "elevated", "high"]);
});

test("brings a node's bands forward and dims the rest while its box is hovered", async () => {
  const user = userEvent.setup();
  const { container } = render(<SankeyChart graph={graph} />);
  const states = () => paths(container).map((p) => p.getAttribute("data-state"));

  expect(states()).toEqual([null, null, null]);

  await user.hover(screen.getByRole("button", { name: /Member Two/ }));
  expect(states().filter((state) => state === "on")).toHaveLength(1);
  expect(states().filter((state) => state === "dim")).toHaveLength(2);

  await user.unhover(screen.getByRole("button", { name: /Member Two/ }));
  expect(states()).toEqual([null, null, null]);
});

test("does the same when a box takes keyboard focus", async () => {
  const user = userEvent.setup();
  const { container } = render(<SankeyChart graph={graph} />);

  await user.tab();

  expect(paths(container).some((p) => p.getAttribute("data-state") === "on")).toBe(true);
});

test("tells the whole story of a band when it is hovered", async () => {
  const user = userEvent.setup();
  const { container } = render(<SankeyChart graph={graph} />);
  const flagged = container.querySelector('path[data-tier="high"]');
  if (!flagged) throw new Error("no flagged band");

  await user.hover(flagged);

  const tip = within(screen.getByRole("tooltip"));
  expect(tip.getByText(/Member Two/)).toBeInTheDocument();
  expect(tip.getByText(/Agency One/)).toBeInTheDocument();
  expect(tip.getByText(renderTemplate(s.edge_label, { work_count: "1", amount: "₹1,00,00,000" }))).toBeInTheDocument();
  expect(tip.getByText(renderTemplate(s.cluster_risk_flag_note, { flagged: "1", total: "1" }))).toBeInTheDocument();
  expect(paths(container).filter((p) => p.getAttribute("data-state") === "on")).toEqual([flagged]);

  await user.unhover(flagged);
  expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
});

test("says nothing about flags on a band whose works carry none", async () => {
  const user = userEvent.setup();
  const { container } = render(<SankeyChart graph={graph} />);
  const plain = container.querySelector('path[data-tier="plain"]');
  if (!plain) throw new Error("no plain band");

  await user.hover(plain);

  expect(screen.getByRole("tooltip")).not.toHaveTextContent(/risk flag/);
});

test("follows the width its frame reports, and never draws narrower than the minimum", () => {
  const reports: number[] = [1200];
  class Watcher {
    constructor(private readonly report: (entries: unknown[]) => void) {}
    observe() {
      this.report([{ contentRect: { width: reports[0] } }]);
    }
    disconnect() {}
  }
  vi.stubGlobal("ResizeObserver", Watcher);

  const wide = render(<SankeyChart graph={graph} />);
  expect(wide.container.querySelector("path[data-tier]")?.closest("svg")).toHaveAttribute("width", "1200");
  wide.unmount();

  reports[0] = 300;
  const narrow = render(<SankeyChart graph={graph} />);
  expect(narrow.container.querySelector("path[data-tier]")?.closest("svg")).toHaveAttribute("width", "720");
});
