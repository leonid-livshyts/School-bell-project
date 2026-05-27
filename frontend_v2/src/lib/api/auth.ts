import { api, tokenStore } from "./client"
import type { LoginResponse, RegisterInput } from "../types"

export async function login(username: string, password: string) {
  const body = new URLSearchParams()
  body.set("username", username)
  body.set("password", password)
  const res = await api<LoginResponse>("/login", { method: "POST", body })
  tokenStore.set(res.access_token)
  return res
}

export async function register(input: RegisterInput) {
  return api<void>("/register", { method: "POST", body: input })
}

export function logout() {
  tokenStore.clear()
}
