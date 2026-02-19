from machine import Pin
from utime import ticks_ms, ticks_diff
import dht

class SensorDHT22:
    """
    Class to handle DHT22 temperature and humidity sensor.
    
    Args:
        pin (int): GPIO pin connected to the DHT22 data pin.
        internal_pullup (bool, optional): Use the MCU's internal pull-up resistor.
            Defaults to False, an external pull-up resistor must be used (typically 4.7k to 10k ohms).
            If True, the pin is configured with an internal pull-up resistor.

    Attributes:
        sensor (dht.DHT22): The DHT22 sensor object.
        temperature (float | None): Last measured temperature in °C.
        humidity (float | None): Last measured humidity in %.

    Methods:
        read() -> tuple[float, float] | tuple[None, None]:
            Perform a measurement and return (temperature, humidity).
            If the sensor fails, (None, None) is returned.
    """

    MIN_INTERVAL = 2000 # Minimum interval between readings in milliseconds (required by DHT22)

    def __init__(self,
                 pin: int,
                 internal_pullup: bool = False) -> None:
        if internal_pullup:
            self.sensor = dht.DHT22(Pin(pin, Pin.IN, Pin.PULL_UP))
        else:
            self.sensor = dht.DHT22(Pin(pin, Pin.IN))
        
        self.temperature: float | None = None
        self.humidity: float | None = None

        self._last_read_time = ticks_ms() - self.MIN_INTERVAL  # Initialize to allow immediate first read

    def read(self) -> tuple[float, float] | tuple[None, None]:
        """
        Read temperature and humidity from the DHT22 sensor.
        
        :return: Tuple containing temperature in °C and humidity in %
        """
        now = ticks_ms()
        if ticks_diff(now, self._last_read_time) < self.MIN_INTERVAL:
            # If the minimum interval has not passed, return the last read values
            return self.temperature, self.humidity
        
        try:
            self.sensor.measure()                           # start measurement
            self.temperature = self.sensor.temperature()    # get temperature in °C
            self.humidity = self.sensor.humidity()          # get humidity in %
            self._last_read_time = now
        except OSError:
            print('Sensor reading failed.')
        finally:
            return round(self.temperature, 1), round(self.humidity, 1)
    
if __name__ == "__main__":
    from utime import sleep

    sensor = SensorDHT22(pin=2,
                         internal_pullup=False)

    while True:
        temp, hum = sensor.read()
        if temp is not None and hum is not None:
            print('Temperature: %3.1f °C' % temp)
            print('Humidity: %3.1f %%' % hum)
        else:
            print('Failed to read from sensor.')

        sleep(5)  # DHT22: maximum one measurement every 2 seconds