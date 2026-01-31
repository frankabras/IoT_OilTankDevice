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

TOTAL_CAPACITY = ((2 * TRAPEZE_CAPACITY) + RECTANGLE_CAPACITY) - CAPACITY_OFFSET

# function to convert the fuel oil level in cm to volume in liters
# OUTPUT:
#   volume: The fuel oil volume in liters
def convert_to_liters(distance):
    level = TANK_HEIGHT - distance

    volume = 0
    if level <= TANK_LEVEL_1:
        # Fuel only in part 1
        surface = SMALL_SIDE + (LARGE_SIDE - SMALL_SIDE) / TANK_LEVEL_1 * level
        volume = (1/2 * (SMALL_SIDE + surface) * level * TANK_LENGTH)/1000  # /1000 for capacity in liters
    elif (level > TANK_LEVEL_1) & (level <= TANK_LEVEL_2):
        # Part 1 filled + Part 2 partially filled
        level = level - TANK_LEVEL_1
        volume = (level * LARGE_SIDE * TANK_LENGTH)/1000  # /1000 for capacity in liters
        volume = volume + TRAPEZE_CAPACITY
    elif (level > TANK_LEVEL_2) & (level <= TANK_HEIGHT):
        # Parts 1 and 2 filled + Part 3 partially or fully filled
        level = level - TANK_LEVEL_2
        surface = LARGE_SIDE + (SMALL_SIDE - LARGE_SIDE) / TANK_LEVEL_1 * level
        volume = (1/2 * (LARGE_SIDE + surface) * level * TANK_LENGTH)/1000   # /1000 for capacity in liters
        volume = volume + TRAPEZE_CAPACITY + RECTANGLE_CAPACITY

    return volume