from machine import RTC
from time import localtime, mktime


class TimeController:
    TIME_FORMAT = "{:04}-{:02}-{:02} {:02}:{:02}:{:02}"
    TIME_FORMAT_EXCLUSIVE = "{:02}:{:02}:{:02}"

    # Timezone offset in seconds from UTC (e.g., 10800 for UTC+3).
    # Set once via set_utc_offset() after RTC is synced with server time.
    # Used to convert local time back to UTC for server comparison.
    UTC_OFFSET = 0
    
    # Track last RTC sync time to monitor sync frequency
    _last_sync_time = 0

    # Epoch offset between Unix (1970) and MicroPython (2000)
    # 946684800 = 30 years * 365 days + 7 leap days (72, 76, 80, 84, 88, 92, 96)
    EPOCH_OFFSET = 946684800

    @staticmethod
    def set_utc_offset(offset_seconds):
        """
        Call this after syncing the RTC with server time.
        offset_seconds is the timezone_offset returned by the server (e.g. 10800 for UTC+3).
        Storing it lets get_current_timestamp() return a true UTC timestamp so it
        can be compared directly with lesson start/end values from the server.
        
        Formula:
        - Server sends: UTC_timestamp and timezone_offset
        - Local time = UTC_timestamp + timezone_offset
        - RTC is set to local time
        - To compare with server: current_UTC = localtime() - timezone_offset
        """
        TimeController.UTC_OFFSET = offset_seconds
        TimeController._last_sync_time = mktime(localtime())
    
    @staticmethod
    def get_last_sync_time():
        """Returns the timestamp when RTC was last synchronized."""
        return TimeController._last_sync_time

    @staticmethod
    def get_current_timestamp():
        """Returns current time as a UTC Unix timestamp."""
        # mktime returns seconds since 2000, we add offset to get Unix timestamp (since 1970)
        return mktime(localtime()) - TimeController.UTC_OFFSET + TimeController.EPOCH_OFFSET

    @staticmethod
    def get_current_time_str():
        t = localtime()
        return TimeController.TIME_FORMAT.format(t[0], t[1], t[2], t[3], t[4], t[5])

    @staticmethod
    def get_current_time_exclusive():
        t = localtime()
        return TimeController.TIME_FORMAT_EXCLUSIVE.format(t[3], t[4], t[5])

    @staticmethod
    def timestamp_to_localtime(timestamp):
        """Convert a UTC+offset timestamp to a localtime tuple."""
        # If timestamp is a Unix timestamp (since 1970), convert it to MicroPython epoch (since 2000)
        if timestamp > TimeController.EPOCH_OFFSET:
            timestamp -= TimeController.EPOCH_OFFSET
        return localtime(timestamp)

    @staticmethod
    def localtime_to_rtc_tuple(t):
        """Convert a localtime tuple to the 8-tuple expected by RTC.datetime()."""
        # RTC expects: (year, month, day, weekday, hour, minute, second, subsecond)
        return (t[0], t[1], t[2], t[6], t[3], t[4], t[5], 0)

    @staticmethod
    def get_rtc():
        try:
            return RTC()
        except Exception:
            return None