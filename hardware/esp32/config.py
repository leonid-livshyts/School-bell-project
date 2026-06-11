import ujson as json

class Config:
    _config = None
    
    def __init__(self, wifi_ap_name, wifi_ap_password, log_folder_name, server_url,
                 secret_key, socket_url, sensor_delay, send_log_delay, schedule_delay,
                 alarm_delay, voice_message_delay, rtc_sync_interval=3600000,
                 schedule_tolerance=20, alarm_duration_min=60, alarm_duration_max=120,
                 ring_duration_min=20, ring_duration_max=30, vm_duration_min=60, vm_duration_max=90):
        self.wifi_ap_name = wifi_ap_name
        self.wifi_ap_password = wifi_ap_password
        self.log_folder_name = log_folder_name
        self.server_url = server_url
        self.secret_key = secret_key
        self.socket_host, _ ,self.socket_port = socket_url.partition(":")
        self.socket_port = int(self.socket_port)
        self.sensor_delay = sensor_delay
        self.send_log_delay = send_log_delay
        self.schedule_delay = schedule_delay
        self.alarm_delay = alarm_delay
        self.voice_message_delay = voice_message_delay
        self.rtc_sync_interval = rtc_sync_interval
        self.schedule_tolerance = schedule_tolerance
        self.alarm_duration_min = alarm_duration_min
        self.alarm_duration_max = alarm_duration_max
        self.ring_duration_min = ring_duration_min
        self.ring_duration_max = ring_duration_max
        self.vm_duration_min = vm_duration_min
        self.vm_duration_max = vm_duration_max
        
        
    @staticmethod
    def from_json(filename):
        with open(filename, encoding="utf8") as f:
            config_json = json.load(f)
        
        wifi_settings = config_json.get("wifi_ap", {})
        server_settings = config_json.get("server", {})
        refresh_settings = config_json.get("refresh_rates", {})
        
        timing_settings = config_json.get("timing", {})
        durations_settings = config_json.get("durations", {})
        
        Config._config = Config(
            wifi_settings.get("name"), 
            wifi_settings.get("password"),
            config_json.get("log_folder"),
            server_settings.get("url"),
            config_json.get("secret_key"),
            server_settings.get("socket"),
            refresh_settings.get("sensor"),
            refresh_settings.get("send_log"),
            refresh_settings.get("schedule"),
            refresh_settings.get("alarm"),
            refresh_settings.get("voice_message"),
            timing_settings.get("rtc_sync_interval", 3600000),
            timing_settings.get("schedule_tolerance", 20),
            durations_settings.get("alarm_min", 60),
            durations_settings.get("alarm_max", 120),
            durations_settings.get("ring_min", 20),
            durations_settings.get("ring_max", 30),
            durations_settings.get("vm_min", 60),
            durations_settings.get("vm_max", 90)
        )
        return Config.get_config()
    
    @staticmethod
    def get_config():
        return Config._config
