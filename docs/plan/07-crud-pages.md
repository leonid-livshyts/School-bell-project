# Step 7 — CRUD pages for every endpoint group

## Goal
Build a working page for each backend resource. By the end of this step,
every HTTP function the backend exposes (except ESP32-only `/private/*`) is
reachable from the UI. Each page follows the same shape so we don't reinvent
patterns.

## Why this is step 7
With auth and the API client in place, all that remains is presentation. This
is the bulk of the work but also the most mechanical — each resource follows
the template below.

## Page order (commit per page)
1. Rooms
2. Lessons
3. Devices (nested under room)
4. Measures (charts, nested under room)
5. Ringtones
6. Voice messages
7. Alarms
8. Dashboard (overview, last because it depends on the others)

Each page lands in its own commit so a regression can be bisected.

## Shared building blocks

Add these shadcn components once and reuse:
`table`, `dialog`, `alert-dialog`, `select`, `textarea`, `tabs`,
`tooltip`, `badge`, `switch`, `popover`, `calendar` (lessons),
`scroll-area`.

### `components/PageHeader.tsx`
```tsx
export function PageHeader({
  title, description, action,
}: { title: string; description?: string; action?: ReactNode }) {
  return (
    <div className="flex items-center justify-between mb-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
        {description && <p className="text-sm text-muted-foreground">{description}</p>}
      </div>
      {action}
    </div>
  )
}
```

### `components/DataTable.tsx`
Thin wrapper around shadcn's `Table`. Accepts `columns` (array of
`{ header, cell(row), className? }`) and `rows`. Renders empty state +
loading skeleton based on TanStack Query's `status`.

### `components/ConfirmDelete.tsx`
`alert-dialog` wrapper. Props: `onConfirm`, `title`, `description`. Shared by
every "delete row" interaction.

### `components/EmptyState.tsx`
Icon + headline + body + optional action. Single source of truth for "no data
yet".

### Error handling pattern
Every mutation:
```ts
const mut = useMutation({
  mutationFn: rooms.create,
  onSuccess: () => { qc.invalidateQueries({ queryKey: ["rooms"] }); toast.success("Saved") },
  onError: (err: ApiError) => toast.error(err.message),
})
```

Every query: rely on `<DataTable>`'s built-in loading/empty rendering.

---

## 7.1 Rooms page (`/rooms`)

### What it does
Lists all rooms, lets the user create, rename, and delete them.

### API
- `GET /rooms/` → list
- `POST /rooms/` with `{ name }` → create
- `POST /rooms/{id}` with `{ name }` → rename
- `DELETE /rooms/{id}` → delete (409 if children exist)

### Layout
- `PageHeader` with **Add room** button → opens a `Dialog` containing a
  one-field form.
- `DataTable`:
  - Columns: ID, Name, Created at (formatted), Updated at, Actions.
  - Row actions: a `…` `DropdownMenu` with **Edit** and **Delete**.
- **Edit** opens the same dialog prefilled.
- **Delete** opens `ConfirmDelete`.

### Form schema (zod)
```ts
const roomSchema = z.object({ name: z.string().min(1).max(64) })
```

### Edge cases handled in UI
- **Duplicate name** → backend returns 409 → toast "A room with this name
  already exists".
- **Delete with children** → 409 → toast "Room is still referenced by
  lessons/devices/measures/etc."

### Verification
- Create `TEST` → appears in table.
- Rename `TEST` → `TEST2` → reflected.
- Delete `TEST2` → row gone.
- Attempt to delete a room that has lessons → toast shown, row not removed.

---

## 7.2 Lessons page (`/lessons`)

### What it does
Full CRUD over lessons. Lessons are scheduled per room with a `start`/`end`
window. Overlapping windows are server-rejected.

### API
- `GET /lessons/`
- `POST /lessons/` with `{ name, start, end, room_id }`
- `POST /lessons/{id}`
- `DELETE /lessons/{id}`

The server normalizes `start`/`end` to naive UTC, treating any wall-clock the
client sends as **Europe/Kyiv** local. The frontend sends ISO strings that
match what the user typed — the backend handles the TZ math.

### Layout
- Tabs at the top: **List** (default) | **By room**.
- **List tab**: a `DataTable` with columns Name, Room, Start, End, Actions.
- **By room tab**: a `Select` for the room + a per-day grouped list (today,
  tomorrow, later this week, later).
- **Add lesson** in `PageHeader` → dialog with:
  - `name` text input
  - `room_id` `Select` (populated from `roomsApi.list()`)
  - `start` date + time picker
  - `end` date + time picker
  - Submit posts ISO strings (`new Date(value).toISOString()` is fine; backend
    strips the TZ and treats as Kyiv wall-clock).

### Edge cases
- **Overlap** (server returns 400 with detail like `"This lesson overlaps
  lesson id=N (...)"`) → show the detail verbatim in a toast and keep the
  form open.
- **Start ≥ End** (client-side check before submit).
- **No rooms exist** → disable the form and link to `/rooms`.

### zod
```ts
const lessonSchema = z.object({
  name: z.string().min(1).max(120),
  room_id: z.number().int().positive(),
  start: z.string().datetime({ offset: true }),
  end:   z.string().datetime({ offset: true }),
}).refine((v) => new Date(v.start) < new Date(v.end), {
  message: "End must be after start", path: ["end"],
})
```

### Verification
- Create a lesson in an empty room → 201, appears.
- Create an overlapping lesson → 400, toast shows the server's overlap detail.
- Edit shifts the lesson 1h later → row updates.
- Delete row → removed.

---

## 7.3 Devices page (`/rooms/:id/devices`, and `/devices` index)

### What it does
ESP32 devices are registered per room with a unique `key` (the X-API-Key the
device sends back on `/private/*`). UI lets admins add, view, edit, delete.

### API
- `GET /{room_id}/devices/`
- `POST /{room_id}/devices/`
- `POST /{room_id}/devices/{id}`
- `DELETE /{room_id}/devices/{id}`

### Layout
Two-level navigation:
- `/devices` — index page: lists rooms (from `roomsApi.list()`) with a count
  of devices in each (one `devicesApi.list(roomId)` per row — fine at our
  scale; if it grows, add a single GET on the backend later).
- `/rooms/:id/devices` — per-room page: `DataTable` of devices.

### Per-row UI
- Show `key` masked by default (`••••••••<last 4>`) with a `Reveal` toggle
  and a `Copy` button. The key is the only sensitive value in the UI.
- `version` plain text.
- `installed_date` formatted.

### Add device dialog
- `key` (text — also a **Generate** button that fills it with a random 32-char
  hex string from `crypto.getRandomValues`).
- `version` (text, defaults to `"1.0"`).
- `installed_date` (defaults to "now").

### Edge cases
- Backend treats invalid `room_id` as `IntegrityError` → 400 "No such room".
  Toast it.
- `installed_date` is required by the pydantic model; default it on the form.

### Verification
- Generate a key, save → device appears.
- Copy key → clipboard has the value.
- Delete → row gone; ESP32 with that key now gets 403 from `/private/*`.

---

## 7.4 Measures page (`/rooms/:id/measures`, and `/measures` index)

### What it does
View sensor history for each room. Read-only in the UI (creation is the
ESP32's job via `POST /private/sensors`). Admin can delete individual bad
readings.

### API
- `GET /{room_id}/measures/`
- `DELETE /{room_id}/measures/{id}`
- (`POST /{room_id}/measures/` exists but is only useful for testing — wire
  it up as a dev-only button if needed; otherwise skip the create UI.)

### Layout
- `/measures` index: room list with last-reading time per row.
- `/rooms/:id/measures`: four line charts, 2×2 grid, using
  **Recharts** (modern, plays well with TS — install
  `npm install recharts`; alternatively reuse the existing chart.js
  setup, but recharts is cleaner with shadcn's chart helpers).
  - Temperature (°C)
  - Humidity (%)
  - Volume (dB)
  - Air quality (CO₂ %)
- Time range selector: `Last hour`, `Last 24h`, `Last week`, `All`.
  Client-side filter over the full list returned by the backend.
- Beneath the charts, a collapsible `DataTable` of raw rows (timestamp,
  values, delete action).

### shadcn chart wrapper
`npx shadcn@latest add chart` adds a `<ChartContainer>` + `<ChartTooltip>`
that wraps recharts. Use that — it produces nicer-looking output than raw
recharts.

### Edge cases
- **Empty data**: each chart shows a single `EmptyState` instead of an empty
  axis.
- **Mixed null values**: backend returns nulls in any of the four metrics if
  a sensor failed. Filter them out per-series so the line breaks rather than
  jumping to 0.

### Verification
- A room with measures → all four charts render and the table populates.
- Switching the range filter trims the data shown.
- Deleting a row removes it from both the chart and the table.

---

## 7.5 Ringtones page (`/ringtones`)

### What it does
Library of ringtones. Each ringtone is a file on disk + a DB row. Optionally
tied to a `room_id` (the ESP32 in that room plays "its" ringtone via
`/private/ringtone_code`).

### API
- `GET /ringtones/`
- `POST /ringtones/` (multipart `file`, optional form field `room_id`)
- `GET /ringtones/{id}/download`
- `DELETE /ringtones/{id}`

### Layout
- `PageHeader` with **Upload ringtone** → opens an upload dialog:
  - `<input type="file" accept="audio/mpeg,audio/wav">`
  - `Select` for room (with "All rooms" mapping to `null`).
  - Drag-and-drop zone over the dialog body.
- `DataTable`:
  - Columns: Filename, Room, Created at, Actions.
  - "Play" button → expands an inline `<audio controls src={downloadUrl}>`
    using `ringtonesApi.downloadUrl(id)`.
  - "Download" → anchor `<a href={downloadUrl} download>`.
  - "Delete" → `ConfirmDelete`.

### Edge cases
- Large files: show a progress indicator while the upload is in flight
  (TanStack Query `isPending`).
- Wrong mime type: client-side reject before POST.
- Server-side filename collision: backend prepends a timestamp; no collisions
  in practice.

### Verification
- Upload `bell.mp3` assigned to room 1 → appears, plays inline.
- Upload another with same filename → both show with different prefixes.
- Delete → file gone; subsequent download is a 404.

---

## 7.6 Voice messages page (`/voice-messages`)

Identical UX to Ringtones, just hitting `/voice_messages/*`. Same dialog,
same table, same player.

Implementation note: extract a generic `AudioLibraryPage` component that takes
`api`, `resourceName`, `routeBase` props, and use it from both Ringtones and
Voice messages. Saves a few hundred lines of near-duplicate code.

```ts
<AudioLibraryPage
  title="Voice messages"
  description="Pre-recorded announcements played through the bell."
  api={voiceMessagesApi}
  queryKey={["voice_messages"]}
/>
```

### Verification
Mirror the Ringtones checklist.

---

## 7.7 Alarms page (`/alarms`)

### What it does
A board of all rooms with a toggle that flips the alarm on/off. When toggled
on, the ESP32 in that room starts the alarm sound on its next poll of
`/private/alarm`.

### API
- `GET /alarms/` (list — only includes rooms that have *ever* had an alarm
  row; new rooms won't be in the response)
- `POST /alarms/{room_id}` with `{ is_active: boolean }`

To present every room (not only those with alarm rows), the page does:
```ts
const [rooms, alarms] = await Promise.all([
  roomsApi.list(),
  alarmsApi.list(),
])
const byRoom = new Map(alarms.map(a => [a.room_id, a]))
const view = rooms.map(r => ({ room: r, isActive: byRoom.get(r.id)?.is_active ?? false }))
```

### Layout
- Header has a giant red **Stop all** button (POSTs `is_active=false` to every
  room currently active). Behind an `ConfirmDelete`-style confirmation.
- Grid of cards (2–4 columns responsive), one per room:
  - Room name
  - Big toggle (`Switch`)
  - Subtle indicator when toggling (`isPending` spinner)
  - Last changed timestamp (from the alarm row's `updated_at`)
- The "active" card variant uses `border-destructive` and a small badge.

### Edge cases
- The server returns the new state, so the local cache update can just use
  that to avoid an extra GET.
- Toggling fast (off-on-off): TanStack Query keeps the latest mutation;
  surface a sonner notice if a previous request errors out.

### Verification
- Toggle a room on → card highlights, last-changed updates.
- Refresh → state persists.
- "Stop all" with three rooms on → all three flip off; ESP32 polls report
  `ring=true` once and stop the sound.

---

## 7.8 Dashboard (`/`)

### What it does
A landing page that surfaces the most useful at-a-glance signals. Built last
because it composes data from every other page.

### Cards (grid of `Card`s)
1. **Rooms** — count + "View all" link.
2. **Lessons today** — count of today's lessons (filter on the local date)
   plus the next lesson's name and start time.
3. **Active alarms** — count of rooms with `is_active=true`, plus a link to
   `/alarms`.
4. **Devices online** — count of devices that have posted measures in the
   last 5 minutes. Computed by fetching `/{room_id}/measures/?limit=1` per
   room and checking the timestamp. (If this becomes too chatty, add a
   backend `/devices/heartbeats` endpoint — out of scope here.)
5. **Storage** — counts of ringtones and voice messages.

Each card uses `Skeleton` while loading.

### Verification
- With one alarm on and one lesson scheduled in 30 min, the corresponding
  cards reflect both.
- Toggling something on another page invalidates the relevant query and the
  dashboard updates on next visit.

---

## Routing recap

Update `App.tsx` (from step 6) with the real pages:

```tsx
{ path: "/", element: <Dashboard /> },
{ path: "/rooms", element: <RoomsPage /> },
{ path: "/lessons", element: <LessonsPage /> },
{ path: "/devices", element: <DevicesIndex /> },
{ path: "/rooms/:roomId/devices", element: <DevicesByRoom /> },
{ path: "/measures", element: <MeasuresIndex /> },
{ path: "/rooms/:roomId/measures", element: <MeasuresByRoom /> },
{ path: "/ringtones", element: <RingtonesPage /> },
{ path: "/voice-messages", element: <VoiceMessagesPage /> },
{ path: "/alarms", element: <AlarmsPage /> },
```

## Risks and edge cases (page-set wide)
- **Timezones in lessons.** Backend converts naive wall-clock to UTC assuming
  Europe/Kyiv. Frontend displays in the browser's local TZ but submits ISO
  strings — the server reads the wall-clock component and re-interprets in
  Kyiv. Document this near the lesson form so admins outside Kyiv aren't
  surprised. If the admin is in another TZ, recommend setting the workstation
  to Kyiv time for scheduling.
- **No pagination anywhere.** Backend returns everything. Acceptable until
  any list grows past a few thousand rows. Flag for future work; do not add
  client-side pagination now.
- **Optimistic updates** are not used. Every mutation refetches its query on
  success. Simpler; adequate for an admin UI.
- **File uploads** stream into memory before posting. For multi-MB ringtones
  this is fine; for anything > ~25MB, switch to streaming. Out of scope.

## Done when
Each of the eight pages has:
- A working create/list/update/delete path (except where the backend doesn't
  expose one).
- Empty state, loading state, error toast.
- A commit + push with a focused message.

## Commits (one per page)
```
frontend_v2: Rooms page -- list, create, rename, delete
frontend_v2: Lessons page -- list, create with overlap handling, edit, delete
frontend_v2: Devices pages -- index and per-room CRUD w/ key reveal/copy
frontend_v2: Measures pages -- index and per-room charts (recharts) + table
frontend_v2: Ringtones page -- upload, inline player, download, delete
frontend_v2: Voice messages page (reuses AudioLibraryPage component)
frontend_v2: Alarms board -- per-room toggles + Stop all
frontend_v2: Dashboard -- composes counts from rooms/lessons/alarms/devices
```
