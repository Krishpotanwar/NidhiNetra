"use client";

import { useId, useState, type CSSProperties } from "react";
import { STRINGS } from "@/lib/strings";
import { ApiUnreachableError, fetchEnvelope } from "@/lib/api-client";
import { officerInitials } from "@/lib/preferences";

const strings = STRINGS.inspection_capture;

// Object.entries preserves insertion order for string keys, and
// contracts/strings.json's outcome_options is written in the same order as
// contracts/inspection_outcome.schema.json's enum -- see the 2026-09-05
// amendment_log entry on why those two lists must never drift apart.
const OUTCOME_ENTRIES = Object.entries(strings.outcome_options);

interface InspectionCaptureProps {
  workId: string;
}

type Phase = "closed" | "open" | "submitting" | "success" | "error";

function todayIsoDate(): string {
  return new Date().toISOString().slice(0, 10);
}

/**
 * Checkpoints CP8: "The officer can record it on screen, from the row they
 * were told to inspect." A native <select>, not the Radix listbox
 * FilterBar.tsx uses -- this is a form control inside a form, not a filter
 * inside a sticky bar, and a native element is simpler to test and no less
 * accessible for a single-choice field with under a dozen options.
 *
 * inspection_rank_at_time and risk_score_at_time are deliberately NOT
 * fields here -- the API looks those up server-side from the current
 * snapshot at the moment it handles the request (routers/inspections.py),
 * never from anything the client sends. See Checkpoints CP8 and the
 * contract's own docstring for why a client-supplied rank would corrupt
 * precision-at-quota later.
 *
 * The comparison group is not a field here either (F-09): the server decides
 * whether an outcome belongs to a pre-assigned random sample
 * (routers/inspections.py _server_control_assignment). An officer choosing it
 * after seeing the work would make the Reports comparison meaningless.
 */
export function InspectionCapture({ workId }: InspectionCaptureProps) {
  const [phase, setPhase] = useState<Phase>("closed");
  const [outcome, setOutcome] = useState(OUTCOME_ENTRIES[0][0]);
  const [inspectedOn, setInspectedOn] = useState(todayIsoDate);
  const [notes, setNotes] = useState("");
  // Lazy initializer, not an effect: react-hooks/set-state-in-effect
  // (React Compiler lint) flags a setState called synchronously inside an
  // effect body, and there's a cleaner option here anyway. This value never
  // reaches the DOM during the "closed" phase (the only phase that's ever
  // server-rendered -- the form, including this field, only exists after a
  // client click sets phase to "open"), so there's no hydration mismatch to
  // guard against either: the server's copy of this component never
  // renders anything that depends on it.
  const [inspectorId, setInspectorId] = useState(() => officerInitials.get());
  const [errorMessage, setErrorMessage] = useState("");

  const outcomeId = useId();
  const dateId = useId();
  const inspectorIdFieldId = useId();
  const notesId = useId();

  function reset() {
    setPhase("closed");
    setOutcome(OUTCOME_ENTRIES[0][0]);
    setInspectedOn(todayIsoDate());
    setNotes("");
    setErrorMessage("");
  }

  async function handleSubmit() {
    setPhase("submitting");
    try {
      await fetchEnvelope("/api/inspections", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          work_id: workId,
          inspected_on: inspectedOn,
          outcome,
          notes,
          inspector_id: inspectorId,
        }),
      });
      // Remembered for the next recording, and shown in the header menu.
      officerInitials.set(inspectorId);
      setPhase("success");
    } catch (err) {
      // Never render err.message -- it's a raw backend string, not
      // copy-reviewed against contracts/strings.json's lint block. Branch
      // on the HTTP status instead (see api-client.ts's ApiUnreachableError
      // docstring) and pick one of the three curated messages.
      const status = err instanceof ApiUnreachableError ? err.status : undefined;
      setErrorMessage(
        status === 409
          ? strings.error_duplicate
          : status === 404
            ? strings.error_stale_work
            : strings.error_generic,
      );
      setPhase("error");
    }
  }

  if (phase === "closed") {
    return (
      <button type="button" onClick={() => setPhase("open")} className="t-colhead" style={ctaStyle}>
        {strings.cta}
      </button>
    );
  }

  if (phase === "success") {
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-3)" }}>
        <p style={{ fontSize: "var(--font-xs)", color: "var(--ink)" }}>{strings.success}</p>
        <button type="button" onClick={reset} className="t-colhead" style={ctaStyle}>
          {strings.cta}
        </button>
      </div>
    );
  }

  const submitting = phase === "submitting";

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-4)" }}>
      <div style={fieldStyle}>
        <label htmlFor={outcomeId} style={labelStyle}>
          {strings.outcome_label}
        </label>
        <select
          id={outcomeId}
          value={outcome}
          onChange={(e) => setOutcome(e.target.value)}
          disabled={submitting}
          style={controlStyle}
        >
          {OUTCOME_ENTRIES.map(([key, label]) => (
            <option key={key} value={key}>
              {label}
            </option>
          ))}
        </select>
      </div>

      <div style={fieldStyle}>
        <label htmlFor={dateId} style={labelStyle}>
          {strings.date_label}
        </label>
        <input
          id={dateId}
          type="date"
          value={inspectedOn}
          onChange={(e) => setInspectedOn(e.target.value)}
          disabled={submitting}
          style={controlStyle}
        />
      </div>

      <div style={fieldStyle}>
        <label htmlFor={inspectorIdFieldId} style={labelStyle}>
          {strings.inspector_id_label}
        </label>
        <input
          id={inspectorIdFieldId}
          type="text"
          value={inspectorId}
          onChange={(e) => setInspectorId(e.target.value)}
          disabled={submitting}
          style={controlStyle}
        />
      </div>

      <div style={fieldStyle}>
        <label htmlFor={notesId} style={labelStyle}>
          {strings.notes_label}
        </label>
        <textarea
          id={notesId}
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          disabled={submitting}
          rows={2}
          style={{ ...controlStyle, resize: "vertical" as const }}
        />
      </div>

      {phase === "error" && (
        <p role="alert" style={{ fontSize: "var(--font-xs)", color: "var(--risk-3, var(--ink))" }}>
          {errorMessage}
        </p>
      )}

      <div style={{ display: "flex", gap: "var(--space-4)" }}>
        <button type="button" onClick={reset} disabled={submitting} className="t-colhead" style={ctaStyle}>
          {strings.cancel}
        </button>
        <button
          type="button"
          onClick={handleSubmit}
          disabled={submitting || inspectorId.trim() === ""}
          className="t-colhead"
          style={{ ...ctaStyle, color: "var(--accent)" }}
        >
          {submitting ? strings.saving : strings.submit}
        </button>
      </div>
    </div>
  );
}

const ctaStyle: CSSProperties = {
  alignSelf: "flex-start",
  display: "inline-flex",
  alignItems: "center",
  height: "2.25rem",
  padding: "0 var(--space-4)",
  border: "1px solid var(--control-border)",
  borderRadius: "var(--radius-control)",
  background: "var(--surface)",
  fontSize: "var(--font-sm)",
  fontWeight: 600,
  letterSpacing: "normal",
  textTransform: "none",
  color: "var(--ink-2)",
  cursor: "pointer",
};

const fieldStyle: CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: "var(--space-1)",
};

const labelStyle: CSSProperties = {
  fontSize: "var(--font-note)",
  color: "var(--ink-muted)",
};

const controlStyle: CSSProperties = {
  fontFamily: "var(--font-sans)",
  fontSize: "var(--font-sm)",
  color: "var(--ink)",
  background: "var(--surface)",
  border: "1px solid var(--hairline)",
  borderRadius: "var(--radius-control)",
  padding: "var(--space-2) var(--space-3)",
};
