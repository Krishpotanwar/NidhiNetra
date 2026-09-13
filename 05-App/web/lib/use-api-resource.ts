"use client";

import { useCallback, useEffect, useState } from "react";
import { ApiUnreachableError } from "./api-client";

export type ResourceStatus = "loading" | "ready" | "error";

export interface ApiResource<T> {
  /** The last successful result. Kept while a newer request is in flight,
   *  so a view can dim stale rows instead of blanking them
   *  (strings.json data_states.refresh_in_progress: never blank the table). */
  data: T | null;
  status: ResourceStatus;
  /** True while a newer request is in flight and `data` is the previous one. */
  stale: boolean;
  reload: () => void;
}

/**
 * Loads one API resource and keeps it current as `fetcher` changes. The
 * caller memoises `fetcher` (useCallback) on exactly the inputs the request
 * depends on; each change aborts the previous request, so a slow response to
 * an old filter can never overwrite a newer one.
 *
 * "Which request is this result for" is stored with the result rather than
 * tracked with a synchronous setState at the top of the effect, which is the
 * cascading-render pattern React's hooks lint rightly flags.
 */
export function useApiResource<T>(fetcher: (signal: AbortSignal) => Promise<T>): ApiResource<T> {
  const [reloadCount, setReloadCount] = useState(0);
  const [result, setResult] = useState<{
    fetcher: ((signal: AbortSignal) => Promise<T>) | null;
    reloadCount: number;
    data: T | null;
    failed: boolean;
  }>({ fetcher: null, reloadCount: -1, data: null, failed: false });

  useEffect(() => {
    const controller = new AbortController();
    fetcher(controller.signal).then(
      (data) => {
        if (!controller.signal.aborted) setResult({ fetcher, reloadCount, data, failed: false });
      },
      (err: unknown) => {
        if (controller.signal.aborted) return;
        // ApiUnreachableError already carries copy-safe context; anything else
        // is a bug worth seeing in the console, never on screen.
        if (!(err instanceof ApiUnreachableError)) console.error("Unexpected error loading data", err);
        setResult((prev) => ({ fetcher, reloadCount, data: prev.data, failed: true }));
      },
    );
    return () => controller.abort();
  }, [fetcher, reloadCount]);

  const reload = useCallback(() => setReloadCount((c) => c + 1), []);
  const current = result.fetcher === fetcher && result.reloadCount === reloadCount;
  const status: ResourceStatus = !current ? "loading" : result.failed ? "error" : "ready";
  return { data: result.data, status, stale: !current && result.data !== null, reload };
}
