from machine import Pin
from utime import sleep, sleep_us
import dht

# Class to handle DHT22 temperature and humidity sensor
# INPUT:
#   pin: GPIO pin where the sensor is connected
class Sensor_DHT22:
    def __init__(self, pin):
        self.sensor = dht.DHT22(pin)

        self.temperature = 0.0
        self.humidity = 0.0

    # function to read temperature and humidity from the sensor
    # OUTPUTS:
    #   temperature: Temperature in °C 
    #   humidity: Humidity in %
    def read(self):
        try:
            self.sensor.measure()                           # start measurement
            self.temperature = self.sensor.temperature()    # get temperature in °C
            self.humidity = self.sensor.humidity()          # get humidity in %
        except OSError:
            print('Sensor reading failed.')

        return self.temperature, self.humidity
    
if __name__ == "__main__":
    sensor = Sensor_DHT22(Pin(14))

    while True:
        temp, hum = sensor.read()
        print('Temperature: %3.1f °C' % temp)
        print('Humidity: %3.1f %%' % hum)

        sleep(5)  # DHT22: maximum one measurement every 2 seconds