// Decision D6 (F-01/F-02 legacy guard): when the API holds back a graph built
// before the IDA/IA split or before edges carried work IDs, the page explains
// that in contract copy instead of looking like an empty filter.
//
// T17/F-17b: the non-deep-link view now asks the server for concentrations
// and clusters instead of downloading the whole national graph -- these
// tests assert it never falls back to the bare /api/graph endpoint.
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { renderTemplate, STRINGS } from "@/lib/strings";
import { FundFlowClient } from "./FundFlowClient";

const nav = vi.hoisted(() => ({ params: new URLSearchParams() }));
vi.mock("next/navigation", () => ({ useSearchParams: () => nav.params }));

const s = STRINGS.fund_flow;

function envelope(data: unknown, meta: Record<string, unknown> | null): Response {
  return {
    ok: true,
    status: 200,
    json: async () => ({ success: true, data, error: null, meta }),
  } as Response;
}

const requestedUrls: string[] = [];

function mockApi(graphStatus: "current" | "rebuild_required") {
  (global.fetch as ReturnType<typeof vi.fn>).mockImplementation(async (input: RequestInfo | URL) => {
    const url = String(input);
    requestedUrls.push(url);
    if (url.includes("/api/graph/concentrations")) {
      return envelope(
        {
          vendors: [],
          matching_count: 0,
          total_vendor_count: 0,
          median_member_count: 0,
          totals: graphStatus === "current" ? { flow_inr: 0, mp_count: 0, agency_count: 0, vendor_count: 0 } : null,
        },
        { graph_status: graphStatus },
      );
    }
    if (url.includes("/api/graph/cluster")) {
      return envelope({ nodes: [], edges: [] }, { graph_status: graphStatus });
    }
    if (url.includes("/api/graph")) {
      return envelope({ nodes: [], edges: [] }, { graph_status: graphStatus });
    }
    if (url.includes("/api/entity-aliases")) {
      return envelope([], { page: 1, page_size: 25, total: 0, total_pages: 0 });
    }
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

test("holds back a graph the API marks as needing a rebuild, with its own explanation", async () => {
  mockApi("rebuild_required");
  render(<FundFlowClient />);

  expect(await screen.findByText(STRINGS.fund_flow.rebuild_required_title)).toBeInTheDocument();
  expect(screen.getByText(STRINGS.fund_flow.rebuild_required_body)).toBeInTheDocument();
});

test("a current graph never shows the rebuild explanation", async () => {
  mockApi("current");
  render(<FundFlowClient />);

  expect((await screen.findAllByText(STRINGS.fund_flow.empty)).length).toBeGreaterThan(0);
  expect(screen.queryByText(STRINGS.fund_flow.rebuild_required_title)).not.toBeInTheDocument();
});

test("a non-deep-link render asks the server for concentrations and never downloads the bare national graph", async () => {
  mockApi("current");
  render(<FundFlowClient />);

  await screen.findAllByText(STRINGS.fund_flow.empty);

  const concentrationsRequest = requestedUrls.find((url) => url.includes("/api/graph/concentrations"));
  expect(concentrationsRequest).toContain("min_members=3");
  expect(requestedUrls.some((url) => /\/api\/graph(\?|$)/.test(url))).toBe(false);
});

// One flagged vendor cluster: two Members, one agency, one vendor.
const cluster = {
  nodes: [
    { id: "mp_1", type: "MP", label: "Member One", risk_weight: 0 },
    { id: "mp_2", type: "MP", label: "Member Two", risk_weight: 0 },
    { id: "agency_1", type: "Agency", label: "Agency One", risk_weight: 0 },
    { id: "vendor_cv", type: "Vendor", label: "Cluster Vendor", risk_weight: 0 },
  ],
  edges: [
    { source: "mp_1", target: "agency_1", work_count: 2, total_amount_inr: 30_000_000, flagged_work_count: 1, work_ids: ["W1", "W2"] },
    { source: "mp_2", target: "agency_1", work_count: 1, total_amount_inr: 10_000_000, flagged_work_count: 1, work_ids: ["W3"] },
    { source: "agency_1", target: "vendor_cv", work_count: 3, total_amount_inr: 40_000_000, flagged_work_count: 2, work_ids: ["W1", "W2", "W3"] },
  ],
};

const vendorNames = ["Vendor A", "Vendor B", "Vendor C", "Vendor D", "Vendor E", "Vendor F"];

function mockPopulatedApi() {
  (global.fetch as ReturnType<typeof vi.fn>).mockImplementation(async (input: RequestInfo | URL) => {
    const url = String(input);
    requestedUrls.push(url);
    if (url.includes("/api/graph/concentrations")) {
      return envelope(
        {
          vendors: vendorNames.map((name, i) => ({
            vendor_id: `vendor_${name.slice(-1).toLowerCase()}`,
            vendor_label: name,
            member_count: 9 - i,
            agency_count: 4,
            work_count: 12,
            sanctioned_inr: 20_700_000,
            flagged_work_count: 5,
          })),
          matching_count: 36,
          total_vendor_count: 17_455,
          median_member_count: 3,
          totals: { flow_inr: 25_801_524_793, mp_count: 536, agency_count: 754, vendor_count: 16_854 },
        },
        { graph_status: "current" },
      );
    }
    if (url.includes("/api/graph/cluster")) return envelope(cluster, { graph_status: "current" });
    if (url.includes("/api/entity-aliases")) return envelope([], { page: 1, page_size: 25, total: 0, total_pages: 0 });
    throw new Error(`unexpected request ${url}`);
  });
}

test("opens on the most concentrated vendor: totals, toolbar count, cluster header, chart and side cards", async () => {
  mockPopulatedApi();
  render(<FundFlowClient />);

  expect(await screen.findByRole("heading", { level: 2, name: "Vendor A" })).toBeInTheDocument();
  expect(screen.getByText(renderTemplate(s.members_pill, { count: "9" }))).toBeInTheDocument();
  expect(screen.getByText("₹2,580.15")).toBeInTheDocument();
  expect(screen.getByText(renderTemplate(s.toolbar_count, { shown: "6", matching: "36" }))).toBeInTheDocument();
  expect(await screen.findByRole("heading", { name: `${s.column_mp} (2)` })).toBeInTheDocument();
  expect(screen.getByText(renderTemplate(s.cluster_risk_flag_note, { flagged: "5", total: "12" }))).toBeInTheDocument();
  expect(screen.getByText(STRINGS.framing.standing_note)).toBeInTheDocument();
  expect(screen.getByRole("link", { name: new RegExp(s.view_linked_works) })).toHaveAttribute("href", "/inspections?vendor_id=a");
});

test("lists five vendors, expands to all of them in place, and collapses again", async () => {
  mockPopulatedApi();
  const user = userEvent.setup();
  render(<FundFlowClient />);
  const list = within((await screen.findByRole("heading", { name: s.clusters_title })).closest("section") as HTMLElement);

  expect(list.getAllByRole("button", { name: /Vendor/ })).toHaveLength(5);
  expect(list.queryByText("Vendor F")).not.toBeInTheDocument();

  await user.click(list.getByRole("button", { name: renderTemplate(s.view_all, { count: "6" }) }));
  expect(list.getByText("Vendor F")).toBeInTheDocument();

  await user.click(list.getByRole("button", { name: s.show_fewer }));
  expect(list.queryByText("Vendor F")).not.toBeInTheDocument();
});

test("focusing another vendor draws that vendor's own cluster", async () => {
  mockPopulatedApi();
  const user = userEvent.setup();
  render(<FundFlowClient />);
  await screen.findByRole("heading", { level: 2, name: "Vendor A" });

  await user.click(screen.getByRole("button", { name: /Vendor B/ }));

  expect(await screen.findByRole("heading", { level: 2, name: "Vendor B" })).toBeInTheDocument();
  expect(requestedUrls.some((url) => url.includes("/api/graph/cluster") && url.includes("vendor_id=vendor_b"))).toBe(true);
});

test("a search narrows the list and the toolbar count says how many it found", async () => {
  mockPopulatedApi();
  const user = userEvent.setup();
  render(<FundFlowClient />);
  await screen.findByRole("heading", { level: 2, name: "Vendor A" });

  await user.type(screen.getByRole("searchbox", { name: s.search_label }), "vendor c");

  expect(await screen.findByText(renderTemplate(s.toolbar_count, { shown: "1", matching: "1" }))).toBeInTheDocument();
  expect(screen.getByRole("button", { name: s.reset })).toBeEnabled();
});

test("reset is disabled at the defaults", async () => {
  mockPopulatedApi();
  render(<FundFlowClient />);
  await screen.findByRole("heading", { level: 2, name: "Vendor A" });

  expect(screen.getByRole("button", { name: s.reset })).toBeDisabled();
});

test("an agency deep link draws one chart under the agency name, with no totals, toolbar or side cards", async () => {
  nav.params = new URLSearchParams("agency=KRIDL%20DHARWAD");
  (global.fetch as ReturnType<typeof vi.fn>).mockImplementation(async (input: RequestInfo | URL) => {
    const url = String(input);
    requestedUrls.push(url);
    if (url.includes("/api/entity-aliases")) return envelope([], { page: 1, page_size: 25, total: 0, total_pages: 0 });
    return envelope(cluster, { graph_status: "current" });
  });
  render(<FundFlowClient />);

  expect(await screen.findByRole("heading", { level: 2, name: "Kridl Dharwad" })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: s.back_to_clusters })).toHaveAttribute("href", "/fund-flow");
  expect(await screen.findByRole("heading", { name: `${s.column_mp} (2)` })).toBeInTheDocument();
  expect(screen.queryByText(s.totals_flow_label)).not.toBeInTheDocument();
  expect(screen.queryByRole("searchbox")).not.toBeInTheDocument();
  expect(screen.queryByRole("heading", { name: s.clusters_title })).not.toBeInTheDocument();
  expect(requestedUrls.some((url) => url.includes("/api/graph/concentrations"))).toBe(false);
  expect(requestedUrls.find((url) => /\/api\/graph\?/.test(url))).toContain("agency=KRIDL");
});
