import ujson
import uerrno
import uos
import ntptime
import gc

from utime import sleep_ms, mktime, gmtime, time

# -----------------------------------------------------------------------------
# region FSM logic
# -----------------------------------------------------------------------------
def measurment(temp_sensor,
               level_sensor,
               tank) -> tuple[float | None, float | None, float | None]:
    """
    Perform sensor measurements and return results.
    
    :return: Tuple of (temperature in °C, humidity in %, fuel volume in liters) or (None, None, None) on error
    """
    try:
        temp, hum = temp_sensor.read()
        distance = level_sensor.read(temperature_c=temp if temp is not None else 20.0)
        liters = tank.to_liters(tank.tank_height - distance)
        return temp, hum, liters
    except Exception as e:
        print("[MEASURE] Measurement error:", e)
        return None, None, None

def connection(wifi) -> bool | None:
    """
    Test WiFi connection and NTP synchronization.
    
    :return: True if connected successfully, 
             False if connection failed, 
             None if still connecting
    """
    try:
        wifi.enable_connection = True
        if wifi.is_connected:
            print("[CONNECT] WiFi connected successfully")
            return True
        elif wifi.connection_failed:
            print("[CONNECT] WiFi connection failed")
            return False
        else:
            return None
    except Exception as e:
        print("[CONNECT] Connection error:", e)

def flush_data(mqtt,
               csv_filename: str = "data.csv") -> None:
    """
    Read data from the specified CSV file, print it, and delete the file.
    """
    try:
        messages = []

        with open(csv_filename, "r") as f:
            print("[FLUSH] Reading data from " + csv_filename)
            for line in f:
                line = line.strip()
                if not line:
                    continue
                parts = line.split(";")
                if len(parts) >= 4:                    
                    messages.append({
                        "topic": parts[0].encode(),
                        "payload": parts[1].encode(),
                        "retain": bool(int(parts[2])),
                        "qos": int(parts[3])
                    })
        
        if messages:
            print(f"[FLUSH] Processing {len(messages)} historical messages...")
            send_data(mqtt=mqtt, messages=messages)
        
        uos.remove(csv_filename)
        print("[FLUSH] " + csv_filename + " flushed successfully")

    except Exception as e:
        if isinstance(e, OSError) and e.args[0] == uerrno.ENOENT:
            print("[FLUSH] No data to flush (" + csv_filename + " not found)")
        else:
            print("[FLUSH] Error reading " + csv_filename + ":", e)

def save_data(messages: list[dict],
              csv_filename: str = "data.csv") -> None:
    """
    Save the provided data to a CSV file. Each entry is saved as a separate line in the file.
    """
    try:
        with open(csv_filename, "a") as f:
            for msg in messages:
                topic = msg.get("topic").decode()
                payload = msg.get("payload").decode()
                retain = 1 if msg.get("retain", False) else 0
                qos = msg.get("qos", 0)
                
                line = "{};{};{};{}\n".format(topic, payload, retain, qos)
                f.write(line)
                print(f"[SAVE] Data saved to {csv_filename}: {line.strip()}")
        print(f"[SAVE] Buffered {len(messages)} messages to {csv_filename}")
    except Exception as e:
        print("[SAVE] Error saving data:", e)

def send_data(mqtt,
              messages: list[dict]) -> None:
    """
    Send current measurement data to server via MQTT.
    
    :param mqtt: Initializes and connected MQTTManager instance.
    :param messages: List of dictionaries containing 'topic', 'payload', and optional 'retain' and 'qos'.
    """
    try:
        for msg in messages:
            topic = msg.get("topic")
            payload = msg.get("payload")
            retain = msg.get("retain", False)
            qos = msg.get("qos", 0)

            if topic is not None and payload is not None:
                mqtt.publish(topic=topic, message=payload, retain=retain, qos=qos)
                print(f"[SEND] {topic.decode()}: {payload.decode()} published successfully")
            else:
                print("[SEND] Invalid message format, missing topic or payload:", msg)
    except Exception as e:
        print("[SEND] Error sending data:", e)

def go_sleep(wifi) -> None:
    """ Enter low power sleep mode (not implemented) """
    wifi.enable_connection = False
    sleep_ms(5000)                                                                          # TODO: Implement actual deep sleep mode for power saving

# endregion

# -----------------------------------------------------------------------------
# region DATE & TIME
# -----------------------------------------------------------------------------
def last_sunday(year: int,
                month: int) -> int:
    # Returns the last Sunday of the given month and year

    # Determine next month and year based on current month
    if month == 12:
        next_month = (year + 1, 1)
    else:
        next_month = (year, month + 1)

    # timestamp for first day of next month at 00:00 UTC then go back one day
    t = mktime((next_month[0], next_month[1], 1, 0, 0, 0, 0, 0))
    t -= 24 * 3600
    tm = gmtime(t)
    # How many days to subtract to reach Sunday (tm[6] : 0=Monday ... 6=Sunday)
    days_back = (tm[6] + 1) % 7
    return tm[2] - days_back

def is_dst_brussels(utc_tm: tuple[int, int, int, int]) -> bool:
    year = utc_tm[0]
    month = utc_tm[1]
    day = utc_tm[2]
    hour = utc_tm[3]

    # DST in Europe: last Sunday of March at 01:00 UTC
    # ends last Sunday of October at 01:00 UTC
    if month < 3 or month > 10:
        return False
    if 3 < month < 10:
        return True

    if month == 3:
        last = last_sunday(year, 3)
        # DST starts at 01:00 UTC
        # Return True if we're past the last Sunday of March or it's the last Sunday and past 01:00 UTC
        return (day > last) or (day == last and hour >= 3)

    if month == 10:
        last = last_sunday(year, 10)
        # DST ends at 01:00 UTC
        # Return True if we're before the last Sunday of October or it's the last Sunday and before 01:00 UTC
        return (day < last) or (day == last and hour < 3) 

def localtime_brussels() -> tuple[str, str]:
    utc = gmtime()  # UTC
    offset = 2 if is_dst_brussels(utc) else 1  # UTC+2 in summer, UTC+1 in winter
    # Calculate local time by adding the offset to the current UTC time
    local_time = gmtime(time() + offset * 3600)
    # Format local time as date and time strings (not used in return value but can be useful for debugging)
    date_str = "{:02d}/{:02d}/{:04d}".format(local_time[2], # day
                                             local_time[1], # month
                                             local_time[0]) # year
    time_str = "{:02d}:{:02d}:{:02d}".format(local_time[3], # hour
                                             local_time[4], # minute
                                             local_time[5]) # second
    
    # print("Current date (Brussels):", current_date)
    # print("Current time (Brussels):", current_time)

    return date_str, time_str

def update_rtc(retry_count: int = 3) -> None:
    """ Update RTC time from NTP server """
    for _ in range(retry_count):
        try:
            ntptime.settime()
            print("[RTC] Synchronized with NTP server")
            break
        except Exception as e:
            sleep_ms(1000)
    else:
        print("[RTC] Failed to synchronize after retries")

# endregion

# -----------------------------------------------------------------------------
# region MISC
# -----------------------------------------------------------------------------
def data_to_json(**kwargs) -> bytes:
    data = {k: v for k, v in kwargs.items() if v is not None}
    
    return ujson.dumps(data).encode()

def cleanup():
    """ Perform garbage collection and cleanup """
    gc.collect()
    print("Garbage collection completed")

# endregion