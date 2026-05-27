import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import { AlarmClock, OctagonAlert } from "lucide-react"

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Switch } from "@/components/ui/switch"
import { Skeleton } from "@/components/ui/skeleton"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { PageHeader } from "@/components/PageHeader"
import { EmptyState } from "@/components/EmptyState"
import { ConfirmDelete } from "@/components/ConfirmDelete"
import { alarmsApi } from "@/lib/api/alarms"
import { roomsApi } from "@/lib/api/rooms"
import { ApiError } from "@/lib/api/client"
import { formatRelative } from "@/lib/format"
import { cn } from "@/lib/utils"

export default function AlarmsPage() {
  const qc = useQueryClient()
  const rooms = useQuery({ queryKey: ["rooms"], queryFn: roomsApi.list })
  const alarms = useQuery({ queryKey: ["alarms"], queryFn: alarmsApi.list })

  const byRoom = new Map((alarms.data ?? []).map((a) => [a.room_id, a]))

  const setMut = useMutation({
    mutationFn: ({ roomId, on }: { roomId: number; on: boolean }) =>
      alarmsApi.set(roomId, on),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["alarms"] })
    },
    onError: (err: ApiError) => toast.error(err.message),
  })

  const activeRooms =
    rooms.data?.filter((r) => byRoom.get(r.id)?.is_active) ?? []

  async function stopAll() {
    try {
      await Promise.all(activeRooms.map((r) => alarmsApi.set(r.id, false)))
      qc.invalidateQueries({ queryKey: ["alarms"] })
      toast.success("All alarms stopped")
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : "Could not stop all"
      toast.error(msg)
    }
  }

  const loading = rooms.isPending || alarms.isPending

  return (
    <div>
      <PageHeader
        title="Alarms"
        description="Toggle a room's alarm. Each ESP32 polls /private/alarm and reacts on the next tick."
        action={
          activeRooms.length > 0 ? (
            <ConfirmDelete
              title={`Stop ${activeRooms.length} active alarm(s)?`}
              description="All alarming rooms will be quieted on their next poll."
              confirmLabel="Stop all"
              onConfirm={stopAll}
              trigger={
                <Button variant="destructive">
                  <OctagonAlert className="size-4" /> Stop all
                </Button>
              }
            />
          ) : undefined
        }
      />

      {loading ? (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-32 rounded-lg" />
          ))}
        </div>
      ) : !rooms.data?.length ? (
        <EmptyState
          icon={AlarmClock}
          title="No rooms yet"
          description="Add a room first to set its alarm."
        />
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {rooms.data.map((r) => {
            const a = byRoom.get(r.id)
            const isActive = a?.is_active ?? false
            return (
              <Card
                key={r.id}
                className={cn(
                  "transition-colors",
                  isActive && "border-destructive bg-destructive/5",
                )}
              >
                <CardHeader className="flex flex-row items-start justify-between gap-2">
                  <div>
                    <CardTitle className="text-base flex items-center gap-2">
                      {r.name}
                      {isActive && (
                        <Badge variant="destructive" className="font-normal">
                          ACTIVE
                        </Badge>
                      )}
                    </CardTitle>
                    <CardDescription>
                      {a?.updated_at
                        ? `Last changed ${formatRelative(a.updated_at)}`
                        : "Never changed"}
                    </CardDescription>
                  </div>
                  <Switch
                    checked={isActive}
                    disabled={setMut.isPending}
                    onCheckedChange={(on) =>
                      setMut.mutate({ roomId: r.id, on })
                    }
                    aria-label={`Toggle alarm for ${r.name}`}
                  />
                </CardHeader>
                <CardContent className="text-sm text-muted-foreground">
                  Room #{r.id}
                </CardContent>
              </Card>
            )
          })}
        </div>
      )}
    </div>
  )
}
