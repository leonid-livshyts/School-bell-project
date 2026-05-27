import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { toast } from "sonner"
import { Plus, Pencil, Trash2, CalendarRange, MoreHorizontal } from "lucide-react"

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
import { lessonsApi } from "@/lib/api/lessons"
import { roomsApi } from "@/lib/api/rooms"
import { ApiError } from "@/lib/api/client"
import {
  formatDateTime,
  fromDateTimeLocal,
  toDateTimeLocal,
} from "@/lib/format"
import type { Lesson } from "@/lib/types"

const schema = z.object({
  name: z.string().min(1, "Required").max(120),
  room_id: z.number().int().positive("Pick a room"),
  start: z.string().min(1, "Required"),
  end: z.string().min(1, "Required"),
})
type FormValues = z.infer<typeof schema>

export default function LessonsPage() {
  const qc = useQueryClient()
  const [open, setOpen] = useState(false)
  const [editing, setEditing] = useState<Lesson | null>(null)

  const lessons = useQuery({ queryKey: ["lessons"], queryFn: lessonsApi.list })
  const rooms = useQuery({ queryKey: ["rooms"], queryFn: roomsApi.list })
  const roomById = new Map(rooms.data?.map((r) => [r.id, r.name]) ?? [])

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { name: "", room_id: 0, start: "", end: "" },
  })

  function openCreate() {
    setEditing(null)
    form.reset({
      name: "",
      room_id: rooms.data?.[0]?.id ?? 0,
      start: "",
      end: "",
    })
    setOpen(true)
  }
  function openEdit(lesson: Lesson) {
    setEditing(lesson)
    form.reset({
      name: lesson.name,
      room_id: lesson.room_id,
      start: toDateTimeLocal(lesson.start),
      end: toDateTimeLocal(lesson.end),
    })
    setOpen(true)
  }

  const createMut = useMutation({
    mutationFn: (input: FormValues) =>
      lessonsApi.create({
        name: input.name,
        room_id: input.room_id,
        start: fromDateTimeLocal(input.start),
        end: fromDateTimeLocal(input.end),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["lessons"] })
      toast.success("Lesson scheduled")
      setOpen(false)
    },
    onError: (err: ApiError) => toast.error(err.message),
  })
  const updateMut = useMutation({
    mutationFn: (input: FormValues) =>
      lessonsApi.update(editing!.id, {
        name: input.name,
        room_id: input.room_id,
        start: fromDateTimeLocal(input.start),
        end: fromDateTimeLocal(input.end),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["lessons"] })
      toast.success("Lesson saved")
      setOpen(false)
    },
    onError: (err: ApiError) => toast.error(err.message),
  })
  const removeMut = useMutation({
    mutationFn: (id: number) => lessonsApi.remove(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["lessons"] })
      toast.success("Lesson deleted")
    },
    onError: (err: ApiError) => toast.error(err.message),
  })

  function onSubmit(values: FormValues) {
    if (new Date(values.start) >= new Date(values.end)) {
      form.setError("end", { message: "End must be after start" })
      return
    }
    if (editing) updateMut.mutate(values)
    else createMut.mutate(values)
  }

  const sorted = (lessons.data ?? []).slice().sort((a, b) =>
    a.start.localeCompare(b.start),
  )

  return (
    <div>
      <PageHeader
        title="Lessons"
        description="The bell schedule. Times are interpreted as Europe/Kyiv wall-clock by the server."
        action={
          <Button onClick={openCreate} disabled={!rooms.data?.length}>
            <Plus className="size-4" /> Add lesson
          </Button>
        }
      />

      {!rooms.data?.length && !rooms.isPending && (
        <EmptyState
          icon={CalendarRange}
          title="No rooms yet"
          description="Lessons are scheduled per room. Add a room first."
        />
      )}

      {rooms.data?.length ? (
        lessons.isPending ? (
          <div className="rounded-lg border">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="flex items-center gap-4 px-4 py-3 border-b last:border-b-0">
                <Skeleton className="h-4 w-40" />
                <Skeleton className="h-4 w-20" />
                <Skeleton className="h-4 w-32" />
                <Skeleton className="h-4 w-32 ml-auto" />
              </div>
            ))}
          </div>
        ) : sorted.length === 0 ? (
          <EmptyState
            icon={CalendarRange}
            title="Nothing scheduled"
            description="Add a lesson to see it on the board."
            action={<Button onClick={openCreate}><Plus className="size-4" /> Add lesson</Button>}
          />
        ) : (
          <div className="rounded-lg border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Room</TableHead>
                  <TableHead>Start</TableHead>
                  <TableHead>End</TableHead>
                  <TableHead className="w-16" />
                </TableRow>
              </TableHeader>
              <TableBody>
                {sorted.map((l) => (
                  <TableRow key={l.id}>
                    <TableCell className="font-medium">{l.name}</TableCell>
                    <TableCell className="text-muted-foreground">
                      {roomById.get(l.room_id) ?? l.room_id}
                    </TableCell>
                    <TableCell>{formatDateTime(l.start)}</TableCell>
                    <TableCell>{formatDateTime(l.end)}</TableCell>
                    <TableCell>
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="icon" aria-label="Actions">
                            <MoreHorizontal className="size-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem onClick={() => openEdit(l)}>
                            <Pencil className="size-4" /> Edit
                          </DropdownMenuItem>
                          <ConfirmDelete
                            title={`Delete "${l.name}"?`}
                            onConfirm={() => removeMut.mutate(l.id)}
                            trigger={
                              <DropdownMenuItem onSelect={(e) => e.preventDefault()}>
                                <Trash2 className="size-4 text-destructive" />
                                <span className="text-destructive">Delete</span>
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
        )
      ) : null}

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>{editing ? "Edit lesson" : "Add lesson"}</DialogTitle>
            <DialogDescription>
              The server stores times as Europe/Kyiv wall-clock.
            </DialogDescription>
          </DialogHeader>
          <Form {...form}>
            <form
              onSubmit={form.handleSubmit(onSubmit)}
              className="flex flex-col gap-4"
            >
              <FormField
                control={form.control}
                name="name"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Name</FormLabel>
                    <FormControl>
                      <Input autoFocus placeholder="e.g. Math" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <FormField
                control={form.control}
                name="room_id"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Room</FormLabel>
                    <Select
                      onValueChange={(v) => field.onChange(Number(v))}
                      value={field.value ? String(field.value) : undefined}
                    >
                      <FormControl>
                        <SelectTrigger className="w-full">
                          <SelectValue placeholder="Pick a room" />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        {rooms.data?.map((r) => (
                          <SelectItem key={r.id} value={String(r.id)}>
                            {r.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <div className="grid grid-cols-2 gap-4">
                <FormField
                  control={form.control}
                  name="start"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Start</FormLabel>
                      <FormControl>
                        <Input type="datetime-local" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="end"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>End</FormLabel>
                      <FormControl>
                        <Input type="datetime-local" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>
              <DialogFooter>
                <Button type="button" variant="outline" onClick={() => setOpen(false)}>
                  Cancel
                </Button>
                <Button
                  type="submit"
                  disabled={createMut.isPending || updateMut.isPending}
                >
                  {editing ? "Save" : "Create"}
                </Button>
              </DialogFooter>
            </form>
          </Form>
        </DialogContent>
      </Dialog>
    </div>
  )
}
