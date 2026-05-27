import { api } from "./client"
import type { Lesson, LessonInput } from "../types"

export const lessonsApi = {
  list: () => api<Lesson[]>("/lessons/"),
  get: (id: number) => api<Lesson>(`/lessons/${id}`),
  create: (input: LessonInput) =>
    api<void>("/lessons/", { method: "POST", body: input }),
  update: (id: number, input: LessonInput) =>
    api<void>(`/lessons/${id}`, { method: "POST", body: input }),
  remove: (id: number) =>
    api<void>(`/lessons/${id}`, { method: "DELETE" }),
}
