import { api } from "./client"
import type { Ringtone } from "../types"

const BASE = (import.meta.env.VITE_API_URL as string | undefined) ?? ""

export const ringtonesApi = {
  list: () => api<Ringtone[]>("/ringtones/"),
  get: (id: number) => api<Ringtone>(`/ringtones/${id}`),
  upload: (file: File, roomId?: number) => {
    const fd = new FormData()
    fd.append("file", file)
    if (roomId !== undefined) fd.append("room_id", String(roomId))
    return api<void>("/ringtones/", { method: "POST", body: fd })
  },
  remove: (id: number) =>
    api<void>(`/ringtones/${id}`, { method: "DELETE" }),
  downloadUrl: (id: number) => `${BASE}/ringtones/${id}/download`,
}
