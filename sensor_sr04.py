from machine import Pin, time_pulse_us
from utime import sleep, sleep_us

SENSOR_OFFSET = 20  # sensor blind zone in cm

# Class to handle ultrasonic sensor for distance measurement
# INPUTS:
#   trig_pin: GPIO pin connected to the TRIG pin of the sensor
#   echo_pin: GPIO pin connected to the ECHO pin of the sensor
class SensorSR04:
    def __init__(self, trig_pin, echo_pin, sensor_offset):
        self.trig = Pin(trig_pin, Pin.OUT)
        self.echo = Pin(echo_pin, Pin.IN)
        self.sensor_offset = sensor_offset
        self.distance = 0.0

    # function to read the distance from the sensor and calculate the fuel oil level
    # INPUT:
    #   unit: The unit for the returned level ('cm' or 'li') 
    # OUTPUT:
    #   level: The fuel oil level in the specified unit
    def read(self):
        # Send a 10-microsecond pulse to trigger the measurement
        self.trig.value(0)
        sleep_us(2)
        self.trig.value(1)
        sleep_us(10)
        self.trig.value(0)

        # Measure the duration of the echo return in microseconds
        duration = time_pulse_us(self.echo, 1, 30000)  # 30000 us timeout

        # Calculate the distance in cm
        self.distance = ((duration * 0.0343) / 2) - self.sensor_offset

        return self.distance

if __name__ == "__main__":
    from volume_calculator import HexagonalPrismTank

    offset = 20.0 # sensor blind zone in cm

    LevelSensor = SensorSR04(15, 13, offset)
    tank = HexagonalPrismTank(250, 45.5, 59.5, 53, 74)

    # Perform the measurement and record the fuel oil level
    while True:
        distance = LevelSensor.read()

        print('distance from sensor: {:.2f} cm'.format(distance))
        liquid_height = tank.tank_height - distance
        print('Fuel oil height: {:.2f} cm'.format(liquid_height))
        liters = tank.to_liters(distance)
        print('Fuel oil capacity: {:.2f} L'.format(liters))
        sleep(5)