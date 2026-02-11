"""
Docstring for main
"""
from utime import sleep_ms, ticks_ms, ticks_diff
import gc
import ujson

# Import sensor and wifi classes
from sensor_sr04 import SensorSR04
from sensor_dht22 import Sensor_DHT22
from volume_calculator import HexagonalPrismTank
from wifi_manager import WifiManager
from logging import *

""" Constant definitions """
# Tank dimensions in cm
TANK_LENGTH = 250.0
H_RECTANGLE = 45.5
H_TRAPEZE = 59.5
MIN_WIDTH = 53.0
MAX_WIDTH = 74.0
# Level sensor blind zone in cm 
SENSOR_OFFSET = 20.0
# WiFi connection parameters
config = hotspot
WIFI_SSID = config["ssid"]
WIFI_PASSWORD = config["pswd"]
LED_POLARITY = "LO"

""" Pin definitions """
# Temperature and humidity sensor (DHT22)
DHT22_PIN = 2
# Ultrasonic level sensor (SR04)
TRIGGER_PIN = 3
ECHO_PIN = 4
# LED indicator for WiFi status
LED_PIN = 8

""" Main program loop """
temp_sensor = Sensor_DHT22(pin=DHT22_PIN, 
                           internal_pullup=False)

level_sensor = SensorSR04(trig_pin=TRIGGER_PIN, 
                          echo_pin=ECHO_PIN, 
                          sensor_offset=SENSOR_OFFSET)

tank = HexagonalPrismTank(tank_length=TANK_LENGTH, 
                          h_rectangle=H_RECTANGLE, 
                          h_trapeze=H_TRAPEZE, 
                          min_width=MIN_WIDTH, 
                          max_width=MAX_WIDTH)

wifi = WifiManager(ssid=WIFI_SSID, 
                   password=WIFI_PASSWORD,
                   led_pin=LED_PIN,
                   led_polarity=LED_POLARITY)

try: 
    while True:
        sleep_ms(5000)

        # Perform the mesurement of temperature and humidity
        temp, hum = temp_sensor.read()
        if temp is not None and hum is not None:
            print('Temperature: %3.1f °C' % temp)
            print('Humidity: %3.1f %%' % hum)
        else:
            print('Failed to read from temperature and humidity sensor.')

        # Perform the measurement and record the fuel oil level
        distance = level_sensor.read(temperature_c=temp if temp is not None else 20.0)
        liters = tank.to_liters(tank.tank_height - distance)
        print('Fuel oil volume: {:.2f} liters'.format(liters))

        donnees = {
            "temperature": str(temp) + "°C" if temp is not None else "N/A",
            "humidity": str(hum) + "%" if hum is not None else "N/A",
            "volume": str(liters) + "L" if liters is not None else "N/A",
        }

        with open("data.json", "a") as f:
            ujson.dump(donnees, f)
            f.write("\n")
        print("Data saved to data.json")
        print("-------------------------------")

except KeyboardInterrupt:
    print("Program interrupted by user")
    wifi.stop()
