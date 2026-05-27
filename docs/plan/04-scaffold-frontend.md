# Step 4 — Scaffold the new frontend (`frontend_v2/`)

## Goal
A clean Vite + React + TypeScript app at `frontend_v2/`, with Tailwind v4,
shadcn/ui registered, TanStack Query and React Router installed, env config
in place, dev server reachable from the Coder wildcard subdomain. After this
step, `npm run dev` shows a working page with a shadcn `Button` on it.

## Why this is step 4
Backend is unblocked (steps 1–3). Everything from step 5 onward writes
frontend code, and that code needs a working scaffold underneath it. Get the
toolchain right once, then never touch it.

## Files / directories created
- `frontend_v2/` (entire Vite scaffold)
- `frontend_v2/.env`
- `frontend_v2/.env.example`
- `frontend_v2/.gitignore` (Vite default, plus `.env`)
- `frontend_v2/components.json` (shadcn config)
- `frontend_v2/src/lib/utils.ts` (shadcn `cn` helper)
- `frontend_v2/src/components/ui/button.tsx` (first shadcn component)

## Procedure

```bash
cd /home/coder/projects/school_bell

# 1. Vite + React + TypeScript scaffold
npm create vite@latest frontend_v2 -- --template react-ts
cd frontend_v2

# 2. Install Tailwind v4 (no separate config file needed)
npm install tailwindcss @tailwindcss/vite

# 3. Replace src/index.css contents with the Tailwind import
#    (see "src/index.css" below)

# 4. Patch vite.config.ts
#    (see "vite.config.ts" below)

# 5. tsconfig path alias `@/*` -> `src/*`
#    Add to compilerOptions:
#       "baseUrl": ".",
#       "paths": { "@/*": ["src/*"] }
#    Also add the same in tsconfig.app.json.

# 6. Install shadcn-compatible deps
npm install -D @types/node                           # for path.resolve in vite.config
npm install lucide-react class-variance-authority clsx tailwind-merge tailwindcss-animate

# 7. shadcn init (writes components.json, src/lib/utils.ts, etc.)
npx shadcn@latest init -d                            # -d = use defaults
# When prompted, pick: Default style, Slate base color, CSS variables yes.

# 8. Smoke-test component
npx shadcn@latest add button

# 9. Routing + state
npm install react-router-dom @tanstack/react-query

# 10. Run it
npm run dev -- --host :: --port 5173
```

## File contents to drop in

### `frontend_v2/vite.config.ts`
```ts
import path from "node:path"
import { defineConfig } from "vite"
import react from "@vitejs/plugin-react"
import tailwindcss from "@tailwindcss/vite"

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: { "@": path.resolve(__dirname, "./src") },
  },
  server: {
    host: "::",
    port: 5173,
  },
})
```

### `frontend_v2/src/index.css`
```css
@import "tailwindcss";

@layer base {
  :root {
    /* shadcn css variables -- init populates these. Leave as generated. */
  }
}
```

(shadcn's `init` will write the full variable block; this file just shows the
shape.)

### `frontend_v2/.env.example`
```
VITE_API_URL=http://localhost:8080
```

### `frontend_v2/.env` (gitignored)
```
VITE_API_URL=http://localhost:8080
```

`.env` is read by Vite at dev time. In production the same variable will be
baked into the build (`npm run build`). For the Coder workspace, point it at
whichever port the backend is running on.

### `frontend_v2/.gitignore` (append to Vite default)
```
.env
.env.*.local
```

### `frontend_v2/src/App.tsx` (replace template content)
```tsx
import { Button } from "@/components/ui/button"

export default function App() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-background text-foreground">
      <div className="flex flex-col items-center gap-4">
        <h1 className="text-3xl font-semibold">School Bell — frontend_v2</h1>
        <p className="text-muted-foreground">
          Scaffold smoke test. Tailwind + shadcn working.
        </p>
        <Button onClick={() => alert("ok")}>Click me</Button>
      </div>
    </div>
  )
}
```

### `frontend_v2/src/main.tsx` (replace template content)
```tsx
import { StrictMode } from "react"
import { createRoot } from "react-dom/client"
import "./index.css"
import App from "./App"

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
```

## Verification

1. **Build sanity.** `npm run build` finishes without errors.
2. **Dev server.** `npm run dev -- --host :: --port 5173` starts. Visit the URL
   shown by Coder (or compose it manually as documented in `~/.claude/CLAUDE.md`):
   `https://5173--main--school-bell--<owner>.coder.brobots.org.ua`.
   The page shows the heading and a clickable shadcn button.
3. **Path alias.** `import { Button } from "@/components/ui/button"` resolves
   without errors in TypeScript and at runtime.
4. **Env.** Add a temporary `console.log(import.meta.env.VITE_API_URL)` to
   `App.tsx`; the console shows `http://localhost:8080`. Remove the log
   before committing.
5. **Tailwind.** The page actually renders with Tailwind utilities
   (background, spacing). If you remove the Tailwind import, the layout breaks
   — quick way to confirm it's wired up.

## Risks and edge cases
- **Tailwind v4 is new.** It does not use `tailwind.config.js` by default;
  styling is driven by CSS variables and the `@import "tailwindcss";` line.
  shadcn supports it; ignore older Tailwind-v3 guides.
- **`shadcn init` writes to `src/index.css`.** It will overwrite the contents
  shown above with its own variable block. That's fine — we just need to
  keep the `@import "tailwindcss";` line and not delete shadcn's `:root`/
  `.dark` blocks afterwards.
- **CRA-style `process.env`.** Vite uses `import.meta.env.VITE_*` instead.
  Don't reach for `process.env`.
- **Coder subdomain URL.** Vite's `--host ::` listener is required (loopback
  doesn't expose it to the outside container). Per `~/.claude/CLAUDE.md`.
- **Strict mode.** Left on. Step 7 forms will see effects firing twice in dev
  — handle accordingly.

## Done when
- `frontend_v2/` exists at repo root.
- `npm run dev` shows the smoke-test page through the Coder URL.
- `tsc --noEmit` (or `npm run build`) passes.
- `.env` exists, `.env.example` is committed, `.env` is in `.gitignore`.
- One shadcn component (`button`) is committed to `src/components/ui/`.

## Commit
```
frontend_v2: scaffold Vite + React + TS + Tailwind v4 + shadcn/ui

Bootstraps a fresh frontend at frontend_v2/. Adds Tailwind v4 via the
@tailwindcss/vite plugin, registers shadcn/ui with the default theme,
installs react-router-dom and @tanstack/react-query. Path alias @/* ->
src/*. Env config via VITE_API_URL. Smoke-test App renders a shadcn
Button.
```
