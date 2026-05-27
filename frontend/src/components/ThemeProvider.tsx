import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react"

type Theme = "light" | "dark" | "system"
const STORAGE_KEY = "school_bell_theme"

interface ThemeContextValue {
  theme: Theme
  setTheme: (t: Theme) => void
  resolved: "light" | "dark"
}

const ThemeContext = createContext<ThemeContextValue | null>(null)

function readStored(): Theme {
  const t = localStorage.getItem(STORAGE_KEY)
  return t === "light" || t === "dark" || t === "system" ? t : "system"
}

function systemPrefersDark() {
  return window.matchMedia("(prefers-color-scheme: dark)").matches
}

function apply(theme: Theme) {
  const root = document.documentElement
  const dark = theme === "dark" || (theme === "system" && systemPrefersDark())
  root.classList.toggle("dark", dark)
  return dark ? "dark" : "light"
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setThemeState] = useState<Theme>(() => readStored())
  const [resolved, setResolved] = useState<"light" | "dark">(() => apply(readStored()))

  useEffect(() => {
    setResolved(apply(theme))
    localStorage.setItem(STORAGE_KEY, theme)
  }, [theme])

  // Follow OS changes only when on "system".
  useEffect(() => {
    if (theme !== "system") return
    const mq = window.matchMedia("(prefers-color-scheme: dark)")
    const onChange = () => setResolved(apply("system"))
    mq.addEventListener("change", onChange)
    return () => mq.removeEventListener("change", onChange)
  }, [theme])

  const value = useMemo<ThemeContextValue>(
    () => ({ theme, setTheme: setThemeState, resolved }),
    [theme, resolved],
  )

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
}

export function useTheme() {
  const ctx = useContext(ThemeContext)
  if (!ctx) throw new Error("useTheme used outside ThemeProvider")
  return ctx
}
