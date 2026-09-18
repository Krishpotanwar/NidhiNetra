import { Bank, CurrencyInr, type Icon, UserCircle, Wallet } from "@phosphor-icons/react";
import { STRINGS } from "@/lib/strings";
import { formatCurrencyFull, formatIndianInt } from "@/lib/format";
import type { GraphTotals } from "@/lib/graph-data";
import styles from "./StatTiles.module.css";

const s = STRINGS.fund_flow;

interface StatTilesProps {
  totals: GraphTotals;
}

/** The reference's four-tile row: whole-graph totals, computed once from the
 *  already-loaded graph -- no separate request. */
export function StatTiles({ totals }: StatTilesProps) {
  return (
    <div className={styles.row}>
      <Tile icon={CurrencyInr} label={s.totals_flow_label} value={formatCurrencyFull(totals.flowInr)} />
      <Tile icon={UserCircle} label={s.column_mp} value={formatIndianInt(totals.mpCount)} />
      <Tile icon={Bank} label={s.column_agency} value={formatIndianInt(totals.agencyCount)} />
      <Tile icon={Wallet} label={s.totals_vendor_label} value={formatIndianInt(totals.vendorCount)} />
    </div>
  );
}

function Tile({ icon: Glyph, label, value }: { icon: Icon; label: string; value: string }) {
  return (
    <div className={styles.tile}>
      <Glyph size={20} aria-hidden="true" className={styles.tileIcon} />
      <div>
        <p className={styles.tileLabel}>{label}</p>
        <p className={`t-num ${styles.tileValue}`}>{value}</p>
      </div>
    </div>
  );
}
