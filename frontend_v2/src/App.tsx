import { createBrowserRouter, RouterProvider } from "react-router-dom"
import { Toaster } from "@/components/ui/sonner"
import { ProtectedRoute } from "@/components/ProtectedRoute"
import { AppShell } from "@/components/AppShell"
import Login from "@/routes/Login"
import Register from "@/routes/Register"
import NotFound from "@/routes/NotFound"
import Dashboard from "@/routes/Dashboard"
import RoomsPage from "@/routes/Rooms"
import LessonsPage from "@/routes/Lessons"
import DevicesIndex from "@/routes/DevicesIndex"
import DevicesByRoom from "@/routes/DevicesByRoom"
import MeasuresIndex from "@/routes/MeasuresIndex"
import MeasuresByRoom from "@/routes/MeasuresByRoom"
import RingtonesPage from "@/routes/Ringtones"
import VoiceMessagesPage from "@/routes/VoiceMessages"
import AlarmsPage from "@/routes/Alarms"

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
