import { api } from "./client"
import type { VoiceMessage } from "../types"

const BASE = (import.meta.env.VITE_API_URL as string | undefined) ?? ""

export const voiceMessagesApi = {
  list: () => api<VoiceMessage[]>("/voice_messages/"),
  get: (id: number) => api<VoiceMessage>(`/voice_messages/${id}`),
  upload: (file: File, roomId?: number) => {
    const fd = new FormData()
    fd.append("file", file)
    if (roomId !== undefined) fd.append("room_id", String(roomId))
    return api<void>("/voice_messages/", { method: "POST", body: fd })
  },
  remove: (id: number) =>
    api<void>(`/voice_messages/${id}`, { method: "DELETE" }),
  downloadUrl: (id: number) => `${BASE}/voice_messages/${id}/download`,
}
