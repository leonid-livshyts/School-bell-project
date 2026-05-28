// Single fetch wrapper. Attaches the Bearer token, normalizes errors, and
// is the only file that talks to fetch() directly.

import { getSession, setSession } from "../auth/session"

export class ApiError extends Error {
  status: number
  body?: unknown
  constructor(status: number, message: string, body?: unknown) {
    super(message)
    this.status = status
    this.body = body
  }
}

export interface ApiOptions {
  method?: string
  headers?: HeadersInit
  body?: unknown
  query?: Record<string, string | number | boolean | undefined>
  signal?: AbortSignal
}

const BASE = (import.meta.env.VITE_API_URL as string | undefined) ?? ""

if (!BASE) {
  console.warn(
    "[api] VITE_API_URL is not set. Create frontend/.env with " +
      "VITE_API_URL=http://localhost:8080 and restart the dev server.",
  )
}

export async function api<T>(path: string, opts: ApiOptions = {}): Promise<T> {
  // Resolve against the current origin so a missing/relative BASE never makes
  // new URL() throw -- it would otherwise surface as a cryptic generic error.
  const url = new URL(path, BASE || window.location.origin)
  if (opts.query) {
    for (const [k, v] of Object.entries(opts.query)) {
      if (v !== undefined) url.searchParams.set(k, String(v))
    }
  }

  const headers = new Headers(opts.headers)
  const session = getSession()
  if (session) headers.set("Authorization", `Bearer ${session.token}`)

  let body: BodyInit | undefined
  if (opts.body instanceof FormData || opts.body instanceof URLSearchParams) {
    body = opts.body
    if (opts.body instanceof URLSearchParams && !headers.has("Content-Type")) {
      headers.set("Content-Type", "application/x-www-form-urlencoded")
    }
  } else if (opts.body !== undefined) {
    headers.set("Content-Type", "application/json")
    body = JSON.stringify(opts.body)
  }

  let res: Response
  try {
    res = await fetch(url, {
      method: opts.method ?? "GET",
      headers,
      body,
      signal: opts.signal,
    })
  } catch (e) {
    // fetch() rejects only on network-level failure (server down, CORS
    // preflight blocked, DNS, mixed content). Turn it into an ApiError with a
    // message the UI can show, and log the original for debugging.
    console.error("[api] network error for", url.toString(), e)
    throw new ApiError(
      0,
      `Cannot reach the API at ${url.origin}. Is the backend running and is VITE_API_URL correct?`,
    )
  }

  if (res.status === 401) {
    // Token rejected -- drop the session. ProtectedRoute redirects on the
    // next render.
    setSession(null)
  }

  if (!res.ok) {
    let detail: unknown
    try {
      detail = await res.json()
    } catch {
      /* response had no JSON body */
    }
    const message =
      detail && typeof detail === "object" && "detail" in detail
        ? String((detail as { detail: unknown }).detail)
        : res.statusText || "Request failed"
    throw new ApiError(res.status, message, detail)
  }

  if (res.status === 204) return undefined as T

  const ct = res.headers.get("content-type") ?? ""
  if (ct.includes("application/json")) {
    return (await res.json()) as T
  }
  return (await res.blob()) as T
}
