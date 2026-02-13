"""
Docstring for main
"""
from utime import sleep_ms, ticks_ms, ticks_diff
import gc
import ujson
import uerrno
import uos

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

state = "INIT"

try: 
    while True:
        if state == "INIT":
            print("INIT state")
            try:
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
                wifi.start()
                
                state = "MEASURE"
            except Exception as e:
                print("Initialization error:", e)
            
        elif state == "MEASURE":
            print("MEASURE state")
            try: 
                temp, hum = temp_sensor.read()
                distance = level_sensor.read(temperature_c=temp if temp is not None else 20.0)
                liters = tank.to_liters(tank.tank_height - distance)
                
                state = "CONNECT"
                print("CONNECT state")
#                 state = "SAVE_DATA"
            except Exception as e:
                print("Measurement error:", e)

        elif state == "CONNECT":
            try:
                wifi.enable_connection = True
                if wifi.is_connected:
                    print("WiFi connected successfully")
                    state = "FLUSH_DATA"
                elif wifi.connection_failed:
                    print("WiFi connection failed")
                    state = "SAVE_DATA"
            except Exception as e:
                print("WiFi connection error:", e)
            
        elif state == "FLUSH_DATA":
            print("FLUSH_DATA state")
            try:
                with open("data.json", "r") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        object = ujson.loads(line)
                        print("Flushing data:", object)
                uos.remove("data.json")
                print("data.json flushed successfully")                                 # TODO: Implement actual data transmission to server
            except Exception as e:
                if isinstance(e, OSError) and e.args[0] == uerrno.ENOENT:
                    print("No data to flush (data.json not found)")
                else:
                    print("Error reading data.json:", e)

            state = "SEND_DATA"
        
        elif state == "SAVE_DATA":
            print("SAVE_DATA state")

            donnees = {
                "temperature": str(temp) + "°C" if temp is not None else "N/A",
                "humidity": str(hum) + "%" if hum is not None else "N/A",
                "volume": str(liters) + "L" if liters is not None else "N/A",
            }

            with open("data.json", "a") as f:
                ujson.dump(donnees, f)
                f.write("\n")
            print("Data saved to data.json")

            state = "SEND_DATA"

        elif state == "SEND_DATA":
            print("SEND_DATA state")
            if temp is not None and hum is not None:
                print('Temperature: %3.1f °C' % temp)
                print('Humidity: %3.1f %%' % hum)
            else:
                print('Failed to read from temperature and humidity sensor.')
            
            print('Fuel oil volume: {:.2f} liters'.format(liters))

            state = "SLEEP"

        elif state == "SLEEP":
            print("SLEEP state")
            print("-------------------------------")
            wifi.enable_connection = False
            sleep_ms(5000)

            state = "MEASURE"

except KeyboardInterrupt:
    print("Program interrupted by user")
    wifi.stop()
