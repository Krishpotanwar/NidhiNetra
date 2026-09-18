import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";
import { renderTemplate, STRINGS } from "@/lib/strings";
import type { FundFlowGraph } from "@/lib/graph-data";
import { MAX_ROWS_PER_COLUMN } from "./ribbon-layout";
import { RibbonView } from "./RibbonView";

const s = STRINGS.fund_flow;

const graph: FundFlowGraph = {
  nodes: [
    { id: "mp-1", type: "MP", label: "Member One", risk_weight: 0 },
    { id: "agency-1", type: "Agency", label: "Agency One", risk_weight: 1 },
    { id: "vendor-1", type: "Vendor", label: "Vendor One", risk_weight: 2 },
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
      work_count: 1,
      total_amount_inr: 1_000_000,
      flagged_work_count: 1,
      work_ids: ["WORK-1"],
    },
  ],
};

test("shows the existing empty state for an empty graph", () => {
  render(<RibbonView graph={{ nodes: [], edges: [] }} />);

  expect(screen.getByText(s.empty)).toBeInTheDocument();
  expect(screen.getByText(s.empty_body)).toBeInTheDocument();
});

test("renders each node as a named row under its own column", () => {
  render(<RibbonView graph={graph} />);

  expect(screen.getByRole("img", { name: s.subtitle })).toBeInTheDocument();
  expect(screen.getByText(s.column_mp)).toBeInTheDocument();
  expect(screen.getByText(s.column_agency)).toBeInTheDocument();
  expect(screen.getByText(s.column_vendor)).toBeInTheDocument();
  expect(screen.getByText("Member One")).toBeInTheDocument();
  expect(screen.getByText("Agency One")).toBeInTheDocument();
  expect(screen.getByText("Vendor One")).toBeInTheDocument();
});

test("marks the highlighted vendor's row as selected and leaves others alone", () => {
  render(<RibbonView graph={graph} highlightVendorId="vendor-1" />);

  expect(screen.getByText("Vendor One")).toHaveAttribute("data-selected", "true");
  expect(screen.getByText("Agency One")).not.toHaveAttribute("data-selected");
});

test("keeps full edge detail discoverable via the ribbon's title", () => {
  const { container } = render(<RibbonView graph={graph} />);

  const titles = Array.from(container.querySelectorAll("path title")).map((t) => t.textContent);
  expect(titles).toContain(
    renderTemplate(s.edge_label, { work_count: "1", amount: "₹10,00,000" }),
  );
});

test("collapses a column past the row cap into a '+N more' row", () => {
  const nodes: FundFlowGraph["nodes"] = Array.from({ length: MAX_ROWS_PER_COLUMN + 4 }, (_, i) => ({
    id: `mp-${i}`,
    type: "MP" as const,
    label: `Member ${i}`,
    risk_weight: 0,
  }));
  render(<RibbonView graph={{ nodes, edges: [] }} />);

  expect(screen.getByText(renderTemplate(s.ribbon_more_note, { count: "4" }))).toBeInTheDocument();
});
