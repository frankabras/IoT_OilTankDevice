from machine import Pin, time_pulse_us
import utime

# Données et dimensions de la cuve
"""
Découpe de la cuve en 3 parties (vue de côté):
- Partie basse:     forme trapèzoïdal sur le petit côté
                    (de 0 à 45,5cm = 45,5cm)
- Partie centrale:  forme rectangulaire
                    (de 45,5 à 105cm = 59,5cm)
- Partie haute:     forme trapèzoïdal sur le grand côté
                    (de 105 à 150,5cm = 45,5cm)
"""
TANK_LEVEL_1 = 45.5  # hauteur de fin du premier étage
TANK_LEVEL_2 = 105  # hauteur de fin du deuxième étage
TANK_HEIGHT = 150.5  # hauteur réelle de la cuve en cm (complet)
TANK_LENGTH = 250  # longueur réelle de la cuve en cm
GRADUATIONS_HEIGHT = 147.5  # hauteur remplissage max de la cuve en cm (capacité = 2500L)

# Données pour le calcul du volume restant
SMALL_SIDE = 53  # petit côté des parties trapèzoïdal
LARGE_SIDE = 74  # grand côté trapèze et largeur rectangle (car = séparation entre les 2)
TRAPEZE_CAPACITY = 720  # capacité en litres des parties trapèzoïdal
RECTANGLE_CAPACITY = 1100  # capacité en litres de la partie rectangulaire
CAPACITY_OFFSET = 40  # capacité en litres entre le haut de la cuve et le début des graduations
SENSOR_OFFSET = 20  # zone aveugle du capteur en cm
TOTAL_CAPACITY = ((2 * TRAPEZE_CAPACITY) + RECTANGLE_CAPACITY) - CAPACITY_OFFSET

class UltrasonSensor:
    def __init__(self, trig_pin, echo_pin):
        self.trig = trig_pin
        self.echo = echo_pin

        self.level = 0.0

    def read(self, unit='cm'):
        # Envoyer une impulsion de 10 microsecondes pour déclencher la mesure
        self.trig.value(0)
        utime.sleep_us(2)
        self.trig.value(1)
        utime.sleep_us(10)
        self.trig.value(0)

        # Mesurer la durée du retour de l'écho en microsecondes
        duration = time_pulse_us(self.echo, 1, 30000)  # 30000 us timeout

        # Calcul la distance en cm
        distance = ((duration * 0.0343) / 2) - SENSOR_OFFSET
        self.level = TANK_HEIGHT - distance

        if unit == 'cm':
            return self.level
        elif unit == 'li':
            return self.convert_to_liters()
        
    def convert_to_liters(self):
        volume = 0
        if self.level <= TANK_LEVEL_1:
            # Mazout uniquement dans la partie 1
            surface = SMALL_SIDE + (LARGE_SIDE - SMALL_SIDE) / TANK_LEVEL_1 * self.level
            volume = (1/2 * (SMALL_SIDE + surface) * self.level * TANK_LENGTH)/1000  # /1000 pour capacité en litres
        elif (self.level > TANK_LEVEL_1) & (self.level <= TANK_LEVEL_2):
            # Partie 1 remplie + Partie 2 partiellement remplie
            self.level = self.level - TANK_LEVEL_1
            volume = (self.level * LARGE_SIDE * TANK_LENGTH)/1000  # /1000 pour capacité en litres
            volume = volume + TRAPEZE_CAPACITY
        elif (self.level > TANK_LEVEL_2) & (self.level <= TANK_HEIGHT):
            # Partie 1 et 2 remplies + Partie 3 partiellement ou totalement remplie
            self.level = self.level - TANK_LEVEL_2
            surface = LARGE_SIDE + (SMALL_SIDE - LARGE_SIDE) / TANK_LEVEL_1 * self.level
            volume = (1/2 * (LARGE_SIDE + surface) * self.level * TANK_LENGTH)/1000   # /1000 pour capacité en litres
            volume = volume + TRAPEZE_CAPACITY + RECTANGLE_CAPACITY

        return volume

if __name__ == "__main__":
    LevelSensor = UltrasonSensor(15, 13)

    # Effectuer la mesure et enregistrer le niveau de mazout
    while 1:
        level = LevelSensor.read('cm')
        print('Hauteur de mazout: {:.2f} cm'.format(level))
        level = LevelSensor.convert_to_liters()
        print('Volume de mazout: {:.2f} litres'.format(level))
        utime.sleep(1)