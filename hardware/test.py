from sensor_controller import SensorController
from dht_sensor import TemperatureHumiditySensor
from aq_sensor import AirQualitySensor
from mic_sensor import MicrophoneSensor


if __name__ == "__main__":
    sensor_controller = SensorController()
    
    dht_sensor = TemperatureHumiditySensor("dht", 5)
    sensor_controller.add_sensor(dht_sensor)
    
    aq_sensor = AirQualitySensor("aq", 1)
    sensor_controller.add_sensor(aq_sensor)
    
    mic_sensor = MicrophoneSensor("mic", 1)
    sensor_controller.add_sensor(mic_sensor)
    
    measurements = sensor_controller.get_measurements()
    print(measurements)
