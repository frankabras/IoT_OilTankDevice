import ujson
import uerrno
import uos
import ntptime
import gc

from utime import sleep_ms, localtime

# -----------------------------------------------------------------------------
# region FSM logic
# -----------------------------------------------------------------------------
def measurment(temp_sensor,
               level_sensor,
               tank):
    """
    Perform sensor measurements and return results.
    
    :return: Tuple of (temperature in °C, humidity in %, fuel volume in liters) or (None, None, None) on error
    :rtype: Tuple[float | None, float | None, float | None]
    """
    try:
        temp, hum = temp_sensor.read()
        distance = level_sensor.read(temperature_c=temp if temp is not None else 20.0)
        liters = tank.to_liters(tank.tank_height - distance)
        return temp, hum, liters
    except Exception as e:
        print("Measurement error:", e)
        return None, None, None

def connection(wifi):
    """
    Test WiFi connection and NTP synchronization.
    
    :return: True if connected successfully, 
             False if connection failed, 
             None if still connecting
    :rtype: bool | None
    """
    try:
        wifi.enable_connection = True
        if wifi.is_connected:
            print("WiFi connected successfully")
            return True
        elif wifi.connection_failed:
            print("WiFi connection failed")
            return False
        else:
            return None
    except Exception as e:
        print("Connection error:", e)

def flush_data(json_filename: str = "data.json"):
    """
    Read data from the specified JSON file, print it, and delete the file.
    """
    try:
        with open(json_filename, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                object = ujson.loads(line)
                print("Flushing data:", object)
        uos.remove(json_filename)
        print(json_filename + " flushed successfully")                                      # TODO: Implement actual data transmission to server
    except Exception as e:
        if isinstance(e, OSError) and e.args[0] == uerrno.ENOENT:
            print("No data to flush (" + json_filename + " not found)")
        else:
            print("Error reading " + json_filename + ":", e)

def save_data(temp, hum, liters, json_filename: str = "data.json"):
    """
    Save the provided data to a JSON file. Each entry is saved as a separate line in the file.
    """
    try:
        data = {                                                                            # TODO: Add datetime field in ISO format (e.g., "2024-06-01T12:00:00")
            "temperature": str(temp) + "°C" if temp is not None else "N/A",
            "humidity": str(hum) + "%" if hum is not None else "N/A",
            "volume": str(liters) + "L" if liters is not None else "N/A",
        }
        with open(json_filename, "a") as f:
            ujson.dump(data, f)
            f.write("\n")
        print("Data saved to " + json_filename)
    except Exception as e:
        print("Error saving data:", e)

def send_data(temp, hum, liters):                                                           # TODO: Add parameters for datetime
    """ Send current measurement data to server """
    try:
        if temp is not None and hum is not None:
            print('Temperature: %3.1f °C' % temp)
            print('Humidity: %3.1f %%' % hum)
        else:
            print('Failed to read from temperature and humidity sensor.')                   # TODO: Implement actual data transmission to server
        
        print('Fuel oil volume: {:.2f} liters'.format(liters))
    except Exception as e:
        print("Error sending data:", e)

def go_sleep(wifi):
    """ Enter low power sleep mode (not implemented) """
    wifi.enable_connection = False
    sleep_ms(5000)                                                                          # TODO: Implement actual deep sleep mode for power saving

# endregion

# -----------------------------------------------------------------------------
# region DATE & TIME
# -----------------------------------------------------------------------------
def update_rtc(retry_count: int = 3):
    """ Update RTC time from NTP server """
    for _ in range(retry_count):
        try:
            ntptime.settime()
            print("RTC synchronized with NTP server")
            print("Current time (UTC):", localtime())                                       # TODO: Convert to local time
            break
        except Exception as e:
            sleep_ms(1000)
    else:
        print("Failed to synchronize RTC after retries")

# endregion

# -----------------------------------------------------------------------------
# region MISC
# -----------------------------------------------------------------------------
def cleanup():
    """ Perform garbage collection and cleanup """
    gc.collect()
    print("Garbage collection completed")