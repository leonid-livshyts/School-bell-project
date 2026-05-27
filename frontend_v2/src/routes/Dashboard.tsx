import { Link } from "react-router-dom"
import { useQuery } from "@tanstack/react-query"
import {
  Home as HomeIcon,
  CalendarRange,
  AlarmClock,
  Music,
  Mic,
  ArrowRight,
} from "lucide-react"

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { Badge } from "@/components/ui/badge"
import { PageHeader } from "@/components/PageHeader"
import { roomsApi } from "@/lib/api/rooms"
import { lessonsApi } from "@/lib/api/lessons"
import { alarmsApi } from "@/lib/api/alarms"
import { ringtonesApi } from "@/lib/api/ringtones"
import { voiceMessagesApi } from "@/lib/api/voice_messages"
import { useSession } from "@/lib/auth/use-session"
import { formatDateTime } from "@/lib/format"

function StatCard({
  title,
  to,
  icon: Icon,
  loading,
  primary,
  hint,
  badge,
}: {
  title: string
  to: string
  icon: typeof HomeIcon
  loading: boolean
  primary: string | number
  hint?: string
  badge?: string
}) {
  return (
    <Link to={to}>
      <Card className="hover:bg-accent/40 transition-colors h-full">
        <CardHeader className="flex flex-row items-start justify-between gap-2">
          <div className="space-y-1">
            <CardDescription className="flex items-center gap-2 uppercase tracking-wider text-xs">
              <Icon className="size-3.5" />
              {title}
            </CardDescription>
            {loading ? (
              <Skeleton className="h-7 w-16" />
            ) : (
              <CardTitle className="text-3xl">{primary}</CardTitle>
            )}
          </div>
          <ArrowRight className="size-4 text-muted-foreground" />
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground flex items-center gap-2">
          {hint && <span>{hint}</span>}
          {badge && <Badge variant="secondary">{badge}</Badge>}
        </CardContent>
      </Card>
    </Link>
  )
}

function isToday(iso: string) {
  const d = new Date(iso)
  const now = new Date()
  return (
    d.getFullYear() === now.getFullYear() &&
    d.getMonth() === now.getMonth() &&
    d.getDate() === now.getDate()
  )
}

export default function Dashboard() {
  const session = useSession()
  const rooms = useQuery({ queryKey: ["rooms"], queryFn: roomsApi.list })
  const lessons = useQuery({ queryKey: ["lessons"], queryFn: lessonsApi.list })
  const alarms = useQuery({ queryKey: ["alarms"], queryFn: alarmsApi.list })
  const ringtones = useQuery({ queryKey: ["ringtones"], queryFn: ringtonesApi.list })
  const voiceMessages = useQuery({
    queryKey: ["voice_messages"],
    queryFn: voiceMessagesApi.list,
  })

  const today = (lessons.data ?? [])
    .filter((l) => isToday(l.start))
    .sort((a, b) => a.start.localeCompare(b.start))
  const nextLesson = today.find((l) => new Date(l.start) >= new Date()) ?? today[0]
  const activeAlarms = (alarms.data ?? []).filter((a) => a.is_active).length

  return (
    <div>
      <PageHeader
        title={`Welcome${session ? `, ${session.username}` : ""}`}
        description="At-a-glance status across the school bell system."
      />

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        <StatCard
          title="Rooms"
          to="/rooms"
          icon={HomeIcon}
          loading={rooms.isPending}
          primary={rooms.data?.length ?? 0}
          hint="Across the school"
        />
        <StatCard
          title="Lessons today"
          to="/lessons"
          icon={CalendarRange}
          loading={lessons.isPending}
          primary={today.length}
          hint={
            nextLesson
              ? `Next: ${nextLesson.name} · ${formatDateTime(nextLesson.start)}`
              : "Nothing scheduled"
          }
        />
        <StatCard
          title="Active alarms"
          to="/alarms"
          icon={AlarmClock}
          loading={alarms.isPending}
          primary={activeAlarms}
          hint={activeAlarms ? "Rooms currently alarming" : "All quiet"}
          badge={activeAlarms ? "ACTIVE" : undefined}
        />
        <StatCard
          title="Ringtones"
          to="/ringtones"
          icon={Music}
          loading={ringtones.isPending}
          primary={ringtones.data?.length ?? 0}
          hint="In the library"
        />
        <StatCard
          title="Voice messages"
          to="/voice-messages"
          icon={Mic}
          loading={voiceMessages.isPending}
          primary={voiceMessages.data?.length ?? 0}
          hint="In the library"
        />
      </div>
    </div>
  )
}
