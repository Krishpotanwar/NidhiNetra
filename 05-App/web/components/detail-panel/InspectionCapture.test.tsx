// Checkpoints CP8: "The officer can record it on screen, from the row they
// were told to inspect." Covers the states this component can be in:
// closed, open, submitting, and each of the outcomes a submit can land in
// (success, duplicate, stale work) plus a bare network failure -- see
// lib/api-client.ts's ApiUnreachableError.status for why those three are
// distinguishable at all. Also covers inspector_id (outside-voice
// correction, round 2): required, remembered across visits via
// localStorage, and Save stays disabled until it's filled in.
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { InspectionCapture } from "./InspectionCapture";
import { STRINGS } from "@/lib/strings";

const strings = STRINGS.inspection_capture;

beforeEach(() => {
  vi.stubGlobal("fetch", vi.fn());
  localStorage.clear();
});

afterEach(() => {
  vi.unstubAllGlobals();
  localStorage.clear();
});

function mockResponse(status: number, body: unknown) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  } as Response;
}

/** Opens the form and fills the one field Save requires (inspector_id),
 * leaving everything else at its default -- the shared setup every test
 * that needs to actually reach handleSubmit() starts from.
 */
async function openAndIdentify(user: ReturnType<typeof userEvent.setup>) {
  await user.click(screen.getByRole("button", { name: strings.cta }));
  await user.type(screen.getByLabelText(strings.inspector_id_label), "AB");
}

test("starts closed, showing only the record button", () => {
  render(<InspectionCapture workId="W1" />);
  expect(screen.getByRole("button", { name: strings.cta })).toBeInTheDocument();
  expect(screen.queryByLabelText(strings.outcome_label)).not.toBeInTheDocument();
});

test("opens the form on click, and cancel closes it again without submitting", async () => {
  const user = userEvent.setup();
  render(<InspectionCapture workId="W1" />);

  await user.click(screen.getByRole("button", { name: strings.cta }));
  expect(screen.getByLabelText(strings.outcome_label)).toBeInTheDocument();
  expect(screen.getByLabelText(strings.date_label)).toBeInTheDocument();
  expect(screen.getByLabelText(strings.inspector_id_label)).toBeInTheDocument();
  expect(screen.getByLabelText(strings.notes_label)).toBeInTheDocument();

  await user.click(screen.getByRole("button", { name: strings.cancel }));
  expect(screen.queryByLabelText(strings.outcome_label)).not.toBeInTheDocument();
  expect(global.fetch).not.toHaveBeenCalled();
});

test("Save stays disabled until an inspector id is entered", async () => {
  const user = userEvent.setup();
  render(<InspectionCapture workId="W1" />);
  await user.click(screen.getByRole("button", { name: strings.cta }));

  const saveButton = screen.getByRole("button", { name: strings.submit });
  expect(saveButton).toBeDisabled();

  await user.type(screen.getByLabelText(strings.inspector_id_label), "AB");
  expect(saveButton).toBeEnabled();
});

test("submits the right payload, including inspector_id, and shows the success copy on 200", async () => {
  const fetchMock = global.fetch as ReturnType<typeof vi.fn>;
  fetchMock.mockResolvedValueOnce(
    mockResponse(200, {
      success: true,
      data: { work_id: "W1", outcome: "work_present_and_matches" },
      error: null,
      meta: null,
    }),
  );

  const user = userEvent.setup();
  render(<InspectionCapture workId="W1" />);
  await openAndIdentify(user);
  await user.selectOptions(screen.getByLabelText(strings.outcome_label), "work_not_found_at_site");
  await user.type(screen.getByLabelText(strings.notes_label), "Empty plot, neighbours confirmed.");
  await user.click(screen.getByRole("button", { name: strings.submit }));

  await waitFor(() => expect(screen.getByText(strings.success)).toBeInTheDocument());

  expect(fetchMock).toHaveBeenCalledTimes(1);
  const [, init] = fetchMock.mock.calls[0];
  const sentBody = JSON.parse((init as RequestInit).body as string);
  expect(sentBody).toMatchObject({
    work_id: "W1",
    outcome: "work_not_found_at_site",
    notes: "Empty plot, neighbours confirmed.",
    inspector_id: "AB",
  });
  expect(typeof sentBody.inspected_on).toBe("string");
  expect(sentBody).not.toHaveProperty("in_control_sample");
});

test("inspector id is remembered across a remount via localStorage", async () => {
  const fetchMock = global.fetch as ReturnType<typeof vi.fn>;
  fetchMock.mockResolvedValue(mockResponse(200, { success: true, data: {}, error: null, meta: null }));

  const user = userEvent.setup();
  const { unmount } = render(<InspectionCapture workId="W1" />);
  await openAndIdentify(user);
  await user.click(screen.getByRole("button", { name: strings.submit }));
  await waitFor(() => expect(screen.getByText(strings.success)).toBeInTheDocument());
  unmount();

  render(<InspectionCapture workId="W2" />);
  await user.click(screen.getByRole("button", { name: strings.cta }));
  await waitFor(() =>
    expect(screen.getByLabelText(strings.inspector_id_label)).toHaveValue("AB"),
  );
});

test("offers no control-group choice and never sends one (F-09: the server assigns groups)", async () => {
  const fetchMock = global.fetch as ReturnType<typeof vi.fn>;
  fetchMock.mockResolvedValueOnce(
    mockResponse(200, { success: true, data: {}, error: null, meta: null }),
  );

  const user = userEvent.setup();
  render(<InspectionCapture workId="W1" />);
  await openAndIdentify(user);

  expect(screen.queryByRole("checkbox")).not.toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: strings.submit }));

  const [, init] = fetchMock.mock.calls[0];
  const sentBody = JSON.parse((init as RequestInit).body as string);
  expect(sentBody).not.toHaveProperty("in_control_sample");
});

test("shows the duplicate-specific message on a 409, and does not show the raw backend string", async () => {
  const fetchMock = global.fetch as ReturnType<typeof vi.fn>;
  fetchMock.mockResolvedValueOnce(
    mockResponse(409, {
      success: false,
      data: null,
      error: "an outcome for work_id='W1' on '2026-09-05' already exists; rejected rather than overwritten",
      meta: null,
    }),
  );

  const user = userEvent.setup();
  render(<InspectionCapture workId="W1" />);
  await openAndIdentify(user);
  await user.click(screen.getByRole("button", { name: strings.submit }));

  await waitFor(() => expect(screen.getByText(strings.error_duplicate)).toBeInTheDocument());
  expect(screen.queryByText(/rejected rather than overwritten/)).not.toBeInTheDocument();
});

test("shows the stale-work message on a 404", async () => {
  const fetchMock = global.fetch as ReturnType<typeof vi.fn>;
  fetchMock.mockResolvedValueOnce(
    mockResponse(404, { success: false, data: null, error: "No work found.", meta: null }),
  );

  const user = userEvent.setup();
  render(<InspectionCapture workId="W1" />);
  await openAndIdentify(user);
  await user.click(screen.getByRole("button", { name: strings.submit }));

  await waitFor(() => expect(screen.getByText(strings.error_stale_work)).toBeInTheDocument());
});

test("shows the generic error message on a bare network failure", async () => {
  const fetchMock = global.fetch as ReturnType<typeof vi.fn>;
  fetchMock.mockRejectedValueOnce(new TypeError("Failed to fetch"));

  const user = userEvent.setup();
  render(<InspectionCapture workId="W1" />);
  await openAndIdentify(user);
  await user.click(screen.getByRole("button", { name: strings.submit }));

  await waitFor(() => expect(screen.getByText(strings.error_generic)).toBeInTheDocument());
});

test("the date picker defaults to today and cannot pick a later day (F-10)", async () => {
  const user = userEvent.setup();
  render(<InspectionCapture workId="W1" />);
  await user.click(screen.getByRole("button", { name: strings.cta }));

  const now = new Date();
  const today = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
  const dateInput = screen.getByLabelText(strings.date_label);
  expect(dateInput).toHaveAttribute("max", today);
  expect(dateInput).toHaveValue(today);
});
