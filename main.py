"""
Docstring for main
"""
from utils import *
# Import sensor and wifi classes
from sensor_sr04 import PulseSR04
from sensor_dht22 import SensorDHT22
from volume_calculator import HexagonalPrismTank
from wifi_manager import WifiManager
from mqtt_manager import MqttManager
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
WIFI_CONFIG = home
WIFI_SSID = WIFI_CONFIG["ssid"]
WIFI_PASSWORD = WIFI_CONFIG["pswd"]                                                         # TODO: Improve security
LED_POLARITY = "LO"
# MQTT parameters
MQTT_TOPIC_TANK = b"home/ext/oil_tank/measure/in_tank"
MQTT_TOPIC_CASE = b"home/ext/oil_tank/measure/in_case"

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
temp_sensor = SensorDHT22(pin=DHT22_PIN, 
                           internal_pullup=False)

level_sensor = PulseSR04(trig_pin=TRIGGER_PIN, 
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

mqtt = MqttManager(client_id=b"oil_tank_device_",
                    broker_host="192.168.0.223", 
                    broker_port=1883, 
                    keepalive=60)
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
                mqtt_result = mqtt.connect()
                update_rtc()
                current_date, current_time = localtime_brussels()
                state = "FLUSH_DATA"
            elif connection_result is False:
                current_date, current_time = localtime_brussels()
                state = "SAVE_DATA"
            
        elif state == "FLUSH_DATA":
            print("[STATE] FLUSH_DATA")
            flush_data(mqtt)

            state = "SEND_DATA"
        
        elif state == "SAVE_DATA":
            print("[STATE] SAVE_DATA")

            data_tank = data_to_json(date=current_date, time=current_time, quantity_l=liters)
            data_case = data_to_json(date=current_date, time=current_time, temp_c=temp, hum=hum)

            messages_to_buffer = [
                {"topic": MQTT_TOPIC_TANK, "payload": data_tank, "retain": False, "qos": 1},
                {"topic": MQTT_TOPIC_CASE, "payload": data_case, "retain": False, "qos": 1}
            ]

            save_data(messages=messages_to_buffer)
            state = "SLEEP"

        elif state == "SEND_DATA":
            print("[STATE] SEND_DATA")
            
            data_tank = data_to_json(date=current_date,
                                     time=current_time,
                                     quantity_l=liters)
            
            data_case = data_to_json(date=current_date,
                                     time=current_time,
                                     temp_c=temp,
                                     hum=hum)

            msg_to_send = [
                {"topic": MQTT_TOPIC_TANK, "payload": data_tank, "retain": False, "qos": 0},
                {"topic": MQTT_TOPIC_CASE, "payload": data_case, "retain": False, "qos": 0}
            ]

            send_data(mqtt, messages=msg_to_send)

            state = "SLEEP"

        elif state == "SLEEP":
            print("[STATE] SLEEP")
            print("-------------------------------")
            mqtt.disconnect()
            go_sleep(wifi)

            state = "MEASURE"

except KeyboardInterrupt:
    print("Program interrupted by user")
    wifi.stop()
