import { api } from "./client"
import type { Room, RoomInput } from "../types"

export const roomsApi = {
  list: () => api<Room[]>("/rooms/"),
  get: (id: number) => api<Room>(`/rooms/${id}`),
  create: (input: RoomInput) =>
    api<void>("/rooms/", { method: "POST", body: input }),
  update: (id: number, input: RoomInput) =>
    api<void>(`/rooms/${id}`, { method: "POST", body: input }),
  remove: (id: number) =>
    api<void>(`/rooms/${id}`, { method: "DELETE" }),
}
