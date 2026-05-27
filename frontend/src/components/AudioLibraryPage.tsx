import { Fragment, useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import { Upload, Trash2, Download, Play, Music, MoreHorizontal } from "lucide-react"

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
import { Label } from "@/components/ui/label"
import { PageHeader } from "@/components/PageHeader"
import { EmptyState } from "@/components/EmptyState"
import { ConfirmDelete } from "@/components/ConfirmDelete"
import { roomsApi } from "@/lib/api/rooms"
import { ApiError } from "@/lib/api/client"
import { formatDateTime } from "@/lib/format"

interface AudioItem {
  id: number
  filename: string
  room_id: number | null
  created_at?: string
}

export interface AudioLibraryApi {
  list: () => Promise<AudioItem[]>
  upload: (file: File, roomId?: number) => Promise<void>
  remove: (id: number) => Promise<void>
  downloadUrl: (id: number) => string
}

export function AudioLibraryPage({
  title,
  description,
  api,
  queryKey,
  emptyHint,
}: {
  title: string
  description: string
  api: AudioLibraryApi
  queryKey: readonly unknown[]
  emptyHint: string
}) {
  const qc = useQueryClient()
  const [open, setOpen] = useState(false)
  const [playing, setPlaying] = useState<number | null>(null)
  const [file, setFile] = useState<File | null>(null)
  const [roomId, setRoomId] = useState<string>("all")

  const items = useQuery({ queryKey, queryFn: api.list })
  const rooms = useQuery({ queryKey: ["rooms"], queryFn: roomsApi.list })
  const roomById = new Map(rooms.data?.map((r) => [r.id, r.name]) ?? [])

  const uploadMut = useMutation({
    mutationFn: () => {
      if (!file) throw new ApiError(400, "Pick a file first")
      return api.upload(file, roomId === "all" ? undefined : Number(roomId))
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey })
      toast.success("Uploaded")
      setOpen(false)
      setFile(null)
      setRoomId("all")
    },
    onError: (err: ApiError) => toast.error(err.message),
  })
  const removeMut = useMutation({
    mutationFn: (id: number) => api.remove(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey })
      toast.success("Deleted")
    },
    onError: (err: ApiError) => toast.error(err.message),
  })

  return (
    <div>
      <PageHeader
        title={title}
        description={description}
        action={
          <Button onClick={() => setOpen(true)}>
            <Upload className="size-4" /> Upload
          </Button>
        }
      />

      {items.isPending ? (
        <div className="rounded-lg border">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="flex items-center gap-4 px-4 py-3 border-b last:border-b-0">
              <Skeleton className="h-4 w-48" />
              <Skeleton className="h-4 w-20 ml-auto" />
            </div>
          ))}
        </div>
      ) : items.data && items.data.length === 0 ? (
        <EmptyState
          icon={Music}
          title="Library is empty"
          description={emptyHint}
          action={<Button onClick={() => setOpen(true)}><Upload className="size-4" /> Upload</Button>}
        />
      ) : (
        <div className="rounded-lg border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Filename</TableHead>
                <TableHead>Room</TableHead>
                <TableHead>Created</TableHead>
                <TableHead className="w-12" />
              </TableRow>
            </TableHeader>
            <TableBody>
              {items.data?.map((it) => (
                <Fragment key={it.id}>
                  <TableRow>
                    <TableCell className="font-medium">
                      <button
                        type="button"
                        className="flex items-center gap-2 hover:underline"
                        onClick={() =>
                          setPlaying((p) => (p === it.id ? null : it.id))
                        }
                      >
                        <Play className="size-3.5" />
                        {it.filename}
                      </button>
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {it.room_id === null
                        ? "All rooms"
                        : roomById.get(it.room_id) ?? `#${it.room_id}`}
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {formatDateTime(it.created_at)}
                    </TableCell>
                    <TableCell>
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="icon" aria-label="Actions">
                            <MoreHorizontal className="size-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem asChild>
                            <a href={api.downloadUrl(it.id)} download>
                              <Download className="size-4" /> Download
                            </a>
                          </DropdownMenuItem>
                          <ConfirmDelete
                            title={`Delete "${it.filename}"?`}
                            onConfirm={() => removeMut.mutate(it.id)}
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
                  {playing === it.id && (
                    <TableRow>
                      <TableCell colSpan={4} className="bg-muted/40">
                        <audio
                          controls
                          autoPlay
                          src={api.downloadUrl(it.id)}
                          className="w-full"
                        />
                      </TableCell>
                    </TableRow>
                  )}
                </Fragment>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Upload audio</DialogTitle>
            <DialogDescription>MP3 or WAV.</DialogDescription>
          </DialogHeader>
          <div className="flex flex-col gap-4">
            <div className="space-y-2">
              <Label htmlFor="audio-upload">File</Label>
              <Input
                id="audio-upload"
                type="file"
                accept="audio/mpeg,audio/wav,audio/mp3"
                onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="audio-room">Room</Label>
              <Select value={roomId} onValueChange={setRoomId}>
                <SelectTrigger id="audio-room" className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All rooms</SelectItem>
                  {rooms.data?.map((r) => (
                    <SelectItem key={r.id} value={String(r.id)}>{r.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => setOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={() => uploadMut.mutate()}
              disabled={!file || uploadMut.isPending}
            >
              {uploadMut.isPending ? "Uploading..." : "Upload"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
