import { api } from "./client"
import type { Alarm } from "../types"

export const alarmsApi = {
  list: () => api<Alarm[]>("/alarms/"),
  set: (roomId: number, isActive: boolean) =>
    api<{ room_id: number; is_active: boolean }>(`/alarms/${roomId}`, {
      method: "POST",
      body: { is_active: isActive },
    }),
}
