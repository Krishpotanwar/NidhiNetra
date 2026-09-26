// T5: the Dashboard's three MoSPI pendency cards (late sanction, open past
// one year, no payment after 90 days). R3: a card's link carries scope
// (states/districtAuthority/constituency) plus pendency=<kind> only, so its
// count always equals the matching Inspection List total.
import type { ReactNode } from "react";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { STRINGS } from "@/lib/strings";
import { formatCurrencyCrore, formatDate, formatIndianInt } from "@/lib/format";
import { EMPTY_FILTERS, inspectionListHref } from "@/lib/filters";
import type { PendencySummary } from "@/lib/types";
import { PendencyCards } from "./PendencyCards";

vi.mock("next/link", () => ({
  default: ({ href, children, ...rest }: { href: string; children: ReactNode }) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
}));

const copy = STRINGS.pendency;

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

describe("PendencyCards", () => {
  it("shows each card's label, formatted count, value line and context sentence", () => {
    render(<PendencyCards summary={summary()} status="ready" onRetry={() => {}} filters={EMPTY_FILTERS} />);

    expect(screen.getByText(copy.late_sanction_label)).toBeInTheDocument();
    expect(screen.getByText(formatIndianInt(33204))).toBeInTheDocument();
    expect(
      screen.getByText(`${formatIndianInt(33204)} works, ${formatCurrencyCrore(18106900000)} sanctioned`),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        "Sanctioned more than 45 days after the MP's recommendation (para 3.2.4 counts from receipt). Median 90 days.",
      ),
    ).toBeInTheDocument();

    expect(screen.getByText(copy.open_past_one_year_label)).toBeInTheDocument();
    expect(screen.getByText(formatIndianInt(10856))).toBeInTheDocument();
    expect(screen.getByText(copy.open_past_one_year_context)).toBeInTheDocument();

    expect(screen.getByText(copy.no_payment_label)).toBeInTheDocument();
    expect(screen.getByText(formatIndianInt(17441))).toBeInTheDocument();
    expect(screen.getByText(copy.no_payment_context)).toBeInTheDocument();
  });

  it("links each card to the matching Timeline-filtered list, scope only (R3)", () => {
    const filters = { ...EMPTY_FILTERS, states: ["Karnataka"], districtAuthority: "Some DA", constituency: "DHARWAD" };
    render(<PendencyCards summary={summary()} status="ready" onRetry={() => {}} filters={filters} />);

    const links = screen.getAllByRole("link", { name: copy.view_list });
    expect(links).toHaveLength(3);
    const kinds = ["late_sanction", "open_past_one_year", "no_payment_90_days"];
    links.forEach((link, i) => {
      expect(link).toHaveAttribute(
        "href",
        inspectionListHref({
          ...EMPTY_FILTERS,
          states: filters.states,
          districtAuthority: filters.districtAuthority,
          constituency: filters.constituency,
          pendency: kinds[i],
        }),
      );
    });
  });

  it("shows the caveat under the row, with the snapshot's as-of date", () => {
    render(<PendencyCards summary={summary()} status="ready" onRetry={() => {}} filters={EMPTY_FILTERS} />);

    expect(
      screen.getByText(
        `The expenditure record is dated ${formatDate("2026-09-04")} and may be incomplete. A missing payment is a prompt to check.`,
      ),
    ).toBeInTheDocument();
  });

  it("shows a loading skeleton and no figures or links while there is no summary yet", () => {
    render(<PendencyCards summary={null} status="loading" onRetry={() => {}} filters={EMPTY_FILTERS} />);

    expect(screen.queryByText(copy.late_sanction_label)).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: copy.view_list })).not.toBeInTheDocument();
  });

  it("shows an error state with a retry action when the fetch fails and nothing is cached", () => {
    const onRetry = vi.fn();
    render(<PendencyCards summary={null} status="error" onRetry={onRetry} filters={EMPTY_FILTERS} />);

    screen.getByRole("button", { name: STRINGS.data_states.api_unreachable.action }).click();
    expect(onRetry).toHaveBeenCalledOnce();
  });
});
