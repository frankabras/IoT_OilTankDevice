from machine import Pin
from utime import sleep, sleep_us
import dht

class Sensor_DHT22:
    def __init__(self, pin):
        self.sensor = dht.DHT22(pin)

        self.temperature = 0.0
        self.humidity = 0.0

    def read(self):
        try:
            self.sensor.measure()  # lancer la mesure
            self.temperature = self.sensor.temperature()  # récupérer température en °C
            self.humidity = self.sensor.humidity()  # récupérer humidité en %
        except OSError:
            print('Échec de la lecture du capteur.')

        return self.temperature, self.humidity
    
if __name__ == "__main__":
    sensor = Sensor_DHT22(Pin(14))

    while True:
        temp, hum = sensor.read()
        print('Température: %3.1f °C' % temp)
        print('Humidité: %3.1f %%' % hum)

        sleep(5)  # DHT22 maximum une mesure toutes les 2 secondes