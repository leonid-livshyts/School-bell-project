import { Navigate, Outlet, useLocation } from "react-router-dom"
import { useSession } from "@/lib/auth/use-session"

export function ProtectedRoute() {
  const session = useSession()
  const location = useLocation()
  if (!session) {
    return <Navigate to="/login" replace state={{ from: location }} />
  }
  return <Outlet />
}
