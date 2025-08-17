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
            
        # Check if position has changed
        if (self.last_lat == gps_data.latitude and 
            self.last_lon == gps_data.longitude and
            self.last_status == gps_data.get_status_string()):
            return
            
        # Clear image
        self.draw.rectangle((0, 0, self.width, self.height), outline=0, fill=0)
        
        # Line 1: GPS Status (in yellow area - top 16 pixels)
        status_text = gps_data.get_status_string()
        # Center the status text
        bbox = self.draw.textbbox((0, 0), status_text, font=self.font_large)
        text_width = bbox[2] - bbox[0]
        x_pos = (self.width - text_width) // 2
        self.draw.text((x_pos, 0), status_text, font=self.font_large, fill=255)
        
        # Underline
        self.draw.line((10, 18, self.width - 10, 18), fill=255, width=1)
        
        # Blank line (pixels 19-28)
        
        # Line 2: Latitude (pixels 29-44)
        lat_text = f"LAT: {gps_data.latitude:.4f}"
        self.draw.text((5, 29), lat_text, font=self.font_large, fill=255)
        
        # Blank line (pixels 45-48)
        
        # Line 3: Longitude (pixels 49-64)
        lon_text = f"LON: {gps_data.longitude:.4f}"
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
        gps_reader = MA_GPSReader(gps_serial)
        print("GPS serial connection established")
    except Exception as e:
        print(f"Error opening GPS serial port: {e}")
        oled.draw.rectangle((0, 0, oled.width, oled.height), outline=0, fill=0)
        oled.draw.text((10, 25), "GPS Error!", font=oled.font_large, fill=255)
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
































