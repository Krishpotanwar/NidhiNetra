// T8B: the Reports page's "How the early warning works" paragraph. Only the
// early-warning behaviour is covered here (a fresh test file, ReportsClient
// had none before) -- not a full re-test of the recorded-inspections table,
// which the task brief does not touch.
import { render, screen } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import { renderTemplate, STRINGS } from "@/lib/strings";
import { formatDate } from "@/lib/format";
import { ReportsClient } from "./ReportsClient";

function envelope(data: unknown): Response {
  return {
    ok: true,
    status: 200,
    json: async () => ({ success: true, data, error: null, meta: null }),
  } as Response;
}

const REPORT = {
  outcomes: [],
  summary: {
    total: 0,
    ranked: { n: 0, reached_work: 0, issues: 0, within_quota: 0, issue_rate: null },
    spot_check: { n: 0, reached_work: 0, issues: 0, within_quota: 0, issue_rate: null },
    min_reached_per_group: 30,
    comparison_ready: false,
  },
};

const EARLY_WARNING = {
  model_version: "early_warning_v1",
  data_as_of: "2026-09-04",
  status: "shipped" as const,
  cohort: { start: "2024-07-04", train_cutoff: "2025-01-04", end: "2025-04-04", train_n: 5292, test_n: 8738 },
  features: { numeric: ["log_sanctioned", "agency_prior", "sanction_month"], categorical: ["work_category", "state"] },
  metrics: { roc_auc: 0.692, average_precision: 0.431, base_rate: 0.235, lift_at_10: 1.956 },
  scored_n: 33954,
  watch_n: 3396,
};

function mockApi(earlyWarningData: unknown) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("/api/early-warning")) return envelope(earlyWarningData);
      if (url.includes("/api/inspections")) return envelope(REPORT);
      throw new Error(`unexpected request ${url}`);
    }),
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
});

test("shows no early-warning method paragraph when the model has not shipped", async () => {
  mockApi(null);
  render(<ReportsClient />);

  await screen.findByText(STRINGS.reports.table_title);
  expect(screen.queryByText(STRINGS.early_warning.method_title)).not.toBeInTheDocument();
});

test("shows the method paragraph, filled from the API's own cohort and metrics, once shipped", async () => {
  mockApi(EARLY_WARNING);
  render(<ReportsClient />);

  const expected = renderTemplate(STRINGS.early_warning.method, {
    start: formatDate(EARLY_WARNING.cohort.start),
    cutoff: formatDate(EARLY_WARNING.cohort.train_cutoff),
    end: formatDate(EARLY_WARNING.cohort.end),
    lift: EARLY_WARNING.metrics.lift_at_10.toFixed(1),
    auc: EARLY_WARNING.metrics.roc_auc.toFixed(2),
  });

  expect(await screen.findByText(STRINGS.early_warning.method_title)).toBeInTheDocument();
  expect(screen.getByText(expected)).toBeInTheDocument();
});
