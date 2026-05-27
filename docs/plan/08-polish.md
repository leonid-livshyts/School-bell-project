# Step 8 — Polish pass

## Goal
The app feels finished: empty states, loading skeletons, error toasts, dark
mode, responsive layout. No new features; every existing screen gets one
quality bump.

## Why this is step 8
The 8 pages in step 7 will have done the minimum for each pattern. Polish in
one focused pass means consistency across pages, and a single review is
enough to confirm the whole app behaves nicely.

## Scope (concrete list)

### 1. Loading skeletons
- Replace any spinner-only loading state with shadcn `Skeleton` blocks
  shaped like the eventual content (table rows, cards, chart placeholders).
- `DataTable` (from step 7) should render N skeleton rows during `pending`
  status. Default N = 6.

### 2. Empty states
- Every list shows `EmptyState` (icon + headline + body + action) when the
  query returned an empty array.
- Customize copy per page:
  - Rooms: "No rooms yet. Create the first one to get started."
  - Lessons: "Nothing scheduled. Add a lesson to see it on the board."
  - Devices: "No devices in this room yet."
  - Measures: "Waiting for the first reading from the ESP32."
  - Ringtones / Voice messages: "Library is empty. Upload an audio file."
  - Alarms: "All quiet."
  - Dashboard cards: shrink to a one-line muted text instead of a card.

### 3. Error UX
- `<ErrorBoundary>` at the route level: a friendly fallback ("Something
  broke. We logged it. Try refreshing.") + a `<details>` with the stack for
  ourselves.
- `<Toaster>` (sonner) is already there from step 6; standardize copy:
  - Network/5xx: "Server error. Try again in a moment."
  - 401 anywhere: don't toast — the session module already redirects.
  - 4xx with `detail`: show the `detail` verbatim.
  - Successes: `Created`, `Saved`, `Deleted`, `Uploaded`.

### 4. Dark mode
- Add a `theme-provider.tsx` that reads `localStorage.theme` (`"light"`,
  `"dark"`, or `"system"`) and sets `<html class="dark">` accordingly.
- Topbar gets a `ThemeToggle` (sun/moon icon + `DropdownMenu` with the three
  options).
- shadcn's default CSS variables already cover both modes — no extra
  styling needed.

### 5. Responsive layout
- The sidebar (step 6) collapses to an icon-only rail < 768px (use a
  `Sheet` triggered by a hamburger in the topbar to open the full sidebar).
- Tables wrap in `<ScrollArea>` on small screens.
- Card grids on dashboard / alarms switch from 4 to 2 to 1 columns at
  `lg`/`md`/`sm` breakpoints.

### 6. Keyboard + a11y
- Every dialog has a focused first input on open.
- Tab order in forms matches reading order.
- All clickable icons have an `aria-label`.
- Toast region uses `aria-live="polite"` (sonner's default).
- Run an axe pass once at the end (`npm install --save-dev @axe-core/cli`,
  `npx @axe-core/cli http://localhost:5173 --exit`).

### 7. Small visual touches
- `404` page from step 6 gets a usable design (centered, link back home).
- App favicon / logo replaced with something bell-themed (placeholder SVG is
  fine — file lives at `public/bell.svg`).
- Page title (`document.title`) updates per route. Add a `useDocumentTitle`
  hook and call it in each page.

### 8. Performance check
- `npm run build` and inspect `dist/`. Any chunk > 500KB → investigate.
  Recharts often is — fine. Lucide icons should be tree-shaken; verify by
  spot-checking the build output.
- Lighthouse pass on the running prod build. Target ≥ 90 in Performance and
  ≥ 95 in Accessibility.

## Files affected
```
frontend_v2/src/
  components/
    Skeleton variants (per-page)
    EmptyState.tsx              ← extended with per-page copy
    ErrorBoundary.tsx           ← new
    ThemeProvider.tsx           ← new
    ThemeToggle.tsx             ← new
    ResponsiveSidebar.tsx       ← refactor of AppShell
  hooks/
    useDocumentTitle.ts         ← new
  routes/
    NotFound.tsx                ← redesigned
  public/
    bell.svg                    ← favicon
```

Code-quality changes (no behavior change):
- Lint config: enable `@typescript-eslint/no-unused-vars`, `react/jsx-key`.
  Fix all reported issues.
- Run `npx prettier . --write` once across the new frontend.

## Verification

Checklist (eyeball + DevTools), executed once at the end:

- [ ] Each page renders a sensible empty state with no data.
- [ ] Each page shows skeletons (not spinners) while loading.
- [ ] Forcing a 500 from the backend triggers a polite toast, not a console
      error UI.
- [ ] Toggling system / light / dark in the user menu visibly changes every
      page; refresh preserves the choice.
- [ ] Resize to 360px width: sidebar collapses, hamburger opens a sheet,
      tables scroll horizontally, no layout overflow.
- [ ] Tab through the login form: focus order is `username` → `password` →
      `Sign in` → "Create an account" link.
- [ ] Each page has a unique `document.title`.
- [ ] `npm run build` is clean. No chunk > 1MB.
- [ ] `axe-core` reports no critical issues.
- [ ] Lighthouse: Perf ≥ 90, A11y ≥ 95, Best Practices ≥ 95.

## Risks and edge cases
- **Theme flash** on first paint. Mitigate by inlining a tiny script in
  `index.html` that reads `localStorage.theme` and sets `<html class>` before
  React mounts.
- **ErrorBoundary swallowing real bugs**: log the original error to the
  console (and to a future telemetry hook) before rendering the fallback.
- **Sheet keyboard trap**: shadcn handles this; just don't override `onKeyDown`.
- **Lighthouse scores depend on network**: run the test against `npm run
  preview`, not `npm run dev`.

## Done when
The verification checklist is fully checked.

## Commit
```
frontend_v2: polish -- skeletons, empty states, dark mode, responsive shell

Adds shadcn Skeleton placeholders to every list/chart, swaps spinner-only
loading for skeletons, fills out per-page empty states, introduces
ErrorBoundary with a friendly fallback, dark mode via a localStorage-backed
ThemeProvider + topbar toggle, responsive sidebar (Sheet on small
viewports), per-page document.title, and a redesigned 404. Lighthouse ≥
90/95/95.
```
