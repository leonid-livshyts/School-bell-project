# Step 5 — Typed API client + endpoint wrappers

## Goal
A single, typed access layer for the backend. Every later page imports from
`@/lib/api/*` and never writes a raw `fetch`. Bearer token (set later in step 6)
is attached automatically. Errors are normalized so the UI can show one
consistent message format.

## Why this is step 5
Pages should describe *what* they need, not *how* to ask the server. Centralizing
the fetch wrapper means:
- One place to attach `Authorization`.
- One place to handle 401 → "log out and redirect".
- One place to translate FastAPI's `{detail: "..."}` shape into a UI-friendly
  error.
- TanStack Query keys stay readable (`["rooms"]`, `["lessons"]`, ...).

## Files created
```
frontend_v2/src/lib/
  api/
    client.ts           ← fetch wrapper, errors, token helper
    auth.ts             ← login, register
    rooms.ts            ← rooms CRUD
    lessons.ts          ← lessons CRUD
    devices.ts          ← devices CRUD (nested under room_id)
    measures.ts         ← measures CRUD (nested under room_id)
    voice_messages.ts   ← voice messages CRUD + upload/download
    ringtones.ts        ← ringtones CRUD + upload/download
    alarms.ts           ← list + per-room toggle
  types.ts              ← TS mirror of backend pydantic models
  query.ts              ← TanStack QueryClient + Provider wrapper
```

## `lib/types.ts` — mirror of `backend/models.py`

```ts
// Server-side timestamps come back as ISO strings; we keep them as strings.
// The UI converts when displaying.

export interface Lesson {
  id: number
  name: string
  start: string          // ISO datetime (naive UTC on server, harmless here)
  end: string
  room_id: number
  created_at?: string
  updated_at?: string
}

export interface LessonInput {
  name: string
  start: string          // ISO. The server treats wall-clock as Europe/Kyiv.
  end: string
  room_id: number
}

export interface Room {
  id: number
  name: string
  created_at?: string
  updated_at?: string
}

export interface RoomInput { name: string }

export interface Alarm {
  id: number
  is_active: boolean
  room_id: number
  created_at?: string
  updated_at?: string
}

export interface Measure {
  id: number
  temperature: number
  humidity: number
  volume: number
  air_quality: number
  measure_time: string
  room_id: number
}

export interface MeasureInput {
  temperature?: number
  humidity?: number
  volume?: number
  air_quality?: number
  measure_timestamp: number   // unix seconds
}

export interface Device {
  id: number
  key: string
  version: string
  installed_date: string
  room_id: number
  created_at?: string
  updated_at?: string
}

export interface DeviceInput {
  key: string
  version: string
  installed_date: string
}

export interface VoiceMessage {
  id: number
  filename: string
  room_id: number | null
  created_at?: string
  updated_at?: string
}

export interface Ringtone {
  id: number
  filename: string
  room_id: number | null
  created_at?: string
  updated_at?: string
}

export interface LoginResponse {
  access_token: string
  token_type: "bearer"
}

export interface RegisterInput {
  username: string
  password1: string
  password2: string
  email: string | null
  role: string | null
}
```

## `lib/api/client.ts` — fetch wrapper

```ts
const TOKEN_KEY = "school_bell_token"

export const tokenStore = {
  get: () => localStorage.getItem(TOKEN_KEY),
  set: (t: string) => localStorage.setItem(TOKEN_KEY, t),
  clear: () => localStorage.removeItem(TOKEN_KEY),
}

export class ApiError extends Error {
  constructor(public status: number, message: string, public body?: unknown) {
    super(message)
  }
}

interface ApiOptions extends Omit<RequestInit, "body"> {
  body?: unknown                         // auto-JSON unless FormData
  query?: Record<string, string | number | boolean | undefined>
}

const BASE = import.meta.env.VITE_API_URL ?? ""

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
  if (opts.body instanceof FormData) {
    body = opts.body                     // browser sets Content-Type w/ boundary
  } else if (opts.body !== undefined) {
    headers.set("Content-Type", "application/json")
    body = JSON.stringify(opts.body)
  }

  const res = await fetch(url, { ...opts, headers, body })

  if (res.status === 401) {
    tokenStore.clear()
    // Step 6 wires up the redirect. For now, just throw -- ProtectedRoute
    // catches the missing token on the next render.
  }

  if (!res.ok) {
    let detail: unknown
    try { detail = await res.json() } catch { /* not JSON */ }
    const msg =
      (detail && typeof detail === "object" && "detail" in detail
        ? String((detail as { detail: unknown }).detail)
        : res.statusText) || "Request failed"
    throw new ApiError(res.status, msg, detail)
  }

  if (res.status === 204) return undefined as T

  const ct = res.headers.get("content-type") ?? ""
  if (ct.includes("application/json")) return res.json() as Promise<T>
  return res.blob() as Promise<T>        // for /download endpoints
}
```

## `lib/api/auth.ts`

```ts
import { api, tokenStore } from "./client"
import type { LoginResponse, RegisterInput } from "../types"

export async function login(username: string, password: string) {
  const body = new URLSearchParams()
  body.set("username", username)
  body.set("password", password)
  const res = await api<LoginResponse>("/login", {
    method: "POST",
    body,                                // URLSearchParams → x-www-form-urlencoded
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
  } as any)
  tokenStore.set(res.access_token)
  return res
}

export async function register(input: RegisterInput) {
  return api<void>("/register", { method: "POST", body: input })
}

export function logout() {
  tokenStore.clear()
}
```

> NOTE: the cast `as any` is needed because the `body` typing in `ApiOptions`
> assumes JSON-able input. URLSearchParams is the one exception. We could
> broaden the type instead; keeping the cast localized to `login()` is fine.

## `lib/api/rooms.ts`

```ts
import { api } from "./client"
import type { Room, RoomInput } from "../types"

export const roomsApi = {
  list:   ()                              => api<Room[]>("/rooms/"),
  get:    (id: number)                    => api<Room>(`/rooms/${id}`),
  create: (input: RoomInput)              => api<void>("/rooms/", { method: "POST", body: input }),
  update: (id: number, input: RoomInput)  => api<void>(`/rooms/${id}`, { method: "POST", body: input }),
  remove: (id: number)                    => api<void>(`/rooms/${id}`, { method: "DELETE" }),
}
```

## `lib/api/lessons.ts`
```ts
import { api } from "./client"
import type { Lesson, LessonInput } from "../types"

export const lessonsApi = {
  list:   ()                                  => api<Lesson[]>("/lessons/"),
  get:    (id: number)                        => api<Lesson>(`/lessons/${id}`),
  create: (input: LessonInput)                => api<void>("/lessons/", { method: "POST", body: input }),
  update: (id: number, input: LessonInput)    => api<void>(`/lessons/${id}`, { method: "POST", body: input }),
  remove: (id: number)                        => api<void>(`/lessons/${id}`, { method: "DELETE" }),
}
```

## `lib/api/devices.ts`
```ts
import { api } from "./client"
import type { Device, DeviceInput } from "../types"

export const devicesApi = {
  list:   (roomId: number)                                    => api<Device[]>(`/${roomId}/devices/`),
  get:    (roomId: number, id: number)                        => api<Device>(`/${roomId}/devices/${id}`),
  create: (roomId: number, input: DeviceInput)                => api<void>(`/${roomId}/devices/`, { method: "POST", body: input }),
  update: (roomId: number, id: number, input: DeviceInput)    => api<void>(`/${roomId}/devices/${id}`, { method: "POST", body: input }),
  remove: (roomId: number, id: number)                        => api<void>(`/${roomId}/devices/${id}`, { method: "DELETE" }),
}
```

## `lib/api/measures.ts`
```ts
import { api } from "./client"
import type { Measure, MeasureInput } from "../types"

export const measuresApi = {
  list:   (roomId: number)                                    => api<Measure[]>(`/${roomId}/measures/`),
  get:    (roomId: number, id: number)                        => api<Measure>(`/${roomId}/measures/${id}`),
  create: (roomId: number, input: MeasureInput)               => api<void>(`/${roomId}/measures/`, { method: "POST", body: input }),
  update: (roomId: number, id: number, input: MeasureInput)   => api<void>(`/${roomId}/measures/${id}`, { method: "POST", body: input }),
  remove: (roomId: number, id: number)                        => api<void>(`/${roomId}/measures/${id}`, { method: "DELETE" }),
}
```

## `lib/api/voice_messages.ts`
```ts
import { api } from "./client"
import type { VoiceMessage } from "../types"

export const voiceMessagesApi = {
  list:   () => api<VoiceMessage[]>("/voice_messages/"),
  get:    (id: number) => api<VoiceMessage>(`/voice_messages/${id}`),
  upload: (file: File, roomId?: number) => {
    const fd = new FormData()
    fd.append("file", file)
    if (roomId !== undefined) fd.append("room_id", String(roomId))
    return api<void>("/voice_messages/", { method: "POST", body: fd })
  },
  remove: (id: number) => api<void>(`/voice_messages/${id}`, { method: "DELETE" }),
  downloadUrl: (id: number) =>
    `${import.meta.env.VITE_API_URL}/voice_messages/${id}/download`,
}
```

## `lib/api/ringtones.ts`
Same shape as voice_messages — base path `/ringtones/`.

## `lib/api/alarms.ts`
```ts
import { api } from "./client"
import type { Alarm } from "../types"

export const alarmsApi = {
  list: () => api<Alarm[]>("/alarms/"),
  set:  (roomId: number, isActive: boolean) =>
    api<{ room_id: number; is_active: boolean }>(`/alarms/${roomId}`, {
      method: "POST",
      body: { is_active: isActive },
    }),
}
```

## `lib/query.ts` — TanStack Query provider

```ts
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import type { ReactNode } from "react"

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: (count, err) => {
        // Don't retry auth failures.
        if (err && typeof err === "object" && "status" in err) {
          const s = (err as { status: number }).status
          if (s === 401 || s === 403 || s === 404) return false
        }
        return count < 2
      },
    },
  },
})

export function Providers({ children }: { children: ReactNode }) {
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
}
```

(Wrap `<App />` in `<Providers>` in step 6.)

## Verification

1. **Type-check.** `npm run build` (or `tsc --noEmit`) passes — no `any` leaks
   outside the one cast in `auth.ts`.
2. **One smoke call.** Temporarily, in `App.tsx`:
   ```ts
   useEffect(() => {
     roomsApi.list().then(console.log).catch(console.error)
   }, [])
   ```
   With no token, expect `ApiError { status: 401 }`. After manually setting
   `localStorage.setItem("school_bell_token", "anything")` and refreshing,
   expect a 200 with the rooms list (since oauth2 doesn't actually validate
   the token — see step 3 follow-up). Remove the smoke call before commit.
3. **Download URL.** `voiceMessagesApi.downloadUrl(1)` returns
   `http://localhost:8080/voice_messages/1/download`.

## Risks and edge cases
- **Trailing slash.** FastAPI redirects `/rooms` → `/rooms/`. The client
  always uses the slash version to avoid the cross-origin redirect.
- **Form-encoded login.** `/login` is the only form-encoded endpoint. Handled
  explicitly in `auth.ts`. Everything else is JSON.
- **`measures.create` server-side quirk.** The backend converts
  `measure_timestamp` (unix int) into a `datetime` and renames it to
  `measure_time` on the model. The client always sends `measure_timestamp`.
- **`Device.installed_date` is a datetime.** The form will produce an ISO
  string. Backend parses it via Pydantic.
- **Download endpoints return files**, not JSON. Either expose them via the
  `downloadUrl()` helper (preferred — browser handles streaming) or call
  `api<Blob>(...)`. Use the URL form unless we need to stream the bytes in JS.
- **401 self-recovery.** `client.ts` clears the token on 401, but the redirect
  is left to step 6's `ProtectedRoute` to keep the client decoupled from
  React Router.

## Done when
- All files above exist under `frontend_v2/src/lib/`.
- `types.ts` covers every model used by frontend-facing endpoints.
- No raw `fetch()` calls anywhere outside `client.ts`.
- Smoke test from step "Verification" passes manually.

## Commit
```
frontend_v2: typed API client + endpoint wrappers

Adds @/lib/api/client.ts (fetch + ApiError + Bearer attach), per-resource
modules (rooms, lessons, devices, measures, voice_messages, ringtones,
alarms, auth), TS types mirroring the backend pydantic models, and a
TanStack Query provider. No raw fetch calls outside the client wrapper.
```
