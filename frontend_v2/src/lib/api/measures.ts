import { api } from "./client"
import type { Measure, MeasureInput } from "../types"

export const measuresApi = {
  list: (roomId: number) => api<Measure[]>(`/${roomId}/measures/`),
  get: (roomId: number, id: number) =>
    api<Measure>(`/${roomId}/measures/${id}`),
  create: (roomId: number, input: MeasureInput) =>
    api<void>(`/${roomId}/measures/`, { method: "POST", body: input }),
  update: (roomId: number, id: number, input: MeasureInput) =>
    api<void>(`/${roomId}/measures/${id}`, { method: "POST", body: input }),
  remove: (roomId: number, id: number) =>
    api<void>(`/${roomId}/measures/${id}`, { method: "DELETE" }),
}
