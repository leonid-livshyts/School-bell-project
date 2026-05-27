import { useState } from "react"
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
  Menu,
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
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet"
import { Logo } from "@/components/Logo"
import { ThemeToggle } from "@/components/ThemeToggle"
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

function Nav({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <nav className="flex flex-col gap-0.5 px-2 text-sm">
      {NAV.map((item) => {
        const Icon = item.icon
        return (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            onClick={onNavigate}
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
  )
}

export function AppShell() {
  const session = useSession()
  const [sheetOpen, setSheetOpen] = useState(false)
  return (
    <div className="min-h-screen md:grid md:grid-cols-[16rem_1fr] bg-background text-foreground">
      {/* Desktop sidebar */}
      <aside className="hidden md:flex border-r bg-sidebar text-sidebar-foreground flex-col">
        <div className="px-4 py-4">
          <Logo />
        </div>
        <Nav />
      </aside>

      <div className="flex flex-col min-w-0">
        <header className="h-14 border-b flex items-center gap-2 px-4">
          {/* Mobile menu */}
          <Sheet open={sheetOpen} onOpenChange={setSheetOpen}>
            <SheetTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className="md:hidden"
                aria-label="Open menu"
              >
                <Menu className="size-4" />
              </Button>
            </SheetTrigger>
            <SheetContent side="left" className="w-64 p-0">
              <SheetHeader className="px-4 py-4 border-b">
                <SheetTitle className="text-left">
                  <Logo />
                </SheetTitle>
              </SheetHeader>
              <div className="py-2">
                <Nav onNavigate={() => setSheetOpen(false)} />
              </div>
            </SheetContent>
          </Sheet>

          <div className="md:hidden">
            <Logo />
          </div>

          <div className="ml-auto flex items-center gap-1">
            <ThemeToggle />
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" className="font-normal">
                  {session?.username}
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuLabel>
                  Signed in as {session?.username}
                </DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={() => logout()}>
                  <LogOut className="size-4" />
                  Sign out
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </header>
        <main className="p-4 md:p-6 flex-1">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
