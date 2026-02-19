from machine import Pin, time_pulse_us
from utime import sleep, sleep_ms, sleep_us

DEFAULT_OFFSET = 20.0 # default sensor blind zone in cm

class BaseSR04:
    """
    Base class for SR04 ultrasonic distance sensor.

    Args:
        sensor_offset (float, optional): Offset in centimeters to account for sensor blind zone.
    
    Methods:
        read(samples: int = 5, delay: int = 50, temperature_c: float = 20.0) -> float:
            Read the distance from the sensor multiple times and return the median value.
    """
    def __init__(self, 
                 sensor_offset: float = DEFAULT_OFFSET) -> None:
        self.sensor_offset = sensor_offset

    def read(self, 
             samples: int = 5,
             delay: int = 50,
             temperature_c: float = 20.0) -> float:
        """
        Read the distance from the sensor multiple times and return the median value.
        
        :param samples: Number of samples to take
        :param delay: Delay between samples in milliseconds
        :param temperature_c: Temperature in degrees Celsius
        :return: Median distance from the sensor to the object in centimeters
        """
        distances = []
        attempts = 0
        max_attempts = samples * 2  # to avoid infinite loop in case of continuous failures

        while len(distances) < samples and attempts < max_attempts:
            distance = self.read_once(temperature_c)
            if distance >= 0:
                distances.append(distance)

            attempts += 1
            sleep_ms(delay)

        if not distances:
            raise RuntimeError("Sensor read timeout or invalid measurement")

        distances.sort()
        num_distances = len(distances)
        if num_distances % 2:
            # If odd number of samples
            return round(distances[num_distances // 2], 2)
        else:
            # If even number of samples
            mid = num_distances // 2
            return round((distances[mid - 1] + distances[mid]) / 2, 2)
        
class PulseSR04(BaseSR04):
    """
    Class to handle SR04 ultrasonic distance sensor using pulse measurement.

    NOTE: The operation mode (Pulse, Pulse low power, Serial) is determined by 
    the resistor value soldered at the R19/R27 location on the sensor board.
    Refer to the sensor documentation for configuration details 

    Args:
        trig_pin (int): GPIO pin connected to the TRIG pin of the sensor.
        echo_pin (int): GPIO pin connected to the ECHO pin of the sensor.
        sensor_offset (float, optional): Offset in centimeters to account for sensor blind zone.
        timeout_us (int, optional): Timeout for echo pulse measurement in microseconds. 
            Default is 30000us.
        low_power (bool, optional): If True, use a longer trigger pulse for low power mode. 
            Default is False.

    Methods:
        read_once(temperature_c: float = 20.0) -> float:
            Perform a single distance measurement and return the distance in centimeters.
    """
    def __init__(self,
                 trig_pin: int,
                 echo_pin: int,
                 low_power: bool = False,
                 timeout_us: int = 30000,
                 sensor_offset: float = DEFAULT_OFFSET) -> None:

        super().__init__(sensor_offset)
        self.trig = Pin(trig_pin, Pin.OUT)
        self.echo = Pin(echo_pin, Pin.IN)
        self.timeout_us = timeout_us

        # For low power mode, we can use a longer trigger pulse to ensure the sensor wakes up properly,
        self._trig_duration_us = 2000 if low_power else 10

        # cache for speed of sound based on temperature to avoid recalculating it every measurement
        self._cached_speed : float | None = None
        self._cached_temp_c : float | None = None
    
    def _trigger(self) -> None:
        """
        Send a trigger pulse to the ultrasonic sensor.

        :param duration_us: Duration of the trigger pulse in microseconds.
        :return: None
        """
        self.trig.value(0)
        sleep_us(2)
        self.trig.value(1)
        sleep_us(self._trig_duration_us)
        self.trig.value(0)
     
    def _measure_echo(self) -> float:
        """
        Measure the duration of the echo pulse.

        :return: Duration of the echo pulse in microseconds with negative value indicating timeout or error.
        """
        return time_pulse_us(self.echo, 1, self.timeout_us)
    
    def _calc_sound_speed(self,
                          temperature_c: float) -> float:
        """
        Calculate the speed of sound in air based on temperature.

        :param temperature_c: Temperature in degrees Celsius.
        :return: Speed of sound in cm/us
        """
        if self._cached_temp_c == temperature_c and self._cached_speed is not None:
            return self._cached_speed
        
        speed_m_s = 331.3 + (0.606 * temperature_c)     # speed of sound in m/s
        speed_cm_us = speed_m_s / 10_000                # convert to cm/us
        self._cached_speed = speed_cm_us
        self._cached_temp_c = temperature_c
        return speed_cm_us
    
    def _raw_to_distance(self,
                         duration_us: float,
                         sound_speed: float) -> float:
        """
        Convert the raw echo duration to distance in centimeters.

        :param duration_us: Duration of the echo pulse in microseconds.
        :param sound_speed: Speed of sound in cm/us.
        :return: Distance from the sensor to the object in centimeters.
        """
        if duration_us < 0:
            return -1.0  # indicate timeout or error
        
        return ((duration_us * sound_speed) / 2.0) - self.sensor_offset

    def read_once(self,
                  temperature_c: float = 20.0) -> float:
        """
        Read the distance from the sensor once and convert it to centimeters.
        
        :param temperature_c: Temperature in degrees Celsius.
        :return: Distance from the sensor to the object in centimeters.
        """
        self._trigger()
        duration = self._measure_echo()
        speed_cm_us = self._calc_sound_speed(temperature_c)
        return self._raw_to_distance(duration, speed_cm_us)            

if __name__ == "__main__":
    from volume_calculator import HexagonalPrismTank

    offset = 20.0 # sensor blind zone in cm

    LevelSensor = PulseSR04(trig_pin=3, echo_pin=4, sensor_offset=offset)
    tank = HexagonalPrismTank(250, 45.5, 59.5, 53, 74)

    # Perform the measurement and record the fuel oil level
    while True:
        distance = LevelSensor.read(temperature_c=22.8)

        print('distance from sensor: {:.2f} cm'.format(distance))
        liquid_height = tank.tank_height - distance
        print('Fuel oil height: {:.2f} cm'.format(liquid_height))
        liters = tank.to_liters(distance)
        # liters = tank.to_liters(liquid_height)
        print('Fuel oil capacity: {:.2f} L'.format(liters))
        sleep(5)