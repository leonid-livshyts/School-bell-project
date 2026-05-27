import { api } from "./client"
import type { Device, DeviceInput } from "../types"

export const devicesApi = {
  list: (roomId: number) => api<Device[]>(`/${roomId}/devices/`),
  get: (roomId: number, id: number) =>
    api<Device>(`/${roomId}/devices/${id}`),
  create: (roomId: number, input: DeviceInput) =>
    api<void>(`/${roomId}/devices/`, { method: "POST", body: input }),
  update: (roomId: number, id: number, input: DeviceInput) =>
    api<void>(`/${roomId}/devices/${id}`, { method: "POST", body: input }),
  remove: (roomId: number, id: number) =>
    api<void>(`/${roomId}/devices/${id}`, { method: "DELETE" }),
}
