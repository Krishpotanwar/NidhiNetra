import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { INSPECTOR_ID_STORAGE_KEY } from "@/lib/preferences";
import { AliasReviewQueue } from "./AliasReviewQueue";

const candidate = {
  candidate_id: 7,
  entity_type: "vendor" as const,
  proposed_canonical_id: "96542",
  alias_label: "ACME CONSTRUCTIONS",
  reason: "label_has_multiple_identifiers" as const,
  evidence_work_ids: ["W1", "W2"],
  status: "pending" as const,
  current_review: null,
  evidence_works: [
    {
      work_id: "W1",
      state: "Karnataka",
      constituency: "Dharwad",
      mp_name: "Member One",
      implementing_district_authority: "Dharwad District Authority",
      implementing_agency: "Dharwad Zilla Panchayat Engineering Division",
      vendor_id: "96542",
      vendor_name: "ACME CONSTRUCTIONS",
      work_category: "Road",
      sanctioned_amount_inr: 1_000_000,
      completion_status: "In Progress",
    },
    {
      work_id: "W2",
      state: "Karnataka",
      constituency: "Dharwad",
      mp_name: "Member Two",
      implementing_district_authority: "Dharwad District Authority",
      implementing_agency: "Dharwad Zilla Panchayat Engineering Division",
      vendor_id: "88421",
      vendor_name: "ACME CONSTRUCTIONS",
      work_category: "School",
      sanctioned_amount_inr: 500_000,
      completion_status: "Sanctioned",
    },
  ],
};

function response(data: unknown, meta: Record<string, unknown> | null = null, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => ({ success: status < 400, data, error: status < 400 ? null : "raw error", meta }),
  } as Response;
}

function queueResponse(rows: unknown[], total = rows.length, page = 1, totalPages = 1): Response {
  return response(rows, { page, page_size: 25, total, total_pages: totalPages });
}

beforeEach(() => {
  vi.stubGlobal("fetch", vi.fn());
  vi.stubGlobal("matchMedia", vi.fn(() => ({ matches: true })));
  localStorage.clear();
});

afterEach(() => {
  vi.unstubAllGlobals();
  localStorage.clear();
});

describe("AliasReviewQueue", () => {
  test("shows the pending badge, plain-language reason, evidence drill-downs, and exact actions", async () => {
    const fetchMock = global.fetch as ReturnType<typeof vi.fn>;
    fetchMock.mockResolvedValueOnce(queueResponse([candidate, { ...candidate, candidate_id: 8 }]));

    render(<AliasReviewQueue />);

    const badge = await screen.findByRole("link", { name: "2 pending" });
    expect(badge).toHaveAttribute("href", "#entity-alias-review");
    expect(screen.getByRole("table", { name: "Vendor records waiting for review" })).toBeInTheDocument();
    expect(screen.getAllByText("Acme Constructions")).toHaveLength(2);
    expect(screen.getAllByText("Vendor ID 96542")).toHaveLength(2);
    expect(screen.getAllByText("This vendor name appears under more than one vendor ID.")).toHaveLength(2);
    expect(screen.getAllByRole("link", { name: "W1" })[0]).toHaveAttribute(
      "href",
      "/inspections?q=W1",
    );
    expect(screen.getAllByRole("button", { name: "These are the same" })).toHaveLength(2);
    expect(screen.getAllByRole("button", { name: "These are different" })).toHaveLength(2);
  });

  test("shows the competing vendor identities beside their evidence works", async () => {
    const fetchMock = global.fetch as ReturnType<typeof vi.fn>;
    fetchMock.mockResolvedValueOnce(queueResponse([candidate]));

    render(<AliasReviewQueue />);

    expect(await screen.findByText("Acme Constructions · Vendor ID 96542")).toBeInTheDocument();
    expect(screen.getByText("Acme Constructions · Vendor ID 88421")).toBeInTheDocument();
  });

  test("requires self-reported initials and sends the server decision enum", async () => {
    const fetchMock = global.fetch as ReturnType<typeof vi.fn>;
    fetchMock
      .mockResolvedValueOnce(queueResponse([candidate]))
      .mockResolvedValueOnce(response({ review_id: 11, status: "confirmed_merge" }))
      .mockResolvedValueOnce(queueResponse([]));

    const user = userEvent.setup();
    render(<AliasReviewQueue />);

    const same = await screen.findByRole("button", { name: "These are the same" });
    expect(same).toBeDisabled();
    await user.type(screen.getByLabelText("Your initials"), "AB");
    expect(same).toBeEnabled();
    await user.click(same);

    await waitFor(() => expect(screen.getByText("No vendor records are waiting for review.")).toBeInTheDocument());
    const post = fetchMock.mock.calls.find(([, init]) => (init as RequestInit | undefined)?.method === "POST");
    expect(post?.[0]).toContain("/api/entity-aliases/7/review");
    expect(JSON.parse((post?.[1] as RequestInit).body as string)).toEqual({
      status: "confirmed_merge",
      reviewed_by: "AB",
      reviewer_note: "",
    });
    expect(localStorage.getItem(INSPECTOR_ID_STORAGE_KEY)).toBe("AB");
  });

  test("the distinct action posts rejected_distinct", async () => {
    localStorage.setItem(INSPECTOR_ID_STORAGE_KEY, "RK");
    const fetchMock = global.fetch as ReturnType<typeof vi.fn>;
    fetchMock
      .mockResolvedValueOnce(queueResponse([candidate]))
      .mockResolvedValueOnce(response({ review_id: 12, status: "rejected_distinct" }))
      .mockResolvedValueOnce(queueResponse([]));

    const user = userEvent.setup();
    render(<AliasReviewQueue />);
    await user.click(await screen.findByRole("button", { name: "These are different" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(3));
    await screen.findByText("No vendor records are waiting for review.");
    const post = fetchMock.mock.calls[1];
    expect(JSON.parse((post[1] as RequestInit).body as string).status).toBe("rejected_distinct");
  });

  test("reports a failed decision as a save error without removing the row", async () => {
    localStorage.setItem(INSPECTOR_ID_STORAGE_KEY, "RK");
    const fetchMock = global.fetch as ReturnType<typeof vi.fn>;
    fetchMock.mockResolvedValueOnce(queueResponse([candidate])).mockRejectedValueOnce(new Error("offline"));

    const user = userEvent.setup();
    render(<AliasReviewQueue />);
    await user.click(await screen.findByRole("button", { name: "These are the same" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Could not save this review decision. Try again.",
    );
    expect(screen.getByText("Vendor ID 96542")).toBeInTheDocument();
  });

  test("uses the restrained DotCanvas empty and error states", async () => {
    const fetchMock = global.fetch as ReturnType<typeof vi.fn>;
    fetchMock.mockResolvedValueOnce(queueResponse([]));
    const { unmount } = render(<AliasReviewQueue />);
    expect(await screen.findByText("No vendor records are waiting for review.")).toBeInTheDocument();
    unmount();

    fetchMock.mockResolvedValueOnce(response(null, null, 503));
    render(<AliasReviewQueue />);
    expect(await screen.findByText("Could not load vendor records for review.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
  });

  test("shares the keyboard-operable row-treatment preference", async () => {
    const fetchMock = global.fetch as ReturnType<typeof vi.fn>;
    fetchMock.mockResolvedValueOnce(queueResponse([candidate]));
    const user = userEvent.setup();
    render(<AliasReviewQueue />);

    const tableCard = await screen.findByTestId("alias-review-card");
    expect(tableCard).toHaveAttribute("data-treatment", "two-line");
    const group = screen.getByRole("radiogroup", { name: "Row treatment" });
    await user.click(within(group).getByRole("radio", { name: "Hover reveal" }));
    expect(tableCard).toHaveAttribute("data-treatment", "hover-reveal");
  });

  test("paginates the pending queue through the API", async () => {
    const fetchMock = global.fetch as ReturnType<typeof vi.fn>;
    fetchMock
      .mockResolvedValueOnce(queueResponse([candidate], 26, 1, 2))
      .mockResolvedValueOnce(queueResponse([{ ...candidate, candidate_id: 9 }], 26, 2, 2));
    const user = userEvent.setup();
    render(<AliasReviewQueue />);

    await user.click(await screen.findByRole("button", { name: "Next page" }));
    await waitFor(() => expect(String(fetchMock.mock.calls[1][0])).toContain("page=2"));
    expect(screen.getByRole("button", { name: "Previous page" })).toBeEnabled();
  });

  test("returns to the previous page after reviewing its last row", async () => {
    localStorage.setItem(INSPECTOR_ID_STORAGE_KEY, "RK");
    const fetchMock = global.fetch as ReturnType<typeof vi.fn>;
    const lastCandidate = { ...candidate, candidate_id: 9, alias_label: "LAST RECORD" };
    const previousCandidate = { ...candidate, candidate_id: 8, alias_label: "EARLIER RECORD" };
    fetchMock
      .mockResolvedValueOnce(queueResponse([previousCandidate], 26, 1, 2))
      .mockResolvedValueOnce(queueResponse([lastCandidate], 26, 2, 2))
      .mockResolvedValueOnce(response({ ...lastCandidate, status: "confirmed_merge" }))
      .mockResolvedValueOnce(queueResponse([previousCandidate], 25, 1, 1));

    const user = userEvent.setup();
    render(<AliasReviewQueue />);
    await user.click(await screen.findByRole("button", { name: "Next page" }));
    expect(await screen.findByText("Last Record")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "These are the same" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(4));
    expect(String(fetchMock.mock.calls[3][0])).toContain("page=1");
    expect(await screen.findByText("Earlier Record")).toBeInTheDocument();
    expect(screen.queryByText("No vendor records are waiting for review.")).not.toBeInTheDocument();
  });
});
