"""
Docstring for main
"""
# General imports
import ssl 
# Import config and utility functions
from utils import *
from config import *
# Import sensor and wifi classes
from sensor_sr04 import SerialSR04
from sensor_dht22 import SensorDHT22
from volume_calculator import HexagonalPrismTank
from wifi_manager import WifiManager
from mqtt_manager import MqttManager
from secrets import mqtt_auth

""" Main program loop """

print("Starting IoT Oil Tank Device...")
print("Initializing components...")
temp_sensor = SensorDHT22(pin=DHT22_PIN, 
                           internal_pullup=False)

level_sensor = SerialSR04(tx_pin=TX_PIN, 
                          rx_pin=RX_PIN, 
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
                    user=mqtt_auth["user"],
                    password=mqtt_auth["password"], 
                    keepalive=60,
                    use_ssl=True,
                    ssl_params={"cert_reqs": ssl.CERT_NONE})
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
            success = flush_data(mqtt)

            if success:
                state = "SEND_DATA"
            else:
                print("[ERROR] Failed to flush data, will retry later")
                state = "SAVE_DATA"
        
        elif state == "SAVE_DATA":
            print("[STATE] SAVE_DATA")

            data_tank = data_to_json(date=current_date,
                                     time=current_time,
                                     quantity_l=liters)
            
            data_case = data_to_json(date=current_date,
                                     time=current_time,
                                     temp_c=temp, hum=hum)

            messages_to_buffer = [
                {"topic": MQTT_TOPIC_TANK, "payload": data_tank, "retain": False, "qos": 1},
                {"topic": MQTT_TOPIC_CASE, "payload": data_case, "retain": False, "qos": 1}
            ]

            success = save_data(messages=messages_to_buffer)
            if not success:
                print("[ERROR] Failed to save data")

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

            success = send_data(mqtt, messages=msg_to_send)
            if success:
                state = "SLEEP"
            else:
                print("[ERROR] Failed to send data")
                state = "SAVE_DATA"

        elif state == "SLEEP":
            print("[STATE] SLEEP")
            print("-------------------------------")
            mqtt.disconnect()
            go_sleep(wifi)

            state = "MEASURE"

except KeyboardInterrupt:
    print("Program interrupted by user")
    wifi.stop()
