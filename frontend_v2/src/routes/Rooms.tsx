import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { toast } from "sonner"
import { Plus, Pencil, Trash2, Home as HomeIcon, MoreHorizontal } from "lucide-react"

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
import { roomsApi } from "@/lib/api/rooms"
import { ApiError } from "@/lib/api/client"
import { formatDateTime } from "@/lib/format"
import type { Room } from "@/lib/types"

const schema = z.object({
  name: z.string().min(1, "Required").max(64, "Too long"),
})
type FormValues = z.infer<typeof schema>

export default function RoomsPage() {
  const qc = useQueryClient()
  const [open, setOpen] = useState(false)
  const [editing, setEditing] = useState<Room | null>(null)

  const rooms = useQuery({ queryKey: ["rooms"], queryFn: roomsApi.list })

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { name: "" },
  })

  function openCreate() {
    setEditing(null)
    form.reset({ name: "" })
    setOpen(true)
  }
  function openEdit(room: Room) {
    setEditing(room)
    form.reset({ name: room.name })
    setOpen(true)
  }

  const createMut = useMutation({
    mutationFn: (input: FormValues) => roomsApi.create(input),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["rooms"] })
      toast.success("Room created")
      setOpen(false)
    },
    onError: (err: ApiError) => toast.error(err.message),
  })
  const updateMut = useMutation({
    mutationFn: (input: FormValues) =>
      roomsApi.update(editing!.id, input),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["rooms"] })
      toast.success("Room saved")
      setOpen(false)
    },
    onError: (err: ApiError) => toast.error(err.message),
  })
  const removeMut = useMutation({
    mutationFn: (id: number) => roomsApi.remove(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["rooms"] })
      toast.success("Room deleted")
    },
    onError: (err: ApiError) => toast.error(err.message),
  })

  function onSubmit(values: FormValues) {
    if (editing) updateMut.mutate(values)
    else createMut.mutate(values)
  }

  return (
    <div>
      <PageHeader
        title="Rooms"
        description="Physical rooms in the school. Lessons, devices, and measures are scoped per room."
        action={
          <Button onClick={openCreate}>
            <Plus className="size-4" /> Add room
          </Button>
        }
      />

      {rooms.isPending ? (
        <div className="rounded-lg border">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="flex items-center gap-4 px-4 py-3 border-b last:border-b-0">
              <Skeleton className="h-4 w-8" />
              <Skeleton className="h-4 w-40" />
              <Skeleton className="h-4 w-32 ml-auto" />
            </div>
          ))}
        </div>
      ) : rooms.data && rooms.data.length === 0 ? (
        <EmptyState
          icon={HomeIcon}
          title="No rooms yet"
          description="Create the first room to start scheduling lessons and registering devices."
          action={<Button onClick={openCreate}><Plus className="size-4" /> Add room</Button>}
        />
      ) : (
        <div className="rounded-lg border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-16">ID</TableHead>
                <TableHead>Name</TableHead>
                <TableHead>Created</TableHead>
                <TableHead>Updated</TableHead>
                <TableHead className="w-16" />
              </TableRow>
            </TableHeader>
            <TableBody>
              {rooms.data?.map((r) => (
                <TableRow key={r.id}>
                  <TableCell className="text-muted-foreground">{r.id}</TableCell>
                  <TableCell className="font-medium">{r.name}</TableCell>
                  <TableCell className="text-muted-foreground">
                    {formatDateTime(r.created_at)}
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {formatDateTime(r.updated_at)}
                  </TableCell>
                  <TableCell>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="icon" aria-label="Actions">
                          <MoreHorizontal className="size-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem onClick={() => openEdit(r)}>
                          <Pencil className="size-4" /> Rename
                        </DropdownMenuItem>
                        <ConfirmDelete
                          title={`Delete room "${r.name}"?`}
                          description="This will fail if the room still has lessons, devices, or other linked records."
                          onConfirm={() => removeMut.mutate(r.id)}
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
      )}

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{editing ? "Rename room" : "Add room"}</DialogTitle>
            <DialogDescription>
              {editing ? "Change the room's display name." : "Add a new room."}
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
                      <Input autoFocus placeholder="e.g. 201_1" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
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
