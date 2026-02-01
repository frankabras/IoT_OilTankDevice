from abc import ABC, abstractmethod

class VolumeCalculator(ABC):
    @abstractmethod
    def to_liters(self, distance):
        pass


class HexagonalPrismTank(VolumeCalculator):
    # Tank dimensions
    """
    Tank divided into 3 parts (side view):
    - Lower part:   trapezoidal shape on the small side
                    (ex: from 0 to 45.5cm = 45.5cm)
    - Central part: rectangular shape
                    (ex: from 45.5 to 105cm = 59.5cm)
    - Upper part:   trapezoidal shape on the large side
                    (ex: from 105 to 150.5cm = 45.5cm)
    """
    def __init__(self, tank_length, h_rectangle, h_trapeze, min_width, max_width):

        self.tank_length = tank_length
        self.h_rectangle = h_rectangle
        self.h_trapeze = h_trapeze
        self.min_width = min_width
        self.max_width = max_width

        # Calculate levels and tank height
        self.level_1 = h_trapeze
        self.level_2 = h_trapeze + h_rectangle
        self.tank_height = self.level_2 + self.h_trapeze

        # Pre-calculate part capacities
        self.trapeze_capacity = self._calc_trapeze_volume(self.min_width, self.max_width, self.h_trapeze)
        self.rectangle_capacity = self._calc_rectangle_volume(self.max_width, self.h_rectangle)

    def _calc_trapeze_volume(self, side_a, side_b, height):
        area = (side_a + side_b) / 2 * height
        return (area * self.tank_length) / 1000  # /1000 for capacity in liters
    
    def _calc_rectangle_volume(self, side, height):
        return (side * height * self.tank_length) / 1000  # /1000 for capacity in liter

    # function to convert the fuel oil level in cm to volume in liters
    # INPUT:
    #   distance: The distance from the sensor to the fuel oil surface in cm
    # OUTPUT:
    #   volume: The fuel oil volume in liters
    def to_liters(self, distance):
        current_level = self.tank_height - distance
        volume = 0

        if current_level <= self.level_1:
            # Fuel only in part 1
            surface = self.min_width + (self.max_width - self.min_width) / self.h_trapeze * current_level
            volume = (1/2 * (self.min_width + surface) * current_level * self.tank_length) / 1000  # /1000 for capacity in liters
        elif (current_level > self.level_1) & (current_level <= self.level_2):
            # Part 1 filled + Part 2 partially filled
            relative_level = current_level - self.level_1
            volume = self.trapeze_capacity + self._calc_rectangle_volume(self.max_width, relative_level)
            # volume = (current_level * self.max_width * self.tank_length)/1000  # /1000 for capacity in liters
            # volume = volume + self.trapeze_capacity
        elif (current_level > self.level_2) & (current_level <= self.tank_height):
            # Parts 1 and 2 filled + Part 3 partially or fully filled
            relative_level = current_level - self.level_2

            surface = self.max_width + (self.min_width - self.max_width) / self.h_trapeze * relative_level
            volume = (1/2 * (self.max_width + surface) * relative_level * self.tank_length) / 1000   # /1000 for capacity in liters
            volume = volume + self.trapeze_capacity + self.rectangle_capacity

        if volume < 0:
            volume = 0

        return volume