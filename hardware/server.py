import urequests as requests
import json


class ServerSession:
    def __init__(self, server_host, client_key):
        self.url = "http://" + server_host
        self.headers = {
            "X-API-Key": client_key
        }
        
    def _request(self, request_type, path, data=None, header=None):
        headers = self.headers.copy()
            
        if request_type == "GET":
            
            return requests.get(url=self.url + path, headers=headers)
        
        if request_type == "POST":
            try:
                if isinstance(data, (list, tuple, dict)):
                    headers["Content-Type"] = "application/json"
                    data = json.dumps(data)   # <-- Серіалізуємо data в JSON рядок

                return requests.post(url=self.url + path, headers=headers, data=data)
            except Exception as e:
                print(e)

    def send_sensors(self, sensors_data):
        """ Sends sensor data to server """
        return self._request("POST", "/sensors", sensors_data)
    
    def get_time(self):
        """ Returns current unix time """
        return self._request("GET", "/time")
    
    def get_schedule(self):
        """ Returns ring schedule for current day """
        return self._request("GET", "/schedule")
    
    def get_alarm(self, current_alarm):                                   
        """ Returns alert """
        return self._request("GET", f"/alarm?current_alarm={str(current_alarm).lower()}")
    
    def get_ringtone(self):
        """ Returns code of class ringtone """
        return self._request("GET", "/ringtone_code")
    
    def get_voice_messages(self):
        """ Returns voice messages urls """
        return self._request("GET", "/voice_messages")
    
    def send_logs(self, logs):
        """ Send log to the server """
        return self._request("POST", "/logs", logs)
