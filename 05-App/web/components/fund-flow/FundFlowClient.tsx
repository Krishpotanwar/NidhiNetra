"use client";

import { useCallback, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { renderTemplate, STRINGS } from "@/lib/strings";
import { displayName, formatIndianInt } from "@/lib/format";
import { fetchFundFlowGraph, graphTotals } from "@/lib/graph-data";
import { useApiResource } from "@/lib/use-api-resource";
import {
  allVendorConcentrations,
  matchingVendors,
  medianMemberCount,
  subgraphFor,
} from "@/lib/vendor-concentration";
import { RibbonView } from "./RibbonView";
import { DotCanvas } from "@/components/shared/DotCanvas";
import { ClusterInFocus } from "./ClusterInFocus";
import { ConcentrationFilter } from "./ConcentrationFilter";
import { AliasReviewQueue } from "./AliasReviewQueue";
import { StatTiles } from "./StatTiles";
import styles from "./FundFlowClient.module.css";

const s = STRINGS.fund_flow;

// The reference opens with a minimum of 3 Members per vendor, not 1.
const DEFAULT_THRESHOLD = 3;
// How many clusters the side list offers, most concentrated first.
const MAX_VENDORS_LISTED = 25;

/**
 * One cluster at a time. The view's whole purpose is to make concentration
 * visible, and drawing every matching vendor at national scale hid it in bulk
 * (4,845 vendors, 5,695 nodes, a graph 164,778px tall). The list ranks the
 * clusters; the canvas draws the one in focus, with its agencies and the
 * Members behind them.
 */
export function FundFlowClient() {
  const params = useSearchParams();
  const agency = params.get("agency") ?? undefined;
  const vendor = params.get("vendor") ?? undefined;
  const isDeepLink = Boolean(agency || vendor);

  const [threshold, setThreshold] = useState(DEFAULT_THRESHOLD);
  const [search, setSearch] = useState("");
  const [focusedVendorId, setFocusedVendorId] = useState<string | null>(null);

  const load = useCallback(
    (signal: AbortSignal) => fetchFundFlowGraph({ agency, vendor }, signal),
    [agency, vendor],
  );
  const graph = useApiResource(load);

  // Decision D6 (F-01/F-02): the API holds back a graph built before the
  // IDA/IA split or before its edges carried work IDs.
  const graphData = graph.data?.graph ?? null;
  const rebuildRequired = graph.data?.rebuildRequired === true;

  const concentrations = useMemo(
    () => (graphData ? allVendorConcentrations(graphData) : []),
    [graphData],
  );
  const matching = useMemo(() => matchingVendors(concentrations, threshold), [concentrations, threshold]);
  const searched = useMemo(() => {
    const query = search.trim().toLowerCase();
    if (!query) return matching;
    return matching.filter((v) => displayName(v.vendorLabel).toLowerCase().includes(query));
  }, [matching, search]);
  const listed = useMemo(() => searched.slice(0, MAX_VENDORS_LISTED), [searched]);
  const medianMembers = useMemo(() => medianMemberCount(matching), [matching]);
  const totals = useMemo(() => (graphData ? graphTotals(graphData) : null), [graphData]);
  const isDefaultFilter = threshold === DEFAULT_THRESHOLD && search.trim() === "";

  const focused = useMemo(
    () => listed.find((v) => v.vendorId === focusedVendorId) ?? listed[0],
    [listed, focusedVendorId],
  );

  const displayGraph = useMemo(() => {
    if (!graphData) return null;
    if (isDeepLink) return graphData;
    if (!focused) return { nodes: [], edges: [] };
    return subgraphFor(graphData, new Set([focused.vendorId]));
  }, [graphData, isDeepLink, focused]);

  if (graph.status === "error" && !graph.data) {
    const error = STRINGS.data_states.api_unreachable;
    return (
      <div className={`page ${styles.stack}`}>
        <DotCanvas as="section" className={styles.card}>
          <p className={styles.stateTitle}>{error.title}</p>
          <p className={styles.stateBody}>{error.body}</p>
          <button type="button" className={styles.action} onClick={graph.reload}>
            {error.action}
          </button>
        </DotCanvas>
      </div>
    );
  }

  if (rebuildRequired) {
    return (
      <div className={`page ${styles.stack}`}>
        <DotCanvas as="section" className={styles.card}>
          <p className={styles.stateTitle}>{s.rebuild_required_title}</p>
          <p className={styles.stateBody}>{s.rebuild_required_body}</p>
        </DotCanvas>
        <AliasReviewQueue />
      </div>
    );
  }

  return (
    <div className={`page ${styles.stack}`}>
      {totals && <StatTiles totals={totals} />}

      {isDeepLink && (
        <p className={styles.deepLink}>
          {agency ? `${s.legend_agency}: ${displayName(agency)}` : `${s.legend_vendor}: ${displayName(vendor ?? "")}`}
        </p>
      )}

      <div className={styles.layout}>
        <section className={styles.canvasCard} aria-label={s.focus_title}>
          {displayGraph ? (
            <RibbonView graph={displayGraph} highlightVendorId={isDeepLink ? undefined : focused?.vendorId} />
          ) : (
            <div className={styles.canvasSkeleton} aria-hidden="true" />
          )}
        </section>

        <aside className={styles.side}>
          {!isDeepLink && (
            <>
              <ConcentrationFilter
                threshold={threshold}
                onThresholdChange={(next) => {
                  setThreshold(next);
                  // A changed threshold changes which vendors match, so a
                  // manual focus can point at one no longer in the list.
                  setFocusedVendorId(null);
                }}
                search={search}
                onSearchChange={(next) => {
                  setSearch(next);
                  setFocusedVendorId(null);
                }}
                matchingCount={matching.length}
                totalVendorCount={concentrations.length}
                drawnCount={searched.length > listed.length ? listed.length : null}
                isDefault={isDefaultFilter}
                onReset={() => {
                  setThreshold(DEFAULT_THRESHOLD);
                  setSearch("");
                  setFocusedVendorId(null);
                }}
              />

              <section className={styles.card}>
                <h2 className="t-label">{s.clusters_title}</h2>
                <p className={styles.note}>{s.clusters_note}</p>
                {listed.length > 0 && (
                  <div className={styles.clusterHeader} aria-hidden="true">
                    <span className={styles.clusterRank}>{s.clusters_column_rank}</span>
                    <span>{s.clusters_column_vendor}</span>
                    <span className={styles.clusterHeaderCount}>{s.clusters_column_mps}</span>
                  </div>
                )}
                <ul className={styles.clusterList}>
                  {listed.map((cluster, index) => {
                    const active = cluster.vendorId === focused?.vendorId;
                    return (
                      <li key={cluster.vendorId}>
                        <button
                          type="button"
                          className={styles.clusterButton}
                          aria-current={active ? "true" : undefined}
                          onClick={() => setFocusedVendorId(cluster.vendorId)}
                        >
                          <span className={styles.clusterRank}>{index + 1}</span>
                          <span className={styles.clusterName}>{displayName(cluster.vendorLabel)}</span>
                          <span className={styles.clusterCount}>{formatIndianInt(cluster.memberCount)}</span>
                        </button>
                      </li>
                    );
                  })}
                  {listed.length === 0 && graph.status === "ready" && <li className={styles.note}>{s.empty}</li>}
                </ul>
              </section>

              {focused && <ClusterInFocus vendor={focused} medianMemberCount={medianMembers} />}
            </>
          )}
        </aside>
      </div>

      <AliasReviewQueue />

      <p className={styles.caveat}>{s.scale_caveat}</p>
      {!isDeepLink && searched.length > listed.length && (
        <p className={styles.caveat}>
          {renderTemplate(s.drawn_cap_note, { drawn: formatIndianInt(listed.length) })}
        </p>
      )}
    </div>
  );
}
