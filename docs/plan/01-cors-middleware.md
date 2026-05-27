# Step 1 — Add CORS middleware to FastAPI

## Goal
The browser must be able to call the FastAPI backend from the frontend dev origin
(`http://localhost:5173`, plus the Coder wildcard subdomain) and from production
(`https://$DEPLOY_DOMAIN`). Right now FastAPI ships with no CORS middleware, so
every cross-origin browser request is silently blocked at the preflight stage.

## Why this is step 1
Nothing in the new frontend can work until the browser is allowed to talk to the
API. Adding CORS is the smallest possible backend change and unblocks every
later step.

## Files affected
- `backend/main.py` — add one import and one `app.add_middleware(...)` call.
- No new files. No model or router changes.

## Detailed change

```python
# backend/main.py (top of file)
from fastapi.middleware.cors import CORSMiddleware
```

Insert immediately after `app = FastAPI(...)`, before any `app.include_router`
call:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=(
        r"^http://localhost:5173$"
        r"|^https://[a-zA-Z0-9-]+--main--[a-zA-Z0-9-]+--[a-zA-Z0-9-]+\.coder\.brobots\.org\.ua$"
        r"|^https://[a-zA-Z0-9.-]+$"  # production deploy domain
    ),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Why `allow_origin_regex`, not `allow_origins=["*"]`
The frontend will send the `Authorization: Bearer …` header. Per CORS spec,
`allow_origins=["*"]` is **incompatible** with `allow_credentials=True`. The
regex above whitelists the three real origin shapes we use:

1. `http://localhost:5173` — local Vite dev server.
2. `https://<port>--main--<workspace>--<owner>.coder.brobots.org.ua` — Coder
   wildcard subdomains (any port, any workspace, any owner).
3. `https://<any-domain>` — production deploy domain. This is broad but is the
   only entry that lets us talk to `$DEPLOY_DOMAIN` without hardcoding it. If
   we later want to tighten it, swap this third alternative for the literal
   production hostname.

### Why `allow_methods=["*"]` and `allow_headers=["*"]`
We use GET/POST/DELETE plus `Authorization`, `Content-Type`, and (for uploads)
`Content-Disposition`. Wildcard is simpler than listing them and is fine
because the origin regex already gates access.

## Verification

Run the backend, then:

```bash
# 1. Preflight from the dev origin
curl -i -X OPTIONS http://localhost:8080/lessons/ \
  -H "Origin: http://localhost:5173" \
  -H "Access-Control-Request-Method: GET" \
  -H "Access-Control-Request-Headers: Authorization"
```

Expected response headers:
- `HTTP/1.1 200 OK`
- `Access-Control-Allow-Origin: http://localhost:5173`
- `Access-Control-Allow-Credentials: true`
- `Access-Control-Allow-Methods: *`
- `Access-Control-Allow-Headers: *`

```bash
# 2. Preflight from a Coder subdomain
curl -i -X OPTIONS http://localhost:8080/lessons/ \
  -H "Origin: https://5173--main--school-bell--deimocdp.coder.brobots.org.ua" \
  -H "Access-Control-Request-Method: GET"
```
Expected: `Access-Control-Allow-Origin` echoes that origin.

```bash
# 3. Real GET from a disallowed origin should still succeed (CORS is a browser
#    contract, not a server firewall) but the response will not include the
#    allow-origin header, so a real browser would block it.
curl -i http://localhost:8080/lessons/ -H "Origin: https://evil.example"
```
Expected: 2xx body, **no** `Access-Control-Allow-Origin` header.

## Risks and edge cases
- **Wildcard with credentials is rejected by browsers.** Mitigated by using
  `allow_origin_regex` instead.
- **The regex's third alternative is broad.** It accepts any `https://hostname`
  origin. Acceptable trade-off until we know `$DEPLOY_DOMAIN` and can pin it.
  Flag as a follow-up: replace with literal once domain is stable.
- **Cookies vs. Bearer header.** We use Bearer token in localStorage, not
  cookies. `allow_credentials=True` is still needed because some browsers treat
  `Authorization` headers as credentials in CORS preflights.
- **Trailing slashes.** FastAPI returns 307 redirects when `/lessons` is hit
  without the trailing slash. Browsers can choke on cross-origin redirects.
  Frontend always uses the canonical path with the trailing slash to avoid the
  redirect.

## Done when
- `backend/main.py` has the import + middleware call.
- The three curl checks above pass.
- Backend still starts cleanly (`python backend/main.py` runs).

## Commit
```
backend: enable CORS for dev, Coder subdomains, and prod

Adds CORSMiddleware with an origin regex covering localhost:5173,
*.coder.brobots.org.ua, and any https origin (for the prod deploy).
allow_credentials=True so the Authorization header can ride along.
```
