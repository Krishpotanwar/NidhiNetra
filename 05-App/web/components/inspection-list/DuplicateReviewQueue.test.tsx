import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { INSPECTOR_ID_STORAGE_KEY } from "@/lib/preferences";
import { DuplicateReviewQueue } from "./DuplicateReviewQueue";

const candidate = {
  candidate_id: 7,
  finder: "identical_batch" as const,
  scope: "DHARWAD",
  threshold_crossing_batch: true,
  text: "PCC Road, near Ram House",
  work_ids: ["W1", "W2"],
  status: "pending" as const,
  current_review: null,
  evidence_works: [],
};

const judgedCandidate = {
  candidate_id: 20,
  finder: "judged_same_asset_same_place" as const,
  scope: "GURDASPUR",
  threshold_crossing_batch: false,
  text: "Shed at Kheda Chowk",
  text_b: "Shed near Kheda Chowk village",
  quote_a: "Kheda Chowk",
  quote_b: "Kheda Chowk",
  work_relation: "duplicate_candidate" as const,
  work_ids: ["W10", "W11"],
  status: "pending" as const,
  current_review: null,
  evidence_works: [],
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

describe("DuplicateReviewQueue", () => {
  test("shows the pending badge, the shared text, the threshold note, work links, and exact actions", async () => {
    const fetchMock = global.fetch as ReturnType<typeof vi.fn>;
    fetchMock.mockResolvedValueOnce(queueResponse([candidate, { ...candidate, candidate_id: 8 }]));

    render(<DuplicateReviewQueue />);

    const badge = await screen.findByRole("link", { name: "2 pending" });
    expect(badge).toHaveAttribute("href", "#duplicate-review");
    expect(screen.getByRole("table", { name: "Works waiting for review" })).toBeInTheDocument();
    expect(screen.getAllByText("Pcc Road, near Ram House")).toHaveLength(2);
    expect(screen.getAllByText("2 works")).toHaveLength(2);
    expect(
      screen.getAllByText(
        "Every work is under Rs 15 lakh and the group totals Rs 25 lakh or more (MPLADS Guidelines 2023, clause 4.4.2).",
      ),
    ).toHaveLength(2);
    expect(screen.getAllByRole("link", { name: "W1" })[0]).toHaveAttribute("href", "/inspections?q=W1");
    expect(screen.getAllByRole("button", { name: "These are the same" })).toHaveLength(2);
    expect(screen.getAllByRole("button", { name: "These are different" })).toHaveLength(2);
  });

  test("does not show the threshold note for a batch that does not cross it", async () => {
    const fetchMock = global.fetch as ReturnType<typeof vi.fn>;
    fetchMock.mockResolvedValueOnce(queueResponse([{ ...candidate, threshold_crossing_batch: false }]));

    render(<DuplicateReviewQueue />);

    await screen.findByText("Pcc Road, near Ram House");
    expect(screen.queryByText(/clause 4.4.2/)).not.toBeInTheDocument();
  });

  test("requires self-reported initials and sends the server decision enum", async () => {
    const fetchMock = global.fetch as ReturnType<typeof vi.fn>;
    fetchMock
      .mockResolvedValueOnce(queueResponse([candidate]))
      .mockResolvedValueOnce(response({ review_id: 11, status: "confirmed_same" }))
      .mockResolvedValueOnce(queueResponse([]));

    const user = userEvent.setup();
    render(<DuplicateReviewQueue />);

    const same = await screen.findByRole("button", { name: "These are the same" });
    expect(same).toBeDisabled();
    await user.type(screen.getByLabelText("Your initials"), "AB");
    expect(same).toBeEnabled();
    await user.click(same);

    await waitFor(() => expect(screen.getByText("No works are waiting for review.")).toBeInTheDocument());
    const post = fetchMock.mock.calls.find(([, init]) => (init as RequestInit | undefined)?.method === "POST");
    expect(post?.[0]).toContain("/api/duplicates/7/review");
    expect(JSON.parse((post?.[1] as RequestInit).body as string)).toEqual({
      status: "confirmed_same",
      reviewed_by: "AB",
      reviewer_note: "",
    });
    expect(localStorage.getItem(INSPECTOR_ID_STORAGE_KEY)).toBe("AB");
  });

  test("the different action posts rejected_different", async () => {
    localStorage.setItem(INSPECTOR_ID_STORAGE_KEY, "RK");
    const fetchMock = global.fetch as ReturnType<typeof vi.fn>;
    fetchMock
      .mockResolvedValueOnce(queueResponse([candidate]))
      .mockResolvedValueOnce(response({ review_id: 12, status: "rejected_different" }))
      .mockResolvedValueOnce(queueResponse([]));

    const user = userEvent.setup();
    render(<DuplicateReviewQueue />);
    await user.click(await screen.findByRole("button", { name: "These are different" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(3));
    await screen.findByText("No works are waiting for review.");
    const post = fetchMock.mock.calls[1];
    expect(JSON.parse((post[1] as RequestInit).body as string).status).toBe("rejected_different");
  });

  test("reports a failed decision as a save error without removing the row", async () => {
    localStorage.setItem(INSPECTOR_ID_STORAGE_KEY, "RK");
    const fetchMock = global.fetch as ReturnType<typeof vi.fn>;
    fetchMock.mockResolvedValueOnce(queueResponse([candidate])).mockRejectedValueOnce(new Error("offline"));

    const user = userEvent.setup();
    render(<DuplicateReviewQueue />);
    await user.click(await screen.findByRole("button", { name: "These are the same" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Could not save this review decision. Try again.");
    expect(screen.getByText("Pcc Road, near Ram House")).toBeInTheDocument();
  });

  test("uses the restrained DotCanvas empty and error states", async () => {
    const fetchMock = global.fetch as ReturnType<typeof vi.fn>;
    fetchMock.mockResolvedValueOnce(queueResponse([]));
    const { unmount } = render(<DuplicateReviewQueue />);
    expect(await screen.findByText("No works are waiting for review.")).toBeInTheDocument();
    unmount();

    fetchMock.mockResolvedValueOnce(response(null, null, 503));
    render(<DuplicateReviewQueue />);
    expect(await screen.findByText("Could not load works for review.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
  });

  test("shares the keyboard-operable row-treatment preference", async () => {
    const fetchMock = global.fetch as ReturnType<typeof vi.fn>;
    fetchMock.mockResolvedValueOnce(queueResponse([candidate]));
    const user = userEvent.setup();
    render(<DuplicateReviewQueue />);

    const tableCard = await screen.findByTestId("duplicate-review-card");
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
    render(<DuplicateReviewQueue />);

    await user.click(await screen.findByRole("button", { name: "Next page" }));
    await waitFor(() => expect(String(fetchMock.mock.calls[1][0])).toContain("page=2"));
    expect(screen.getByRole("button", { name: "Previous page" })).toBeEnabled();
  });

  test("returns to the previous page after reviewing its last row", async () => {
    localStorage.setItem(INSPECTOR_ID_STORAGE_KEY, "RK");
    const fetchMock = global.fetch as ReturnType<typeof vi.fn>;
    const lastCandidate = { ...candidate, candidate_id: 9, text: "Last road text" };
    const previousCandidate = { ...candidate, candidate_id: 8, text: "Earlier road text" };
    // Every word in these two already carries a lowercase letter, so displayName() returns them
    // unchanged verbatim -- unlike "PCC" above, there is no all-caps word here to re-case.
    fetchMock
      .mockResolvedValueOnce(queueResponse([previousCandidate], 26, 1, 2))
      .mockResolvedValueOnce(queueResponse([lastCandidate], 26, 2, 2))
      .mockResolvedValueOnce(response({ ...lastCandidate, status: "confirmed_same" }))
      .mockResolvedValueOnce(queueResponse([previousCandidate], 25, 1, 1));

    const user = userEvent.setup();
    render(<DuplicateReviewQueue />);
    await user.click(await screen.findByRole("button", { name: "Next page" }));
    expect(await screen.findByText("Last road text")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "These are the same" }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(4));
    expect(String(fetchMock.mock.calls[3][0])).toContain("page=1");
    expect(await screen.findByText("Earlier road text")).toBeInTheDocument();
    expect(screen.queryByText("No works are waiting for review.")).not.toBeInTheDocument();
  });

  test("shows the judged badge, both descriptions, and the judge's rates for a near-copy candidate", async () => {
    const fetchMock = global.fetch as ReturnType<typeof vi.fn>;
    fetchMock.mockResolvedValueOnce(
      response([judgedCandidate], {
        page: 1,
        page_size: 25,
        total: 1,
        total_pages: 1,
        judge_abstention_rate: 5.8,
        judge_quote_rejection_rate: 6.3,
        judge_pairs_total: 39093,
      }),
    );

    render(<DuplicateReviewQueue />);

    await screen.findByText("Shed at Kheda Chowk");
    expect(screen.getByText("Shed near Kheda Chowk village")).toBeInTheDocument();
    expect(
      screen.getByText("Near-identical descriptions, read by a model, quotes checked by code"),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        "Of 39,093 near-identical description pairs a model read, 6% were left unclear and 6% had a quoted word rejected by code.",
      ),
    ).toBeInTheDocument();
  });
});
