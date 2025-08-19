import serial
from MB_init import MB_GPSReader
import time
import traceback


"""
OUTPUT:

GPS Data (Valid Fix):
  Position: 42.328299°N, 83.397636°W
  Altitude: 207.5 m
  Fix: 3D (12 satellites)
  Speed: 0.0 km/h
  Time: 06:30:33 17/08/2025




INSTALLATION REQUIREMENTS:

# Install required packages
sudo apt-get update
sudo apt-get install -y python3-pip python3-pil python3-serial i2c-tools

# Install Python libraries
pip3 install adafruit-circuitpython-ssd1306 pillow

# Enable I2C and Serial
sudo raspi-config
# Enable I2C and Serial Port (disable login shell over serial)

# Add user to dialout group for serial access
sudo usermod -a -G dialout $USER

# Reboot for changes to take effect
sudo reboot
  
"""


# INITIAL GPS PARSER MODULE TEST. INTEGRATE WITH OLED DISPLAY BELOW THIS...

# ser = serial.Serial('/dev/serial0', 9600, timeout=1)
# gps = MB_GPSReader(ser)

# while True:
#     gps_data = gps.get_data()
#     print(gps_data)
#     time.sleep(1)


















#!/usr/bin/env python3
"""
GPS OLED Display for Raspberry Pi
Shows GPS status and coordinates on SSD1306 OLED display
"""

import time
import serial
import board
import busio
from PIL import Image, ImageDraw, ImageFont
import adafruit_ssd1306
from gpsParser import GPSReader


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
            self.font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14)
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
        self.draw.text((30, 20), "GPS NODE", font=self.font_large, fill=255)
        self.draw.text((25, 40), "Initializing...", font=self.font_small, fill=255)
        
        self.display.image(self.image)
        self.display.show()
        


    def display_waiting(self):
        """Display waiting for GPS fix message"""
        self.draw.rectangle((0, 0, self.width, self.height), outline=0, fill=0)
        
        # Waiting message
        self.draw.text((25, 25), "Waiting for", font=self.font_small, fill=255)
        self.draw.text((30, 40), "GPS Fix...", font=self.font_small, fill=255)
        
        self.display.image(self.image)
        self.display.show()
        


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
            
        # Format coordinates with 2 decimal places
        lat_rounded = round(gps_data.latitude, 2)
        lon_rounded = round(gps_data.longitude, 2)
        
        # Determine fix type string (simplified)
        if gps_data.fix_type:
            status_text = f"{gps_data.fix_type} Fix"
        else:
            status_text = "GPS Fix"
            
        # Check if position has changed (using rounded values)
        if (self.last_lat == lat_rounded and 
            self.last_lon == lon_rounded and
            self.last_status == status_text):
            return
            
        # Clear image
        self.draw.rectangle((0, 0, self.width, self.height), outline=0, fill=0)
        
        # Line 1: GPS Status (in yellow area - top 16 pixels)
        # Center the status text
        bbox = self.draw.textbbox((0, 0), status_text, font=self.font_large)
        text_width = bbox[2] - bbox[0]
        x_pos = (self.width - text_width) // 2
        self.draw.text((x_pos, 1), status_text, font=self.font_large, fill=255)
        
        # Underline
        self.draw.line((10, 18, self.width - 10, 18), fill=255, width=1)
        
        # Blank line (pixels 19-28)
        
        # Line 2: Latitude (pixels 29-44)
        lat_dir = 'N' if gps_data.latitude >= 0 else 'S'
        lat_text = f"{abs(lat_rounded):.2f}°{lat_dir}"
        # Center latitude text
        bbox = self.draw.textbbox((0, 0), lat_text, font=self.font_large)
        text_width = bbox[2] - bbox[0]
        x_pos = (self.width - text_width) // 2
        self.draw.text((x_pos, 29), lat_text, font=self.font_large, fill=255)
        
        # Blank line (pixels 45-48)
        
        # Line 3: Longitude (pixels 49-64)
        lon_dir = 'E' if gps_data.longitude >= 0 else 'W'
        lon_text = f"{abs(lon_rounded):.2f}°{lon_dir}"
        # Center longitude text
        bbox = self.draw.textbbox((0, 0), lon_text, font=self.font_large)
        text_width = bbox[2] - bbox[0]
        x_pos = (self.width - text_width) // 2
        self.draw.text((x_pos, 48), lon_text, font=self.font_large, fill=255)
        
        # Update display
        self.display.image(self.image)
        self.display.show()
        
        # Update last displayed values
        self.last_lat = lat_rounded
        self.last_lon = lon_rounded
        self.last_status = status_text
        
    def clear(self):
        """Clear the display"""
        self.display.fill(0)
        self.display.show()


def main():
    """Main function to run GPS OLED display"""
    print("Starting GPS OLED Display...")
    
    # Initialize display
    oled = GPSOLEDDisplay()
    oled.display_startup()
    time.sleep(2)
    
    # Initialize GPS serial connection
    try:
        # RPi hardware UART
        gps_serial = serial.Serial('/dev/serial0', 9600, timeout=1)
        gps_reader = GPSReader(gps_serial)
        print("GPS serial connection established")
    except Exception as e:
        print(f"Error opening GPS serial port: {e}")
        oled.draw.rectangle((0, 0, oled.width, oled.height), outline=0, fill=0)
        oled.draw.text((20, 25), "GPS Error!", font=oled.font_large, fill=255)
        oled.display.image(oled.image)
        oled.display.show()
        return
        
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



























# # MB test cases below

# #!/usr/bin/env python3
# """
# Test cases for GPS parser redundancy logic
# Tests failover between RMC, GGA, and GLL sentences
# """

# import io
# import time
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
#         if self.position >= len(self.data):
#             return b''
#         end = min(self.position + size, len(self.data))
#         result = self.data[self.position:end]
#         self.position = end
#         return result


# def calculate_checksum(sentence):
#     """Calculate NMEA checksum"""
#     checksum = 0
#     for char in sentence[1:]:  # Skip the $
#         checksum ^= ord(char)
#     return f"{sentence}*{checksum:02X}"


# def test_rmc_primary():
#     """Test that RMC is used as primary position source"""
#     print("\nTest 1: RMC as primary source")
#     print("-" * 40)
    
#     sentences = [
#         calculate_checksum("$GPRMC,123519,A,4807.038,N,01131.000,E,022.4,084.4,230394,003.1,W"),
#         calculate_checksum("$GPGGA,123519,4805.000,N,01130.000,E,1,08,0.9,545.4,M,46.9,M,,"),
#         calculate_checksum("$GPGLL,4806.000,N,01132.000,E,123519,A"),
#     ]
    
#     data = "\r\n".join(sentences) + "\r\n"
#     mock_serial = MockSerial(data.encode())
#     reader = GPSReader(mock_serial)
    
#     gps_data = reader.read_and_parse(timeout=0.5)
    
#     # Should use RMC coordinates (4807.038,N,01131.000,E)
#     expected_lat = 48.0 + (7.038 / 60.0)
#     expected_lon = 11.0 + (31.000 / 60.0)
    
#     print(f"Expected: Lat={expected_lat:.6f}, Lon={expected_lon:.6f}")
#     print(f"Actual:   Lat={gps_data.latitude:.6f}, Lon={gps_data.longitude:.6f}")
#     print(f"Source: RMC (Primary)")
    
#     assert abs(gps_data.latitude - expected_lat) < 0.0001
#     assert abs(gps_data.longitude - expected_lon) < 0.0001
#     print("✓ PASSED: RMC coordinates used")


# def test_gga_fallback():
#     """Test that GGA is used when RMC has no position"""
#     print("\nTest 2: GGA fallback when RMC invalid")
#     print("-" * 40)
    
#     sentences = [
#         calculate_checksum("$GPRMC,123519,V,,,,,022.4,084.4,230394,003.1,W"),  # Invalid (V)
#         calculate_checksum("$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,"),
#         calculate_checksum("$GPGLL,4806.000,N,01132.000,E,123519,A"),
#     ]
    
#     data = "\r\n".join(sentences) + "\r\n"
#     mock_serial = MockSerial(data.encode())
#     reader = GPSReader(mock_serial)
    
#     gps_data = reader.read_and_parse(timeout=0.5)
    
#     # Should use GGA coordinates
#     expected_lat = 48.0 + (7.038 / 60.0)
#     expected_lon = 11.0 + (31.000 / 60.0)
    
#     print(f"Expected: Lat={expected_lat:.6f}, Lon={expected_lon:.6f}")
#     print(f"Actual:   Lat={gps_data.latitude:.6f}, Lon={gps_data.longitude:.6f}")
#     print(f"Source: GGA (Fallback)")
    
#     assert abs(gps_data.latitude - expected_lat) < 0.0001
#     assert abs(gps_data.longitude - expected_lon) < 0.0001
#     print("✓ PASSED: GGA coordinates used as fallback")


# def test_gll_last_resort():
#     """Test that GLL is used only when RMC and GGA have no position"""
#     print("\nTest 3: GLL as last resort")
#     print("-" * 40)
    
#     sentences = [
#         calculate_checksum("$GPRMC,123519,V,,,,,022.4,084.4,230394,003.1,W"),  # Invalid
#         calculate_checksum("$GPGGA,123519,,,,,0,00,0.9,545.4,M,46.9,M,,"),  # No fix
#         calculate_checksum("$GPGLL,4807.038,N,01131.000,E,123519,A"),  # Valid
#     ]
    
#     data = "\r\n".join(sentences) + "\r\n"
#     mock_serial = MockSerial(data.encode())
#     reader = GPSReader(mock_serial)
    
#     gps_data = reader.read_and_parse(timeout=0.5)
    
#     # Should use GLL coordinates
#     expected_lat = 48.0 + (7.038 / 60.0)
#     expected_lon = 11.0 + (31.000 / 60.0)
    
#     print(f"Expected: Lat={expected_lat:.6f}, Lon={expected_lon:.6f}")
#     print(f"Actual:   Lat={gps_data.latitude:.6f}, Lon={gps_data.longitude:.6f}")
#     print(f"Source: GLL (Last Resort)")
    
#     assert abs(gps_data.latitude - expected_lat) < 0.0001
#     assert abs(gps_data.longitude - expected_lon) < 0.0001
#     print("✓ PASSED: GLL coordinates used as last resort")


# def test_invalid_gll_ignored():
#     """Test that invalid GLL is ignored when RMC is valid"""
#     print("\nTest 4: Invalid GLL ignored with valid RMC")
#     print("-" * 40)
    
#     sentences = [
#         calculate_checksum("$GPRMC,123519,A,4807.038,N,01131.000,E,022.4,084.4,230394,003.1,W"),
#         calculate_checksum("$GPGLL,4806.000,N,01132.000,E,123519,V"),  # Void status
#     ]
    
#     data = "\r\n".join(sentences) + "\r\n"
#     mock_serial = MockSerial(data.encode())
#     reader = GPSReader(mock_serial)
    
#     gps_data = reader.read_and_parse(timeout=0.5)
    
#     # Should use RMC coordinates, not GLL
#     expected_lat = 48.0 + (7.038 / 60.0)
#     expected_lon = 11.0 + (31.000 / 60.0)
    
#     print(f"Expected: Lat={expected_lat:.6f}, Lon={expected_lon:.6f}")
#     print(f"Actual:   Lat={gps_data.latitude:.6f}, Lon={gps_data.longitude:.6f}")
#     print(f"Source: RMC (GLL ignored due to void status)")
    
#     assert abs(gps_data.latitude - expected_lat) < 0.0001
#     assert abs(gps_data.longitude - expected_lon) < 0.0001
#     print("✓ PASSED: Invalid GLL ignored")


# def test_zero_coordinates_invalid():
#     """Test that zero coordinates are considered invalid"""
#     print("\nTest 5: Zero coordinates treated as invalid")
#     print("-" * 40)
    
#     sentences = [
#         calculate_checksum("$GPRMC,123519,A,0000.000,N,00000.000,E,022.4,084.4,230394,003.1,W"),
#     ]
    
#     data = "\r\n".join(sentences) + "\r\n"
#     mock_serial = MockSerial(data.encode())
#     reader = GPSReader(mock_serial)
    
#     gps_data = reader.read_and_parse(timeout=0.5)
    
#     print(f"Latitude: {gps_data.latitude}")
#     print(f"Longitude: {gps_data.longitude}")
#     print(f"Is Valid: {gps_data.is_valid()}")
    
#     assert gps_data.latitude == 0.0
#     assert gps_data.longitude == 0.0
#     assert gps_data.is_valid() == False
#     print("✓ PASSED: Zero coordinates marked as invalid")


# def test_gsv_satellite_parsing():
#     """Test GSV satellite information parsing"""
#     print("\nTest 6: GSV satellite information")
#     print("-" * 40)
    
#     sentences = [
#         calculate_checksum("$GPGSV,2,1,08,01,40,083,46,02,17,308,41,12,07,344,39,14,22,228,45"),
#         calculate_checksum("$GPGSV,2,2,08,17,40,208,46,19,36,149,42,24,12,273,44,25,25,111,37"),
#     ]
    
#     data = "\r\n".join(sentences) + "\r\n"
#     mock_serial = MockSerial(data.encode())
#     reader = GPSReader(mock_serial)
    
#     gps_data = reader.read_and_parse(timeout=0.5)
    
#     print(f"Satellites in view: {gps_data.satellites_in_view}")
#     print(f"Satellite info count: {len(gps_data.satellite_info)}")
    
#     assert gps_data.satellites_in_view == 8
#     assert len(gps_data.satellite_info) == 8
#     print("✓ PASSED: GSV satellite data parsed")


# def test_position_change_tracking():
#     """Test that position changes are tracked"""
#     print("\nTest 7: Position change tracking")
#     print("-" * 40)
    
#     sentences1 = [
#         calculate_checksum("$GPRMC,123519,A,4807.038,N,01131.000,E,022.4,084.4,230394,003.1,W"),
#     ]
    
#     sentences2 = [
#         calculate_checksum("$GPRMC,123520,A,4807.039,N,01131.001,E,022.4,084.4,230394,003.1,W"),
#     ]
    
#     data1 = "\r\n".join(sentences1) + "\r\n"
#     data2 = "\r\n".join(sentences2) + "\r\n"
    
#     # First position
#     mock_serial = MockSerial(data1.encode())
#     reader = GPSReader(mock_serial)
#     gps_data = reader.read_and_parse(timeout=0.5)
    
#     first_lat = gps_data.latitude
#     first_lon = gps_data.longitude
    
#     # Second position
#     mock_serial = MockSerial(data2.encode())
#     reader = GPSReader(mock_serial)
#     gps_data = reader.read_and_parse(timeout=0.5)
    
#     print(f"First position:  Lat={first_lat:.6f}, Lon={first_lon:.6f}")
#     print(f"Second position: Lat={gps_data.latitude:.6f}, Lon={gps_data.longitude:.6f}")
#     print(f"Previous stored: Lat={gps_data.previous_latitude:.6f}, Lon={gps_data.previous_longitude:.6f}")
#     print(f"Position changed: {gps_data.has_position_changed()}")
    
#     assert gps_data.previous_latitude == first_lat
#     assert gps_data.previous_longitude == first_lon
#     assert gps_data.has_position_changed() == True
#     print("✓ PASSED: Position changes tracked correctly")


# def run_all_tests():
#     """Run all test cases"""
#     print("=" * 50)
#     print("GPS REDUNDANCY LOGIC TEST SUITE")
#     print("=" * 50)
    
#     tests = [
#         test_rmc_primary,
#         test_gga_fallback,
#         test_gll_last_resort,
#         test_invalid_gll_ignored,
#         test_zero_coordinates_invalid,
#         test_gsv_satellite_parsing,
#         test_position_change_tracking,
#     ]
    
#     passed = 0
#     failed = 0
    
#     for test in tests:
#         try:
#             test()
#             passed += 1
#         except AssertionError as e:
#             print(f"✗ FAILED: {e}")
#             failed += 1
#         except Exception as e:
#             print(f"✗ ERROR: {e}")
#             failed += 1
    
#     print("\n" + "=" * 50)
#     print(f"RESULTS: {passed} passed, {failed} failed")
#     print("=" * 50)
    
#     return failed == 0


# if __name__ == "__main__":
#     success = run_all_tests()
#     exit(0 if success else 1)







































































# # OLD GPS DISPLAY SCRIPT, WHERE THE TEXT WAS CENTERED!

# #!/usr/bin/env python3
# """
# GPS Display Script for Raspberry Pi with SSD1306 OLED
# Displays GPS fix status, latitude, and longitude on OLED screen
# """

# # import time
# # import serial
# from PIL import Image, ImageDraw, ImageFont
# import adafruit_ssd1306
# import board
# import busio
# # from gpsParser import GPSReader


# # OLED Configuration
# OLED_WIDTH = 128
# OLED_HEIGHT = 64
# OLED_ADDR = 0x3C  # Default I2C address for SSD1306

# # Display settings
# UPDATE_INTERVAL = 1.0  # seconds between GPS reads
# COORDINATE_PRECISION = 4  # decimal places for coordinates

# DEBUG = True


# def with_checksum(payload: str) -> str:
#     # payload example: "$GPRMC,...."
#     data = payload[1:]  # drop leading $
#     cs = 0
#     for ch in data:
#         cs ^= ord(ch)
#     return f"{payload}*{cs:02X}"



# class GPSDisplay:
#     """
#     Manages GPS data display on OLED screen
#     """
    
#     def __init__(self):
#         """Initialize GPS and OLED display"""
        
#         # Initialize I2C and OLED
#         print("Initializing OLED display...")
#         self.i2c = busio.I2C(board.SCL, board.SDA)
#         self.oled = adafruit_ssd1306.SSD1306_I2C(OLED_WIDTH, OLED_HEIGHT, self.i2c, addr=OLED_ADDR)
        
#         # Clear display
#         self.oled.fill(0)
#         self.oled.show()
        
#         # Create image for drawing
#         self.image = Image.new("1", (OLED_WIDTH, OLED_HEIGHT))
#         self.draw = ImageDraw.Draw(self.image)
        
#         # Load fonts (using larger font for better visibility)
#         try:
#             # Try to load a nice font - adjust path as needed
#             self.font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)
#             self.font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
#         except:
#             # Fallback to default font
#             self.font_large = ImageFont.load_default()
#             self.font_small = ImageFont.load_default()
        
#         # Initialize serial port for GPS
#         print("Initializing GPS...")
#         try:
#             if DEBUG:
#                 print("DEBUG MODE")
#                 self.gps = MB_GPSReader(None)
#             else:
#                 self.serial = serial.Serial('/dev/serial0', 9600, timeout=1)
#                 self.gps = MB_GPSReader(self.serial)
#         except Exception as e:
#             print(f"Error initializing GPS: {e}")
#             raise
        
#         # Track last displayed values
#         self.last_displayed_lat = None
#         self.last_displayed_lon = None
#         self.startup_message_shown = False
        
#         print("GPS Display initialized successfully")
    


#     def show_startup_message(self):
#         """Display startup message while waiting for GPS fix"""
#         self.draw.rectangle((0, 0, OLED_WIDTH, OLED_HEIGHT), outline=0, fill=0)
        
#         # Title in yellow zone (top 16 pixels)
#         self.draw.text((20, 0), "GPS TRACKER", font=self.font_large, fill=255)
        
#         # Status in blue zone
#         self.draw.text((15, 25), "Waiting for fix...", font=self.font_small, fill=255)
#         self.draw.text((25, 40), "Please wait", font=self.font_small, fill=255)
        
#         # Display the image
#         self.oled.image(self.image)
#         self.oled.show()
#         self.startup_message_shown = True
    


#     def display_gps_data(self, gps_data):
#         """
#         Display GPS data on OLED screen
        
#         Args:
#             gps_data: GPSData object from gpsParser
#         """
#         # Check if we have valid non-zero coordinates
#         if not gps_data.is_valid():
#             if not self.startup_message_shown:
#                 self.show_startup_message()
#             return
        
#         # Check if position has changed significantly
#         if (self.last_displayed_lat is not None and 
#             self.last_displayed_lon is not None):
            
#             lat_changed = abs(gps_data.latitude - self.last_displayed_lat) > 0.0001
#             lon_changed = abs(gps_data.longitude - self.last_displayed_lon) > 0.0001
            
#             if not (lat_changed or lon_changed):
#                 return  # No significant change, don't update display
        
#         # Clear the display buffer
#         self.draw.rectangle((0, 0, OLED_WIDTH, OLED_HEIGHT), outline=0, fill=0)
        
#         # Prepare display text
#         fix_text = f"FIX: {gps_data.fix_type}"
#         if gps_data.satellites_used:
#             fix_text += f" ({gps_data.satellites_used})"
        
#         lat_text = f"LAT: {gps_data.latitude:.{COORDINATE_PRECISION}f}"
#         lon_text = f"LON: {gps_data.longitude:.{COORDINATE_PRECISION}f}"
        
#         # Draw fix status in yellow zone (top 16 pixels)
#         # Center the text
#         bbox = self.draw.textbbox((0, 0), fix_text, font=self.font_large)
#         text_width = bbox[2] - bbox[0]
#         x_pos = (OLED_WIDTH - text_width) // 2
#         self.draw.text((x_pos, 0), fix_text, font=self.font_large, fill=255)
        
#         # Draw underline
#         self.draw.line((10, 17, OLED_WIDTH-10, 17), fill=255, width=1)
        
#         # Add blank line (spacing)
#         y_position = 22
        
#         # Draw latitude (with spacing)
#         bbox = self.draw.textbbox((0, 0), lat_text, font=self.font_large)
#         text_width = bbox[2] - bbox[0]
#         x_pos = (OLED_WIDTH - text_width) // 2
#         self.draw.text((x_pos, y_position), lat_text, font=self.font_large, fill=255)
        
#         # Add spacing
#         y_position += 20
        
#         # Draw longitude
#         bbox = self.draw.textbbox((0, 0), lon_text, font=self.font_large)
#         text_width = bbox[2] - bbox[0]
#         x_pos = (OLED_WIDTH - text_width) // 2
#         self.draw.text((x_pos, y_position), lon_text, font=self.font_large, fill=255)
        
#         # Update the display
#         self.oled.image(self.image)
#         self.oled.show()
        
#         # Update last displayed values
#         self.last_displayed_lat = gps_data.latitude
#         self.last_displayed_lon = gps_data.longitude
        
#         # Update the GPSData object's last valid position
#         gps_data.last_valid_lat = gps_data.latitude
#         gps_data.last_valid_lon = gps_data.longitude
        
#         print(f"Display updated: {fix_text} | LAT: {gps_data.latitude:.{COORDINATE_PRECISION}f} | LON: {gps_data.longitude:.{COORDINATE_PRECISION}f}")
        
        
    
    


#     def run(self):
#         """Main loop to continuously read GPS and update display"""
#         print("Starting GPS display loop...")
#         print("Waiting for GPS fix with non-zero coordinates...")
        
#         if DEBUG:
#             print("ENTERING DEBUG MODE")
#             # 1) RMC invalid -> GLL should fill
#             self.gps._parse_nmea_sentence(with_checksum("$GPRMC,123519,V,,,,,,,230394,,,A"))
#             self.gps._parse_nmea_sentence(with_checksum("$GPGLL,4916.45,N,12311.12,W,123520,A,A"))
#             print(f"Status: {self.gps.gps_data.status}")
#             print(f"Latitude: {self.gps.gps_data.latitude}")
#             assert self.gps.gps_data.status == 'A'
#             assert self.gps.gps_data.latitude is not None
#             print(f"DEBUG MODE 1 COMPLETE")
#             print("DEBUG MODE 1 COMPLETE")

#             # 2) RMC valid -> GLL 'V' must NOT demote
#             # reader = MA_GPSReader(None)
#             self.gps._parse_nmea_sentence(with_checksum("$GPRMC,123519,A,4916.45,N,12311.12,W,0.5,054.7,230394,,,A"))
#             lat_before = self.gps.gps_data.latitude
#             self.gps._parse_nmea_sentence(with_checksum("$GPGLL,4916.45,N,12311.12,W,123521,V,A"))
#             print(f"Status: {self.gps.gps_data.status}")
#             assert self.gps.gps_data.status == 'A'
#             assert self.gps.gps_data.latitude == lat_before
#             print("DEBUG MODE 2 COMPLETE")
#             # 3) Only GLL valid -> should populate
#             # reader = MA_GPSReader(None)
#             self.gps._parse_nmea_sentence(with_checksum("$GPRMC,123519,V,,,,,,,230394,,,A"))
#             assert self.gps.gps_data.is_valid() == False
#             self.gps._parse_nmea_sentence(with_checksum("$GPGLL,4916.45,N,12311.12,W,123520,A,A"))
#             assert self.gps.gps_data.is_valid()
#             print("DEBUG MODE COMPLETE")
#             return
#         else:
#             try:
#                 while True:
#                     # Read and parse GPS data
#                     gps_data = self.gps.read_and_parse(timeout=UPDATE_INTERVAL)
                    
#                     # Update display if we have valid data
#                     self.display_gps_data(gps_data)
#                     print(self.gps.get_summary())
                    
#                     # Small delay to prevent CPU overload
#                     time.sleep(0.1)
                    
#             except KeyboardInterrupt:
#                 print("\nShutting down GPS display...")
#                 self.cleanup()
#             except Exception as e:
#                 print(f"Error in main loop: {e}")
#                 self.cleanup()
#                 raise
    

    
#     def cleanup(self):
#         """Clean up resources"""
#         try:
#             # Clear the display
#             self.oled.fill(0)
#             self.oled.show()
            
#             # Close serial port
#             if hasattr(self, 'serial') and self.serial.is_open:
#                 self.serial.close()
                
#             print("Cleanup complete")
#         except Exception as e:
#             print(f"Error during cleanup: {e}")





# def main():
#     """Main entry point"""
#     try:
#         display = GPSDisplay()
#         display.run()
#     except Exception as e:
#         print(f"Fatal error: {e}")
#         traceback.print_exc()
#         return 1
    
#     return 0



# if __name__ == "__main__":
#     exit(main())




































    
    
    
    
    
    
    
    