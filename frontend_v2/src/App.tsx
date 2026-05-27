import { lazy, Suspense } from "react"
import { createBrowserRouter, RouterProvider } from "react-router-dom"
import { Toaster } from "@/components/ui/sonner"
import { ProtectedRoute } from "@/components/ProtectedRoute"
import { AppShell } from "@/components/AppShell"
import { ErrorBoundary } from "@/components/ErrorBoundary"
import { ThemeProvider } from "@/components/ThemeProvider"
import { Skeleton } from "@/components/ui/skeleton"
import Login from "@/routes/Login"
import Register from "@/routes/Register"
import NotFound from "@/routes/NotFound"

// Code-split heavy routes (Measures pulls in recharts; Lessons / Dashboard /
// pages pull in react-hook-form / zod) so the initial login screen is tiny.
const Dashboard = lazy(() => import("@/routes/Dashboard"))
const RoomsPage = lazy(() => import("@/routes/Rooms"))
const LessonsPage = lazy(() => import("@/routes/Lessons"))
const DevicesIndex = lazy(() => import("@/routes/DevicesIndex"))
const DevicesByRoom = lazy(() => import("@/routes/DevicesByRoom"))
const MeasuresIndex = lazy(() => import("@/routes/MeasuresIndex"))
const MeasuresByRoom = lazy(() => import("@/routes/MeasuresByRoom"))
const RingtonesPage = lazy(() => import("@/routes/Ringtones"))
const VoiceMessagesPage = lazy(() => import("@/routes/VoiceMessages"))
const AlarmsPage = lazy(() => import("@/routes/Alarms"))

function Lazy({ children }: { children: React.ReactNode }) {
  return (
    <Suspense
      fallback={
        <div className="flex flex-col gap-3">
          <Skeleton className="h-8 w-64" />
          <Skeleton className="h-4 w-96" />
          <div className="grid gap-3 mt-6 sm:grid-cols-2 lg:grid-cols-3">
            <Skeleton className="h-32 rounded-lg" />
            <Skeleton className="h-32 rounded-lg" />
            <Skeleton className="h-32 rounded-lg" />
          </div>
        </div>
      }
    >
      {children}
    </Suspense>
  )
}

const router = createBrowserRouter([
  { path: "/login", element: <Login /> },
  { path: "/register", element: <Register /> },
  {
    element: <ProtectedRoute />,
    children: [
      {
        element: <AppShell />,
        children: [
          { index: true, element: <Lazy><Dashboard /></Lazy> },
          { path: "rooms", element: <Lazy><RoomsPage /></Lazy> },
          { path: "lessons", element: <Lazy><LessonsPage /></Lazy> },
          { path: "devices", element: <Lazy><DevicesIndex /></Lazy> },
          { path: "rooms/:roomId/devices", element: <Lazy><DevicesByRoom /></Lazy> },
          { path: "measures", element: <Lazy><MeasuresIndex /></Lazy> },
          { path: "rooms/:roomId/measures", element: <Lazy><MeasuresByRoom /></Lazy> },
          { path: "ringtones", element: <Lazy><RingtonesPage /></Lazy> },
          { path: "voice-messages", element: <Lazy><VoiceMessagesPage /></Lazy> },
          { path: "alarms", element: <Lazy><AlarmsPage /></Lazy> },
        ],
      },
    ],
  },
  { path: "*", element: <NotFound /> },
])

export default function App() {
  return (
    <ErrorBoundary>
      <ThemeProvider>
        <RouterProvider router={router} />
        <Toaster />
      </ThemeProvider>
    </ErrorBoundary>
  )
}
