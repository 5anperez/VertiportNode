import time
import threading
import serial
from gps_parser import GPSReader
from luma.core.interface.serial import i2c
from luma.oled.device import ssd1306
from luma.core.render import canvas
from PIL import ImageFont

# Init GPS
ser = serial.Serial('/dev/serial0', 9600, timeout=0)
gps = GPSReader(ser)

# Init OLED (change address if your scan shows different)
serial_i2c = i2c(port=1, address=0x3C)
device = ssd1306(serial_i2c, width=128, height=64)

font16 = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)

# Shared state between worker and UI
lock = threading.Lock()
shared = {
    "has_fix": False,
    "lat": 0.0,
    "lon": 0.0,
    "sats": 0,
}

stop_event = threading.Event()

def gps_worker() -> None:
    while not stop_event.is_set():
        d = gps.get_data()
        with lock:
            shared["has_fix"] = d.has_fix
            shared["lat"] = d.latitude
            shared["lon"] = d.longitude
            shared["sats"] = d.satellites
        time.sleep(0.05)

threading.Thread(target=gps_worker, daemon=True).start()

prev_lat_str = None
prev_lon_str = None
fix_latched = False

try:
    while True:
        with lock:
            has_fix = shared["has_fix"]
            lat = shared["lat"]
            lon = shared["lon"]
            print(f"fix = {has_fix} sats = {shared['sats']}")
            print(f"lat = {lat} lon = {lon}")

        if not fix_latched and has_fix:
            fix_latched = True
            prev_lat_str = None
            prev_lon_str = None

        if fix_latched:
            lat_str = f"{lat:.5f}"
            lon_str = f"{lon:.5f}"
            if (lat != 0 and lat_str != prev_lat_str) or (lon != 0 and lon_str != prev_lon_str):
                with canvas(device) as draw:
                    draw.text(xy=(0, 0), text="GPS: FIX", font=font16, fill=255)
                    draw.line(xy=(0, 16, device.width - 1, 16), fill=255)
                    draw.text(xy=(0, 24), text=f"Lat: {lat_str}", font=font16, fill=255)
                    draw.text(xy=(0, 48), text=f"Lon: {lon_str}", font=font16, fill=255)

                prev_lat_str = lat_str
                prev_lon_str = lon_str

        time.sleep(0.1)
except KeyboardInterrupt:
    stop_event.set()


























