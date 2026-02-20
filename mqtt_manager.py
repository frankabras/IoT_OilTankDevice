import ubinascii
from machine import unique_id
from utime import sleep_ms
from umqtt.simple import MQTTClient

class MqttManager:
    def __init__(self,
                 client_id: bytes,
                 broker_host: str,
                 broker_port: int,
                 keepalive: int = 60) -> None:
        # Generate a unique client ID by appending the device's unique ID to the provided client_id prefix
        self._client_id = client_id + ubinascii.hexlify(unique_id())
        self._broker_host = broker_host
        self._broker_port = broker_port
        self._keepalive = keepalive
        self._client = None
        
    
    def connect(self,
                retry: int = 3,
                retry_delay_ms: int = 500) -> bool:                                    # TODO: evaluate optimal retry delay and count
        for attempt in range(retry):
            self._client = MQTTClient(self._client_id,
                                      self._broker_host,
                                      self._broker_port,
                                      keepalive=self._keepalive)
            try:
                self._client.connect()
                print("[MQTT] Connected to broker.")
                return True
            except Exception as e:
                print("[MQTT] connection failed:", e)
                if attempt < retry - 1:
                    sleep_ms(retry_delay_ms)
        self._client = None
        return False
    
    def disconnect(self) -> None:
        if self._client is not None:
            try:
                self._client.disconnect()
            finally:
                self._client = None
                print("[MQTT] Disconnected from broker.")
        
    def publish(self, 
                topic: bytes,
                message: bytes,
                retain: bool = False,
                qos: int = 0) -> bool:
        if self._client is None:
            if not self.connect():
                print("[MQTT] Publish failed: Not connected to broker.")
                return False
        try:
            self._client.publish(topic, message, retain=retain, qos=qos)
            print(f"[MQTT] Published to {topic.decode()}")
            return True
        except Exception as e:
            print("[MQTT] Publish failed:", e)
            return False

if __name__ == "__main__":
    from wifi_manager import WifiManager
    from logging import *

    config = hotspot
    wifi = WifiManager(config["ssid"], config["pswd"], led_pin=8, led_polarity="LO", verbose=True)
    mqtt = MqttManager(client_id=b"test_client_", 
                       broker_host="192.168.0.223", 
                       broker_port=1883, 
                       keepalive=60)
    
    wifi.start()
    wifi.enable_connection = True

    while True:
        if wifi.is_connected:
            if mqtt.connect():
                mqtt.publish(topic=b"test/topic", message=b"Hello from ESP32")
                mqtt.disconnect()
            else:
                print("Failed to connect to MQTT broker.")
        else:
            print("WiFi not connected.")
        sleep_ms(5000)  # Wait before retrying