# Step 3 — Require Bearer auth on every frontend-facing router

## Goal
Per user decision, the entire admin API must require a logged-in session.
Currently only `rooms_router` enforces auth (`dependencies=[Depends(oauth2)]`).
Extend that to `lessons`, `devices`, `voice_messages`, `ringtones`, `alarms`.

Keep `private_router` **open to its existing `X-API-Key`** auth — the ESP32
uses it and must not be locked behind oauth2.

Keep `auth_router` (`/login`, `/register`) open — otherwise nobody can log in.

## Why this is step 3
Step 6 (auth shell) will attach a Bearer token to every API call. The token is
worthless unless the server actually demands it. Doing the backend lockdown
first means the frontend can be tested with real "must be logged in" semantics
from day one.

## What changes per router

`oauth2` is already defined in `backend/routers/oauth_tools.py`:

```python
from fastapi.security import OAuth2PasswordBearer
oauth2 = OAuth2PasswordBearer(tokenUrl="/login")
```

For each router that needs locking down, add `Depends(oauth2)` at the
router-level `dependencies=[...]`. Router-level beats per-handler because:
- It can't be forgotten on a new endpoint.
- It surfaces a single `Authorize` button in Swagger.

### `backend/routers/lessons.py`
```python
from fastapi import APIRouter, Depends                # add Depends
from routers.oauth_tools import oauth2                # add import

lessons_router = APIRouter(
    prefix="/lessons",
    tags=["lessons"],
    dependencies=[Depends(oauth2)],                   # NEW
)
```

### `backend/routers/devices.py`
```python
from fastapi import APIRouter, Depends, HTTPException, status
from routers.oauth_tools import oauth2

devices_router = APIRouter(
    prefix="/{room_id}/devices",
    tags=["rooms", "devices"],
    dependencies=[Depends(oauth2)],                   # NEW
)
```

### `backend/routers/voice_messages.py`
```python
from fastapi import APIRouter, Depends, File, UploadFile, Form, HTTPException, status
from routers.oauth_tools import oauth2

voice_messages_router = APIRouter(
    prefix="/voice_messages",
    tags=["voice_messages"],
    dependencies=[Depends(oauth2)],                   # NEW
)
```

### `backend/routers/ringtones.py`
Same shape as voice_messages.

### `backend/routers/alarms.py`
```python
from fastapi import APIRouter, Depends, HTTPException, status
from routers.oauth_tools import oauth2

alarms_router = APIRouter(
    prefix="/alarms",
    tags=["alarms"],
    dependencies=[Depends(oauth2)],                   # NEW
)
```

### `measures` is already protected — do not touch it
`measures_router` is mounted as a **sub-router** of `rooms_router` in
`backend/main.py:29`:

```python
rooms.rooms_router.include_router(measures.measures_router)
```

Sub-routers inherit the parent's `dependencies`, so `oauth2` is already
applied to every measures endpoint. Adding it again would just put two copies
into the dependency chain — harmless but noisy. Leave measures alone.

### Untouched routers and why

| Router | Why it stays open |
|---|---|
| `auth_router` (login / register) | Bootstrapping — needs to be reachable without a token. |
| `private_router` | ESP32-only; uses `X-API-Key` via `room_id_dependency`. Adding oauth2 would break the hardware. |
| `site_router` | Not registered in `main.py`. Dead code in this scope. |

## Files affected
- `backend/routers/lessons.py`
- `backend/routers/devices.py`
- `backend/routers/voice_messages.py`
- `backend/routers/ringtones.py`
- `backend/routers/alarms.py`

Each touched in exactly two places: the `from fastapi import …` line and the
`APIRouter(...)` call.

## Verification

```bash
# 1. Without a token: every protected endpoint returns 401
for path in /lessons/ /rooms/ /voice_messages/ /ringtones/ /alarms/ /1/devices/ /1/measures/; do
  printf "%-25s " "$path"
  curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8080$path
done
# Expected: 401 for every line.

# 2. /login is still open
curl -s -o /dev/null -w "%{http_code}\n" -X POST http://localhost:8080/login \
  -d "username=admin&password=wrong"
# Expected: 400 (bad creds) — not 401 (would mean we accidentally locked login).

# 3. /private is still open to X-API-Key, NOT to Bearer
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8080/private/time \
  -H "X-API-Key: <a real device key>"
# Expected: 200.

curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8080/private/time \
  -H "Authorization: Bearer some.token"
# Expected: 403 (missing X-API-Key) — confirms private is NOT using oauth2.

# 4. With a real token, protected endpoints work
TOKEN=$(curl -s -X POST http://localhost:8080/login \
  -d "username=admin&password=admin" | jq -r .access_token)
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8080/lessons/ \
  -H "Authorization: Bearer $TOKEN"
# Expected: 200.
```

## Risks and edge cases
- **Token validation is currently a no-op.** `OAuth2PasswordBearer` only checks
  that *some* `Authorization: Bearer …` header is present; it does not verify
  the token against the `Session` table. Anyone with any string can call the
  API. **Out of scope for this step.** Flagged as a follow-up:
  `routers/security.py` already has a `get_user_id` cookie-based check;
  consider extracting it into a header-based one and using it instead of
  `oauth2` directly. We will not do that now — it's a security hardening
  pass, not a wiring step.
- **The ESP32 keeps working.** It only calls `/private/*`. None of those
  endpoints are being changed in this step.
- **The legacy `frontend/`** (CRA) was hitting `/site/*` which is not mounted.
  Locking down other routers does not affect it (it was already broken).

## Done when
- Five routers have `dependencies=[Depends(oauth2)]`.
- All four verification scenarios above behave as expected.
- `private_router` is untouched.
- `auth_router` is untouched.

## Commit
```
backend: require Bearer auth on lessons/devices/voice/ring/alarms

Adds Depends(oauth2) at router level for every frontend-facing router.
measures inherits via rooms_router. private_router stays on X-API-Key
for ESP32 compatibility. auth_router stays open for login/register.
```

## Follow-up (not in this step)
Open a separate issue: "Token validation is a no-op — bind oauth2 to the
`Session` table." Either replace `oauth2` with a custom `Depends` that looks
up the session by token, or move every protected handler to depend on a real
`get_current_user` function.
