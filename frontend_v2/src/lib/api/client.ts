// Single fetch wrapper. Attaches the Bearer token, normalizes errors, and
// is the only file that talks to fetch() directly.

const TOKEN_KEY = "school_bell_token"

export const tokenStore = {
  get: () => localStorage.getItem(TOKEN_KEY),
  set: (t: string) => localStorage.setItem(TOKEN_KEY, t),
  clear: () => localStorage.removeItem(TOKEN_KEY),
}

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

export async function api<T>(path: string, opts: ApiOptions = {}): Promise<T> {
  const url = new URL(BASE + path)
  if (opts.query) {
    for (const [k, v] of Object.entries(opts.query)) {
      if (v !== undefined) url.searchParams.set(k, String(v))
    }
  }

  const headers = new Headers(opts.headers)
  const token = tokenStore.get()
  if (token) headers.set("Authorization", `Bearer ${token}`)

  let body: BodyInit | undefined
  if (opts.body instanceof FormData || opts.body instanceof URLSearchParams) {
    body = opts.body
    // For URLSearchParams, browsers set the content-type automatically; do
    // the same explicitly so the server reads it as a form.
    if (opts.body instanceof URLSearchParams && !headers.has("Content-Type")) {
      headers.set("Content-Type", "application/x-www-form-urlencoded")
    }
  } else if (opts.body !== undefined) {
    headers.set("Content-Type", "application/json")
    body = JSON.stringify(opts.body)
  }

  const res = await fetch(url, {
    method: opts.method ?? "GET",
    headers,
    body,
    signal: opts.signal,
  })

  if (res.status === 401) {
    tokenStore.clear()
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
