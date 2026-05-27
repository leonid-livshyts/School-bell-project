import { Link } from "react-router-dom"
import { useQuery, useQueries } from "@tanstack/react-query"
import { Cpu, ChevronRight } from "lucide-react"

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { Badge } from "@/components/ui/badge"
import { PageHeader } from "@/components/PageHeader"
import { EmptyState } from "@/components/EmptyState"
import { roomsApi } from "@/lib/api/rooms"
import { devicesApi } from "@/lib/api/devices"

export default function DevicesIndex() {
  const rooms = useQuery({ queryKey: ["rooms"], queryFn: roomsApi.list })
  const roomList = rooms.data ?? []

  const counts = useQueries({
    queries: roomList.map((r) => ({
      queryKey: ["devices", r.id],
      queryFn: () => devicesApi.list(r.id),
      staleTime: 60_000,
    })),
  })

  return (
    <div>
      <PageHeader
        title="Devices"
        description="ESP32 bell controllers, grouped by room."
      />

      {rooms.isPending ? (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-24 rounded-lg" />
          ))}
        </div>
      ) : roomList.length === 0 ? (
        <EmptyState
          icon={Cpu}
          title="No rooms yet"
          description="Devices are registered per room. Add a room first."
        />
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {roomList.map((r, i) => {
            const c = counts[i]
            const count = c?.data?.length ?? 0
            return (
              <Link key={r.id} to={`/rooms/${r.id}/devices`}>
                <Card className="hover:bg-accent/40 transition-colors">
                  <CardHeader className="flex flex-row items-start justify-between gap-2">
                    <div>
                      <CardTitle className="text-base">{r.name}</CardTitle>
                      <CardDescription>Room #{r.id}</CardDescription>
                    </div>
                    <ChevronRight className="size-4 text-muted-foreground" />
                  </CardHeader>
                  <CardContent>
                    {c?.isPending ? (
                      <Skeleton className="h-5 w-20" />
                    ) : (
                      <Badge variant="secondary">
                        {count} device{count === 1 ? "" : "s"}
                      </Badge>
                    )}
                  </CardContent>
                </Card>
              </Link>
            )
          })}
        </div>
      )}
    </div>
  )
}
