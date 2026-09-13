"use client";

import { useId, type ReactNode } from "react";
import type { Icon } from "@phosphor-icons/react";
import { CalendarBlank, Database, Eye, Flag, MapPin, SquaresFour } from "@phosphor-icons/react";
import { STRINGS } from "@/lib/strings";
import { EMPTY_FILTERS, flagLabel, isFilterActive, optionsFromFacet, type FilterState } from "@/lib/filters";
import type { Facets } from "@/lib/types";
import { rowTreatment, usePresenterMode, useRowTreatment } from "@/lib/preferences";
import { SelectControl } from "./SelectControl";
import { StateSelect } from "./StateSelect";
import { Segmented } from "./Segmented";
import styles from "./FilterPanel.module.css";

/** Which screen the table should show. Only reachable in presenter mode. */
export type PreviewState = "loaded" | "loading" | "empty";

const filters = STRINGS.filters;
const view = STRINGS.view_options;

interface FilterPanelProps {
  value: FilterState;
  onChange: (next: FilterState) => void;
  facets: Facets | null;
  previewState: PreviewState;
  onPreviewStateChange: (next: PreviewState) => void;
}

/**
 * The reference's filter row: four filters on the left, view options on the
 * right. Every option list comes from the API's facets, counted over the
 * whole quota population, so an option is never missing because it was not
 * on the page the browser happened to fetch.
 *
 * Row treatment is a real preference an officer keeps. Data state is a
 * presenter device and appears only in presenter mode.
 */
export function FilterPanel({ value, onChange, facets, previewState, onPreviewStateChange }: FilterPanelProps) {
  const presenter = usePresenterMode();
  const treatment = useRowTreatment();
  const stateId = useId();
  const yearId = useId();
  const categoryId = useId();
  const flagId = useId();
  const treatmentId = useId();
  const previewId = useId();

  return (
    <section className={styles.panel} aria-label={filters.panel_label}>
      <div className={styles.group}>
        <Field glyph={MapPin} label={filters.states} labelId={stateId}>
          <StateSelect
            labelId={stateId}
            value={value.states}
            options={facets?.states ?? []}
            onChange={(states) => onChange({ ...value, states })}
          />
        </Field>
        <Field glyph={CalendarBlank} label={filters.year} labelId={yearId}>
          <SelectControl
            labelId={yearId}
            value={value.year}
            options={optionsFromFacet(facets?.years, filters.all_years)}
            onValueChange={(year) => onChange({ ...value, year })}
            width="narrow"
          />
        </Field>
        <Field glyph={SquaresFour} label={filters.category} labelId={categoryId}>
          <SelectControl
            labelId={categoryId}
            value={value.category}
            options={optionsFromFacet(facets?.categories, filters.all_categories)}
            onValueChange={(category) => onChange({ ...value, category })}
          />
        </Field>
        <Field glyph={Flag} label={filters.flag} labelId={flagId}>
          <SelectControl
            labelId={flagId}
            value={value.flag}
            options={optionsFromFacet(facets?.flags, filters.all_flags, flagLabel)}
            onValueChange={(flag) => onChange({ ...value, flag })}
          />
        </Field>
        {/* Only once something is actually filtered: a permanent "clear" next
            to four untouched filters is an action that does nothing. */}
        {isFilterActive(value) && (
          <button type="button" className={styles.clear} onClick={() => onChange(EMPTY_FILTERS)}>
            {filters.clear}
          </button>
        )}
      </div>

      <span className={styles.divider} aria-hidden="true" />

      <div className={styles.group}>
        <Field glyph={Eye} label={view.row_treatment} labelId={treatmentId}>
          <Segmented
            labelId={treatmentId}
            value={treatment}
            onChange={(next) => rowTreatment.set(next)}
            options={[
              { value: "two-line", label: view.two_line },
              { value: "hover-reveal", label: view.hover_reveal },
            ]}
          />
        </Field>
        {presenter && (
          <Field glyph={Database} label={view.data_state} labelId={previewId} note={STRINGS.presenter.data_state_note}>
            <Segmented
              labelId={previewId}
              value={previewState}
              onChange={onPreviewStateChange}
              options={[
                { value: "loaded", label: view.loaded },
                { value: "loading", label: view.loading },
                { value: "empty", label: view.empty },
              ]}
            />
          </Field>
        )}
      </div>
    </section>
  );
}

function Field({
  glyph: Glyph,
  label,
  labelId,
  note,
  children,
}: {
  glyph: Icon;
  label: string;
  labelId: string;
  note?: string;
  children: ReactNode;
}) {
  return (
    <div className={styles.field}>
      <Glyph size={22} aria-hidden="true" className={styles.fieldIcon} />
      <div className={styles.fieldBody}>
        <span id={labelId} className="t-label" title={note}>
          {label}
        </span>
        {children}
      </div>
    </div>
  );
}
