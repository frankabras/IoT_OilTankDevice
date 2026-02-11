from abc import ABC, abstractmethod

class VolumeCalculator(ABC):
    @abstractmethod
    def to_liters(self, distance):
        pass


class HexagonalPrismTank(VolumeCalculator):
    """
    Class to calculate the volume of fuel oil in a hexagonal prism tank 
    based on the distance from the sensor to the fuel oil surface.

    Args:
        tank_length (float): Length of the tank in cm
        h_rectangle (float): Height of the rectangular part of the tank in cm
        h_trapeze (float): Height of the trapezoidal part of the tank in cm
        min_width (float): Minimum width of the trapezoidal part in cm
        max_width (float): Maximum width of the trapezoidal part in cm

    Attributes:
        tank_length (float): Length of the tank in cm
        h_rectangle (float): Height of the rectangular part of the tank in cm
        h_trapeze (float): Height of the trapezoidal part of the tank in cm
        min_width (float): Minimum width of the trapezoidal part in cm
        max_width (float): Maximum width of the trapezoidal part in cm
        level_1 (float): Level at which the trapezoidal part is filled in cm
        level_2 (float): Level at which the rectangular part is filled in cm
        tank_height (float): Total height of the tank in cm
    
    Methods:
        to_liters(distance: float) -> float:
            Convert the fuel oil level in cm to volume in liters.
            :param distance: The distance from the sensor to the fuel oil surface in cm
            :return: The fuel oil volume in liters
    """
    def __init__(self,
                 tank_length: float,
                 h_rectangle: float,
                 h_trapeze: float,
                 min_width: float,
                 max_width: float) -> None:

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

    def _calc_trapeze_volume(self,
                             side_a: float,
                             side_b: float,
                             height: float) -> float:
        """
        Calculate the volume of a trapezoidal section of the tank.
        
        :param side_a: The length of one parallel side of the trapezoid in cm
        :type side_a: float
        :param side_b: The length of the other parallel side of the trapezoid in cm
        :type side_b: float
        :param height: The height of the trapezoidal section in cm
        :type height: float
        :return: The volume of the trapezoidal section in liters
        :rtype: float
        """
        area = (side_a + side_b) / 2 * height
        return (area * self.tank_length) / 1000  # /1000 for capacity in liters
    
    def _calc_rectangle_volume(self,
                               side: float,
                               height: float) -> float:
        """
        Calculate the volume of a rectangular section of the tank.

        :param side: The length of the side of the rectangle in cm
        :type side: float
        :param height: The height of the rectangular section in cm
        :type height: float
        :return: The volume of the rectangular section in liters
        :rtype: float
        """
        return (side * height * self.tank_length) / 1000  # /1000 for capacity in liters

    def to_liters(self,
                  distance: float) -> float:
        """
        Convert the fuel oil level in cm to volume in liters.
        
        :param distance: The distance from the sensor to the fuel oil surface in cm
        :type distance: float
        :return: The volume of fuel oil in liters
        :rtype: float
        """
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