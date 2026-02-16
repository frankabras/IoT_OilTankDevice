"""
Docstring for main
"""
from utils import *
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

""" Main program loop """

print("Starting IoT Oil Tank Device...")
print("Initializing components...")
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
print("Initialization complete. Entering main loop...")

wifi.start()
state = "MEASURE"

try: 
    while True:            
        if state == "MEASURE":
            print("[STATE] MEASURE")
            temp, hum, liters = measurment(temp_sensor, level_sensor, tank)
            if None not in (temp, hum, liters):
                state = "CONNECT"
                print("[STATE] CONNECT")

        elif state == "CONNECT":
            connection_result = connection(wifi)
            if connection_result is True:
                update_rtc()
                current_date, current_time = localtime_brussels()
                state = "FLUSH_DATA"
            elif connection_result is False:
                current_date, current_time = localtime_brussels()
                state = "SAVE_DATA"
            
        elif state == "FLUSH_DATA":
            print("[STATE] FLUSH_DATA")
            flush_data()

            state = "SEND_DATA"
        
        elif state == "SAVE_DATA":
            print("[STATE] SAVE_DATA")
            save_data(current_date, current_time, temp, hum, liters)

            state = "SEND_DATA"                                                             # NOTE: Change to "SLEEP" when testing is complete to avoid sending data when offline

        elif state == "SEND_DATA":
            print("[STATE] SEND_DATA")
            send_data(current_date, current_time, temp, hum, liters)

            state = "SLEEP"

        elif state == "SLEEP":
            print("[STATE] SLEEP")
            print("-------------------------------")
            go_sleep(wifi)

            state = "MEASURE"

except KeyboardInterrupt:
    print("Program interrupted by user")
    wifi.stop()
