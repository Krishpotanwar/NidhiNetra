// T6: one duty sentence per role lens, every number taken from the
// scope-only GET /api/pendency summary (ruling R5) -- never works-page meta,
// which moves with the flag/category filters and would make the sentence
// disagree with the scope the officer is actually looking at.
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { renderTemplate, STRINGS } from "@/lib/strings";
import { formatIndianInt } from "@/lib/format";
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
