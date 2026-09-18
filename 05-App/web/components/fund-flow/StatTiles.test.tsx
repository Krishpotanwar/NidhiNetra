import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";
import { STRINGS } from "@/lib/strings";
import { StatTiles } from "./StatTiles";

const s = STRINGS.fund_flow;

test("renders the whole-graph totals it is given", () => {
  render(<StatTiles totals={{ flowInr: 25_801_500, mpCount: 536, agencyCount: 754, vendorCount: 16_854 }} />);

  expect(screen.getByText(s.totals_flow_label)).toBeInTheDocument();
  expect(screen.getByText("₹2,58,01,500")).toBeInTheDocument();
  expect(screen.getByText("536")).toBeInTheDocument();
  expect(screen.getByText("754")).toBeInTheDocument();
  expect(screen.getByText("16,854")).toBeInTheDocument();
});
