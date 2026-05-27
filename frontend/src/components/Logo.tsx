import { Bell } from "lucide-react"
import { cn } from "@/lib/utils"

export function Logo({ className }: { className?: string }) {
  return (
    <div className={cn("flex items-center gap-2", className)}>
      <div className="grid place-items-center size-8 rounded-md bg-primary text-primary-foreground">
        <Bell className="size-4" />
      </div>
      <span className="font-semibold tracking-tight">School Bell</span>
    </div>
  )
}
