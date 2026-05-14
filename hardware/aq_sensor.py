from machine import Pin, ADC
from sensor import Sensor


class AirQualitySensor(Sensor):
    def __init__(self, name, analog_pin, digital_pin=None):
        super().__init__(name)
        self._analog_pin = ADC(analog_pin)
        self._digital_pin = digital_pin if digital_pin is None else Pin(analog_pin, Pin.IN)
    
    def read(self):
        result = {"value": self._analog_pin.read()}

        if self._digital_pin is not None:
            result["trigger"] = bool(self._digital_pin.value())
            
        return result