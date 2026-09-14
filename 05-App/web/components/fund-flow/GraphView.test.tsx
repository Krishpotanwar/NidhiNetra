import { act, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { STRINGS } from "@/lib/strings";
import type { FundFlowGraph } from "@/lib/graph-data";
import { GraphView } from "./GraphView";

const sigmaHarness = vi.hoisted(() => ({
  construct: vi.fn(),
  kill: vi.fn(),
  listeners: new Map<string, (payload: unknown) => void>(),
  constructionError: null as Error | null,
}));

vi.mock("sigma", () => ({
  default: class MockSigma {
    constructor(...args: unknown[]) {
      sigmaHarness.construct(...args);
      if (sigmaHarness.constructionError) throw sigmaHarness.constructionError;
    }

    on(event: string, listener: (payload: unknown) => void) {
      sigmaHarness.listeners.set(event, listener);
      return this;
    }

    kill() {
      sigmaHarness.kill();
    }
  },
}));

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

beforeEach(() => {
  sigmaHarness.construct.mockClear();
  sigmaHarness.kill.mockClear();
  sigmaHarness.listeners.clear();
  sigmaHarness.constructionError = null;
  vi.stubGlobal(
    "matchMedia",
    vi.fn(() => ({ matches: true })),
  );
});

afterEach(() => vi.unstubAllGlobals());

test("uses a bounded Sigma surface instead of the hand-rolled SVG", () => {
  const { container } = render(<GraphView graph={graph} />);

  expect(screen.getByRole("img", { name: STRINGS.fund_flow.subtitle })).toHaveAttribute(
    "data-graph-renderer",
    "sigma",
  );
  expect(container.querySelector("svg")).not.toBeInTheDocument();
});

test("constructs Sigma for graph data and releases each renderer", async () => {
  const { rerender, unmount } = render(<GraphView graph={graph} />);

  await waitFor(() => expect(sigmaHarness.construct).toHaveBeenCalledTimes(1));
  const [sigmaGraph, mount, settings] = sigmaHarness.construct.mock.calls[0];
  expect(sigmaGraph).toMatchObject({ order: graph.nodes.length, size: graph.edges.length });
  expect(mount).toBe(screen.getByRole("img", { name: STRINGS.fund_flow.subtitle }));
  expect(settings).toMatchObject({ enableEdgeEvents: true, renderEdgeLabels: false });

  rerender(<GraphView graph={{ ...graph, nodes: graph.nodes.slice(0, 2), edges: graph.edges.slice(0, 1) }} />);
  await waitFor(() => expect(sigmaHarness.construct).toHaveBeenCalledTimes(2));
  expect(sigmaHarness.kill).toHaveBeenCalledTimes(1);

  unmount();
  expect(sigmaHarness.kill).toHaveBeenCalledTimes(2);
});

test("keeps full node and edge details discoverable on hover", async () => {
  render(<GraphView graph={graph} />);
  await waitFor(() => expect(sigmaHarness.construct).toHaveBeenCalledTimes(1));

  act(() => {
    sigmaHarness.listeners.get("enterNode")?.({
      node: "vendor-1",
      event: { x: 40, y: 24 },
    });
  });
  expect(screen.getByRole("tooltip")).toHaveTextContent("Vendor One");

  act(() => {
    sigmaHarness.listeners.get("enterEdge")?.({
      edge: "edge-1",
      event: { x: 40, y: 24 },
    });
  });
  expect(screen.getByRole("tooltip")).toHaveTextContent("1 works, ₹10,00,000 sanctioned");

  act(() => {
    sigmaHarness.listeners.get("leaveEdge")?.({});
  });
  expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
});

test("keeps hover details inside the bounded canvas", async () => {
  render(<GraphView graph={graph} />);
  await waitFor(() => expect(sigmaHarness.construct).toHaveBeenCalledTimes(1));
  const surface = screen.getByRole("img", { name: STRINGS.fund_flow.subtitle });
  Object.defineProperties(surface, {
    clientWidth: { configurable: true, value: 800 },
    clientHeight: { configurable: true, value: 432 },
  });

  act(() => {
    sigmaHarness.listeners.get("enterNode")?.({
      node: "vendor-1",
      event: { x: 780, y: 12 },
    });
  });

  expect(screen.getByRole("tooltip")).toHaveAttribute("data-horizontal", "left");
  expect(screen.getByRole("tooltip")).toHaveAttribute("data-vertical", "below");
});

test("contains renderer initialization failures instead of rejecting globally", async () => {
  const consoleError = vi.spyOn(console, "error").mockImplementation(() => undefined);
  sigmaHarness.constructionError = new Error("WebGL unavailable");

  render(<GraphView graph={graph} />);
  const surface = screen.getByRole("img", { name: STRINGS.fund_flow.subtitle });

  await waitFor(() => expect(surface).toHaveAttribute("data-render-state", "failed"));
  expect(consoleError).toHaveBeenCalledWith(
    "Fund-flow renderer failed to initialise.",
    sigmaHarness.constructionError,
  );
  consoleError.mockRestore();
});

test("does not load Sigma for the existing empty state", async () => {
  render(<GraphView graph={{ nodes: [], edges: [] }} />);

  expect(screen.getByText(STRINGS.fund_flow.empty)).toBeInTheDocument();
  expect(screen.getByText(STRINGS.fund_flow.empty_body)).toBeInTheDocument();
  await Promise.resolve();
  expect(sigmaHarness.construct).not.toHaveBeenCalled();
});
