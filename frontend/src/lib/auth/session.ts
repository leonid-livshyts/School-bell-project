// Canonical auth state. Token + display username live together so the
// topbar has something to show -- the backend has no /me endpoint.

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
  try {
    return JSON.parse(raw) as Session
  } catch {
    return null
  }
}

let cache = read()

export function getSession() {
  return cache
}

export function setSession(s: Session | null) {
  cache = s
  if (s) {
    localStorage.setItem(KEY, JSON.stringify(s))
  } else {
    localStorage.removeItem(KEY)
  }
  for (const l of listeners) l(s)
}

export function subscribe(l: Listener) {
  listeners.add(l)
  return () => {
    listeners.delete(l)
  }
}
