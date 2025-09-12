# Importation des modules
from machine import Pin, time_pulse_us
import utime

# Définition des pins utilisés par le capteur ultrason
trig_pin = Pin(15, Pin.OUT)
echo_pin = Pin(13, Pin.IN)

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

""" ********** Fonctions de mesure *********** """
# Mesure de distance via le capteur ultrason
def measure_level():
    # Envoyer une impulsion de 10 microsecondes pour déclencher la mesure
    trig_pin.value(0)
    utime.sleep_us(2)
    trig_pin.value(1)
    utime.sleep_us(10)
    trig_pin.value(0)

    # Mesurer la durée du retour de l'écho en microsecondes
    duration = time_pulse_us(echo_pin, 1, 30000)  # 30000 us timeout

    # Calcul la distance en cm
    distance = (duration * 0.0343) / 2
    print('Distance entre le capteur et le mazout: {:.2f} cm'.format(distance))

    # Correction de la distance en prenant en compte la zone aveugle du capteur
    correctedDistance = distance - SENSOR_OFFSET
    print('Distance entre le hau de la cuve et le mazout: {:.2f} cm'.format(correctedDistance))

    # Calcul de la hauteur de mazout en cm
    oilLevel = TANK_HEIGHT - correctedDistance
    print('Hauteur de mazout: {:.2f} cm'.format(oilLevel))

    return oilLevel

# Conversion de la mesure en cm en litres restants
def measure_conversion(oilLevel):
    volume = 0
    if oilLevel <= TANK_LEVEL_1:
        # Mazout uniquement dans la partie 1
        oilSurface = SMALL_SIDE + (LARGE_SIDE - SMALL_SIDE) / TANK_LEVEL_1 * oilLevel
        volume = (1/2 * (SMALL_SIDE + oilSurface) * oilLevel * TANK_LENGTH)/1000  # /1000 pour capacité en litres
    elif (oilLevel > TANK_LEVEL_1) & (oilLevel <= TANK_LEVEL_2):
        # Partie 1 remplie + Partie 2 partiellement remplie
        level = oilLevel - TANK_LEVEL_1
        volume = (level * LARGE_SIDE * TANK_LENGTH)/1000  # /1000 pour capacité en litres
        volume = volume + TRAPEZE_CAPACITY
    elif (oilLevel > TANK_LEVEL_2) & (oilLevel <= TANK_HEIGHT):
        # Partie 1 et 2 remplies + Partie 3 partiellement ou totalement remplie
        level = oilLevel - TANK_LEVEL_2
        oilSurface = LARGE_SIDE + (SMALL_SIDE - LARGE_SIDE) / TANK_LEVEL_1 * level
        volume = (1/2 * (LARGE_SIDE + oilSurface) * level * TANK_LENGTH)/1000   # /1000 pour capacité en litres
        volume = volume + TRAPEZE_CAPACITY + RECTANGLE_CAPACITY

    return volume


""" ********** Fonctions gestion des données *********** """
# Affichage et enregistrement des données
def log_oil_level(oil_volume):
    print('Volume de mazout restant: {:.2f} litres'.format(oil_volume))
    print('Pourcentage de mazout restant: {:.0f} %'.format((oil_volume/TOTAL_CAPACITY)*100))
    # Ajouter du code pour sauvegarder la mesure



while True:
    measure_level()
    utime.sleep(1)