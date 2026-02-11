from machine import Pin, time_pulse_us
from utime import sleep, sleep_ms, sleep_us

class SensorSR04:
    """
    Class to handle HC-SR04 ultrasonic distance sensor.
    
    Args:
        trig_pin (int): GPIO pin connected to the TRIG pin of the sensor.
        echo_pin (int): GPIO pin connected to the ECHO pin of the sensor.
        sensor_offset (float): Offset in centimeters to account for sensor blind zone.
        timeout_us (int, optional): Timeout for echo pulse measurement in microseconds. Default is 30000us.
    
    Attributes:
        trig (Pin): Pin object for the TRIG pin.
        echo (Pin): Pin object for the ECHO pin.
        sensor_offset (float): Offset in centimeters to account for sensor blind zone.
        timeout_us (int): Timeout for echo pulse measurement in microseconds.

    Methods:
        read_once(temperature_c: float = 20.0) -> float:
            Perform a single distance measurement and return the distance in centimeters.
        read(samples: int = 5, delay: int = 50, temperature_c: float = 20.0) -> float:
            Perform multiple distance measurements and return the median distance in centimeters.
    """
    def __init__(self,
                 trig_pin: int,
                 echo_pin: int,
                 sensor_offset: float,
                 timeout_us: int = 30000) -> None:
        self.trig = Pin(trig_pin, Pin.OUT)
        self.echo = Pin(echo_pin, Pin.IN)
        self.sensor_offset = sensor_offset
        self.timeout_us = timeout_us

        # cache for speed of sound based on temperature to avoid recalculating it every measurement
        self._cached_speed : float | None = None
        self._cached_temp_c : float | None = None

    def _trigger(self) -> None:
        """
        Send a trigger pulse to the ultrasonic sensor.

        :return: None
        :rtype: None
        """
        # Send a 10-microsecond pulse to trigger the measurement
        self.trig.value(0)
        sleep_us(2)
        self.trig.value(1)
        sleep_us(10)
        self.trig.value(0)
     
    def _measure_echo(self) -> int:
        """
        Measure the duration of the echo pulse.

        :return: Duration of the echo pulse in microseconds with negative value indicating timeout or error
        :rtype: int 
        """
        return time_pulse_us(self.echo, 1, self.timeout_us)
    
    def _calc_sound_speed(self,
                          temperature_c: float) -> float:
        """
        Calculate the speed of sound in air based on temperature.

        :param temperature_c: Temperature in degrees Celsius
        :type temperature_c: float
        :return: Speed of sound in cm/us
        :rtype: float
        """
        if self._cached_temp_c == temperature_c and self._cached_speed is not None:
            return self._cached_speed
        
        speed_m_s = 331.3 + (0.606 * temperature_c)     # speed of sound in m/s
        speed_cm_us = speed_m_s / 10_000                # convert to cm/us
        self._cached_speed = speed_cm_us
        self._cached_temp_c = temperature_c
        return speed_cm_us
    
    def _raw_to_distance(self,
                         duration_us: int,
                         sound_speed: float) -> float:
        """
        Convert the raw echo duration to distance in centimeters.

        :param duration_us: Duration of the echo pulse in microseconds
        :type duration_us: int
        :param sound_speed: Speed of sound in cm/us
        :type sound_speed: float
        :return: Distance from the sensor to the object in centimeters
        :rtype: float
        """
        if duration_us < 0:
            return -1.0  # indicate timeout or error
        
        return ((duration_us * sound_speed) / 2.0) - self.sensor_offset

    def read_once(self,
                  temperature_c: float = 20.0) -> float:
        """
        Read the distance from the sensor once and convert it to centimeters.
        
        :param temperature_c: Temperature in degrees Celsius
        :type temperature_c: float
        :return: Distance from the sensor to the object in centimeters
        :rtype: float
        """
        self._trigger()
        duration = self._measure_echo()
        speed_cm_us = self._calc_sound_speed(temperature_c)
        return self._raw_to_distance(duration, speed_cm_us)
    
    def read(self, 
             samples: int = 5,
             delay: int = 50,
             temperature_c: float = 20.0) -> float:
        """
        Read the distance from the sensor multiple times and return the median value.
        
        :param samples: Number of samples to take
        :type samples: int
        :param delay: Delay between samples in milliseconds
        :type delay: int
        :param temperature_c: Temperature in degrees Celsius
        :type temperature_c: float
        :return: Median distance from the sensor to the object in centimeters
        :rtype: float
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
        if samples % 2:
            # If odd number of samples
            return distances[samples // 2]
        else:
            # If even number of samples
            mid = samples // 2
            return (distances[mid - 1] + distances[mid]) / 2

if __name__ == "__main__":
    from volume_calculator import HexagonalPrismTank

    offset = 20.0 # sensor blind zone in cm

    LevelSensor = SensorSR04(3, 4, offset)
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