// Placeholder pages -- replaced in step 7 with real CRUD pages.

function Placeholder({ title }: { title: string }) {
  return (
    <div className="flex flex-col gap-2">
      <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
      <p className="text-sm text-muted-foreground">Coming in step 7.</p>
    </div>
  )
}

export const Dashboard = () => <Placeholder title="Dashboard" />
export const RoomsPage = () => <Placeholder title="Rooms" />
export const LessonsPage = () => <Placeholder title="Lessons" />
export const DevicesIndex = () => <Placeholder title="Devices" />
export const DevicesByRoom = () => <Placeholder title="Devices (by room)" />
export const MeasuresIndex = () => <Placeholder title="Measures" />
export const MeasuresByRoom = () => <Placeholder title="Measures (by room)" />
export const RingtonesPage = () => <Placeholder title="Ringtones" />
export const VoiceMessagesPage = () => <Placeholder title="Voice messages" />
export const AlarmsPage = () => <Placeholder title="Alarms" />
