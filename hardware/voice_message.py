class VoiceMessagesMonitor:
    def __init__(self):
        self.voice_messages_container = []
    
    def add_voice_message(self, url):
        if url not in self.voice_messages_container:
            self.voice_messages_container.append(url)
        
    def get_message(self):
        if self.voice_messages_container:
            return self.voice_messages_container[0]
    
    def set_message_finished(self, url):
        self.voice_messages_container.remove(url)