import { api } from "./client"
import { setSession } from "../auth/session"
import type { LoginResponse, RegisterInput } from "../types"

export async function login(username: string, password: string) {
  const body = new URLSearchParams()
  body.set("username", username)
  body.set("password", password)
  const res = await api<LoginResponse>("/login", { method: "POST", body })
  setSession({ token: res.access_token, username })
  return res
}

export async function register(input: RegisterInput) {
  return api<void>("/register", { method: "POST", body: input })
}

export function logout() {
  setSession(null)
}
