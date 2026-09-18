import { describe, expect, it } from "vitest";
import { EMPTY_FILTERS, filtersToQuery, listSearchParams, readListParams } from "./filters";

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
