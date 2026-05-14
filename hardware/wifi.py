import network
from time import sleep


class WIFIManager:    
    def __init__(self, ap_name, password):
        self.ap_name = ap_name
        self.password = password
        
        self.sta_if = network.WLAN(network.STA_IF)
        self.sta_if.active(True)
        
    def connect(self, retries=20, delay=2):
        self.sta_if.connect(self.ap_name, self.password)
        for _ in range(retries):
            if self.sta_if.isconnected():
                return True
            sleep(delay)
        return False
