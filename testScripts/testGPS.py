import serial
from gps_parser import GPSReader
import time





# Establish serial connection to GPS
ser = serial.Serial('/dev/serial0', 9600, timeout=1)

# Using the serial port
while True:
    line = ser.readline().decode('ascii', errors='replace').strip()
    if line:
        print(line)










# Using the library
# gps = GPSReader(ser)

# # Read data from GPS
# while True:
#     if gps.update():
#         d = gps.current_data
#         print(f"fix = {d.has_fix}, lat = {d.latitude:.6f}, lon = {d.longitude:.6f} "
#               f"alt = {d.altitude:.1f}m, sats = {d.satellites}, hdop = {d.hdop:.2f}, "
#               f"speed = {d.speed_knots:.2f}km/h, time = {d.time}, date = {d.date}")
#     time.sleep(1)
        
        
        
        
        
        
        
        
        
        
        
        
        
        

