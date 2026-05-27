import { createBrowserRouter, RouterProvider } from "react-router-dom"
import { Toaster } from "@/components/ui/sonner"
import { ProtectedRoute } from "@/components/ProtectedRoute"
import { AppShell } from "@/components/AppShell"
import Login from "@/routes/Login"
import Register from "@/routes/Register"
import NotFound from "@/routes/NotFound"
import {
  Dashboard,
  RoomsPage,
  LessonsPage,
  DevicesIndex,
  DevicesByRoom,
  MeasuresIndex,
  MeasuresByRoom,
  RingtonesPage,
  VoiceMessagesPage,
  AlarmsPage,
} from "@/routes/placeholders"

const router = createBrowserRouter([
  { path: "/login", element: <Login /> },
  { path: "/register", element: <Register /> },
  {
    element: <ProtectedRoute />,
    children: [
      {
        element: <AppShell />,
        children: [
          { index: true, element: <Dashboard /> },
          { path: "rooms", element: <RoomsPage /> },
          { path: "lessons", element: <LessonsPage /> },
          { path: "devices", element: <DevicesIndex /> },
          { path: "rooms/:roomId/devices", element: <DevicesByRoom /> },
          { path: "measures", element: <MeasuresIndex /> },
          { path: "rooms/:roomId/measures", element: <MeasuresByRoom /> },
          { path: "ringtones", element: <RingtonesPage /> },
          { path: "voice-messages", element: <VoiceMessagesPage /> },
          { path: "alarms", element: <AlarmsPage /> },
        ],
      },
    ],
  },
  { path: "*", element: <NotFound /> },
])

export default function App() {
  return (
    <>
      <RouterProvider router={router} />
      <Toaster />
    </>
  )
}
