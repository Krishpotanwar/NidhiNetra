import { Bank, Briefcase, Database, type Icon, UsersThree } from "@phosphor-icons/react";
import { STRINGS } from "@/lib/strings";
import { formatCroreParts, formatIndianInt } from "@/lib/format";
import type { GraphTotals } from "@/lib/graph-data";
import styles from "./StatTiles.module.css";

const s = STRINGS.fund_flow;

interface StatTilesProps {
  /** Null until the totals arrive: the cards then hold skeletons, so the page does not shift. */
  totals: GraphTotals | null;
}

/** The reference's four-card row: whole-graph totals, the flow in crore like every other KPI. */
export function StatTiles({ totals }: StatTilesProps) {
  const flow = totals ? formatCroreParts(totals.flowInr) : null;
  return (
    <div className={styles.row} aria-busy={!totals}>
      <Tile icon={Database} label={s.totals_flow_label} value={flow?.value ?? null} unit={flow?.unit} />
      <Tile icon={UsersThree} label={s.column_mp} value={totals ? formatIndianInt(totals.mpCount) : null} />
      <Tile icon={Bank} label={s.column_agency} value={totals ? formatIndianInt(totals.agencyCount) : null} />
      <Tile
        icon={Briefcase}
        tone="violet"
        label={s.totals_vendor_label}
        value={totals ? formatIndianInt(totals.vendorCount) : null}
      />
    </div>
  );
}

interface TileProps {
  icon: Icon;
  label: string;
  value: string | null;
  unit?: string;
  tone?: "blue" | "violet";
}

function Tile({ icon: Glyph, label, value, unit, tone = "blue" }: TileProps) {
  return (
    <div className={styles.tile} data-tone={tone}>
      <span className={styles.icon} aria-hidden="true">
        <Glyph size={23} />
      </span>
      <div className={styles.text}>
        <p className={styles.label}>{label}</p>
        {value === null ? (
          <span className={styles.skeleton} aria-hidden="true" />
        ) : (
          <p className={styles.value}>
            {value}
            {unit ? <span className={styles.unit}>{unit}</span> : null}
          </p>
        )}
      </div>
    </div>
  );
}
