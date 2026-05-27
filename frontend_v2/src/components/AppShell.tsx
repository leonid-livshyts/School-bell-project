import { NavLink, Outlet } from "react-router-dom"
import {
  LayoutDashboard,
  Home as HomeIcon,
  CalendarRange,
  Cpu,
  Activity,
  Music,
  Mic,
  AlarmClock,
  LogOut,
} from "lucide-react"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Button } from "@/components/ui/button"
import { Logo } from "@/components/Logo"
import { useSession } from "@/lib/auth/use-session"
import { logout } from "@/lib/api/auth"
import { cn } from "@/lib/utils"
import type { ComponentType } from "react"

interface NavItem {
  to: string
  label: string
  icon: ComponentType<{ className?: string }>
  end?: boolean
}

const NAV: NavItem[] = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/rooms", label: "Rooms", icon: HomeIcon },
  { to: "/lessons", label: "Lessons", icon: CalendarRange },
  { to: "/devices", label: "Devices", icon: Cpu },
  { to: "/measures", label: "Measures", icon: Activity },
  { to: "/ringtones", label: "Ringtones", icon: Music },
  { to: "/voice-messages", label: "Voice messages", icon: Mic },
  { to: "/alarms", label: "Alarms", icon: AlarmClock },
]

export function AppShell() {
  const session = useSession()
  return (
    <div className="min-h-screen grid grid-cols-[16rem_1fr] bg-background text-foreground">
      <aside className="border-r bg-sidebar text-sidebar-foreground flex flex-col">
        <div className="px-4 py-4">
          <Logo />
        </div>
        <nav className="flex-1 flex flex-col gap-0.5 px-2 text-sm">
          {NAV.map((item) => {
            const Icon = item.icon
            return (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                className={({ isActive }) =>
                  cn(
                    "flex items-center gap-2 rounded-md px-3 py-2 transition-colors",
                    "hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
                    isActive &&
                      "bg-sidebar-accent text-sidebar-accent-foreground font-medium",
                  )
                }
              >
                <Icon className="size-4" />
                {item.label}
              </NavLink>
            )
          })}
        </nav>
      </aside>
      <div className="flex flex-col min-w-0">
        <header className="h-14 border-b flex items-center justify-end gap-2 px-4">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" className="font-normal">
                {session?.username}
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuLabel>Signed in as {session?.username}</DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={() => logout()}>
                <LogOut className="size-4" />
                Sign out
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </header>
        <main className="p-6 flex-1">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
