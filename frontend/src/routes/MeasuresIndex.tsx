import { Link } from "react-router-dom"
import { useQuery, useQueries } from "@tanstack/react-query"
import { Activity, ChevronRight } from "lucide-react"

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { PageHeader } from "@/components/PageHeader"
import { EmptyState } from "@/components/EmptyState"
import { roomsApi } from "@/lib/api/rooms"
import { measuresApi } from "@/lib/api/measures"
import { formatRelative } from "@/lib/format"
import { useDocumentTitle } from "@/hooks/useDocumentTitle"

export default function MeasuresIndex() {
  useDocumentTitle("Measures")
  const rooms = useQuery({ queryKey: ["rooms"], queryFn: roomsApi.list })
  const roomList = rooms.data ?? []

  const measures = useQueries({
    queries: roomList.map((r) => ({
      queryKey: ["measures", r.id],
      queryFn: () => measuresApi.list(r.id),
      staleTime: 30_000,
    })),
  })

  return (
    <div>
      <PageHeader
        title="Measures"
        description="Sensor data per room. ESP32 devices push readings via /private/sensors."
      />

      {rooms.isPending ? (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-28 rounded-lg" />
          ))}
        </div>
      ) : roomList.length === 0 ? (
        <EmptyState
          icon={Activity}
          title="No rooms yet"
          description="Measures are stored per room. Add a room first."
        />
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {roomList.map((r, i) => {
            const data = measures[i]?.data ?? []
            const latest = data.length ? data[data.length - 1] : null
            return (
              <Link key={r.id} to={`/rooms/${r.id}/measures`}>
                <Card className="hover:bg-accent/40 transition-colors">
                  <CardHeader className="flex flex-row items-start justify-between gap-2">
                    <div>
                      <CardTitle className="text-base">{r.name}</CardTitle>
                      <CardDescription>Room #{r.id}</CardDescription>
                    </div>
                    <ChevronRight className="size-4 text-muted-foreground" />
                  </CardHeader>
                  <CardContent className="text-sm text-muted-foreground">
                    {measures[i]?.isPending ? (
                      <Skeleton className="h-4 w-32" />
                    ) : latest ? (
                      <span>
                        Last reading {formatRelative(latest.measure_time)} ·{" "}
                        {data.length} total
                      </span>
                    ) : (
                      <span>No data yet</span>
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
