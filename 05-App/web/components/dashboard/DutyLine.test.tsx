// T6: one duty sentence per role lens, every number taken from the
// scope-only GET /api/pendency summary (ruling R5) -- never works-page meta,
// which moves with the flag/category filters and would make the sentence
// disagree with the scope the officer is actually looking at.
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { renderTemplate, STRINGS } from "@/lib/strings";
import { formatIndianInt } from "@/lib/format";
import { EMPTY_FILTERS, isLensScoped } from "@/lib/filters";
import type { PendencySummary } from "@/lib/types";
import { DutyLine } from "./DutyLine";

const copy = STRINGS.lens;

function summary(overrides: Partial<PendencySummary> = {}): PendencySummary {
  return {
    as_of: "2026-09-04",
    population_n: 44810,
    population_inr: 24967300000,
    kinds: {
      late_sanction: { count: 33204, sanctioned_inr: 18106900000, median_days_to_sanction: 90 },
      open_past_one_year: { count: 10856, sanctioned_inr: 5962400000 },
      no_payment_90_days: { count: 17441, sanctioned_inr: 9068700000 },
    },
    district_authority_n: 729,
    quota_sum: 4820,
    third_party: { at_or_above_25_lakh: 986, between_15_and_25_lakh: 1739, required_n: 1856 },
    groups: null,
    ...overrides,
  };
}

describe("DutyLine", () => {
  it("renders nothing while pendency is null", () => {
    const { container } = render(<DutyLine view="ministry" pendency={null} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("states the Ministry's duty: the sum of every District Authority's own quota, in view", () => {
    render(<DutyLine view="ministry" pendency={summary()} />);
    expect(
      screen.getByText(
        renderTemplate(copy.duty_ministry, { da_n: formatIndianInt(729), quota_sum: formatIndianInt(4820) }),
      ),
    ).toBeInTheDocument();
  });

  it("states the State Nodal Authority's third-party inspection duty", () => {
    render(<DutyLine view="state" pendency={summary()} />);
    expect(
      screen.getByText(
        renderTemplate(copy.duty_state, {
          n25: formatIndianInt(986),
          n15: formatIndianInt(1739),
          required: formatIndianInt(1856),
        }),
      ),
    ).toBeInTheDocument();
  });

  it("states the District Authority's own quota (R5: quota_sum and population_n, scope-only)", () => {
    render(
      <DutyLine
        view="district"
        pendency={summary({ population_n: 813, quota_sum: 82, district_authority_n: 1 })}
      />,
    );
    expect(
      screen.getByText(
        renderTemplate(copy.duty_district, { quota: formatIndianInt(82), n: formatIndianInt(813) }),
      ),
    ).toBeInTheDocument();
  });

  it("states the MP's late-sanction and open-past-a-year counts for the constituency", () => {
    render(<DutyLine view="mp" pendency={summary({ population_n: 120 })} />);
    expect(
      screen.getByText(
        renderTemplate(copy.duty_mp, {
          late: formatIndianInt(33204),
          n: formatIndianInt(120),
          open: formatIndianInt(10856),
        }),
      ),
    ).toBeInTheDocument();
  });
});

// T6 fix (review round 1, Critical): DashboardClient and InspectionListClient
// both call DutyLine as `pendency={isLensScoped(filters) ? pendency.data :
// null}` -- never the raw fetched summary. Mounting either of those two
// components here would need mocking fetchSummary/fetchFacets/fetchPendency/
// fetchWorksPage/triggerRefresh and useApiResource's async lifecycle for
// coverage this same-shaped composition already gives directly, so this
// exercises the exact call-site expression instead: a "real-looking" -- and,
// before this fix, actually-returned -- national summary must still produce
// no sentence for an unscoped district/mp lens, and must produce one the
// moment the lens is scoped.
describe("the call-site gate (isLensScoped), matching DashboardClient/InspectionListClient's own wiring", () => {
  it("renders no duty sentence for the district lens before a District Authority is chosen, even with a (national) summary already fetched", () => {
    const filters = { ...EMPTY_FILTERS, view: "district" as const };
    const { container } = render(
      <DutyLine view={filters.view} pendency={isLensScoped(filters) ? summary() : null} />,
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("renders the district duty sentence once a District Authority is chosen", () => {
    const filters = { ...EMPTY_FILTERS, view: "district" as const, districtAuthority: "Some DA" };
    render(<DutyLine view={filters.view} pendency={isLensScoped(filters) ? summary() : null} />);
    expect(
      screen.getByText(
        renderTemplate(copy.duty_district, { quota: formatIndianInt(4820), n: formatIndianInt(44810) }),
      ),
    ).toBeInTheDocument();
  });

  it("renders no duty sentence for the mp lens before a constituency is chosen, even with a (national) summary already fetched", () => {
    const filters = { ...EMPTY_FILTERS, view: "mp" as const };
    const { container } = render(
      <DutyLine view={filters.view} pendency={isLensScoped(filters) ? summary() : null} />,
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("renders the mp duty sentence once a constituency is chosen", () => {
    const filters = { ...EMPTY_FILTERS, view: "mp" as const, constituency: "DHARWAD" };
    render(<DutyLine view={filters.view} pendency={isLensScoped(filters) ? summary() : null} />);
    expect(
      screen.getByText(
        renderTemplate(copy.duty_mp, {
          late: formatIndianInt(33204),
          n: formatIndianInt(44810),
          open: formatIndianInt(10856),
        }),
      ),
    ).toBeInTheDocument();
  });

  it("is unaffected for the ministry and state lenses, which always render", () => {
    render(<DutyLine view="ministry" pendency={isLensScoped(EMPTY_FILTERS) ? summary() : null} />);
    expect(
      screen.getByText(
        renderTemplate(copy.duty_ministry, { da_n: formatIndianInt(729), quota_sum: formatIndianInt(4820) }),
      ),
    ).toBeInTheDocument();
  });
});
