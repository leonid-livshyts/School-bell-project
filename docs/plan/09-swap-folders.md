# Step 9 — Replace the old `frontend/` with `frontend_v2/`

## Goal
The new frontend lives at `frontend/` (the canonical name). The old CRA app is
gone. Anything outside the repo that referenced the old layout has been
updated.

## Why this is step 9
We've been working in `frontend_v2/` to keep the old app intact for
reference. Once the new app is feature-complete (steps 4–8) and the user has
explicitly approved, we swap.

## Pre-flight — confirm with the user
Before doing **anything destructive**, confirm one more time:
- "Frontend_v2 is feature complete. About to delete the old `frontend/` and
  rename `frontend_v2/` → `frontend/`. OK to proceed?"

Do **not** proceed without an explicit yes. This step touches state that's
hard to recover quickly.

## Files / directories affected
- `frontend/` (entire directory) — **deleted**.
- `frontend_v2/` → renamed to `frontend/`.
- Any reference to "frontend_v2" in the repo — search and replace to
  "frontend".

## Procedure

```bash
cd /home/coder/projects/school_bell

# 0. Sanity: working tree must be clean before we start.
git status                                  # expect: only untracked __pycache__ stuff

# 1. Confirm new app builds standalone.
( cd frontend_v2 && npm run build )         # must succeed

# 2. Remove the old frontend.
git rm -r frontend/

# 3. Move the new one into place.
git mv frontend_v2/ frontend/

# 4. Find any stale references.
git grep -n "frontend_v2"                   # expect: zero hits

# 5. The old frontend's package-lock referenced CRA-specific deps. The new
#    one's package-lock is already correct -- nothing to regenerate.

# 6. Build from the new location to confirm nothing broke during the move.
( cd frontend && npm run build )

# 7. Smoke the dev server.
( cd frontend && npm run dev -- --host :: --port 5173 ) &
DEV_PID=$!
sleep 5
curl -fsS http://localhost:5173/ > /dev/null && echo "dev server OK"
kill $DEV_PID
```

## Repo-wide cross-references to check

```bash
git grep -n "frontend"
```

Likely hits and what to do with them:
- `AI.md` — mentions a "Frontend" part. Leave the prose; the path label is
  still correct.
- `~/.claude/CLAUDE.md` — examples reference Vite/CRA workflows. Out of scope
  (user-managed file).
- Any deploy-related Dockerfile or compose file inside `frontend/` (none
  exists today). If one is added later, it will already point at the right
  path.
- Memory files under `~/.claude/projects/-home-coder-projects-school-bell/memory/`
  — none currently reference the frontend path. Leave alone.

## Verification

1. **Repo state.** `ls frontend_v2 2>/dev/null` → "No such file or directory".
   `ls frontend/package.json` → exists.
2. **Build.** `cd frontend && npm run build` → exits 0.
3. **Dev.** `npm run dev -- --host :: --port 5173` → page loads through the
   Coder URL; login still works; one CRUD round-trip succeeds against a real
   backend running on port 8080.
4. **No dangling references.** `git grep -n "frontend_v2"` → nothing.
5. **Git history.** `git log --follow frontend/src/App.tsx` shows the history
   from when the file was created in `frontend_v2/`. (`git mv` preserves
   history.)

## Risks and edge cases
- **Uncommitted changes in `frontend/`** — the pre-flight `git status` would
  catch them. If anything turns up, commit or stash before deleting.
- **`__pycache__` and other ignored cruft** — already in `.gitignore`; no
  effect on the swap.
- **Open Coder port mapping** — the dev server still listens on 5173; the
  Coder URL is unchanged. No reconfiguration needed.
- **Browser-cached old assets** — CRA's `service worker` is **not** registered
  (we deleted before any users got it). No cache to bust.
- **External deploy scripts** — the user's `~/.claude/CLAUDE.md` documents
  cloning the project on a VPS and running `docker compose up`. No
  Dockerfile/compose exists in the repo yet. If they're added later, point
  them at `/app/frontend/` (the new path). Out of scope here.

## Done when
- `frontend_v2/` no longer exists.
- `frontend/` is the new app, builds and runs.
- `git grep "frontend_v2"` is empty.
- One end-to-end smoke (login → make a room → delete it) succeeds against
  the live backend.

## Commit
```
chore: replace legacy CRA frontend with frontend_v2

Removes the abandoned CRA app at frontend/ (which hit /site/* endpoints
that aren't mounted in main.py) and promotes frontend_v2/ to the
canonical frontend/. git mv preserves history. Build and dev server
verified from the new location.
```

## After the merge
- Push to `master` (per AI.md).
- Confirm the deploy domain still serves the new app (if a deploy pipeline
  exists by then).
- Open follow-ups (separate issues / TODOs, not in this PR):
  1. Replace `oauth2`'s no-op token check with a real `Session`-table lookup
     (carried over from step 3).
  2. Tighten the CORS regex's third alternative to literal production hostname
     once `$DEPLOY_DOMAIN` is fixed (carried over from step 1).
  3. Consider adding `ondelete="CASCADE"` to the room-id FKs if the 409 UX
     gets in the way (carried over from step 2).
```
