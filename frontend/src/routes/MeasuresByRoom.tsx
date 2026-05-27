import { useState, useMemo } from "react"
import { useParams, Link } from "react-router-dom"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import {
  Activity,
  ArrowLeft,
  Thermometer,
  Droplets,
  Volume2,
  Wind,
  Trash2,
} from "lucide-react"
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
} from "recharts"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Skeleton } from "@/components/ui/skeleton"
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart"
import { PageHeader } from "@/components/PageHeader"
import { EmptyState } from "@/components/EmptyState"
import { ConfirmDelete } from "@/components/ConfirmDelete"
import { measuresApi } from "@/lib/api/measures"
import { roomsApi } from "@/lib/api/rooms"
import { ApiError } from "@/lib/api/client"
import { formatDateTime } from "@/lib/format"
import { useDocumentTitle } from "@/hooks/useDocumentTitle"
import type { Measure } from "@/lib/types"

const RANGES = {
  hour: { label: "Last hour", ms: 60 * 60 * 1000 },
  day: { label: "Last 24h", ms: 24 * 60 * 60 * 1000 },
  week: { label: "Last week", ms: 7 * 24 * 60 * 60 * 1000 },
  all: { label: "All time", ms: Infinity },
} as const

type RangeKey = keyof typeof RANGES

interface Series {
  key: keyof Measure
  label: string
  unit: string
  color: string
  icon: typeof Thermometer
}

const SERIES: Series[] = [
  { key: "temperature", label: "Temperature", unit: "°C", color: "var(--chart-1)", icon: Thermometer },
  { key: "humidity", label: "Humidity", unit: "%", color: "var(--chart-2)", icon: Droplets },
  { key: "volume", label: "Volume", unit: "dB", color: "var(--chart-3)", icon: Volume2 },
  { key: "air_quality", label: "Air quality (CO₂)", unit: "%", color: "var(--chart-4)", icon: Wind },
]

export default function MeasuresByRoom() {
  const { roomId: roomIdParam } = useParams()
  const roomId = Number(roomIdParam)
  useDocumentTitle("Measures")
  const qc = useQueryClient()
  const [range, setRange] = useState<RangeKey>("day")

  const room = useQuery({
    queryKey: ["room", roomId],
    queryFn: () => roomsApi.get(roomId),
    enabled: Number.isFinite(roomId),
  })
  const measures = useQuery({
    queryKey: ["measures", roomId],
    queryFn: () => measuresApi.list(roomId),
    enabled: Number.isFinite(roomId),
  })

  const filtered = useMemo(() => {
    const cutoff = Date.now() - RANGES[range].ms
    return (measures.data ?? [])
      .slice()
      .sort((a, b) => a.measure_time.localeCompare(b.measure_time))
      .filter((m) => new Date(m.measure_time).getTime() >= cutoff)
  }, [measures.data, range])

  const removeMut = useMutation({
    mutationFn: (id: number) => measuresApi.remove(roomId, id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["measures", roomId] })
      toast.success("Reading deleted")
    },
    onError: (err: ApiError) => toast.error(err.message),
  })

  return (
    <div>
      <Button asChild variant="ghost" size="sm" className="mb-2 -ml-2">
        <Link to="/measures">
          <ArrowLeft className="size-4" /> All rooms
        </Link>
      </Button>
      <PageHeader
        title={`Measures — ${room.data?.name ?? `Room #${roomId}`}`}
        description="Latest sensor history from this room's ESP32."
        action={
          <Select value={range} onValueChange={(v) => setRange(v as RangeKey)}>
            <SelectTrigger className="w-36">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {Object.entries(RANGES).map(([k, v]) => (
                <SelectItem key={k} value={k}>{v.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        }
      />

      {measures.isPending ? (
        <div className="grid gap-4 md:grid-cols-2">
          {SERIES.map((s) => (
            <Skeleton key={s.key as string} className="h-64 rounded-lg" />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <EmptyState
          icon={Activity}
          title="Waiting for readings"
          description="The ESP32 in this room hasn't pushed any sensor data in the selected window."
        />
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {SERIES.map((s) => {
            const data = filtered
              .filter((m) => m[s.key] !== null && m[s.key] !== undefined)
              .map((m) => ({
                t: m.measure_time,
                v: m[s.key] as number,
              }))
            const config: ChartConfig = {
              v: { label: s.label, color: s.color },
            }
            const Icon = s.icon
            return (
              <Card key={s.key as string}>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-base">
                    <Icon className="size-4 text-muted-foreground" />
                    {s.label}
                  </CardTitle>
                  <CardDescription>{s.unit}</CardDescription>
                </CardHeader>
                <CardContent>
                  {data.length === 0 ? (
                    <p className="text-sm text-muted-foreground py-8 text-center">
                      No data in this window.
                    </p>
                  ) : (
                    <ChartContainer config={config} className="h-48 w-full">
                      <LineChart data={data} margin={{ left: 8, right: 8, top: 8 }}>
                        <CartesianGrid strokeDasharray="3 3" vertical={false} />
                        <XAxis
                          dataKey="t"
                          tickFormatter={(t) =>
                            new Date(t).toLocaleTimeString([], {
                              hour: "2-digit",
                              minute: "2-digit",
                            })
                          }
                          tickLine={false}
                          axisLine={false}
                          minTickGap={32}
                        />
                        <YAxis tickLine={false} axisLine={false} width={32} />
                        <ChartTooltip content={<ChartTooltipContent />} />
                        <Line
                          type="monotone"
                          dataKey="v"
                          stroke="var(--color-v)"
                          strokeWidth={2}
                          dot={false}
                          isAnimationActive={false}
                        />
                      </LineChart>
                    </ChartContainer>
                  )}
                </CardContent>
              </Card>
            )
          })}
        </div>
      )}

      {filtered.length > 0 && (
        <details className="mt-6 rounded-lg border">
          <summary className="cursor-pointer px-4 py-3 select-none text-sm font-medium">
            Raw readings ({filtered.length})
          </summary>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Time</TableHead>
                <TableHead>Temp</TableHead>
                <TableHead>Humidity</TableHead>
                <TableHead>Volume</TableHead>
                <TableHead>Air</TableHead>
                <TableHead className="w-16" />
              </TableRow>
            </TableHeader>
            <TableBody>
              {filtered.slice().reverse().map((m) => (
                <TableRow key={m.id}>
                  <TableCell>{formatDateTime(m.measure_time)}</TableCell>
                  <TableCell>{m.temperature ?? "—"}</TableCell>
                  <TableCell>{m.humidity ?? "—"}</TableCell>
                  <TableCell>{m.volume ?? "—"}</TableCell>
                  <TableCell>{m.air_quality ?? "—"}</TableCell>
                  <TableCell>
                    <ConfirmDelete
                      title="Delete reading?"
                      onConfirm={() => removeMut.mutate(m.id)}
                      trigger={
                        <Button variant="ghost" size="icon" aria-label="Delete">
                          <Trash2 className="size-3.5 text-destructive" />
                        </Button>
                      }
                    />
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </details>
      )}
    </div>
  )
}
