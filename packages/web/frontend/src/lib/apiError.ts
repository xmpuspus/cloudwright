/**
 * Parse a non-ok fetch Response into a human-readable error string.
 *
 * The backend returns {code, message, suggestion} from error_response().
 * FastAPI's own 404s use {detail}. HTTP 429s carry a Retry-After header.
 * Falls back to res.statusText for anything else.
 */
export async function parseApiError(res: Response): Promise<string> {
  if (res.status === 429) {
    const retryAfter = res.headers.get("Retry-After");
    const suffix = retryAfter ? ` Retry after ${retryAfter}s.` : "";
    try {
      const j = await res.json();
      const base = j.message || j.detail || "Rate limited";
      return `${base}${suffix}`;
    } catch {
      return `Rate limited.${suffix}`;
    }
  }

  try {
    const j = await res.json();
    return formatApiError(j, res.statusText);
  } catch {
    return res.statusText || "Request failed";
  }
}

/**
 * Format an already-parsed JSON error body.
 *
 * Use this when the response body was already consumed (e.g. parsed for a
 * success-path field) and parseApiError cannot be called.
 */
export function formatApiError(
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  body: Record<string, any>,
  fallback = "Request failed",
): string {
  const message: string = body.message || body.detail || fallback;
  if (body.suggestion) return `${message} ${body.suggestion}`;
  return message;
}
