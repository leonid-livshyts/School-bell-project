import { AudioLibraryPage } from "@/components/AudioLibraryPage"
import { voiceMessagesApi } from "@/lib/api/voice_messages"
import { useDocumentTitle } from "@/hooks/useDocumentTitle"

export default function VoiceMessagesPage() {
  useDocumentTitle("Voice messages")
  return (
    <AudioLibraryPage
      title="Voice messages"
      description="Pre-recorded announcements. The ESP32 in the target room plays each one once."
      api={voiceMessagesApi}
      queryKey={["voice_messages"] as const}
      emptyHint="Upload an MP3 or WAV to broadcast as a voice message."
    />
  )
}
