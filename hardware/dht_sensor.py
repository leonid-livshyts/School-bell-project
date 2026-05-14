from dht import DHT11
from machine import Pin
from sensor import Sensor


class TemperatureHumiditySensor(Sensor):
    def __init__(self, name, data_pin):
        super().__init__(name)
        self._sensor = DHT11(Pin(data_pin))
        
    def read(self):
        self._sensor.measure()
        return {
            "temperature": self._sensor.temperature(),
            "humidity": self._sensor.humidity()
        }
