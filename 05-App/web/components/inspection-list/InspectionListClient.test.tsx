// T7: the printable inspection plan. These tests cover exactly the three
// behaviours the task brief calls out for TDD -- the print button, the
// District Authority page-size bump, and R22's filtered fix -- not a full
// re-test of everything InspectionListClient already does. The Playwright
// PDF check (recipe in the task's global context) is what actually verifies
// the print-only header renders and prints cleanly.
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { renderTemplate, STRINGS } from "@/lib/strings";
import { formatIndianInt } from "@/lib/format";
import { InspectionListClient } from "./InspectionListClient";

const nav = vi.hoisted(() => ({ params: new URLSearchParams() }));
vi.mock("next/navigation", () => ({
  useSearchParams: () => nav.params,
  usePathname: () => "/inspections",
  useRouter: () => ({ push: vi.fn() }),
}));

function envelope(data: unknown, meta: Record<string, unknown> | null): Response {
  return {
    ok: true,
    status: 200,
    json: async () => ({ success: true, data, error: null, meta }),
  } as Response;
}

const FACETS = {
  states: [],
  years: [],
  categories: [],
  district_authorities: [{ value: "Test Authority", count: 20 }],
  constituencies: [{ value: "Test Constituency", count: 1, mp_name: "Test MP" }],
  flags: [],
};

const PENDENCY = {
  as_of: "2026-09-04",
  population_n: 20,
  population_inr: 200_000_000,
  kinds: {
    late_sanction: { count: 10, sanctioned_inr: 100_000_000, median_days_to_sanction: 90 },
    open_past_one_year: { count: 5, sanctioned_inr: 50_000_000 },
    no_payment_90_days: { count: 3, sanctioned_inr: 30_000_000 },
  },
  district_authority_n: 1,
  quota_sum: 2,
  third_party: { at_or_above_25_lakh: 0, between_15_and_25_lakh: 0, required_n: 0 },
  groups: null,
};

const SUMMARY = {
  works_under_implementation: 20,
  flagged_count: 5,
  total_flagged_amount_inr: 50_000_000,
  idle_beyond_12_months_amount_inr: 0,
  total_works_all_statuses: 25,
  idle_work_count: 0,
  total_sanctioned_under_implementation_inr: 200_000_000,
  state_count: 1,
  constituency_count: 1,
  data_as_of: "2026-09-04",
};

const ROW = {
  work_id: "W1",
  state: "Test State",
  constituency: "Test Constituency",
  mp_name: "Test MP",
  tenure: "18th Lok Sabha",
  implementing_district_authority: "Test Authority",
  implementing_agency: "Test Agency",
  vendor_id: "V1",
  vendor_name: "Test Vendor",
  work_category: "Road",
  work_description: "Road work near the market",
  activity_name: "Road building",
  recommendation_date: "2025-01-01",
  sanctioned_amount_inr: 1_000_000,
  expenditure_amount_inr: 500_000,
  sanction_date: "2025-02-01",
  completion_status: "In Progress",
  last_updated: "2026-08-01",
  source_rung: 1,
  inspection_rank: 1,
  risk_score: 80,
  flags: ["cost_outlier"],
  why_flagged: { cost_outlier: "Costs more than 90 percent of its peer group." },
  peer_group: { label: "Road works in Test State", n: 40 },
  days_to_sanction: 31,
  days_since_sanction: 200,
};

// T7 fix round 1: rung 5 is the hand-curated seed dataset (lib/data.ts
// isDemoDataset -- true only when every row's source_rung is 5), mirrored
// from ROW with nothing else changed so the only variable is source_rung.
const DEMO_ROW = { ...ROW, work_id: "W2", source_rung: 5 };

const requestedUrls: string[] = [];

function mockApi(rows: unknown[], worksMeta: Record<string, unknown> | null = null) {
  (global.fetch as ReturnType<typeof vi.fn>).mockImplementation(async (input: RequestInfo | URL) => {
    const url = String(input);
    requestedUrls.push(url);
    if (url.includes("/api/works/facets")) return envelope(FACETS, null);
    if (url.includes("/api/pendency")) return envelope(PENDENCY, null);
    if (url.includes("/api/stats/summary")) return envelope(SUMMARY, null);
    if (url.includes("/api/early-warning")) return envelope(null, null);
    if (url.includes("/api/duplicates")) {
      return envelope({ rows: [], page: 1, pageSize: 25, total: 0, totalPages: 0 }, null);
    }
    if (url.includes("/api/works")) return envelope(rows, worksMeta);
    throw new Error(`unexpected request ${url}`);
  });
}

beforeEach(() => {
  nav.params = new URLSearchParams();
  requestedUrls.length = 0;
  vi.stubGlobal("fetch", vi.fn());
  vi.stubGlobal(
    "matchMedia",
    vi.fn(() => ({
      matches: false,
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

test("Print this list calls window.print", async () => {
  mockApi([ROW]);
  const printSpy = vi.spyOn(window, "print").mockImplementation(() => {});
  const user = userEvent.setup();
  render(<InspectionListClient />);
  await screen.findByRole("button", { name: /Road work, Test Constituency/ });

  await user.click(screen.getByRole("button", { name: STRINGS.print.button }));

  expect(printSpy).toHaveBeenCalledTimes(1);
});

test("requests pageSize 100 once a District Authority narrows the list", async () => {
  nav.params = new URLSearchParams("district_authority=Test+Authority");
  mockApi([ROW]);
  render(<InspectionListClient />);

  await screen.findByRole("button", { name: /Road work, Test Constituency/ });

  const worksRequest = requestedUrls.find((url) => url.includes("/api/works?"));
  expect(worksRequest).toContain("page_size=100");
});

test("requests pageSize 50 without a District Authority", async () => {
  mockApi([ROW]);
  render(<InspectionListClient />);

  await screen.findByRole("button", { name: /Road work, Test Constituency/ });

  const worksRequest = requestedUrls.find((url) => url.includes("/api/works?"));
  expect(worksRequest).toContain("page_size=50");
});

// FilterPanel's own "Clear all filters" button (driven by the already-correct
// isFilterActive) shares its exact label with the empty state's action
// (driven by InspectionListClient's own `filtered`, what R22 fixes) --
// STRINGS.filters.clear and STRINGS.data_states.empty_after_filter.action are
// both literally "Clear all filters". An unscoped getByRole would pass off
// FilterPanel's button as proof of R22's fix even with the bug still in
// place, so every R22 assertion below is scoped to the table's own root
// (data-treatment, a plain HTML attribute InspectionTable always renders,
// stable across CSS module hashing) to isolate the button `filtered` gates.
function emptyStateWithin() {
  const table = screen.getByRole("table", { name: STRINGS.nav.inspection_list });
  return within(table.closest("[data-treatment]") as HTMLElement);
}

test("R22: a pendency filter alone still offers Clear all filters on an empty result", async () => {
  nav.params = new URLSearchParams("pendency=late_sanction");
  mockApi([]);
  render(<InspectionListClient />);

  expect(
    await emptyStateWithin().findByRole("button", { name: STRINGS.data_states.empty_after_filter.action }),
  ).toBeInTheDocument();
});

test("R22: a District Authority alone still offers Clear all filters on an empty result", async () => {
  nav.params = new URLSearchParams("district_authority=Test+Authority");
  mockApi([]);
  render(<InspectionListClient />);

  expect(
    await emptyStateWithin().findByRole("button", { name: STRINGS.data_states.empty_after_filter.action }),
  ).toBeInTheDocument();
});

test("R22: a constituency alone still offers Clear all filters on an empty result", async () => {
  nav.params = new URLSearchParams("constituency=Test+Constituency");
  mockApi([]);
  render(<InspectionListClient />);

  expect(
    await emptyStateWithin().findByRole("button", { name: STRINGS.data_states.empty_after_filter.action }),
  ).toBeInTheDocument();
});

test("R22: no filters active means no Clear all filters button in the table's own empty state", async () => {
  mockApi([]);
  render(<InspectionListClient />);

  const scope = emptyStateWithin();
  await scope.findByText(STRINGS.data_states.empty_after_filter.title);
  expect(scope.queryByRole("button", { name: STRINGS.data_states.empty_after_filter.action })).not.toBeInTheDocument();
});

// T7 fix round 1 (Important): SummaryLine's demo-dataset banner is
// data-print="hide" (screen only), and .print-only's own asOf line renders
// regardless of isDemoDataset -- a print of rung-5 seed data carried no
// indication it was demo data. ".print-only" is a plain global class (not a
// CSS module one, see globals.css), so it survives hashing and scopes these
// assertions away from SummaryLine's own on-screen copy of the same text.
function printOnlyHeader() {
  return within(document.querySelector(".print-only") as HTMLElement);
}

test("the print-only header keeps the demo-dataset label for rung-5 seed rows", async () => {
  mockApi([DEMO_ROW]);
  render(<InspectionListClient />);
  await screen.findByRole("button", { name: /Road work, Test Constituency/ });

  const demo = STRINGS.data_states.showing_cached_data.demo_dataset_variant;
  const header = printOnlyHeader();
  expect(header.getByText(demo.label)).toBeInTheDocument();
  expect(header.getByText(demo.detail)).toBeInTheDocument();
  // "Data as of {date}" stays as is -- the fix adds the demo label, it does
  // not replace the date line the way SummaryLine's own either/or does.
  expect(header.getByText(renderTemplate(STRINGS.print.as_of, { date: "4 Sep 2026" }))).toBeInTheDocument();
});

test("the print-only header has no demo-dataset label for real data", async () => {
  mockApi([ROW]);
  render(<InspectionListClient />);
  await screen.findByRole("button", { name: /Road work, Test Constituency/ });

  const demo = STRINGS.data_states.showing_cached_data.demo_dataset_variant;
  expect(printOnlyHeader().queryByText(demo.label)).not.toBeInTheDocument();
});

// Final review M2: the duty sentence names the role's scope, not a Timeline/flag/category/year
// filter or search narrowing it further, so a filtered printout carried a sentence about a
// different (larger) population than the list actually printed below it. The fix reuses
// SummaryLine's own filtered-population sentence and figures inside .print-only.
test("the print-only header carries the actual filtered count under a non-scope filter", async () => {
  nav.params = new URLSearchParams("pendency=late_sanction");
  mockApi([ROW], { total: 1, quota_n: 1, total_pages: 1, page: 1, page_size: 50 });
  render(<InspectionListClient />);
  await screen.findByRole("button", { name: /Road work, Test Constituency/ });

  expect(
    printOnlyHeader().getByText(
      renderTemplate(STRINGS.table.filtered_summary_short, {
        total_n: formatIndianInt(1),
        cutoff_rank: formatIndianInt(1),
      }),
    ),
  ).toBeInTheDocument();
});

test("the print-only header has no filtered-count sentence when the filter matches nothing", async () => {
  nav.params = new URLSearchParams("pendency=late_sanction");
  mockApi([], { total: 0, quota_n: 0, total_pages: 0, page: 1, page_size: 50 });
  render(<InspectionListClient />);
  await screen.findByText(STRINGS.data_states.empty_after_filter.title);

  expect(
    printOnlyHeader().queryByText(renderTemplate(STRINGS.table.filtered_summary_short, { total_n: "0", cutoff_rank: "0" })),
  ).not.toBeInTheDocument();
});
