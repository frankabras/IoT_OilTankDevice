import network
import utime
import gc
import micropython
from machine import Pin, Timer
import socket

class WifiManager:
    """
    Class to manage WiFi connections.

    Args:
        ssid (str): WiFi SSID to connect to.
        password (str): WiFi password.
        led_pin (int | str, optional): GPIO pin for LED indicator. If "OFF", no LED is used. Defaults to "OFF".
        led_polarity (str, optional): Polarity of the LED, either "HI" for active high or "LO" for active low. Defaults to "HI".
        max_retries (int, optional): Maximum number of connection attempts before giving up. Defaults to 5.
        retry_delay (int, optional): Delay in seconds between connection attempts. Defaults to 2.
        connect_timeout (int, optional): Timeout in seconds for each connection attempt. Defaults to 20.

    Attributes:
        ssid (str): WiFi SSID to connect to.
        password (str): WiFi password.
        max_retries (int): Maximum number of connection attempts before giving up.
        retry_delay (int): Delay in seconds between connection attempts.
        connect_timeout (int): Timeout in seconds for each connection attempt.
        enable_connection (bool): Flag to enable or disable the connection process.
        is_connected (bool): Flag indicating whether the device is currently connected to WiFi.
        has_connectivity (bool): Flag indicating whether the device has internet connectivity.
        connection_failed (bool): Flag indicating whether the connection process has failed after maximum retries.
    
    Methods:
        start() -> None:
            Start the WiFi manager and its internal FSM.
        stop() -> None:
            Stop the WiFi manager and disconnect from WiFi.
        check_internet(host: str = "8.8.8.8") -> bool:
            Check if the internet is reachable by pinging a host. Defaults to Google's DNS server.
    """

    STATE_DISCONNECTED = 'disconnected'
    STATE_CONNECTING   = 'connecting'
    STATE_CONNECTED    = 'connected'
    STATE_ERROR        = 'error'

    def __init__(self, ssid: str, 
                 password: str, led_pin: str = "OFF",
                 led_polarity: str = "HI",
                 max_retries: int = 5,
                 retry_delay: int = 2,
                 connect_timeout: int = 20,
                 max_error_count: int = 3,
                 verbose: bool = True) -> None:
        # Control flags and status indicators
        self.enable_connection = False
        self.is_connected = False
        self.has_connectivity = False
        self.connection_failed = False

        # Configuration parameters
        self._ssid = ssid
        self._password = password
        self._max_retries = max_retries
        self._retry_delay = retry_delay
        self._connect_timeout = connect_timeout
        self._max_error_count = max_error_count
        self._verbose = verbose

        # Internal state variables for FSM and LED management
        self._attempt_count = 0
        self._last_action_ms = 0
        self._error_count = 0
        self._blink_state = False
        self._tick_count = 0

        # Initialize WLAN in station mode
        self.wlan = network.WLAN(network.STA_IF)
        self.wlan.active(True)
        gc.collect() # Clean up after WLAN activation

        # LED setup
        self._led = None
        if led_pin != "OFF":
            self._led = Pin(led_pin, Pin.OUT)
            self._led_polarity_mask = 0 if led_polarity.upper() == "HI" else 1
            self._set_led(False)
        
        # FSM setup
        self._fsm_timer = Timer(0) 
        self._state = self.STATE_DISCONNECTED
        self._fsm_ref = self._fsm_logic # Reference for the scheduler

    def _set_led(self, state: bool) -> None:
        """
        Set the LED state.

        :param state: The desired LED state (True for on, False for off).
        :type state: bool
        :return: None
        :rtype: None
        """
        if self._led:
            self._led.value(int(state) ^ self._led_polarity_mask)

    def _fsm_logic(self, _) -> None:
        """
        Finite State Machine logic for WiFi management.

        :param _: Placeholder for timer callback parameter.
        :type _: any
        :return: None
        :rtype: None
        """
        try:
            now = utime.ticks_ms()
            self._tick_count += 1
            
            # --- STATE: DISCONNECTED ---
            if self._state == self.STATE_DISCONNECTED:
                gc.collect() # Clean up before connection attempt
                self.wlan.disconnect()
                self._set_led(True)
                if self.enable_connection:
                    if self._verbose: print("[WiFi] Connection enabled, starting connection procedure...")
                    self._attempt_count = 0
                    self.connection_failed = False
                    self._state = self.STATE_CONNECTING
                    self._last_action_ms = 0 # Force immediate connection

            # --- STATE: CONNECTING ---
            elif self._state == self.STATE_CONNECTING:
                # 1. Blink management
                self._set_led((self._tick_count // 5) % 2 == 0)

                # 2. If not currently attempting, start an attempt
                if not self.wlan.isconnected() and utime.ticks_diff(now, self._last_action_ms) > (self._retry_delay * 1000):
                    if self._attempt_count < self._max_retries:
                        gc.collect() # Clean up before connection attempt
                        self.wlan.disconnect() # Ensure we start clean
                        try :
                            self.wlan.connect(self._ssid, self._password)
                            self._attempt_count += 1
                            if self._verbose: print(f"[WiFi] Attempt {self._attempt_count}/{self._max_retries}")
                            self._last_action_ms = now
                        except Exception as e:
                            if self._verbose: print(f"[WiFi Error] Driver currently busy: {e}")
                            pass
                    elif not self.enable_connection:
                        self._error_count = 0
                        self._state = self.STATE_DISCONNECTED
                        self._last_action_ms = now
                        if self._verbose: print("[WiFi] Connection disabled.")
                    else:
                        if self._verbose: print("[WiFi] Total failure.")
                        self._error_count += 1
                        self._state = self.STATE_ERROR
                        self._last_action_ms = now

                # 3. Success check
                if self.wlan.isconnected():
                    # Check if we have an IP
                    if self.wlan.ifconfig()[0] != '0.0.0.0':
                        print(f"[WiFi] Connected! IP: {self.wlan.ifconfig()[0]}")
                        self.is_connected = True
                        self._error_count = 0
                        self._state = self.STATE_CONNECTED
                        self._set_led(True)

            # --- STATE: CONNECTED (Monitoring) ---
            elif self._state == self.STATE_CONNECTED:
                self._set_led(False)
                if not self.wlan.isconnected():
                    if self._verbose: print("[WiFi] Link lost!")
                    self.is_connected = False
                    self._state = self.STATE_DISCONNECTED
                    gc.collect() # Clean up after disconnection
                elif not self.enable_connection:
                    self._error_count = 0
                    self._state = self.STATE_DISCONNECTED
                    if self._verbose: print("[WiFi] Connection disabled.")

            # --- STATE: ERROR (Pause before reset) ---
            elif self._state == self.STATE_ERROR:
                # Fast blink
                self._set_led(self._tick_count % 2 == 0)
                if self._error_count >= self._max_error_count:
                    if self._verbose: print("[WiFi] Maximum error count reached. Stopping attempts.")
                    self._error_count = 0
                    self.enable_connection = False
                    self.connection_failed = True
                
                if utime.ticks_diff(now, self._last_action_ms) > 10000: # 10s rest
                    self._state = self.STATE_DISCONNECTED
                elif not self.enable_connection:
                    self._error_count = 0
                    self._state = self.STATE_DISCONNECTED
                    if self._verbose: print("[WiFi] Connection disabled.")

        except Exception as e:
            # If an error occurs, we do NOT kill the timer, we just print
            if self._verbose: print(f"[WiFi Critical Error] {e}")

    def _timer_callback(self, t: Timer) -> None:
        """
        Timer callback for the WiFi manager.
        
        :param t: The timer object triggering the callback.
        :type t: Timer
        :return: None
        :rtype: None
        """
        # We do NOTHING here, we delegate everything to the scheduler
        micropython.schedule(self._fsm_ref, 0)

    def start(self) -> None:
        """
        Start the WiFi manager FSM.
        
        :return: None
        :rtype: None
        """
        if self._verbose: print("[WiFi] Manager started")
        # We trigger the measurement every 200ms to give time to the SDK
        self._fsm_timer.init(period=200, mode=Timer.PERIODIC, callback=self._timer_callback)

    def stop(self) -> None:
        """
        Stop the WiFi manager FSM.
        
        :return: None
        :rtype: None
        """
        gc.collect() # Clean up before stopping
        if self._verbose: print("[WiFi] Manager stopped")

        self._fsm_timer.deinit()
        self.wlan.disconnect()
        self._set_led(False)
        self._state = self.STATE_DISCONNECTED
    
    def check_internet(self,
                       host: str = "8.8.8.8",
                       port: int = 53,
                       timeout: int = 3) -> bool:
        """
        Check internet connectivity by attempting to connect to a specified host and port.
        
        :param host: The host to connect to (default is Google's DNS server 8.8.8.8).
        :type host: str
        :param port: The port to connect to (default is 53, DNS service).
        :type port: int
        :param timeout: The timeout for the connection attempt in seconds (default is 3).
        :type timeout: int
        :return: True if the internet is reachable, False otherwise.
        :rtype: bool
        """
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
    wifi = WifiManager(config["ssid"], config["pswd"], led_pin=8, led_polarity="LO", verbose=True)
    
    wifi.start()
    wifi.enable_connection = True

    last_tick = ticks_ms()
    try:
        while True:
            if ticks_diff(ticks_ms(), last_tick) >= 1000:
                last_tick = ticks_ms()
                # print("Main")
                if wifi.is_connected:
                    if wifi.check_internet():
                        print(" - Internet reachable")
                    else:
                        print(" - No internet connectivity")
                elif wifi.connection_failed:
                    if input("Retry connection ? (y/n) : ").lower() == 'y':
                        wifi.enable_connection = True
                        last_tick = ticks_ms() # Reset timer to avoid immediate retry

    except KeyboardInterrupt:
        print("Stopping WiFi Manager by user")
        wifi.stop()