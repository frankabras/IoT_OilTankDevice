"""
Docstring for main
"""
from utime import sleep_ms, ticks_ms, ticks_diff, localtime
import ntptime
import ujson
import uerrno
import uos
import gc

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
WIFI_CONFIG = hotspot
WIFI_SSID = WIFI_CONFIG["ssid"]
WIFI_PASSWORD = WIFI_CONFIG["pswd"]                                                         # TODO: Improve security
LED_POLARITY = "LO"

""" Pin definitions """
# Temperature and humidity sensor (DHT22)
DHT22_PIN = 2
# Ultrasonic level sensor (SR04)
TRIGGER_PIN = 3
ECHO_PIN = 4
# LED indicator for WiFi status
LED_PIN = 8

""" Function definitions """
def cleanup():
    """ Perform garbage collection and cleanup """
    gc.collect()
    print("Garbage collection completed")

def init_components(): 
    """ Initialize sensors, WiFi, and other components """
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
        
        return temp_sensor, level_sensor, tank, wifi
    except Exception as e:
        print("Initialization error:", e)
        return None, None, None, None

def measurment():
    """ Perform sensor measurements and return results """
    try:
        temp, hum = temp_sensor.read()                                                      # TODO: 2 decimal places for temperature and humidity (returned from read method)
        distance = level_sensor.read(temperature_c=temp if temp is not None else 20.0)
        liters = tank.to_liters(tank.tank_height - distance)                                # TODO: 2 decimal places for liters (returned from to_liters method)
        return temp, hum, liters
    except Exception as e:
        print("Measurement error:", e)
        return None, None, None

def connection():
    """ Manage WiFi connection and NTP synchronization """
    try:
        wifi.enable_connection = True
        if wifi.is_connected:
            print("WiFi connected successfully")
            return True
        elif wifi.connection_failed:
            print("WiFi connection failed")
            return False
        else:
            return None
    except Exception as e:
        print("Connection error:", e)

def update_rtc():                                                                           # TODO: Add parameter for retry count
    """ Update RTC time from NTP server """
    for _ in range(3):
        try:
            ntptime.settime()
            print("RTC synchronized with NTP server")
            print("Current time (UTC):", localtime())
            break
        except Exception as e:
            sleep_ms(1000)
    else:
        print("Failed to synchronize RTC after retries")

def flush_data():                                                                           # TODO: Add parameter for json filename 
    """ Flush saved data to server and clear local storage """
    try:
        with open("data.json", "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                object = ujson.loads(line)
                print("Flushing data:", object)
        uos.remove("data.json")
        print("data.json flushed successfully")                                             # TODO: Implement actual data transmission to server
    except Exception as e:
        if isinstance(e, OSError) and e.args[0] == uerrno.ENOENT:
            print("No data to flush (data.json not found)")
        else:
            print("Error reading data.json:", e)

def save_data(temp, hum, liters):                                                           # TODO: Add parameter for json filename and datetime
    """ Save measurement data to local file """
    try:
        data = {
            "temperature": str(temp) + "°C" if temp is not None else "N/A",
            "humidity": str(hum) + "%" if hum is not None else "N/A",
            "volume": str(liters) + "L" if liters is not None else "N/A",
        }
        with open("data.json", "a") as f:
            ujson.dump(data, f)
            f.write("\n")
        print("Data saved to data.json")
    except Exception as e:
        print("Error saving data:", e)

def send_data(temp, hum, liters):                                                           # TODO: Add parameters for datetime
    """ Send current measurement data to server """
    try:
        if temp is not None and hum is not None:
            print('Temperature: %3.1f °C' % temp)
            print('Humidity: %3.1f %%' % hum)
        else:
            print('Failed to read from temperature and humidity sensor.')                   # TODO: Implement actual data transmission to server
        
        print('Fuel oil volume: {:.2f} liters'.format(liters))
    except Exception as e:
        print("Error sending data:", e)

def go_sleep():
    """ Enter low power sleep mode (not implemented) """
    wifi.enable_connection = False
    sleep_ms(5000)                                                                          # TODO: Implement actual deep sleep mode for power saving

""" Main program loop """

state = "INIT"

try: 
    while True:
        if state == "INIT":
            print("[STATE] INIT")
            temp_sensor, level_sensor, tank, wifi = init_components()
            if None not in (temp_sensor, level_sensor, tank, wifi):
                state = "MEASURE"
            
        elif state == "MEASURE":
            print("[STATE] MEASURE")
            temp, hum, liters = measurment()
            if None not in (temp, hum, liters):
                state = "CONNECT"
                print("[STATE] CONNECT")

        elif state == "CONNECT":
            connection_result = connection()
            if connection_result is True:
                update_rtc()
                state = "FLUSH_DATA"
            elif connection_result is False:
                state = "SAVE_DATA"
            
        elif state == "FLUSH_DATA":
            print("[STATE] FLUSH_DATA")
            flush_data()

            state = "SEND_DATA"
        
        elif state == "SAVE_DATA":
            print("[STATE] SAVE_DATA")
            save_data(temp, hum, liters)

            state = "SEND_DATA"

        elif state == "SEND_DATA":
            print("[STATE] SEND_DATA")
            send_data(temp, hum, liters)

            state = "SLEEP"

        elif state == "SLEEP":
            print("[STATE] SLEEP")
            print("-------------------------------")
            go_sleep()

            state = "MEASURE"

except KeyboardInterrupt:
    print("Program interrupted by user")
    wifi.stop()
