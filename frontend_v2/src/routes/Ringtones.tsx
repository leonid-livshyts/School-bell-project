import { AudioLibraryPage } from "@/components/AudioLibraryPage"
import { ringtonesApi } from "@/lib/api/ringtones"

export default function RingtonesPage() {
  return (
    <AudioLibraryPage
      title="Ringtones"
      description="Audio files that play as the bell. Attach one to a room or leave 'All rooms' for school-wide."
      api={ringtonesApi}
      queryKey={["ringtones"] as const}
      emptyHint="Upload an MP3 or WAV to use as a bell ringtone."
    />
  )
}
