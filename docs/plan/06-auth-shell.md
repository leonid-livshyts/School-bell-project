# Step 6 — Auth shell: login, route guard, app chrome, logout

## Goal
A user lands at the app, gets redirected to `/login`, signs in, sees the app
shell (sidebar + topbar with their username and a logout button), and from
that point on every API call attaches the Bearer token automatically. A page
refresh keeps them logged in. Clicking logout (or hitting a 401) drops them
back to `/login` with the token cleared.

## Why this is step 6
Step 3 locked the API behind Bearer auth. Step 5 built the client that
attaches Bearer headers. Step 6 is the missing piece: an in-app way to
obtain that token and a guard that gates every protected page.

Doing this before the CRUD pages means each page can assume "user is logged
in" and never has to render its own login fallback.

## Files created / changed
```
frontend_v2/src/
  App.tsx                        ← becomes router root
  main.tsx                       ← wraps App in Providers
  lib/
    auth/
      session.ts                 ← token+user state (reactive)
      use-session.ts             ← hook over the session store
  routes/
    Login.tsx
    Register.tsx
    NotFound.tsx
  components/
    AppShell.tsx                 ← sidebar + topbar
    ProtectedRoute.tsx
    Logo.tsx
```

shadcn primitives to add (`npx shadcn@latest add ...`):
- `card` (login/register containers)
- `input`
- `label`
- `form` (RHF wrapper; brings in `react-hook-form`, `zod`, `@hookform/resolvers`)
- `sonner` (toaster — used here for login errors, broadly later)
- `dropdown-menu` (user menu in topbar)
- `separator`
- `skeleton` (used in step 7 too; install now)

## Session model

There is **no `/me` endpoint** on the backend. The username we display in the
topbar must come from somewhere local. Options:
1. Decode the username from the token. Not viable — the token is a random
   hex string with no payload.
2. Store the username the user typed into the login form alongside the token.
3. Render `Bell admin` as a generic label.

Pick **option 2**: stash `{ token, username }` together in `localStorage`.
It's already known to the client at login time and doesn't drift.

```ts
// lib/auth/session.ts
const KEY = "school_bell_session"

export interface Session {
  token: string
  username: string
}

type Listener = (s: Session | null) => void
const listeners = new Set<Listener>()

function read(): Session | null {
  const raw = localStorage.getItem(KEY)
  if (!raw) return null
  try { return JSON.parse(raw) as Session } catch { return null }
}

let cache = read()

export function getSession() { return cache }

export function setSession(s: Session | null) {
  cache = s
  if (s) localStorage.setItem(KEY, JSON.stringify(s))
  else localStorage.removeItem(KEY)
  listeners.forEach((l) => l(s))
}

export function subscribe(l: Listener) {
  listeners.add(l)
  return () => { listeners.delete(l) }
}
```

The session module owns the canonical state. `lib/api/client.ts` still reads
the raw token via its own `tokenStore`, but we update it to read from
`session.ts` instead — single source of truth. Adjust `client.ts`:

```ts
// in lib/api/client.ts
import { getSession, setSession } from "@/lib/auth/session"

// replace tokenStore with:
function token() { return getSession()?.token ?? null }

// inside api(): replace `const token = tokenStore.get()` with `const t = token()`
// On 401: setSession(null) instead of tokenStore.clear()
```

Drop the local `tokenStore` from step 5 — it served as a placeholder until the
session module existed. Update `auth.ts` similarly:

```ts
// lib/api/auth.ts
import { setSession } from "@/lib/auth/session"
// ...
export async function login(username: string, password: string) {
  const res = await api<LoginResponse>(...)
  setSession({ token: res.access_token, username })
  return res
}

export function logout() { setSession(null) }
```

## `lib/auth/use-session.ts`

```ts
import { useSyncExternalStore } from "react"
import { getSession, subscribe } from "./session"

export function useSession() {
  return useSyncExternalStore(subscribe, getSession, getSession)
}
```

`useSyncExternalStore` keeps every consumer (topbar, ProtectedRoute, etc.) in
sync without a context provider. Simpler than a global Zustand/Context setup
and exactly the use-case it was added for.

## `components/ProtectedRoute.tsx`

```tsx
import { Navigate, Outlet, useLocation } from "react-router-dom"
import { useSession } from "@/lib/auth/use-session"

export function ProtectedRoute() {
  const session = useSession()
  const location = useLocation()
  if (!session) {
    return <Navigate to="/login" replace state={{ from: location }} />
  }
  return <Outlet />
}
```

## `routes/Login.tsx`

Form with `username`, `password`. On submit:
- `login(username, password)` (from `@/lib/api/auth`).
- On success: read `location.state.from?.pathname` (or `/`), `navigate(there, { replace: true })`.
- On `ApiError` (status 400, "Wrong credentials"): show a `sonner` toast and a
  field-level error.

UI shape (no full code — kept terse):

```tsx
<Card className="w-full max-w-sm">
  <CardHeader>
    <CardTitle>Sign in</CardTitle>
    <CardDescription>School Bell admin</CardDescription>
  </CardHeader>
  <CardContent>
    <Form {...form}>
      ...username, password fields...
      <Button type="submit" disabled={form.formState.isSubmitting}>
        {form.formState.isSubmitting ? "Signing in..." : "Sign in"}
      </Button>
    </Form>
  </CardContent>
  <CardFooter>
    <Link to="/register" className="text-sm underline-offset-4 hover:underline">
      Create an account
    </Link>
  </CardFooter>
</Card>
```

Use `react-hook-form` + `zod`:

```ts
const schema = z.object({
  username: z.string().min(1, "Required"),
  password: z.string().min(1, "Required"),
})
```

## `routes/Register.tsx`
Fields: `username`, `email`, `password1`, `password2`. Client-side check
`password1 === password2`. POST `/register`. On success, auto-login the user
(call the new `login()` straight after). Surface backend errors verbatim
(`Username is taken`, `User with this email already exists`, etc.) via toast.

`role` is omitted from the UI — the backend defaults it to `"user"`.

## `components/AppShell.tsx`

Layout for every authenticated page. Two-pane shell:

```
+----------------------+----------------------------------------------+
|  Logo                | Topbar: page title, theme toggle, user menu  |
|  ─────               +----------------------------------------------+
|  ▸ Dashboard         |                                              |
|  ▸ Rooms             |                                              |
|  ▸ Lessons           |   <Outlet />                                 |
|  ▸ Devices           |                                              |
|  ▸ Measures          |                                              |
|  ▸ Ringtones         |                                              |
|  ▸ Voice messages    |                                              |
|  ▸ Alarms            |                                              |
+----------------------+----------------------------------------------+
```

```tsx
export function AppShell() {
  const session = useSession()
  return (
    <div className="min-h-screen grid grid-cols-[14rem_1fr]">
      <aside className="border-r bg-muted/40">
        <Logo className="m-4" />
        <nav className="flex flex-col gap-1 px-2 text-sm">
          <NavLink to="/" end>Dashboard</NavLink>
          <NavLink to="/rooms">Rooms</NavLink>
          <NavLink to="/lessons">Lessons</NavLink>
          <NavLink to="/devices">Devices</NavLink>
          <NavLink to="/measures">Measures</NavLink>
          <NavLink to="/ringtones">Ringtones</NavLink>
          <NavLink to="/voice-messages">Voice messages</NavLink>
          <NavLink to="/alarms">Alarms</NavLink>
        </nav>
      </aside>
      <div className="flex flex-col">
        <header className="h-14 border-b flex items-center justify-end gap-2 px-4">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost">{session?.username}</Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={logout}>Sign out</DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </header>
        <main className="p-6"><Outlet /></main>
      </div>
    </div>
  )
}
```

Nav uses `NavLink`'s `aria-current="page"` so the active item can be styled with
Tailwind's `aria-[current=page]` selector — no JS-driven active state needed.

## `App.tsx` — router

```tsx
import { createBrowserRouter, RouterProvider } from "react-router-dom"

const router = createBrowserRouter([
  { path: "/login", element: <Login /> },
  { path: "/register", element: <Register /> },
  {
    element: <ProtectedRoute />,
    children: [
      {
        element: <AppShell />,
        children: [
          { path: "/", element: <Dashboard /> },           // step 7
          { path: "/rooms", element: <RoomsPage /> },      // step 7
          { path: "/lessons", element: <LessonsPage /> },  // step 7
          // ...placeholder routes for step 7 pages
        ],
      },
    ],
  },
  { path: "*", element: <NotFound /> },
])

export default function App() {
  return (
    <>
      <RouterProvider router={router} />
      <Toaster />
    </>
  )
}
```

For step 6 itself, the step-7 pages can be temporary placeholder components
(`<div>Rooms — coming in step 7</div>`). Replace them in step 7 file-by-file.

## `main.tsx`

```tsx
createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <Providers>
      <App />
    </Providers>
  </StrictMode>,
)
```

## Verification

1. **Hard reload at `/`** → redirected to `/login` (since no session).
2. **Bad creds** → toast "Wrong credentials", form re-enables, no token saved.
3. **Good creds** → redirect to `/`, app shell renders, topbar shows the
   username typed at login.
4. **Refresh after login** → still logged in; session is read back from
   `localStorage`.
5. **Logout** → `localStorage` cleared, redirected to `/login`.
6. **Forced 401**: in DevTools, `localStorage.setItem("school_bell_session", JSON.stringify({token:"bad", username:"x"}))`, then call any API. The client clears the session, `ProtectedRoute` redirects on the next render.
7. **Register flow** → registering with new creds auto-logs-in and lands on
   `/`. Re-registering the same username surfaces the backend's error.
8. **DevTools Network**: every protected request has `Authorization: Bearer …`.
9. **a11y smoke**: tab order on login form is sensible; submit on Enter.

## Risks and edge cases
- **Token does nothing server-side.** `oauth2` only checks header presence.
  Any non-empty string passes. We accept this here; flagged as a follow-up
  from step 3.
- **`useSyncExternalStore`** is the right tool. Skip the temptation to wrap
  it in a Context provider.
- **Race**: the `ProtectedRoute` first render reads from `localStorage` via
  `getSession()` synchronously, so there is no flash-of-login-page on a
  logged-in refresh.
- **CSRF**: not relevant — we use Bearer header, not cookies.
- **XSS**: token in `localStorage` is vulnerable to XSS. Accepted risk for
  the admin UI; no cookies, no third-party scripts. Document, don't fix.
- **Multi-tab**: `localStorage` writes don't fire `storage` events in the
  same tab. Across tabs they do, but we don't subscribe. Logout in one tab
  won't immediately log out other tabs. Out of scope.

## Done when
- `/login`, `/register`, app shell, logout all work as described.
- Every protected page renders under `ProtectedRoute` → `AppShell`.
- `localStorage.school_bell_session` is the single source of truth.
- No console errors at boot, hot reload, or logout.
- `tsc --noEmit` clean.

## Commit
```
frontend_v2: auth shell -- login, register, route guard, app chrome

Adds the session store (token + username in localStorage), useSession
hook via useSyncExternalStore, /login and /register pages with
react-hook-form + zod, ProtectedRoute, and an AppShell with sidebar
nav + topbar user menu. All protected pages render under the shell.
Bearer header is attached automatically via lib/api/client.ts.
```
