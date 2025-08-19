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



Installation requirements:

# Install required libraries on your RPi4B
sudo apt-get update
sudo apt-get install -y python3-pip python3-pil python3-serial i2c-tools

# Install Adafruit libraries
pip3 install adafruit-circuitpython-ssd1306

# Enable I2C and UART
sudo raspi-config
# Navigate to Interface Options -> I2C -> Enable
# Navigate to Interface Options -> Serial Port -> No (login shell) -> Yes (serial hardware)

# Verify I2C device
i2cdetect -y 1  # Should show device at 0x3C






To check if the libraries are available in venv:

python -c "import sys; print(sys.executable)"
python -c "import adafruit_ssd1306, inspect; print(adafruit_ssd1306.__file__)"
pip show adafruit-circuitpython-ssd1306

"""




# INITIAL GPS PARSER MODULE TEST. INTEGRATE WITH OLED DISPLAY BELOW THIS...

# # Initialize serial port
# ser = serial.Serial('/dev/serial0', 9600, timeout=1)

# # Create GPS reader
# gps = MA_GPSReader(ser)

# # Read and parse GPS data
# while True:
#     gps_data = gps.read_and_parse()
#     print(gps.get_summary())
#     time.sleep(1)








# OLED DISPLAY MODULE
#!/usr/bin/env python3
"""
GPS OLED Display for Raspberry Pi
Shows GPS status and coordinates on SSD1306 OLED display
"""

# import time
# import serial
import board
import busio
from PIL import Image, ImageDraw, ImageFont
import adafruit_ssd1306
# from gpsParser import GPSReader




class GPSOLEDDisplay:
    """
    Handles displaying GPS data on SSD1306 OLED
    """
    
    def __init__(self, i2c_address=0x3C):
        """
        Initialize OLED display
        
        Args:
            i2c_address: I2C address of the OLED (usually 0x3C)
        """
        # Create I2C interface
        self.i2c = busio.I2C(board.SCL, board.SDA)
        
        # Create SSD1306 OLED class (128x64 pixels)
        self.display = adafruit_ssd1306.SSD1306_I2C(128, 64, self.i2c, addr=i2c_address)
        
        # Clear display
        self.display.fill(0)
        self.display.show()
        
        # Create blank image for drawing
        self.width = self.display.width
        self.height = self.display.height
        self.image = Image.new("1", (self.width, self.height))
        self.draw = ImageDraw.Draw(self.image)
        
        # Load fonts - using default font but larger sizes
        try:
            # Try to load a nice font if available
            self.font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)
            self.font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
        except:
            # Fallback to default font
            self.font_large = ImageFont.load_default()
            self.font_small = ImageFont.load_default()
            
        # Track last displayed values
        self.last_lat = None
        self.last_lon = None
        self.last_status = None
        


    def display_startup(self):
        """Display startup message"""
        self.draw.rectangle((0, 0, self.width, self.height), outline=0, fill=0)
        
        # Startup message
        self.draw.text((20, 20), "GPS NODE", font=self.font_large, fill=255)
        self.draw.text((15, 40), "Initializing...", font=self.font_small, fill=255)
        
        self.display.image(self.image)
        self.display.show()
        


    def display_waiting(self):
        """Display waiting for GPS fix message"""
        self.draw.rectangle((0, 0, self.width, self.height), outline=0, fill=0)
        
        # Waiting message
        self.draw.text((15, 25), "Waiting for", font=self.font_small, fill=255)
        self.draw.text((20, 40), "GPS Fix...", font=self.font_small, fill=255)
        
        self.display.image(self.image)
        self.display.show()
        

    # # OLD:
    # def display_gps_data(self, gps_data):
    #     """
    #     Display GPS data on OLED
    #     Only updates if position has changed
        
    #     Args:
    #         gps_data: GPSData object from gpsParser
    #     """
    #     # Check if we have valid non-zero coordinates
    #     if not gps_data.is_valid():
    #         return
            
    #     # Check if position has changed
    #     if (self.last_lat == gps_data.latitude and 
    #         self.last_lon == gps_data.longitude and
    #         self.last_status == gps_data.get_status_string()):
    #         return
            
    #     # Clear image
    #     self.draw.rectangle((0, 0, self.width, self.height), outline=0, fill=0)
        
    #     # Line 1: GPS Status (in yellow area - top 16 pixels)
    #     status_text = gps_data.get_status_string()
    #     # Center the status text
    #     bbox = self.draw.textbbox((0, 0), status_text, font=self.font_large)
    #     text_width = bbox[2] - bbox[0]
    #     x_pos = (self.width - text_width) // 2
    #     self.draw.text((x_pos, 0), status_text, font=self.font_large, fill=255)
        
    #     # Underline
    #     self.draw.line((10, 18, self.width - 10, 18), fill=255, width=1)
        
    #     # Blank line (pixels 19-28)
        
    #     # Line 2: Latitude (pixels 29-44)
    #     lat_text = f"LAT: {gps_data.latitude:.4f}"
    #     self.draw.text((5, 29), lat_text, font=self.font_large, fill=255)
        
    #     # Blank line (pixels 45-48)
        
    #     # Line 3: Longitude (pixels 49-64)
    #     lon_text = f"LON: {gps_data.longitude:.4f}"
    #     self.draw.text((5, 49), lon_text, font=self.font_large, fill=255)
        
    #     # Update display
    #     self.display.image(self.image)
    #     self.display.show()
        
    #     # Update last displayed values
    #     self.last_lat = gps_data.latitude
    #     self.last_lon = gps_data.longitude
    #     self.last_status = status_text




    # NEW:
    def display_gps_data(self, gps_data):
        """
        Display GPS data on OLED
        Only updates if position has changed
        
        Args:
            gps_data: GPSData object from gpsParser
        """
        # Check if we have valid non-zero coordinates
        if not gps_data.is_valid():
            return
            
        # Format the status text without satellite count
        if gps_data.fix_type:
            status_text = f"{gps_data.fix_type} Fix"
        else:
            status_text = "GPS Fix"
            
        # Check if position has changed
        if (self.last_lat == gps_data.latitude and 
            self.last_lon == gps_data.longitude and
            self.last_status == status_text):
            return
            
        # Clear image
        self.draw.rectangle((0, 0, self.width, self.height), outline=0, fill=0)
        
        # Line 1: GPS Status (in yellow area - top 16 pixels)
        # Center the status text
        bbox = self.draw.textbbox((0, 0), status_text, font=self.font_large)
        text_width = bbox[2] - bbox[0]
        x_pos = (self.width - text_width) // 2
        self.draw.text((x_pos, 0), status_text, font=self.font_large, fill=255)
        
        # Underline
        self.draw.line((10, 18, self.width - 10, 18), fill=255, width=1)
        
        # Blank line (pixels 19-28)
        
        # Line 2: Latitude (pixels 29-44)
        lat_dir = 'N' if gps_data.latitude >= 0 else 'S'
        lat_text = f"LAT: {abs(gps_data.latitude):.2f}°{lat_dir}"
        self.draw.text((5, 29), lat_text, font=self.font_large, fill=255)
        
        # Blank line (pixels 45-48)
        
        # Line 3: Longitude (pixels 49-64)
        lon_dir = 'E' if gps_data.longitude >= 0 else 'W'
        lon_text = f"LON: {abs(gps_data.longitude):.2f}°{lon_dir}"
        self.draw.text((5, 49), lon_text, font=self.font_large, fill=255)
        
        # Update display
        self.display.image(self.image)
        self.display.show()
        
        # Update last displayed values
        self.last_lat = gps_data.latitude
        self.last_lon = gps_data.longitude
        self.last_status = status_text
        


    def clear(self):
        """Clear the display"""
        self.display.fill(0)
        self.display.show()



def with_checksum(payload: str) -> str:
    """
    Add checksum to NMEA sentence
    """
    # payload example: "$GPRMC,...."
    data = payload[1:]  # drop leading $
    cs = 0
    for ch in data:
        cs ^= ord(ch)
    return f"{payload}*{cs:02X}"


# DEBUG = True
DEBUG = False

def main():
    """Main function to run GPS OLED display"""
    
    # Initialize GPS serial connection
    try:
        if DEBUG:
            print("DEBUG MODE")
            reader = MA_GPSReader(serial_port=None)  # you won’t use serial in this test
        else:
            print("Starting GPS OLED Display...")
    
            # Initialize display
            oled = GPSOLEDDisplay()
            oled.display_startup()
            time.sleep(2)

            # RPi hardware UART
            gps_serial = serial.Serial('/dev/serial0', 9600, timeout=1)
            gps_reader = MA_GPSReader(gps_serial)
            print("GPS serial connection established")
    except Exception as e:
        print(f"Error opening GPS serial port: {e}")
        oled.draw.rectangle((0, 0, oled.width, oled.height), outline=0, fill=0)
        oled.draw.text((10, 25), "GPS Error!", font=oled.font_large, fill=255)
        oled.display.image(oled.image)
        oled.display.show()
        return
    
    

    
    

    if DEBUG:
        # 1) RMC invalid -> GLL should fill
        reader._parse_nmea_sentence(with_checksum("$GPRMC,123519,V,,,,,,,230394,,,A"))
        reader._parse_nmea_sentence(with_checksum("$GPGLL,4916.45,N,12311.12,W,123520,A,A"))
        assert reader.gps_data.status == 'A'
        assert reader.gps_data.latitude is not None

        # 2) RMC valid -> GLL 'V' must NOT demote
        # reader = MA_GPSReader(None)
        reader._parse_nmea_sentence(with_checksum("$GPRMC,123519,A,4916.45,N,12311.12,W,0.5,054.7,230394,,,A"))
        lat_before = reader.gps_data.latitude
        reader._parse_nmea_sentence(with_checksum("$GPGLL,4916.45,N,12311.12,W,123521,V,A"))
        print(f"Status: {reader.gps_data.status}")
        assert reader.gps_data.status == 'A'
        assert reader.gps_data.latitude == lat_before

        # 3) Only GLL valid -> should populate
        # reader = MA_GPSReader(None)
        reader._parse_nmea_sentence(with_checksum("$GPRMC,123519,V,,,,,,,230394,,,A"))
        assert reader.gps_data.is_valid() == False
        reader._parse_nmea_sentence(with_checksum("$GPGLL,4916.45,N,12311.12,W,123520,A,A"))
        assert reader.gps_data.is_valid()
        print("DEBUG MODE COMPLETE")

        return
    else:
        # Show waiting message
        oled.display_waiting()
        
        # Main loop
        try:
            while True:
                # Read and parse GPS data
                gps_data = gps_reader.read_and_parse(timeout=1.0)
                
                # Display data if valid
                if gps_data.is_valid():
                    oled.display_gps_data(gps_data)
                    print(gps_reader.get_summary())
                
                # Small delay to prevent CPU overuse
                time.sleep(0.1)
                
        except KeyboardInterrupt:
            print("\nShutting down GPS OLED Display...")
            oled.clear()
            gps_serial.close()
            
        except Exception as e:
            print(f"Error in main loop: {e}")
            oled.clear()
        

if __name__ == "__main__":
    main()











































# # MA TEST CASES BELOW
# #!/usr/bin/env python3
# """
# Test cases for GPS parser redundancy logic
# Tests fallback to GLL when other sentences are invalid
# """

# import io
# from gpsParser import GPSReader, GPSData


# class MockSerial:
#     """Mock serial port for testing"""
#     def __init__(self, data):
#         self.data = data
#         self.position = 0
        
#     @property
#     def in_waiting(self):
#         return len(self.data) - self.position
        
#     def read(self, size):
#         result = self.data[self.position:self.position + size]
#         self.position += len(result)
#         return result


# def test_valid_rmc_overrides_gll():
#     """Test that valid RMC data takes precedence over GLL, i.e., confirm that good RMC values are not overwritten by GLL values"""
#     '''
#     NOTE: 
    
#     THE RMC SENT. WILL YIELD LAT = 48.1173, AND LON = 11.51666667. 
    
#     THE GLL SENT. WILL YIELD LAT = 48.1, AND LON = 11.5
    
#     SO WHEN WE TAKE THE DIFFERENCE WE WILL GET 0 < 0.001 = TRUE AND 0 < 0.001 = TRUE IF THE RMC VALUES WERE STORED, AND WE WILL GET 0.0173 < 0.001 = FALSE AND 0.01666667 < 0.001 = FALSE IF THE GLL VALUES WERE STORED. 
    
#     HOWEVER, THE GLL SENT. DOES NOT HAVE THE STATUS FIELD, SO IT WOULDNT BE USED ANYWAYS. THEREFORE, THIS MIGHT BE A REDUNDANT TEST.
#     '''
#     nmea_data = (
#         "$GPRMC,123519,A,4807.038,N,01131.000,E,022.4,084.4,230394,003.1,W*6A\r\n"
#         "$GPGLL,4806.000,N,01130.000,E,123520,A*7C\r\n"
#     ).encode()
    
#     serial = MockSerial(nmea_data)
#     reader = GPSReader(serial)
#     gps_data = reader.read_and_parse()
    
#     # NOTE: THESE VALUES ARE RETURNED BY THE _parse_coordinate METHOD.
#     print("Test 1: Valid RMC overrides GLL")
#     print(f"  Expected lat: 48.1173, Got: {gps_data.latitude:.4f}")
#     print(f"  Expected lon: 11.5167, Got: {gps_data.longitude:.4f}")
#     assert abs(gps_data.latitude - 48.1173) < 0.001
#     assert abs(gps_data.longitude - 11.5167) < 0.001
#     print("  ✓ PASSED\n")


# def test_invalid_rmc_uses_gll():
#     """Test that GLL is used when RMC has invalid status, i.e., confirm that bad RMC values are overwritten by GLL values, which is the fallback."""
#     '''
#     NOTE:
    
#     THE GLL SENT. WILL YIELD LAT = 48.1173 AND LON = 11.51666667
    
#     SO WHEN WE TAKE THE DIFFERENCE WE WILL GET 0 AND 0 IF THE GLL VALUES WERE STORED, WHICH PASSES, AND WE WILL GET 48.1173 AND 11.5167 IF THE RMC VALUES WERE STORED, WHICH FAILS. 
#     '''
#     nmea_data = (
#         "$GPRMC,123519,V,,,,,022.4,084.4,230394,003.1,W*7E\r\n"
#         "$GPGLL,4807.038,N,01131.000,E,123520,A*7D\r\n"
#     ).encode()
    
#     serial = MockSerial(nmea_data)
#     reader = GPSReader(serial)
#     gps_data = reader.read_and_parse()
    
#     print("Test 2: Invalid RMC, valid GLL used")
#     print(f"  Expected lat: 48.1173, Got: {gps_data.latitude:.4f if gps_data.latitude else 'None'}")
#     print(f"  Expected lon: 11.5167, Got: {gps_data.longitude:.4f if gps_data.longitude else 'None'}")
#     assert gps_data.latitude is not None
#     assert gps_data.longitude is not None
#     assert abs(gps_data.latitude - 48.1173) < 0.001
#     assert abs(gps_data.longitude - 11.5167) < 0.001
#     print("  ✓ PASSED\n")


# def test_gga_without_position_uses_gll():
#     """Test that GLL provides position when GGA lacks it, i.e., confirm that bad RMC values are overwritten by GLL values, which is the fallback."""
#     '''
#     NOTE:
    
#     THE GLL SENT. WILL YIELD LAT = 48.1173 AND LON = 11.51666667
    
#     SO WHEN WE TAKE THE DIFFERENCE WE WILL GET 0 AND 0 IF THE GLL VALUES WERE STORED, WHICH PASSES, AND WE WILL GET 48.1173 AND 11.5167 IF THE GGA VALUES WERE STORED, WHICH FAILS. 
#     '''
#     nmea_data = (
#         "$GPGGA,123519,,,,,0,4,0.9,545.4,M,46.9,M,,*40\r\n"
#         "$GPGLL,4807.038,N,01131.000,E,123520,A*7D\r\n"
#     ).encode()
    
#     serial = MockSerial(nmea_data)
#     reader = GPSReader(serial)
#     gps_data = reader.read_and_parse()
    
#     print("Test 3: GGA without position, GLL provides backup")
#     print(f"  Got lat: {gps_data.latitude:.4f if gps_data.latitude else 'None'}")
#     print(f"  Got lon: {gps_data.longitude:.4f if gps_data.longitude else 'None'}")
#     assert gps_data.latitude is not None
#     assert gps_data.longitude is not None
#     print("  ✓ PASSED\n")


# def test_zero_coordinates_filtered():
#     """Test that zero coordinates are properly filtered"""
#     nmea_data = (
#         "$GPRMC,123519,A,0000.000,N,00000.000,E,022.4,084.4,230394,003.1,W*47\r\n"
#         "$GPGLL,4807.038,N,01131.000,E,123520,A*7D\r\n"
#     ).encode()
    
#     serial = MockSerial(nmea_data)
#     reader = GPSReader(serial)
#     gps_data = reader.read_and_parse()
    
#     print("Test 4: Zero coordinates from RMC")
#     print(f"  is_valid() should be False: {gps_data.is_valid()}")
#     assert gps_data.is_valid() == False
#     print("  ✓ PASSED\n")


# def test_gsv_parsing():
#     """Test GSV satellite parsing"""
#     nmea_data = (
#         "$GPGSV,3,1,11,03,03,111,00,04,15,270,00,06,01,010,00,13,06,292,00*74\r\n"
#         "$GPGSV,3,2,11,14,25,170,00,16,57,208,39,18,67,296,40,19,40,246,00*74\r\n"
#         "$GPGSV,3,3,11,22,42,067,42,24,14,311,43,27,05,244,00*4D\r\n"
#     ).encode()
    
#     serial = MockSerial(nmea_data)
#     reader = GPSReader(serial)
#     gps_data = reader.read_and_parse()
    
#     print("Test 5: GSV satellite data parsing")
#     print(f"  Satellites in view: {gps_data.satellites_in_view}")
#     print(f"  Number of satellite records: {len(gps_data.satellite_info)}")
#     assert gps_data.satellites_in_view == 11
#     assert len(gps_data.satellite_info) > 0
#     print("  ✓ PASSED\n")


# if __name__ == "__main__":
#     print("Running GPS Redundancy Tests\n" + "="*40 + "\n")
    
#     test_valid_rmc_overrides_gll()
#     test_invalid_rmc_uses_gll()
#     test_gga_without_position_uses_gll()
#     test_zero_coordinates_filtered()
#     test_gsv_parsing()
    
#     print("All tests passed! ✓")
































