// Decision D6 (F-01/F-02 legacy guard): when the API holds back a graph built
// before the IDA/IA split or before edges carried work IDs, the page explains
// that in contract copy instead of looking like an empty filter.
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

function mockApi(graphStatus: "current" | "rebuild_required") {
  (global.fetch as ReturnType<typeof vi.fn>).mockImplementation(async (input: RequestInfo | URL) => {
    const url = String(input);
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
