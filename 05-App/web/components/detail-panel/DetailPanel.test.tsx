// F-01 (nemotronreview.md): a work's record must show the District Authority
// (IDA_NAME) and the Implementing agency (IA_NAME) as two separately labelled
// values, and never put the authority where the agency belongs.
import type { ReactNode } from "react";
import { render, screen } from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { STRINGS, renderTemplate } from "@/lib/strings";
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
    work_stage: "Work partially Completed",
    completion_date: "2024-09-05",
    has_public_document: true,
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
    days_to_sanction: 7,
    days_since_sanction: 30,
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

test("says so plainly when the record has no description", () => {
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

test("lists the portal's work stage, completion date and document presence as published", () => {
  render(<DetailPanel row={row()} onClose={() => {}} quotaN={10} />);

  // Exactly as published, like activity_name -- no title-casing of the
  // portal's own irregular capitalization ("partially" stays lowercase).
  expect(screen.getByText(fields.work_stage).nextElementSibling).toHaveTextContent(
    "Work partially Completed",
  );
  expect(screen.getByText(fields.completion_date).nextElementSibling).toHaveTextContent(
    formatDate("2024-09-05"),
  );
  expect(screen.getByText(fields.has_public_document).nextElementSibling).toHaveTextContent(
    STRINGS.detail_panel.document_yes,
  );
});

test("shows document presence as published when the portal recorded no attachment", () => {
  render(<DetailPanel row={row({ has_public_document: false })} onClose={() => {}} quotaN={10} />);

  expect(screen.getByText(fields.has_public_document).nextElementSibling).toHaveTextContent(
    STRINGS.detail_panel.document_no,
  );
});

test("says so plainly when the portal has no stage, completion date or document flag", () => {
  render(
    <DetailPanel
      row={row({ work_stage: null, completion_date: null, has_public_document: null })}
      onClose={() => {}}
      quotaN={10}
    />,
  );

  expect(screen.getByText(fields.work_stage).nextElementSibling).toHaveTextContent(
    STRINGS.missing_fields.generic,
  );
  expect(screen.getByText(fields.completion_date).nextElementSibling).toHaveTextContent(
    STRINGS.missing_fields.date,
  );
  expect(screen.getByText(fields.has_public_document).nextElementSibling).toHaveTextContent(
    STRINGS.missing_fields.generic,
  );
});

// T5: "Timelines against the guidelines" -- the three MoSPI pendency facts
// for this one work, each an independent branch (R4/D4).
const pendency = STRINGS.pendency;

test("states the measured days to sanction when both dates are present", () => {
  render(<DetailPanel row={row({ days_to_sanction: 50 })} onClose={() => {}} quotaN={10} />);

  expect(
    screen.getByText(renderTemplate(pendency.detail_days_to_sanction, { days: 50 })),
  ).toBeInTheDocument();
  expect(screen.queryByText(pendency.detail_dates_missing)).not.toBeInTheDocument();
});

test("says the recommendation or sanction date is not published when days_to_sanction is null", () => {
  render(
    <DetailPanel
      row={row({ days_to_sanction: null, recommendation_date: null })}
      onClose={() => {}}
      quotaN={10}
    />,
  );

  expect(screen.getByText(pendency.detail_dates_missing)).toBeInTheDocument();
  expect(
    screen.queryByText(renderTemplate(pendency.detail_days_to_sanction, { days: 50 })),
  ).not.toBeInTheDocument();
});

test("flags a work open past one year when under implementation and sanctioned over 365 days ago", () => {
  render(
    <DetailPanel
      row={row({ completion_status: "In Progress", days_since_sanction: 400 })}
      onClose={() => {}}
      quotaN={10}
    />,
  );

  expect(screen.getByText(renderTemplate(pendency.detail_open, { days: 400 }))).toBeInTheDocument();
});

test("does not flag open past one year at 365 days or under", () => {
  render(
    <DetailPanel
      row={row({ completion_status: "In Progress", days_since_sanction: 365 })}
      onClose={() => {}}
      quotaN={10}
    />,
  );

  expect(screen.queryByText(renderTemplate(pendency.detail_open, { days: 365 }))).not.toBeInTheDocument();
});

test("does not flag open past one year for a work no longer under implementation", () => {
  render(
    <DetailPanel
      row={row({ completion_status: "Completed", days_since_sanction: 400 })}
      onClose={() => {}}
      quotaN={10}
    />,
  );

  expect(screen.queryByText(renderTemplate(pendency.detail_open, { days: 400 }))).not.toBeInTheDocument();
});

test("shows payments recorded when expenditure is above zero", () => {
  render(<DetailPanel row={row({ expenditure_amount_inr: 250000 })} onClose={() => {}} quotaN={10} />);

  expect(screen.getByText(pendency.detail_payment_seen)).toBeInTheDocument();
});

test("shows no payment recorded when spend is zero more than 90 days after sanction", () => {
  render(
    <DetailPanel
      row={row({ expenditure_amount_inr: 0, days_since_sanction: 120 })}
      onClose={() => {}}
      quotaN={10}
    />,
  );

  expect(screen.getByText(renderTemplate(pendency.detail_no_payment, { days: 120 }))).toBeInTheDocument();
});

test("never claims payments for a zero-spend work within 90 days of sanction (R4)", () => {
  render(
    <DetailPanel
      row={row({ expenditure_amount_inr: 0, days_since_sanction: 30 })}
      onClose={() => {}}
      quotaN={10}
    />,
  );

  expect(screen.queryByText(pendency.detail_payment_seen)).not.toBeInTheDocument();
  expect(
    screen.queryByText(renderTemplate(pendency.detail_no_payment, { days: 30 })),
  ).not.toBeInTheDocument();
});

// T8B: the early-warning line in the same "Timelines against the
// guidelines" section, keyed off the row's own flag -- no separate fetch.
const earlyWarning = STRINGS.early_warning;

test("shows the early-warning line when the row is in the watch tenth", () => {
  render(<DetailPanel row={row({ early_warning: true })} onClose={() => {}} quotaN={10} />);

  expect(screen.getByText(earlyWarning.detail)).toBeInTheDocument();
});

test("shows no early-warning line when the row is not in the watch tenth", () => {
  render(<DetailPanel row={row({ early_warning: false })} onClose={() => {}} quotaN={10} />);

  expect(screen.queryByText(earlyWarning.detail)).not.toBeInTheDocument();
});

test("shows both descriptions and the quoted spans for a near-copy shared-description entry", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => ({
      ok: true,
      status: 200,
      json: async () => ({
        success: true,
        error: null,
        meta: null,
        data: {
          duplicate_context: [
            {
              candidate_id: 20,
              finder: "judged_same_asset_same_place",
              threshold_crossing_batch: false,
              text: "Shed at Kheda Chowk",
              text_b: "Shed near Kheda Chowk village",
              quote_a: "Kheda Chowk",
              quote_b: "Kheda Chowk",
              work_relation: "duplicate_candidate",
              work_count: 2,
              other_work_ids: ["MPLADS-FX-0099"],
              status: "pending",
            },
          ],
        },
      }),
    })),
  );

  render(<DetailPanel row={row()} onClose={() => {}} quotaN={10} />);

  expect(await screen.findByText("Shed at Kheda Chowk")).toBeInTheDocument();
  expect(screen.getByText("Shed near Kheda Chowk village")).toBeInTheDocument();
  expect(
    screen.getByText('The words a model quoted from each description: “Kheda Chowk” and “Kheda Chowk”.'),
  ).toBeInTheDocument();
});
