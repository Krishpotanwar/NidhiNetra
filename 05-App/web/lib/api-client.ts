/**
 * Shared fetch primitives, extracted from data.ts when the fund-flow graph
 * view needed the same envelope-unwrapping and error handling that
 * fetchInspectionData already had. One implementation of "never let a raw
 * HTTP status or fetch error reach a component," not two.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

interface Envelope<T> {
  success: boolean;
  data: T | null;
  error: string | null;
  meta: Record<string, unknown> | null;
}

export class ApiUnreachableError extends Error {
  /** The HTTP status that produced this error, when there was a response to
   * read one from (undefined for a genuine network failure/timeout, which
   * never reached a server at all). Callers that need to distinguish
   * "duplicate" from "not found" from "unreachable" -- POST /api/inspections
   * does -- read this rather than parsing `message`, which stays a raw
   * backend string never meant for display (see contracts/strings.json's
   * house rule: no user-visible string exists anywhere except that file).
   */
  status?: number;
}

// CP6: "a hung pull times out into a stated failure rather than spinning
// forever." No contract value pins this duration -- there was none to
// find in strings.json -- so this is an engineering choice, not a frozen
// number: long enough that a real (if slow) government-site round trip
// isn't false-flagged as hung, short enough that an officer waiting on a
// dead connection sees a stated failure well within one demo slot.
const DEFAULT_TIMEOUT_MS = 20_000;

export interface EnvelopeResult<T> {
  data: T;
  meta: Record<string, unknown> | null;
}

/**
 * The request primitive. Returns both the envelope's data and its meta
 * (pagination, quota and flag counts on GET /api/works); fetchEnvelope below
 * is the data-only shorthand most callers want.
 */
export async function fetchEnvelopeWithMeta<T>(
  path: string,
  init?: RequestInit,
  timeoutMs: number = DEFAULT_TIMEOUT_MS,
): Promise<EnvelopeResult<T>> {
  const controller = new AbortController();
  // A caller-supplied signal (a superseded filter request, an unmounting
  // view) aborts ours too; ours is the only one actually wired to fetch().
  if (init?.signal?.aborted) controller.abort();
  init?.signal?.addEventListener("abort", () => controller.abort());
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, { ...init, signal: controller.signal });
  } catch (cause) {
    // Both a genuine network failure (service down, DNS, CORS preflight
    // rejected) and an abort land here -- fetch() rejects with an
    // AbortError, which reads exactly like a network error from the
    // caller's side, and both get the same honest "could not be reached"
    // treatment rather than a raw stack trace. strings.json's
    // api_unreachable state is what the UI is built to render; it must
    // never show an HTTP status code or an AbortError message.
    throw new ApiUnreachableError("The data service could not be reached.", { cause });
  } finally {
    clearTimeout(timer);
  }
  const body = (await res.json().catch(() => null)) as Envelope<T> | null;
  if (!res.ok || !body || !body.success) {
    const err = new ApiUnreachableError(body?.error ?? `Request to ${path} failed.`);
    err.status = res.status;
    throw err;
  }
  return { data: body.data as T, meta: body.meta };
}

export async function fetchEnvelope<T>(
  path: string,
  init?: RequestInit,
  timeoutMs: number = DEFAULT_TIMEOUT_MS,
): Promise<T> {
  return (await fetchEnvelopeWithMeta<T>(path, init, timeoutMs)).data;
}

/** True when an error only means a newer request replaced this one. */
export function isAbort(signal: AbortSignal | undefined): boolean {
  return signal?.aborted === true;
}
