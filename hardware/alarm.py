NO_EVENT = 0
ALARM_START = 1
ALARM_END = 2


class AlarmMonitor:
    def __init__(self):
        self._alarm = False
        self._event = NO_EVENT
        
    @property
    def alarm(self):
        return self._alarm
    
    @alarm.setter
    def alarm(self, value):
        if not isinstance(value, bool):
            raise ValueError("Wrong value")
        
        if value != self.alarm:
            self._alarm = value
            self._event = ALARM_START if value else ALARM_END
            
    def ring(self):
        if self._event != NO_EVENT:
            result = self._event == ALARM_START
            self._event = NO_EVENT
            return True, result
        else:
            return False, False
