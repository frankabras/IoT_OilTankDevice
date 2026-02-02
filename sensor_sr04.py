from machine import Pin, time_pulse_us
from utime import sleep, sleep_ms, sleep_us

class SensorSR04:
    """
    Class to handle HC-SR04 ultrasonic distance sensor.
    INPUTS:
        trig_pin: GPIO pin connected to the TRIG pin of the sensor
        echo_pin: GPIO pin connected to the ECHO pin of the sensor
        sensor_offset: Offset in cm to account for the sensor's blind zone
    """
    def __init__(self, trig_pin: int, echo_pin: int, sensor_offset: float) -> None:
        self.trig = Pin(trig_pin, Pin.OUT)
        self.echo = Pin(echo_pin, Pin.IN)
        self.sensor_offset = sensor_offset
        self.timeout_us = 30000  # timeout for echo pulse in microseconds

        # cache for speed of sound based on temperature to avoid recalculating it every measurement
        self._cached_speed : float | None = None
        self._cached_temp_c : float | None = None

    def _trigger(self) -> None:
        """
        Send a trigger pulse to the ultrasonic sensor.
        :param self: Instance of the SensorSR04 class
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

        :param self: Instance of the SensorSR04 class
        :return: Duration of the echo pulse in microseconds with negative value indicating timeout or error
        :rtype: int 
        """
        return time_pulse_us(self.echo, 1, self.timeout_us)
    
    def _calc_sound_speed(self, temperature_c: float) -> float:
        """
        Calculate the speed of sound in air based on temperature.

        :param self: Instance of the SensorSR04 class
        :param temperature_c: Temperature in degrees Celsius
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
    
    def _raw_to_distance(self, duration_us: int, sound_speed: float) -> float:
        """
        Convert the raw echo duration to distance in centimeters.

        :param self: Instance of the SensorSR04 class
        :param duration_us: Duration of the echo pulse in microseconds
        :param sound_speed: Speed of sound in cm/us
        :return: Distance from the sensor to the object in centimeters
        :rtype: float
        """
        if duration_us < 0:
            return -1.0  # indicate timeout or error
        
        return ((duration_us * sound_speed) / 2.0) - self.sensor_offset

    def read_once(self, temperature_c: float = 20.0) -> float:
        """
        Read the distance from the sensor once and convert it to centimeters.
        
        :param self: Instance of the SensorSR04 class
        :param temperature_c: Temperature in degrees Celsius
        :return: Distance from the sensor to the object in centimeters
        :rtype: float
        """
        self._trigger()
        duration = self._measure_echo()
        speed_cm_us = self._calc_sound_speed(temperature_c)
        return self._raw_to_distance(duration, speed_cm_us)
    
    def read(self, samples: int = 5, delay: int = 50, temperature_c: float = 20.0) -> float:
        """
        Read the distance from the sensor multiple times and return the median value.
        
        :param self: Instance of the SensorSR04 class
        :param samples: Number of samples to take
        :param delay: Delay between samples in milliseconds
        :param temperature_c: Temperature in degrees Celsius
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
            # If odd number of samples, return the median
            return distances[samples // 2]
        else:
            # If even number of samples
            mid = samples // 2
            return (distances[mid - 1] + distances[mid]) / 2

if __name__ == "__main__":
    from volume_calculator import HexagonalPrismTank

    offset = 20.0 # sensor blind zone in cm

    LevelSensor = SensorSR04(15, 13, offset)
    tank = HexagonalPrismTank(250, 45.5, 59.5, 53, 74)

    # Perform the measurement and record the fuel oil level
    while True:
        distance = LevelSensor.read(temperature_c=20.0)

        print('distance from sensor: {:.2f} cm'.format(distance))
        liquid_height = tank.tank_height - distance
        print('Fuel oil height: {:.2f} cm'.format(liquid_height))
        liters = tank.to_liters(distance)
        # liters = tank.to_liters(liquid_height)
        print('Fuel oil capacity: {:.2f} L'.format(liters))
        sleep(5)