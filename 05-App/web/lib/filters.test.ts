import { describe, expect, it } from "vitest";
import { ALL, EMPTY_FILTERS, filtersToQuery, listSearchParams, readListParams, withView } from "./filters";

describe("vendor_id (Fund Flow's \"View linked works\" deep link)", () => {
  it("is included on the API query only when given", () => {
    expect(filtersToQuery(EMPTY_FILTERS, null, "42595").get("vendor_id")).toBe("42595");
    expect(filtersToQuery(EMPTY_FILTERS, null, null).has("vendor_id")).toBe(false);
  });

  it("round-trips through the address bar alongside the page", () => {
    const qs = listSearchParams(EMPTY_FILTERS, null, 2, "42595");
    const parsed = readListParams(qs);

    expect(parsed.vendorId).toBe("42595");
    expect(parsed.page).toBe(2);
  });

  it("is absent from the address-bar form when not given", () => {
    const parsed = readListParams(listSearchParams(EMPTY_FILTERS, null, 1));
    expect(parsed.vendorId).toBeNull();
  });
});

describe("pendency scope (T5: FilterState.pendency/districtAuthority/constituency)", () => {
  it("round-trips pendency, districtAuthority and constituency through the address bar", () => {
    const filters = {
      ...EMPTY_FILTERS,
      pendency: "late_sanction",
      districtAuthority: "DHARWAD(DEPUTY COMMISSIONER DHARWAR_IDA)",
      constituency: "DHARWAD",
    };
    const qs = listSearchParams(filters, null, 1);
    expect(qs.get("pendency")).toBe("late_sanction");
    expect(qs.get("district_authority")).toBe("DHARWAD(DEPUTY COMMISSIONER DHARWAR_IDA)");
    expect(qs.get("constituency")).toBe("DHARWAD");

    const parsed = readListParams(qs);
    expect(parsed.filters.pendency).toBe("late_sanction");
    expect(parsed.filters.districtAuthority).toBe("DHARWAD(DEPUTY COMMISSIONER DHARWAR_IDA)");
    expect(parsed.filters.constituency).toBe("DHARWAD");
  });

  it("drops an unknown pendency value back to ALL rather than reaching the API with it", () => {
    const params = new URLSearchParams({ pendency: "not_a_real_kind" });
    expect(readListParams(params).filters.pendency).toBe(ALL);
  });

  it("defaults pendency, districtAuthority and constituency to ALL when absent from the address bar", () => {
    const parsed = readListParams(new URLSearchParams());
    expect(parsed.filters.pendency).toBe(ALL);
    expect(parsed.filters.districtAuthority).toBe(ALL);
    expect(parsed.filters.constituency).toBe(ALL);
  });

  it("omits pendency, district_authority and constituency from the query when they are ALL", () => {
    const qs = filtersToQuery(EMPTY_FILTERS);
    expect(qs.has("pendency")).toBe(false);
    expect(qs.has("district_authority")).toBe(false);
    expect(qs.has("constituency")).toBe(false);
  });
});

describe("view (T6: the 'View as' role lens)", () => {
  it("defaults to ministry", () => {
    expect(EMPTY_FILTERS.view).toBe("ministry");
  });

  it("round-trips a non-default view through the address bar", () => {
    const filters = { ...EMPTY_FILTERS, view: "district" as const };
    const qs = listSearchParams(filters, null, 1);
    expect(qs.get("view")).toBe("district");
    expect(readListParams(qs).filters.view).toBe("district");
  });

  it("omits view from the address bar when it is the default ministry", () => {
    const qs = listSearchParams(EMPTY_FILTERS, null, 1);
    expect(qs.has("view")).toBe(false);
  });

  it("drops an unknown view back to ministry rather than reaching the API with it", () => {
    const params = new URLSearchParams({ view: "not_a_real_view" });
    expect(readListParams(params).filters.view).toBe("ministry");
  });

  it("is never sent to the API: filtersToQuery does not carry it", () => {
    const filters = { ...EMPTY_FILTERS, view: "mp" as const };
    expect(filtersToQuery(filters).has("view")).toBe(false);
  });

  it("withView clears states, districtAuthority and constituency", () => {
    const filters = {
      ...EMPTY_FILTERS,
      view: "state" as const,
      states: ["Bihar"],
      districtAuthority: "Some DA",
      constituency: "DHARWAD",
    };
    const next = withView(filters, "district");
    expect(next).toEqual({ ...EMPTY_FILTERS, view: "district" });
  });
});
