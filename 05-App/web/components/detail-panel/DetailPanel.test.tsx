// F-01 (nemotronreview.md): a work's record must show the District Authority
// (IDA_NAME) and the Implementing agency (IA_NAME) as two separately labelled
// values, and never put the authority where the agency belongs.
import type { ReactNode } from "react";
import { render, screen } from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { STRINGS } from "@/lib/strings";
import { displayName, formatDate } from "@/lib/format";
import type { InspectionRow } from "@/lib/types";
import { DetailPanel } from "./DetailPanel";

vi.mock("next/link", () => ({
  default: ({ href, children, ...rest }: { href: string; children: ReactNode }) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
}));

const fields = STRINGS.detail_panel.record_fields;

function row(overrides: Partial<InspectionRow> = {}): InspectionRow {
  return {
    work_id: "133166",
    state: "Karnataka",
    constituency: "DHARWAD",
    mp_name: "Pralhad Venkatesh Joshi",
    tenure: "2024-2029",
    implementing_district_authority: "DHARWAD(DEPUTY COMMISSIONER DHARWAR_IDA)",
    implementing_agency: "KRIDL DHARWAD",
    vendor_id: "3562",
    vendor_name: "SHRINIVAS CONTRACTOR",
    work_category: "Road",
    work_description: "PCC Road from Ram house to Shyam house",
    activity_name: "Construction of roads",
    recommendation_date: "2024-07-02",
    sanctioned_amount_inr: 497185,
    expenditure_amount_inr: 250000,
    sanction_date: "2024-07-09",
    completion_status: "In Progress",
    last_updated: "2026-08-21",
    source_rung: 1,
    inspection_rank: 12,
    risk_score: 42.5,
    flags: [],
    why_flagged: {},
    peer_group: null,
    displayRank: 3,
    ...overrides,
  };
}

beforeEach(() => {
  vi.stubGlobal(
    "matchMedia",
    vi.fn(() => ({
      matches: true,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      addListener: vi.fn(),
      removeListener: vi.fn(),
    })),
  );
  localStorage.clear();
});

afterEach(() => {
  vi.unstubAllGlobals();
  localStorage.clear();
});

test("shows the District Authority and the Implementing agency as two labelled fields", () => {
  render(<DetailPanel row={row()} onClose={() => {}} quotaN={10} />);

  const authority = screen.getByText(fields.district_authority);
  const agency = screen.getByText(fields.agency);
  expect(authority.nextElementSibling).toHaveTextContent(
    displayName("DHARWAD(DEPUTY COMMISSIONER DHARWAR_IDA)"),
  );
  expect(agency.nextElementSibling).toHaveTextContent(displayName("KRIDL DHARWAD"));
});

test("a work with no recorded agency says so and never shows the authority in its place", () => {
  render(<DetailPanel row={row({ implementing_agency: null })} onClose={() => {}} quotaN={10} />);

  expect(screen.getByText(fields.agency).nextElementSibling).toHaveTextContent(
    STRINGS.missing_fields.agency,
  );
  expect(
    screen.queryByRole("link", { name: STRINGS.detail_panel.fund_flow_entry }),
  ).not.toBeInTheDocument();
});

test("a work with no recorded District Authority says so", () => {
  render(
    <DetailPanel row={row({ implementing_district_authority: null })} onClose={() => {}} quotaN={10} />,
  );

  expect(screen.getByText(fields.district_authority).nextElementSibling).toHaveTextContent(
    STRINGS.missing_fields.district_authority,
  );
});

test("the fund-flow link follows the Implementing agency, not the District Authority", () => {
  render(<DetailPanel row={row()} onClose={() => {}} quotaN={10} />);

  expect(screen.getByRole("link", { name: STRINGS.detail_panel.fund_flow_entry })).toHaveAttribute(
    "href",
    `/fund-flow?agency=${encodeURIComponent("KRIDL DHARWAD")}`,
  );
});

test("shows the portal's own description under the title", () => {
  render(<DetailPanel row={row()} onClose={() => {}} quotaN={10} />);

  expect(screen.getByText(fields.work_description)).toBeInTheDocument();
  expect(screen.getByText("PCC Road from Ram house to Shyam house")).toBeInTheDocument();
});

test("says so plainly when the portal has no description", () => {
  render(<DetailPanel row={row({ work_description: null })} onClose={() => {}} quotaN={10} />);

  expect(screen.getByText(STRINGS.missing_fields.description)).toBeInTheDocument();
});

test("lists the portal activity and the recommendation date as published", () => {
  render(<DetailPanel row={row()} onClose={() => {}} quotaN={10} />);

  expect(screen.getByText(fields.activity).nextElementSibling).toHaveTextContent(
    "Construction of roads",
  );
  expect(screen.getByText(fields.recommendation_date).nextElementSibling).toHaveTextContent(
    formatDate("2024-07-02"),
  );
});

test("shows a portal activity with capitals exactly as published", () => {
  render(
    <DetailPanel
      row={row({ activity_name: "Fitting of Sitting RCC Benches in Public Places" })}
      onClose={() => {}}
      quotaN={10}
    />,
  );

  expect(screen.getByText(fields.activity).nextElementSibling).toHaveTextContent(
    "Fitting of Sitting RCC Benches in Public Places",
  );
});
