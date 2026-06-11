import os
import json
from machine import Timer, enable_irq, disable_irq
from time import sleep, localtime, mktime
from config import Config
from wifi import WIFIManager
from logger import Logger
from time_utils import TimeController
from display_controller import DisplayController
from server import ServerSession
from sensor_controller import SensorController
from dht_sensor import TemperatureHumiditySensor
from aq_sensor import AirQualitySensor
from mic_sensor import MicrophoneSensor
from schedule import ScheduleMonitor
from alarm import AlarmMonitor
from player import PlayerController, PlayerException
from voice_message import VoiceMessagesMonitor
from time import localtime


def time_updater(t):
    """Update display time and sync RTC periodically (every hour, not just daily)."""
    global previous_day, last_rtc_sync
    
    dc.time = TimeController.get_current_time_exclusive()
    current_time = localtime()
    day = current_time[2]
    current_timestamp = mktime(current_time)
    
    # Sync RTC on day boundary OR every rtc_sync_interval milliseconds
    should_sync_on_day_change = day != previous_day
    should_sync_on_interval = (current_timestamp - last_rtc_sync) >= (current_config.rtc_sync_interval / 1000)
    
    if should_sync_on_day_change or should_sync_on_interval:
        try:
            server_time_offset = json.loads(server_time_resp.text)["timezone_offset"]
            server_utc_timestamp = json.loads(server_time_resp.text)["timestamp"]
            
            # Convert UTC timestamp to local time using offset
            # Local time = UTC + offset (offset is in seconds, positive for east of UTC)
            server_local_timestamp = server_utc_timestamp + server_time_offset
            server_time_tuple = TimeController.timestamp_to_localtime(server_local_timestamp)
            
            rtc = TimeController.get_rtc()
            if rtc:
                rtc_tuple = TimeController.localtime_to_rtc_tuple(server_time_tuple)
                rtc.datetime(rtc_tuple)
                TimeController.set_utc_offset(server_time_offset)
                last_rtc_sync = current_timestamp
                current_logger.info("RTC synced successfully")
            else:
                current_logger.warning("no rtc")
            dc.server_connected = True
        except Exception as e:
            current_logger.error(f"RTC sync failed: {e}")
        sleep(1)
        
    previous_day = day
    
def sensor_updater(t):
    measurements = sensor_controller.get_measurements()
    
    req = {
        "temperature": measurements["dht"]["temperature"],
        "humidity": measurements["dht"]["humidity"],
        "air_quality": measurements["aq"]["value"],
        "volume": 0,
        "measure_timestamp": TimeController.get_current_timestamp()
    }
    try:
        server_session.send_sensors(req)
    except Exception as e:
        current_logger.error("Cannot send sensors", e)
        dc.server_connected = False
    else:
        dc.server_connected = True
        

def schedule_updater(t):
    try:
        server_schedule_response = server_session.get_schedule()
        server_schedule = json.loads(server_schedule_response.text)
    except Exception as e:
        current_logger.error("Cannot get schedule", e)
        dc.server_connected = False
    else:
        dc.server_connected = True
        current_logger.info("LESSONS_UPDATED", server_schedule)
        schedule_monitor.load_schedule(server_schedule)
        

def alarm_updater(t):
    try:
        alarm_response = server_session.get_alarm(alarm_monitor.alarm)
        is_alarm = json.loads(alarm_response.text)["is_alarm"]
    except Exception as e:
        current_logger.error("Cannot get alarm", e)
        dc.server_connected = False
    else:
        dc.server_connected = True
        alarm_monitor.alarm = is_alarm
        

def vm_updater(t):
    try:
        vm_response = server_session.get_voice_messages()
        current_vm = json.loads(vm_response.text)
    except Exception as e:
        current_logger.error("Cannot get voice messages", e)
        dc.server_connected = False
    else:
        dc.server_connected = True
        if isinstance(current_vm, list):
            for vm in current_vm:
                vm_monitor.add_voice_message(vm)
                
                
def log_updater(t):
    try:
        vm_response = server_session.send_logs(Logger.cache)
    except Exception as e:
        current_logger.error("Cannot send logs", e)
        dc.server_connected = False
    else:
        state = disable_irq()
        Logger.cache = []
        enable_irq(state)
        
previous_day = 40
last_rtc_sync = 0
current_config = Config.from_json("config.json")
logs_path = current_config.log_folder_name or "logs"
try:
    os.mkdir(logs_path)
except OSError:
    pass
Logger.FILENAME = logs_path + "/log.txt"
Logger.TIME_FUNC = TimeController.get_current_time_str
current_logger = Logger.get_logger()
current_logger.info("Started")

dc = DisplayController()


wifi_manager = WIFIManager(current_config.wifi_ap_name,
                           current_config.wifi_ap_password)
while not wifi_manager.connect():
    current_logger.error("Cannot connect to Wifi")
    dc.wifi_connected = False
    sleep(60)
    
dc.wifi_connected = True

server_session = ServerSession(current_config.server_url,
                               current_config.secret_key)


server_time_resp = server_session.get_time()
if not server_time_resp:
    dc.server_connected = False
else:
    try:
        server_time_offset = json.loads(server_time_resp.text)["timezone_offset"]
        server_utc_timestamp = json.loads(server_time_resp.text)["timestamp"]
        
        # Convert UTC timestamp to local time using offset
        # Local time = UTC + offset (offset is in seconds, positive for east of UTC)
        server_local_timestamp = server_utc_timestamp + server_time_offset
        server_time_tuple = TimeController.timestamp_to_localtime(server_local_timestamp)
        print(server_time_tuple)
        
        rtc = TimeController.get_rtc()
        if rtc:
            rtc_tuple = TimeController.localtime_to_rtc_tuple(server_time_tuple)
            rtc.datetime(rtc_tuple)
            TimeController.set_utc_offset(server_time_offset)
            current_logger.info("RTC initialized successfully")
            last_rtc_sync = mktime(localtime())
        else:
            current_logger.warning("no rtc")
        dc.server_connected = True
    except Exception as e:
        current_logger.error(f"Failed to initialize RTC: {e}")
        dc.server_connected = False
    sleep(1)

current_logger.info("Initializing sensors...")
try:
    sensor_controller = SensorController()
    dht_sensor = TemperatureHumiditySensor("dht", 14)
    sensor_controller.add_sensor(dht_sensor)
    aq_sensor = AirQualitySensor("aq", 34)
    sensor_controller.add_sensor(aq_sensor)
except Exception as e:
    current_logger.error("Sensor initialization failed", e)

# Initialize timers and monitors
current_logger.info("Initializing timers and monitors...")
try:
    # Time timer
    time_timer = Timer(1)
    time_timer.init(mode=Timer.PERIODIC, period=1000, callback=time_updater)

    # Sensor timer
    sensor_timer = Timer(0)
    sensor_timer.init(mode=Timer.PERIODIC, period=current_config.sensor_delay, callback=sensor_updater)

    # Log sending timer
    log_send_timer = Timer(6)
    log_send_timer.init(mode=Timer.PERIODIC, period=current_config.send_log_delay, callback=log_updater)

    # Schedule monitor
    schedule_monitor = ScheduleMonitor(current_config.schedule_tolerance)
    schedule_monitor.set_tolerance(current_config.schedule_tolerance)
    schedule_timer = Timer(2)
    schedule_timer.init(mode=Timer.PERIODIC, period=current_config.schedule_delay, callback=schedule_updater)

    # Alarm monitor
    alarm_monitor = AlarmMonitor()
    alarm_timer = Timer(3)
    alarm_timer.init(mode=Timer.PERIODIC, period=current_config.alarm_delay, callback=alarm_updater)

    # Voice message monitor
    vm_monitor = VoiceMessagesMonitor()
    vm_timer = Timer(4)
    vm_timer.init(mode=Timer.PERIODIC, period=current_config.voice_message_delay, callback=vm_updater)
except Exception as e:
    current_logger.error("Timer and monitor initialization failed", e)

# Create a logger function for the player to use
current_logger.info("Creating player logger function...")

def player_logger(msg):
    if "ERROR" in msg or "DEBUG" in msg:
        current_logger.info(f"PLAYER: {msg}")


current_logger.info("Initializing player controller...")
try:
    player_controller = PlayerController(current_config.socket_host, current_config.socket_port, logger=player_logger)
except Exception as e:
    current_logger.error("Player controller initialization failed", e)
    player_controller = None

current_player_session = None

ring_started = alarm_started = vm_started = last_hop_timestamp = last_logged_second = 0
current_vm = None
current_logger.info("Initialization complete. Entering main loop.")
while True:
    try:
        current_timestamp = TimeController.get_current_timestamp()
        # The loop runs many times per second; only log once per second so the
        # log file and the in-memory log cache do not flood.
        new_second = current_timestamp != last_logged_second
        if new_second:
            last_logged_second = current_timestamp
        if new_second and current_timestamp % 2 == 0:
            current_logger.info(f"STATUS: Time={current_timestamp}, Local={TimeController.get_current_time_str()}")
        
        seconds_from_alarm_started = current_timestamp - alarm_started
        
        if current_config.alarm_duration_min <= seconds_from_alarm_started < current_config.alarm_duration_max:  # ALARM NOTIFICATION ENDED
            current_logger.info("ALARM OFF")
            if current_player_session is not None:
                current_player_session.stop()
                current_player_session = None
            alarm_started = 0  
        elif alarm_started == 0:  # ALARM NOTIFICATION IS NOT ONGOING
            is_alarm, start = alarm_monitor.ring()
            if is_alarm:
                # STOP RING IF ALARM
                current_logger.info("RING INTERRUPTED")
                ring_started = 0
                schedule_monitor.ringing_end()
                current_logger.info("VOICE MESSAGE INTERRUPTED")
                vm_started = 0
                current_vm = None
                
                if current_player_session is not None:
                    current_player_session.stop()
                    current_player_session = None
                
                current_player_session = player_controller.get_session()
                try:
                    if start:
                        current_logger.info("ALARM START ON")
                        current_player_session.play("alarm_start")
                    else:
                        current_logger.info("ALARM FINISH ON")
                        current_player_session.play("alarm_finish")
                except PlayerException as pe:
                    current_logger.error("Error while playing alarm sound", pe)
                except Exception as e:
                    current_logger.error("Unexpeted error", e)
                    
                alarm_started = current_timestamp  
            else:
                if current_vm is None:
                    current_vm = vm_monitor.get_message()
                    if current_vm is not None:
                        current_logger.info("RING INTERRUPTED")
                        ring_started = 0
                        schedule_monitor.ringing_end()
                        
                        if current_player_session is not None:
                            current_player_session.stop()
                            current_player_session = None
                            
                        current_player_session = player_controller.get_session()
                        try:
                            current_player_session.play(current_vm)
                        except PlayerException as pe:
                            current_logger.error(f"Error while playing voice message '{current_vm}'", pe)
                        except Exception as e:
                            current_logger.error("Unexpeted error", e)
                        else:
                            current_logger.info(f"VOICE_MESSAGE '{current_vm}' ON")
                                
                        vm_started = current_timestamp
                    else:
                        seconds_from_ring_started = current_timestamp - ring_started
                        if current_config.ring_duration_min <= seconds_from_ring_started < current_config.ring_duration_max:  # RING NOTIFICATION ENDED
                            if current_player_session is not None:
                                current_player_session.stop()
                                current_player_session = None
                            current_logger.info("RING OFF")
                            ring_started = 0
                            schedule_monitor.ringing_end()
                        elif ring_started == 0:  # RING NOTIFICATION IS NOT ONGOING
                            if schedule_monitor.time_to_ring():
                                if current_player_session is not None:
                                    current_player_session.stop()
                                    current_player_session = None
                                current_player_session = player_controller.get_session()
                                try:
                                    ringtone_resp = server_session.get_ringtone()
                                    ringtone_data = json.loads(ringtone_resp.text)
                                    ringtone_code = ringtone_data.get("code")
                                    if not ringtone_code:
                                        current_logger.error("No ringtone code in server response")
                                    else:
                                        current_player_session.play(ringtone_code)
                                        current_logger.info(f"RING ON for code {ringtone_code}")
                                        ring_started = current_timestamp
                                except PlayerException as pe:
                                    current_logger.error(f"Error while playing ringtone", pe)
                                    ring_started = current_timestamp
                                except Exception as e:
                                    current_logger.error(f"Error getting or playing ringtone: {e}")
                                    ring_started = current_timestamp
                            else:
                                # Periodic check of why it's not ringing
                                if new_second and current_timestamp % 30 == 0:
                                    next_lesson = "None"
                                    if schedule_monitor._schedule:
                                        # Find the first upcoming lesson
                                        for l in schedule_monitor._schedule:
                                            if l["start"] >= current_timestamp - 60:
                                                next_lesson = f"{l['start']} (in {l['start']-current_timestamp}s)"
                                                break
                                    current_logger.info(f"DEBUG: Not ringing. Next potential: {next_lesson}")
                else:
                    seconds_from_vm_started = current_timestamp - vm_started
                    if current_config.vm_duration_min <= seconds_from_vm_started <= current_config.vm_duration_max:
                        current_logger.info("VOICE MESSAGE OFF")
                        
                        if current_player_session is not None:
                            current_player_session.stop()
                            current_player_session = None
                        vm_started = 0
                        vm_monitor.set_message_finished(current_vm)
                        current_vm = None

        if current_timestamp - last_hop_timestamp >= 1:
            last_hop_timestamp = current_timestamp
        else:
            sleep(0.1)
    except Exception as e:
        current_logger.error(f"FATAL ERROR IN MAIN LOOP: {e}")
        sleep(5) # Avoid tight loop if error persists