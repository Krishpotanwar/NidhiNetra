// Decision D6 (F-01/F-02 legacy guard): when the API holds back a graph built
// before the IDA/IA split or before edges carried work IDs, the page explains
// that in contract copy instead of looking like an empty filter.
//
// T17/F-17b: the non-deep-link view now asks the server for concentrations
// and clusters instead of downloading the whole national graph -- these
// tests assert it never falls back to the bare /api/graph endpoint.
import { render, screen } from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { STRINGS } from "@/lib/strings";
import { FundFlowClient } from "./FundFlowClient";

vi.mock("next/navigation", () => ({ useSearchParams: () => new URLSearchParams() }));

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
