from time_utils import TimeController


class ScheduleMonitor:
    def __init__(self, schedule_tolerance=20):
        self._schedule = []
        self._ringing_lesson_id = None  # Store ID or unique identifier
        self._last_rung_id = None      # Unique key: "lesson_id_start" or "lesson_id_end"
        self._schedule_tolerance = schedule_tolerance
        
    def load_schedule(self, server_schedule):
        self._schedule = server_schedule
    
    def set_tolerance(self, tolerance_seconds):
        """Set the time window (in seconds) around lesson start/end for detection."""
        self._schedule_tolerance = tolerance_seconds
        
    def time_to_ring(self):
        if self._ringing_lesson_id is None:
            current_time = TimeController.get_current_timestamp()
            for lesson in self._schedule:
                # Use a unique identifier for the lesson boundary
                # Assuming lessons have unique start/end times if ID is not available
                start_id = f"{lesson['start']}_start"
                end_id = f"{lesson['end']}_end"

                if abs(lesson["start"] - current_time) <= self._schedule_tolerance:
                    if self._last_rung_id != start_id:
                        from logger import Logger
                        Logger.get_logger().info(f"MATCH: Ringing start for {lesson['start']} (current: {current_time}, diff: {lesson['start']-current_time})")
                        self._ringing_lesson_id = start_id
                        self._last_rung_id = start_id
                        return True
                
                if abs(lesson["end"] - current_time) <= self._schedule_tolerance:
                    if self._last_rung_id != end_id:
                        from logger import Logger
                        Logger.get_logger().info(f"MATCH: Ringing end for {lesson['end']} (current: {current_time}, diff: {lesson['end']-current_time})")
                        self._ringing_lesson_id = end_id
                        self._last_rung_id = end_id
                        return True
                
        return False
    
    def ringing_end(self):
        self._ringing_lesson_id = None
