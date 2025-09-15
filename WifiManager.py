import network
import urequests
from utime import sleep
from machine import Pin

from logging import *

# WifiManager class to handle WiFi connections and connectivity checks.
# INPUTS:
#   ssid: WiFi SSID
#   password: WiFi password
#   led_pin: Pin for LED indicator, set to "OFF" to disable
#   **kwargs:
#           - led_polarity: Indicates if the LED is active HIGH ("HI") or LOW ("LO"). Default is "HI".
class WifiManager:
    def __init__(self, ssid, password, led_pin="OFF", **kwargs):
        self.ssid           = ssid                              # wifi credentials
        self.password       = password
        self.connected      = False                             # connection status
        self.connectivity   = False                             # internet connectivity status
        self.wlan           = network.WLAN(network.STA_IF)      # initialize WLAN in station mode
        
        self.wlan.active(True)                                  # activate the WLAN interface

        if not led_pin == "OFF":                                # setup LED if not disabled  
            if led_pin == "PICO":                               # setup led from board type 
                self.led = Pin(25, Pin.OUT)
                self.led_polarity = "HI"
                self.led.value(True)
            elif led_pin == "PICOW":
                self.led = Pin("LED", Pin.OUT)
                self.led_polarity = "HI"
                self.led.value(True) 
            else:                                               # or setup led from pin number
                pin = int(led_pin) 
                self.led = Pin(pin, Pin.OUT)
                self.led_polarity = kwargs.get("led_polarity", "HI") # default polarity is "HI"
                if self.led_polarity == "LO":
                    self.led.value(False)
                else:
                    self.led.value(True)                         
        else:
            self.led = None 

        # Autres fonctions à développer:
        # - gestion des erreurs de connexion
        # - gestion mqtt
    
    # function to disconnect device from WiFi
    def disconnect(self):
        self.wlan.disconnect()
        self.connected = False
        if self.led is not None: 
            # LED on when disconnected             
            if self.led_polarity == "LO": 
                self.led.value(True) 
            else:                            
                self.led.value(False)
        print("Disconnected from WiFi")

    # function to connect device to WiFi
    # INPUTS:
    #   retry: number of connection attempts (default is 10)
    # OUTPUTS:
    #   self.connected: Boolean indicating whether the connection was successful.
    def connect(self, retry=10): 
        self.wlan.connect(self.ssid, self.password)     # attempt to connect to WiFi
        for attempt in range(retry):                    # try to connect for 'retry' times
            if self.wlan.isconnected():                 # check internet connectivity
                self.connected = True
                print("Connected to WiFi!")
                print(self.wlan.ifconfig())
                break                                   # exit loop if connected
            self.connected = False
            print(f"Connecting...{attempt+1}/{retry}")
            sleep(1)
        else:                                           # executed if the loop is not broken (connection failed)
            print("Connection failure")

        if self.led is not None:
            # LED off if connected
            if self.led_polarity == "LO":
                self.led.value(self.connected)
            else:
                self.led.value(not self.connected)
        
        return self.connected

    # function to check internet connectivity by sending a HEAD request to a specified URL
    # HEAD: requests only retrieve headers, not the full content
    # INPUTS:
    #   url: The URL to check (default is "http://www.google.com")
    #   timeout: The timeout for the request in seconds (default is 5)
    # OUTPUTS:
    #   self.connectivity: Boolean indicating whether the connection was successful.
    def check_connectivity(self, url="http://www.google.com", timeout=5):
        connectivity = False
        try:                                                    # try to connect to the specified URL to check internet connectivity
            response = urequests.head(url, timeout=timeout)
            if response.status_code == 200:                     # check if the response status code is 200 (OK)
                print(f"Successfully connected to {url} (Status: {response.status_code})")
                self.connectivity = True
            else:
                print(f"Request to {url} failed (Status: {response.status_code})")
                self.connectivity = False
            response.close()    
        except Exception as e:
            print(f"Error during request to {url}: {e}")
            self.connectivity = False
        
        return self.connectivity

# --------------------------------------------------------------------------------------------------------------------------------------- __name__ == "__main__":
if __name__ == "__main__":
    config = hotspot
    wifi = WifiManager(config["ssid"], config["pswd"], led_pin="PICOW")
    
    while True:
        try:
            wifi.connect()
            if wifi.connected:
                wifi.check_connectivity()
            sleep(5)
        except KeyboardInterrupt:
            print("Program interrupted")
            wifi.disconnect()                           # wifi disconnection
            break