// T6: the "View as" role lens control -- Ministry/State Nodal Authority/
// District Authority/Member of Parliament -- and its matching scope picker.
import { useState } from "react";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it } from "vitest";
import { STRINGS, setLocale } from "@/lib/strings";
import { EMPTY_FILTERS, type FilterState } from "@/lib/filters";
import type { Facets } from "@/lib/types";
import { FilterPanel, type PreviewState } from "./FilterPanel";

const lens = STRINGS.lens;
const filtersCopy = STRINGS.filters;

const FACETS: Facets = {
  states: [
    { value: "Bihar", count: 120 },
    { value: "Odisha", count: 80 },
  ],
  years: [],
  categories: [],
  flags: [],
  district_authorities: [{ value: "DHARWAD(DEPUTY COMMISSIONER DHARWAR_IDA)", count: 42 }],
  constituencies: [{ value: "DHARWAD", count: 12, mp_name: "Pralhad Venkatesh Joshi" }],
};

function Harness({
  initial = EMPTY_FILTERS,
  earlyWarningAvailable,
}: {
  initial?: FilterState;
  earlyWarningAvailable?: boolean;
}) {
  const [value, setValue] = useState<FilterState>(initial);
  const [preview, setPreview] = useState<PreviewState>("loaded");
  return (
    <FilterPanel
      value={value}
      onChange={setValue}
      facets={FACETS}
      previewState={preview}
      onPreviewStateChange={setPreview}
      earlyWarningAvailable={earlyWarningAvailable}
    />
  );
}

describe("FilterPanel: the 'View as' role lens (T6)", () => {
  it("defaults to Ministry with no scope picker shown", () => {
    render(<Harness />);

    const group = screen.getByRole("radiogroup", { name: lens.view_label });
    expect(within(group).getByRole("radio", { name: lens.ministry })).toHaveAttribute("aria-checked", "true");
    for (const label of [lens.state, lens.district, lens.mp]) {
      expect(within(group).getByRole("radio", { name: label })).toHaveAttribute("aria-checked", "false");
    }

    expect(screen.queryByRole("button", { name: new RegExp(filtersCopy.all_states) })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: new RegExp(lens.all_district_authorities) })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: new RegExp(lens.choose_constituency) })).not.toBeInTheDocument();
  });

  it("shows the multi StateSelect only under the State Nodal Authority lens", async () => {
    const user = userEvent.setup();
    render(<Harness />);

    await user.click(screen.getByRole("radio", { name: lens.state }));

    expect(screen.getByRole("button", { name: new RegExp(filtersCopy.all_states) })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: new RegExp(lens.all_district_authorities) })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: new RegExp(lens.choose_constituency) })).not.toBeInTheDocument();
  });

  it("shows a single-choice District Authority picker under that lens", async () => {
    const user = userEvent.setup();
    render(<Harness />);

    await user.click(screen.getByRole("radio", { name: lens.district }));

    expect(screen.getByRole("button", { name: new RegExp(lens.all_district_authorities) })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: new RegExp(filtersCopy.all_states) })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: new RegExp(lens.choose_constituency) })).not.toBeInTheDocument();
  });

  it("shows a single-choice constituency picker, labelled '{constituency}, {mp_name}', under the MP lens", () => {
    // Seeded rather than clicked through the popover: the closed trigger's
    // own summary already runs the selected value through optionLabel
    // (StateSelect's labelFor), so this exercises the real formatting
    // without needing to open the Radix popover at all.
    render(<Harness initial={{ ...EMPTY_FILTERS, view: "mp", constituency: "DHARWAD" }} />);

    expect(screen.getByRole("button", { name: /Dharwad, Pralhad Venkatesh Joshi/ })).toBeInTheDocument();
  });

  it("clears states, districtAuthority and constituency when the lens is switched, even back to the same one", async () => {
    const user = userEvent.setup();
    const seeded: FilterState = {
      ...EMPTY_FILTERS,
      view: "district",
      districtAuthority: "DHARWAD(DEPUTY COMMISSIONER DHARWAR_IDA)",
    };
    render(<Harness initial={seeded} />);
    expect(screen.getByRole("button", { name: /DHARWAD\(DEPUTY COMMISSIONER DHARWAR_IDA\)/ })).toBeInTheDocument();

    await user.click(screen.getByRole("radio", { name: lens.mp }));
    await user.click(screen.getByRole("radio", { name: lens.district }));

    expect(screen.getByRole("button", { name: new RegExp(lens.all_district_authorities) })).toBeInTheDocument();
  });

  it("choosing a District Authority replaces the value and closes the popover", async () => {
    const user = userEvent.setup();
    render(<Harness initial={{ ...EMPTY_FILTERS, view: "district" }} />);

    await user.click(screen.getByRole("button", { name: new RegExp(lens.all_district_authorities) }));
    await user.click(screen.getByText("DHARWAD(DEPUTY COMMISSIONER DHARWAR_IDA)"));

    // Exactly one match left (the closed trigger's own summary): the
    // popover's option list is gone, proving the choice closed it.
    expect(screen.getAllByText("DHARWAD(DEPUTY COMMISSIONER DHARWAR_IDA)")).toHaveLength(1);
    expect(screen.getByRole("button", { name: /DHARWAD\(DEPUTY COMMISSIONER DHARWAR_IDA\)/ })).toBeInTheDocument();
  });
});

describe("FilterPanel: the early-warning Timeline option (T8B)", () => {
  const pendencyCopy = STRINGS.pendency;
  const earlyWarningCopy = STRINGS.early_warning;

  // Seeded with pendency already set to "early_warning" rather than opened
  // through the popover (same technique as the MP-lens test above): the
  // closed trigger's own summary already runs the selected value through
  // SelectControl's own option lookup, so this exercises the real
  // shown-or-hidden logic without needing to drive Radix Select's portal.
  it("falls back to 'All timelines' when the model has not shipped", () => {
    render(<Harness initial={{ ...EMPTY_FILTERS, pendency: "early_warning" }} />);
    expect(screen.getByRole("combobox", { name: pendencyCopy.filter_label })).toHaveTextContent(
      pendencyCopy.filter_all,
    );
  });

  it("shows 'At risk of running late' once the caller says the model has shipped", () => {
    render(<Harness initial={{ ...EMPTY_FILTERS, pendency: "early_warning" }} earlyWarningAvailable />);
    expect(screen.getByRole("combobox", { name: pendencyCopy.filter_label })).toHaveTextContent(
      earlyWarningCopy.filter,
    );
  });
});

describe("FilterPanel: lens labels track the Hindi overlay at render time (T11B R24)", () => {
  afterEach(() => {
    setLocale("en");
  });

  it("shows the Hindi lens labels when the locale is already Hindi at mount, not the English labels frozen at module load", () => {
    setLocale("hi");
    render(<Harness />);

    const group = screen.getByRole("radiogroup", { name: lens.view_label });
    expect(within(group).getByRole("radio", { name: lens.ministry })).toBeInTheDocument();
    expect(within(group).getByRole("radio", { name: lens.state })).toBeInTheDocument();
    expect(within(group).getByRole("radio", { name: lens.district })).toBeInTheDocument();
    expect(within(group).getByRole("radio", { name: lens.mp })).toBeInTheDocument();
  });
});
