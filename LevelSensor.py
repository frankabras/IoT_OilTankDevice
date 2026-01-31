from machine import Pin, time_pulse_us
from utime import sleep, sleep_us

# Tank data and dimensions
"""
Tank divided into 3 parts (side view):
- Lower part:      trapezoidal shape on the small side
                   (from 0 to 45.5cm = 45.5cm)
- Central part:    rectangular shape
                   (from 45.5 to 105cm = 59.5cm)
- Upper part:      trapezoidal shape on the large side
                   (from 105 to 150.5cm = 45.5cm)
"""
TANK_LEVEL_1 = 45.5  # end height of the first stage
TANK_LEVEL_2 = 105  # end height of the second stage
TANK_HEIGHT = 150.5  # actual height of the tank in cm (full)
TANK_LENGTH = 250  # actual length of the tank in cm
GRADUATIONS_HEIGHT = 147.5  # max filling height of the tank in cm (capacity = 2500L)

# Data for calculating the remaining volume
SMALL_SIDE = 53  # small side of the trapezoidal parts
LARGE_SIDE = 74  # large side of the trapezoid and width of the rectangle (i.e. separation between the two)
TRAPEZE_CAPACITY = 720  # capacity in liters of the trapezoidal parts
RECTANGLE_CAPACITY = 1100  # capacity in liters of the rectangular part
CAPACITY_OFFSET = 40  # capacity in liters between the top of the tank and the start of the graduations
SENSOR_OFFSET = 20  # sensor blind zone in cm
TOTAL_CAPACITY = ((2 * TRAPEZE_CAPACITY) + RECTANGLE_CAPACITY) - CAPACITY_OFFSET

# Class to handle ultrasonic sensor for distance measurement
# INPUTS:
#   trig_pin: GPIO pin connected to the TRIG pin of the sensor
#   echo_pin: GPIO pin connected to the ECHO pin of the sensor
class Sensor_Utlrason:
    def __init__(self, trig_pin, echo_pin):
        self.trig = Pin(trig_pin, Pin.OUT)
        self.echo = Pin(echo_pin, Pin.IN)

        self.level = 0.0

    # function to read the distance from the sensor and calculate the fuel oil level
    # INPUT:
    #   unit: The unit for the returned level ('cm' or 'li') 
    # OUTPUT:
    #   level: The fuel oil level in the specified unit
    def read(self, unit='cm'):
        # Send a 10-microsecond pulse to trigger the measurement
        self.trig.value(0)
        sleep_us(2)
        self.trig.value(1)
        sleep_us(10)
        self.trig.value(0)

        # Measure the duration of the echo return in microseconds
        duration = time_pulse_us(self.echo, 1, 30000)  # 30000 us timeout

        # Calculate the distance in cm
        distance = ((duration * 0.0343) / 2) - SENSOR_OFFSET
        self.level = TANK_HEIGHT - distance
        if self.level <= 0.0:
            self.level = 0.0

        if unit == 'cm':
            return self.level
        elif unit == 'li':
            return self.convert_to_liters()
    
    # function to convert the fuel oil level in cm to volume in liters
    # OUTPUT:
    #   volume: The fuel oil volume in liters
    def convert_to_liters(self):
        volume = 0
        if self.level <= TANK_LEVEL_1:
            # Fuel only in part 1
            surface = SMALL_SIDE + (LARGE_SIDE - SMALL_SIDE) / TANK_LEVEL_1 * self.level
            volume = (1/2 * (SMALL_SIDE + surface) * self.level * TANK_LENGTH)/1000  # /1000 for capacity in liters
        elif (self.level > TANK_LEVEL_1) & (self.level <= TANK_LEVEL_2):
            # Part 1 filled + Part 2 partially filled
            self.level = self.level - TANK_LEVEL_1
            volume = (self.level * LARGE_SIDE * TANK_LENGTH)/1000  # /1000 for capacity in liters
            volume = volume + TRAPEZE_CAPACITY
        elif (self.level > TANK_LEVEL_2) & (self.level <= TANK_HEIGHT):
            # Parts 1 and 2 filled + Part 3 partially or fully filled
            self.level = self.level - TANK_LEVEL_2
            surface = LARGE_SIDE + (SMALL_SIDE - LARGE_SIDE) / TANK_LEVEL_1 * self.level
            volume = (1/2 * (LARGE_SIDE + surface) * self.level * TANK_LENGTH)/1000   # /1000 for capacity in liters
            volume = volume + TRAPEZE_CAPACITY + RECTANGLE_CAPACITY

        return volume

if __name__ == "__main__":
    LevelSensor = Sensor_Utlrason(15, 13)

    # Perform the measurement and record the fuel oil level
    while True:
        level = LevelSensor.read('cm')
        print('Fuel oil height: {:.2f} cm'.format(level))
        level = LevelSensor.convert_to_liters()
        print('Fuel oil volume: {:.2f} liters'.format(level))
        sleep(5)