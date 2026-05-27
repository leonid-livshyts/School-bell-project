import { useState } from "react"
import { useParams, Link } from "react-router-dom"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { toast } from "sonner"
import {
  Plus,
  Trash2,
  Cpu,
  ArrowLeft,
  Eye,
  EyeOff,
  Copy,
  Sparkles,
  MoreHorizontal,
} from "lucide-react"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Skeleton } from "@/components/ui/skeleton"
import { PageHeader } from "@/components/PageHeader"
import { EmptyState } from "@/components/EmptyState"
import { ConfirmDelete } from "@/components/ConfirmDelete"
import { devicesApi } from "@/lib/api/devices"
import { roomsApi } from "@/lib/api/rooms"
import { ApiError } from "@/lib/api/client"
import { formatDateTime, toDateTimeLocal, fromDateTimeLocal } from "@/lib/format"
import { useDocumentTitle } from "@/hooks/useDocumentTitle"

const schema = z.object({
  key: z.string().min(8, "At least 8 chars"),
  version: z.string().min(1, "Required"),
  installed_date: z.string().min(1, "Required"),
})
type FormValues = z.infer<typeof schema>

function genKey() {
  const bytes = new Uint8Array(16)
  crypto.getRandomValues(bytes)
  return Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("")
}

function maskKey(key: string) {
  if (key.length <= 8) return "•".repeat(Math.max(0, key.length))
  return "•".repeat(key.length - 4) + key.slice(-4)
}

export default function DevicesByRoom() {
  const { roomId: roomIdParam } = useParams()
  const roomId = Number(roomIdParam)
  useDocumentTitle("Devices")
  const qc = useQueryClient()
  const [open, setOpen] = useState(false)
  const [revealed, setRevealed] = useState<Record<number, boolean>>({})

  const room = useQuery({
    queryKey: ["room", roomId],
    queryFn: () => roomsApi.get(roomId),
    enabled: Number.isFinite(roomId),
  })
  const devices = useQuery({
    queryKey: ["devices", roomId],
    queryFn: () => devicesApi.list(roomId),
    enabled: Number.isFinite(roomId),
  })

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      key: "",
      version: "1.0",
      installed_date: toDateTimeLocal(new Date().toISOString()),
    },
  })

  function openCreate() {
    form.reset({
      key: genKey(),
      version: "1.0",
      installed_date: toDateTimeLocal(new Date().toISOString()),
    })
    setOpen(true)
  }

  const createMut = useMutation({
    mutationFn: (input: FormValues) =>
      devicesApi.create(roomId, {
        key: input.key,
        version: input.version,
        installed_date: fromDateTimeLocal(input.installed_date),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["devices", roomId] })
      toast.success("Device registered")
      setOpen(false)
    },
    onError: (err: ApiError) => toast.error(err.message),
  })
  const removeMut = useMutation({
    mutationFn: (id: number) => devicesApi.remove(roomId, id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["devices", roomId] })
      toast.success("Device removed")
    },
    onError: (err: ApiError) => toast.error(err.message),
  })

  async function copy(text: string) {
    try {
      await navigator.clipboard.writeText(text)
      toast.success("Copied to clipboard")
    } catch {
      toast.error("Could not copy")
    }
  }

  return (
    <div>
      <Button asChild variant="ghost" size="sm" className="mb-2 -ml-2">
        <Link to="/devices">
          <ArrowLeft className="size-4" /> All rooms
        </Link>
      </Button>
      <PageHeader
        title={`Devices — ${room.data?.name ?? `Room #${roomId}`}`}
        description="Each device authenticates to /private/* using its X-API-Key."
        action={
          <Button onClick={openCreate}>
            <Plus className="size-4" /> Register device
          </Button>
        }
      />

      {devices.isPending ? (
        <div className="rounded-lg border">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="flex items-center gap-4 px-4 py-3 border-b last:border-b-0">
              <Skeleton className="h-4 w-48" />
              <Skeleton className="h-4 w-16" />
              <Skeleton className="h-4 w-32 ml-auto" />
            </div>
          ))}
        </div>
      ) : devices.data && devices.data.length === 0 ? (
        <EmptyState
          icon={Cpu}
          title="No devices in this room"
          description="Register an ESP32 by generating a key and flashing it into the firmware config."
          action={<Button onClick={openCreate}><Plus className="size-4" /> Register device</Button>}
        />
      ) : (
        <div className="rounded-lg border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-12">ID</TableHead>
                <TableHead>X-API-Key</TableHead>
                <TableHead>Version</TableHead>
                <TableHead>Installed</TableHead>
                <TableHead className="w-16" />
              </TableRow>
            </TableHeader>
            <TableBody>
              {devices.data?.map((d) => (
                <TableRow key={d.id}>
                  <TableCell className="text-muted-foreground">{d.id}</TableCell>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <code className="font-mono text-xs">
                        {revealed[d.id] ? d.key : maskKey(d.key)}
                      </code>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() =>
                          setRevealed((r) => ({ ...r, [d.id]: !r[d.id] }))
                        }
                        aria-label="Toggle reveal"
                      >
                        {revealed[d.id] ? (
                          <EyeOff className="size-3.5" />
                        ) : (
                          <Eye className="size-3.5" />
                        )}
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => copy(d.key)}
                        aria-label="Copy key"
                      >
                        <Copy className="size-3.5" />
                      </Button>
                    </div>
                  </TableCell>
                  <TableCell>{d.version}</TableCell>
                  <TableCell>{formatDateTime(d.installed_date)}</TableCell>
                  <TableCell>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="icon" aria-label="Actions">
                          <MoreHorizontal className="size-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <ConfirmDelete
                          title="Remove device?"
                          description="The ESP32 with this key will no longer be able to talk to /private/* endpoints."
                          onConfirm={() => removeMut.mutate(d.id)}
                          trigger={
                            <DropdownMenuItem onSelect={(e) => e.preventDefault()}>
                              <Trash2 className="size-4 text-destructive" />
                              <span className="text-destructive">Remove</span>
                            </DropdownMenuItem>
                          }
                        />
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Register device</DialogTitle>
            <DialogDescription>
              Copy the key into the firmware config before flashing.
            </DialogDescription>
          </DialogHeader>
          <Form {...form}>
            <form
              onSubmit={form.handleSubmit((v) => createMut.mutate(v))}
              className="flex flex-col gap-4"
            >
              <FormField
                control={form.control}
                name="key"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>X-API-Key</FormLabel>
                    <div className="flex gap-2">
                      <FormControl>
                        <Input className="font-mono text-xs" {...field} />
                      </FormControl>
                      <Button
                        type="button"
                        variant="outline"
                        onClick={() => field.onChange(genKey())}
                      >
                        <Sparkles className="size-4" /> Generate
                      </Button>
                    </div>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="version"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Firmware version</FormLabel>
                    <FormControl>
                      <Input {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="installed_date"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Installed</FormLabel>
                    <FormControl>
                      <Input type="datetime-local" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <DialogFooter>
                <Button type="button" variant="outline" onClick={() => setOpen(false)}>
                  Cancel
                </Button>
                <Button type="submit" disabled={createMut.isPending}>
                  Register
                </Button>
              </DialogFooter>
            </form>
          </Form>
        </DialogContent>
      </Dialog>
    </div>
  )
}
