import network
import utime
import gc
import micropython
from machine import Pin, Timer
import socket

class WifiManager:
    STATE_DISCONNECTED = 'disconnected'
    STATE_CONNECTING   = 'connecting'
    STATE_CONNECTED    = 'connected'
    STATE_ERROR        = 'error'

    def __init__(self, ssid, password, led_pin="OFF", led_polarity="HI", max_retries=5, retry_delay=2, connect_timeout=20):
        self.ssid = ssid
        self.password = password
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.connect_timeout = connect_timeout

        self.enable_connection = False
        self.is_connected = False
        
        self.wlan = network.WLAN(network.STA_IF)
        self.wlan.active(True)
        gc.collect() # Clean up after WLAN activation

        self._led = None
        if led_pin != "OFF":
            self._led = Pin(led_pin, Pin.OUT)
            self._led_polarity_mask = 0 if led_polarity.upper() == "HI" else 1
            self._set_led(False)

        # Using a hardware timer for the FSM
        self._fsm_timer = Timer(0) 
        self._state = self.STATE_DISCONNECTED
        
        self._attempt_count = 0
        self._last_action_ms = 0
        self._blink_state = False
        self._tick_count = 0
        
        # RReference for the scheduler
        self._fsm_ref = self._fsm_logic

    def _set_led(self, state):
        if self._led:
            self._led.value(int(state) ^ self._led_polarity_mask)

    def _fsm_logic(self, _):
        """ Logic executed OUTSIDE interruption thanks to schedule """
        try:
            now = utime.ticks_ms()
            self._tick_count += 1
            
            # --- STATE: DISCONNECTED ---
            if self._state == self.STATE_DISCONNECTED:
                self._set_led(False)
                if self.enable_connection:
                    print("[WiFi] Starting procedure...")
                    self._attempt_count = 0
                    self._state = self.STATE_CONNECTING
                    self._last_action_ms = 0 # Force immediate connection

            # --- STATE: CONNECTING ---
            elif self._state == self.STATE_CONNECTING:
                # 1. Blink management
                self._set_led((self._tick_count // 5) % 2 == 0)

                # 2. If not currently attempting, start an attempt
                if not self.wlan.isconnected() and utime.ticks_diff(now, self._last_action_ms) > (self.retry_delay * 1000):
                    if self._attempt_count < self.max_retries:
                        gc.collect() # Clean up before connection attempt
                        self.wlan.disconnect() # Ensure we start clean
                        try :
                            self.wlan.connect(self.ssid, self.password)
                            self._attempt_count += 1
                            print(f"[WiFi] Attempt {self._attempt_count}/{self.max_retries}")
                            self._last_action_ms = now
                        except Exception as e:
                            print(f"[WiFi Error] Driver currently busy: {e}")
                            pass
                    else:
                        print("[WiFi] Total failure.")
                        self._state = self.STATE_ERROR
                        self._last_action_ms = now

                # 3. Success check
                if self.wlan.isconnected():
                    # Check if we have an IP
                    if self.wlan.ifconfig()[0] != '0.0.0.0':
                        print(f"[WiFi] Connected! IP: {self.wlan.ifconfig()[0]}")
                        self.is_connected = True
                        self._state = self.STATE_CONNECTED
                        self._set_led(True)

            # --- STATE: CONNECTED (Monitoring) ---
            elif self._state == self.STATE_CONNECTED:
                self._set_led(True)
                if not self.wlan.isconnected():
                    print("[WiFi] Link lost!")
                    self.is_connected = False
                    self._state = self.STATE_DISCONNECTED
                    gc.collect() # Clean up after disconnection

            # --- STATE: ERROR (Pause before reset) ---
            elif self._state == self.STATE_ERROR:
                # Fast blink
                self._set_led(self._tick_count % 2 == 0)
                if utime.ticks_diff(now, self._last_action_ms) > 20000: # 20s rest
                    self._state = self.STATE_DISCONNECTED

        except Exception as e:
            # If an error occurs, we do NOT kill the timer, we just print
            print(f"[WiFi Critical Error] {e}")

    def _timer_callback(self, t):
        # We do NOTHING here, we delegate everything to the scheduler
        micropython.schedule(self._fsm_ref, 0)

    def start(self):
        print("[WiFi] Manager started")
        # We trigger the measurement every 200ms to give time to the SDK
        self._fsm_timer.init(period=200, mode=Timer.PERIODIC, callback=self._timer_callback)

    def stop(self):
        self._fsm_timer.deinit()
        self.wlan.disconnect()
        self._set_led(False)
        self._state = self.STATE_DISCONNECTED
    
    def check_internet(self, host="8.8.8.8", port=53, timeout=3):
        if not self.is_connected:
            return False
        try:
            # We do not even go through DNS (we use the direct IP)
            # to avoid blocking if the router's DNS server fails.
            gc.collect() # Clean up before socket operation
            addr = (host, port)
            s = socket.socket()
            s.settimeout(timeout)
            s.connect(addr) # Brutal connection attempt
            s.close()
            self.has_connectivity = True
            return True
        except:
            gc.collect() # Clean up after failure
            self.has_connectivity = False
            return False

# --------------------------------------------------------------------------------------------------------

if __name__ == "__main__":
    from logging import *
    from utime import sleep, ticks_ms, ticks_diff
    
    config = hotspot
    wifi = WifiManager(config["ssid"], config["pswd"], led_pin=8, led_polarity="LO")
    
    wifi.start()
    wifi.enable_connection = True

    last_tick = ticks_ms()
    try:
        while True:
            if ticks_diff(ticks_ms(), last_tick) >= 1000:
                last_tick = ticks_ms()
                print("Main")
                if wifi.is_connected:
                    if wifi.check_internet():
                        print(" - Internet reachable")
                    else:
                        print(" - No internet connectivity")
    except KeyboardInterrupt:
        print("Stopping WiFi Manager by user")
        wifi.stop()