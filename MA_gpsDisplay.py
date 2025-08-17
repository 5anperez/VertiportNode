# EXAMPLE USAGE:
# This would be in your main GPS node script
import serial
from MA_init import MA_GPSReader
import time



"""

OUTPUT:

GPS Status Summary
--------------------
Status: 3D Fix (12 sats)
Position: 42.328312°N, 83.397625°W
Altitude: 202.8m
Time: 17/08/2025 05:34:52 UTC
Speed: 0.1 km/h
HDOP: 0.8

"""




# Initialize serial port
ser = serial.Serial('/dev/serial0', 9600, timeout=1)

# Create GPS reader
gps = MA_GPSReader(ser)

# Read and parse GPS data
while True:
    gps_data = gps.read_and_parse()
    print(gps.get_summary())
    time.sleep(1)







