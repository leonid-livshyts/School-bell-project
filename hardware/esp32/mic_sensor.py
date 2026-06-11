from machine import ADC
from sensor import Sensor


class MicrophoneSensor(Sensor):
    def __init__(self, name, analog_pin):
        super().__init__(name)
        self._analog_pin = ADC(analog_pin)
    
    def read(self):
        return {"value": self._analog_pin.read()}