"use client";

import { useCallback, useMemo, useState } from "react";
import { useSearchParams } from "next/navigation";
import { renderTemplate, STRINGS } from "@/lib/strings";
import { displayName, formatIndianInt } from "@/lib/format";
import { fetchFundFlowGraph, fetchVendorCluster, fetchVendorConcentrations } from "@/lib/graph-data";
import { useApiResource } from "@/lib/use-api-resource";
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
// How many clusters the side list displays, most concentrated first.
const MAX_VENDORS_LISTED = 25;
// The server's own maximum (models.py's ConcentrationsQuery, ge=1/le=100),
// requested unconditionally rather than exactly MAX_VENDORS_LISTED: the text
// search below filters vendor names client-side over whatever comes back,
// and searching only the displayed 25 would make a real match ranked, say,
// 40th unfindable. This is the fixed design's own stated bound, not a new
// server capability -- see SIHGit/tasks/T17-F17b-server-side-concentration.md.
const SERVER_FETCH_LIMIT = 100;

/**
 * One cluster at a time. T17/F-17b: the server now ranks vendors and
 * extracts one vendor's cluster (graph_analysis.py, a parity-tested port of
 * this file's own vendor-concentration.ts), so the non-deep-link view never
 * downloads the whole national graph.json (about 10 MB) just to draw the
 * 25 most concentrated vendors and one cluster. Deep links
 * (?agency=/?vendor= from a work's detail panel) are unchanged: one
 * filtered GET /api/graph request, no concentration ranking involved.
 */
export function FundFlowClient() {
  const params = useSearchParams();
  const agency = params.get("agency") ?? undefined;
  const vendor = params.get("vendor") ?? undefined;
  const isDeepLink = Boolean(agency || vendor);

  const [threshold, setThreshold] = useState(DEFAULT_THRESHOLD);
  const [search, setSearch] = useState("");
  const [focusedVendorId, setFocusedVendorId] = useState<string | null>(null);

  // Both fetchers below are always called (React's rules of hooks), but each
  // short-circuits to an instant, network-free empty result in the mode it
  // does not serve -- otherwise a non-deep-link render would still fetch the
  // bare national graph on the side, exactly the download T17 exists to cut.
  const loadDeepLinkGraph = useCallback(
    (signal: AbortSignal) =>
      isDeepLink
        ? fetchFundFlowGraph({ agency, vendor }, signal)
        : Promise.resolve({ graph: { nodes: [], edges: [] }, rebuildRequired: false }),
    [isDeepLink, agency, vendor],
  );
  const deepLinkGraph = useApiResource(loadDeepLinkGraph);

  const loadConcentrations = useCallback(
    (signal: AbortSignal) =>
      isDeepLink
        ? Promise.resolve({
            vendors: [],
            matchingCount: 0,
            totalVendorCount: 0,
            medianMemberCount: 0,
            totals: null,
            rebuildRequired: false,
          })
        : fetchVendorConcentrations(threshold, SERVER_FETCH_LIMIT, signal),
    [isDeepLink, threshold],
  );
  const concentrationsResource = useApiResource(loadConcentrations);

  const vendors = useMemo(() => concentrationsResource.data?.vendors ?? [], [concentrationsResource.data]);
  const searched = useMemo(() => {
    const query = search.trim().toLowerCase();
    if (!query) return vendors;
    return vendors.filter((v) => displayName(v.vendorLabel).toLowerCase().includes(query));
  }, [vendors, search]);
  const listed = useMemo(() => searched.slice(0, MAX_VENDORS_LISTED), [searched]);
  const isDefaultFilter = threshold === DEFAULT_THRESHOLD && search.trim() === "";

  const focused = useMemo(
    () => listed.find((v) => v.vendorId === focusedVendorId) ?? listed[0],
    [listed, focusedVendorId],
  );

  // The focused vendor's own cluster, fetched on demand -- no network call
  // at all until a vendor is actually known (before concentrations resolve).
  // Keyed on the vendor id, not the `focused` object itself: a threshold
  // change re-fetches a new `vendors` array (new object identities) even
  // when the top vendor's id is unchanged, and re-fetching its cluster
  // again would waste exactly the request this is meant to avoid.
  const resolvedFocusVendorId = focused?.vendorId;
  const loadCluster = useCallback(
    (signal: AbortSignal) =>
      resolvedFocusVendorId
        ? fetchVendorCluster(resolvedFocusVendorId, signal)
        : Promise.resolve({ graph: { nodes: [], edges: [] }, rebuildRequired: false }),
    [resolvedFocusVendorId],
  );
  const clusterGraph = useApiResource(loadCluster);

  // Which resource speaks for "is the API actually reachable right now" and
  // "is this graph.json build too old to serve" depends on the mode: a deep
  // link never touches the concentrations/cluster endpoints at all.
  const primaryResource = isDeepLink ? deepLinkGraph : concentrationsResource;
  const displayGraph = isDeepLink ? deepLinkGraph.data?.graph ?? null : clusterGraph.data?.graph ?? null;
  const rebuildRequired = isDeepLink
    ? deepLinkGraph.data?.rebuildRequired === true
    : concentrationsResource.data?.rebuildRequired === true;
  const totals = concentrationsResource.data?.totals ?? null;

  const handleReload = useCallback(() => {
    if (isDeepLink) {
      deepLinkGraph.reload();
    } else {
      concentrationsResource.reload();
      clusterGraph.reload();
    }
  }, [isDeepLink, deepLinkGraph, concentrationsResource, clusterGraph]);

  if (primaryResource.status === "error" && !primaryResource.data) {
    const error = STRINGS.data_states.api_unreachable;
    return (
      <div className={`page ${styles.stack}`}>
        <DotCanvas as="section" className={styles.card}>
          <p className={styles.stateTitle}>{error.title}</p>
          <p className={styles.stateBody}>{error.body}</p>
          <button type="button" className={styles.action} onClick={handleReload}>
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
      {!isDeepLink && totals && <StatTiles totals={totals} />}

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
                matchingCount={concentrationsResource.data?.matchingCount ?? 0}
                totalVendorCount={concentrationsResource.data?.totalVendorCount ?? 0}
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
                  {listed.length === 0 && concentrationsResource.status === "ready" && (
                    <li className={styles.note}>{s.empty}</li>
                  )}
                </ul>
              </section>

              {focused && (
                <ClusterInFocus
                  vendor={focused}
                  medianMemberCount={concentrationsResource.data?.medianMemberCount ?? 0}
                />
              )}
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
