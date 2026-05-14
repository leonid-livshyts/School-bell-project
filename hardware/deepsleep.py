from machine import Pin, Timer, RTC, DEEPSLEEP, deepsleep
from time import sleep, localtime
from time_utils import TimeController

def deep_sleep(seconds, validate_rtc=True):
    """
    Enter deep sleep mode with RTC alarm wake-up.
    
    Args:
        seconds: Sleep duration in seconds
        validate_rtc: If True, checks that RTC has been synced before sleeping
        
    Raises:
        RuntimeError: If validate_rtc=True and RTC is not synced
    """
    if validate_rtc:
        # Check if RTC has been synced at least once
        last_sync = TimeController.get_last_sync_time()
        if last_sync == 0:
            raise RuntimeError("RTC not synced - cannot enter deep sleep")
        
        # Verify RTC is readable
        try:
            rtc = RTC()
            current_time = localtime()
            if current_time[0] < 2000:  # Year is unreasonable
                raise RuntimeError("RTC contains invalid time")
        except Exception as e:
            raise RuntimeError(f"RTC validation failed: {e}")
    else:
        rtc = RTC()
    
    if seconds <= 0:
        raise ValueError("Sleep duration must be positive")
    
    rtc.irq(trigger=rtc.ALARM0, wake=DEEPSLEEP)
    rtc.alarm(rtc.ALARM0, int(seconds * 1000))
    deepsleep()
    
    
led = Pin(5, Pin.OUT)
led.value(1)
sleep(1)
led.value(0)
sleep(1)

print("I'm here")
deep_sleep(10)

# 
# def toogle(timer):
#     led.value(not led.value())
#     
# t = Timer(1)
# t.init(mode=Timer.ONE_SHOT, period=5000, callback=toogle)
# 
# try:
#     while True:
#         print("Timer is working")
#         time.sleep(2)
# except KeyboardInterrupt:
#     t.deinit()
#     print("Timer has been stopped")
#     led.value(0)
