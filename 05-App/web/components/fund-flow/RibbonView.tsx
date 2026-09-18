import { formatIndianInt } from "@/lib/format";
import type { FundFlowGraph, GraphNodeType } from "@/lib/graph-data";
import { renderTemplate, STRINGS } from "@/lib/strings";
import { DotCanvas } from "@/components/shared/DotCanvas";
import { buildRibbonLayout, ROW_HEIGHT, type RibbonColumn, type RibbonEdgeState, type RibbonPath } from "./ribbon-layout";
import styles from "./RibbonView.module.css";

const s = STRINGS.fund_flow;

const COLUMN_LABEL: Record<GraphNodeType, string> = {
  MP: s.column_mp,
  Agency: s.column_agency,
  Vendor: s.column_vendor,
};

const RIBBON_CLASS: Record<RibbonEdgeState, string> = {
  plain: styles.ribbonPlain,
  elevated: styles.ribbonElevated,
  high: styles.ribbonHigh,
};

interface RibbonViewProps {
  graph: FundFlowGraph;
  /** Draws this vendor's row with the same highlight styling as a "high"
   *  ribbon; every ribbon's own colour is driven entirely by its real
   *  flagged-work share regardless. */
  highlightVendorId?: string;
}

/**
 * The three-column MP -> Agency -> Vendor visual (the reference's Fund Flow
 * chart), replacing the earlier sigma.js force layout: FundFlowClient only
 * ever hands this component one vendor's own subgraph (or, on a deep link,
 * one agency/vendor's server-filtered graph) -- small enough that a plain
 * SVG draws it without sigma's WebGL renderer.
 */
export function RibbonView({ graph, highlightVendorId }: RibbonViewProps) {
  if (graph.nodes.length === 0) {
    return (
      <DotCanvas className={styles.empty}>
        <p className={styles.emptyTitle}>{s.empty}</p>
        <p className={styles.emptyBody}>{s.empty_body}</p>
      </DotCanvas>
    );
  }

  const layout = buildRibbonLayout(graph, highlightVendorId);

  return (
    <div>
      <div className={styles.legend}>
        <span className={styles.legendItem}>
          <span className={`${styles.swatch} ${styles.swatchPlain}`} aria-hidden="true" />
          {s.ribbon_legend_plain}
        </span>
        <span className={styles.legendItem}>
          <span className={`${styles.swatch} ${styles.swatchElevated}`} aria-hidden="true" />
          {s.ribbon_legend_elevated}
        </span>
        <span className={styles.legendItem}>
          <span className={`${styles.swatch} ${styles.swatchHigh}`} aria-hidden="true" />
          {s.ribbon_legend_high}
        </span>
      </div>

      <div className={styles.scroller} role="img" aria-label={s.subtitle}>
        <div className={styles.grid}>
          <Column type="MP" column={layout.columns.MP} />
          <Gutter ribbons={layout.mpAgencyRibbons} height={layout.height} />
          <Column type="Agency" column={layout.columns.Agency} />
          <Gutter ribbons={layout.agencyVendorRibbons} height={layout.height} />
          <Column type="Vendor" column={layout.columns.Vendor} />
        </div>
      </div>

      <p className={styles.infoNote}>{s.ribbon_info_note}</p>
    </div>
  );
}

function Column({ type, column }: { type: GraphNodeType; column: RibbonColumn }) {
  return (
    <div className={styles.column} data-column-type={type}>
      <h3 className={styles.columnHeader}>{COLUMN_LABEL[type]}</h3>
      <ul className={styles.rows}>
        {column.rows.map((row) => (
          <li
            key={row.id}
            className={row.selected ? `${styles.row} ${styles.rowSelected}` : styles.row}
            style={{ height: ROW_HEIGHT }}
            title={row.fullLabel}
            data-selected={row.selected || undefined}
          >
            {row.label}
          </li>
        ))}
        {column.overflowCount > 0 && (
          <li className={styles.overflowRow} style={{ height: ROW_HEIGHT }}>
            {renderTemplate(s.ribbon_more_note, { count: formatIndianInt(column.overflowCount) })}
          </li>
        )}
      </ul>
    </div>
  );
}

function Gutter({ ribbons, height }: { ribbons: RibbonPath[]; height: number }) {
  return (
    <svg
      className={styles.gutter}
      viewBox={`0 0 100 ${height}`}
      preserveAspectRatio="none"
      style={{ height }}
      aria-hidden="true"
    >
      {ribbons.map((ribbon) => (
        <path key={ribbon.id} d={ribbon.d} className={RIBBON_CLASS[ribbon.state]} strokeWidth={ribbon.strokeWidth}>
          <title>{ribbon.title}</title>
        </path>
      ))}
    </svg>
  );
}
