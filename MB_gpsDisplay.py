import serial
from MB_init import MB_GPSReader
import time



"""
OUTPUT:

GPS Data (Valid Fix):
  Position: 42.328299°N, 83.397636°W
  Altitude: 207.5 m
  Fix: 3D (12 satellites)
  Speed: 0.0 km/h
  Time: 06:30:33 17/08/2025
  
"""




ser = serial.Serial('/dev/serial0', 9600, timeout=1)
gps = MB_GPSReader(ser)

while True:
    gps_data = gps.get_data()
    print(gps_data)
    time.sleep(1)
    
    
    
    
    
    
    
    