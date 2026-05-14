from machine import Pin, SoftI2C, Timer
import ssd1306
from time import sleep, localtime


class DisplayController:
    TIME_FORMAT = "{:02}:{:02}:{:02}"
    SDA_PORT = 21
    SCL_PORT = 22
    
    def __init__(self):
        self._wifi_connected = False
        self._server_connected = False
        self._time = DisplayController.TIME_FORMAT.format(0, 0, 0)
        
        self._i2c = SoftI2C(
            sda=Pin(DisplayController.SDA_PORT),
            scl=Pin(DisplayController.SCL_PORT)
        ) 
        self._display = ssd1306.SSD1306_I2C(128, 64, self._i2c)
        
        self.display()
        
    def display(self):
        self._display.fill(0)
        self._display.text(f"WIFI: {'ON' if self._wifi_connected else 'OFF'}", 0, 0, 1)
        self._display.text(f"Server: {'ON' if self._server_connected else 'OFF'}", 0, 21, 1)
        self._display.text("Time: " + self._time, 0, 42, 1)
        self._display.show()
    
    @property
    def wifi_connected(self):
        return self._wifi_connected
    
    @wifi_connected.setter
    def wifi_connected(self, value):
        if value != self._wifi_connected:
            self._wifi_connected = value
            self.display()
    
    @property
    def server_connected(self):
        return self._server_connected
    
    @server_connected.setter
    def server_connected(self, value):
        if value != self._server_connected:
            self._server_connected = value
            self.display()
    
    @property
    def time(self):
        return self._time
    
    @time.setter
    def time(self, value):
        if value != self._time:
            self._time = value
            self.display()
    
    @staticmethod
    def get_current_time_str():
        t = localtime()
        return DisplayController.TIME_FORMAT.format(t[3], t[4], t[5])
    


def time_updater(t):
    dc.time = DisplayController.get_current_time_str()
    

# if __name__ == "__main__":
#     dc = DisplayController()
#     time_timer = Timer(1)
#     time_timer.init(mode=Timer.PERIODIC, freq=1, callback=time_updater)  # period - ms, freq - hz
#     try:
#         while True:
#             sleep(1)
#     except KeyboardInterrupt:
#         time_timer.deinit()
#     sleep(2)
#     dc.wifi_connected = True
#     sleep(2)
#     dc.server_connected = True
#     sleep(2)
#     dc.time = DisplayController.get_current_time_str()
#     sleep(10)
    
    
    