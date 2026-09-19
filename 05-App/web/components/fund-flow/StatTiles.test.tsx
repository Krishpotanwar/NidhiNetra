import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";
import { STRINGS } from "@/lib/strings";
import { StatTiles } from "./StatTiles";

const s = STRINGS.fund_flow;

test("renders the whole-graph totals, the flow in crore with a small unit", () => {
  render(<StatTiles totals={{ flowInr: 25_801_524_793, mpCount: 536, agencyCount: 754, vendorCount: 16_854 }} />);

  expect(screen.getByText(s.totals_flow_label)).toBeInTheDocument();
  expect(screen.getByText("₹2,580.15")).toBeInTheDocument();
  expect(screen.getByText("Cr")).toBeInTheDocument();
  expect(screen.getByText(s.column_mp)).toBeInTheDocument();
  expect(screen.getByText("536")).toBeInTheDocument();
  expect(screen.getByText(s.column_agency)).toBeInTheDocument();
  expect(screen.getByText("754")).toBeInTheDocument();
  expect(screen.getByText(s.totals_vendor_label)).toBeInTheDocument();
  expect(screen.getByText("16,854")).toBeInTheDocument();
});

test("holds the four cards in place with skeletons until the totals arrive", () => {
  const { container } = render(<StatTiles totals={null} />);

  expect(screen.getByText(s.totals_flow_label)).toBeInTheDocument();
  expect(screen.getByText(s.column_mp)).toBeInTheDocument();
  expect(screen.queryByText("Cr")).not.toBeInTheDocument();
  expect(container.firstElementChild).toHaveAttribute("aria-busy", "true");
});
