from sensor import Sensor


class SensorController:
    def __init__(self):
        self._sensors = []

    def add_sensor(self, sensor):
        if isinstance(sensor, Sensor):
            self._sensors.append(sensor)
        else:
            raise ValueError("THIS IS NOT A SENSOR, MOTHERLOVER")

    def get_measurements(self):
        result = {}
        for sensor in self._sensors:
            result[sensor.name] = sensor.read()
        return result
