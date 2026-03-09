from secrets import home

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
WIFI_PASSWORD = WIFI_CONFIG["pswd"]
LED_POLARITY = "LO"

# MQTT parameters
MQTT_TOPIC_TANK = b"home/ext/oil_tank/measure/in_tank"
MQTT_TOPIC_CASE = b"home/ext/oil_tank/measure/in_case"

""" Pin definitions """
# Temperature and humidity sensor (DHT22)
DHT22_PIN = 2
# Ultrasonic level sensor (SR04)
TX_PIN = 20
RX_PIN = 21
# LED indicator for WiFi status
LED_PIN = 8