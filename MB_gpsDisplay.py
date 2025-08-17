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
GPS Display Script for Raspberry Pi with SSD1306 OLED
Displays GPS fix status, latitude, and longitude on OLED screen
"""

# import time
# import serial
from PIL import Image, ImageDraw, ImageFont
import adafruit_ssd1306
import board
import busio
# from gpsParser import GPSReader



# OLED Configuration
OLED_WIDTH = 128
OLED_HEIGHT = 64
OLED_ADDR = 0x3C  # Default I2C address for SSD1306

# Display settings
UPDATE_INTERVAL = 1.0  # seconds between GPS reads
COORDINATE_PRECISION = 4  # decimal places for coordinates



class GPSDisplay:
    """
    Manages GPS data display on OLED screen
    """
    
    def __init__(self):
        """Initialize GPS and OLED display"""
        
        # Initialize I2C and OLED
        print("Initializing OLED display...")
        self.i2c = busio.I2C(board.SCL, board.SDA)
        self.oled = adafruit_ssd1306.SSD1306_I2C(OLED_WIDTH, OLED_HEIGHT, self.i2c, addr=OLED_ADDR)
        
        # Clear display
        self.oled.fill(0)
        self.oled.show()
        
        # Create image for drawing
        self.image = Image.new("1", (OLED_WIDTH, OLED_HEIGHT))
        self.draw = ImageDraw.Draw(self.image)
        
        # Load fonts (using larger font for better visibility)
        try:
            # Try to load a nice font - adjust path as needed
            self.font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)
            self.font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
        except:
            # Fallback to default font
            self.font_large = ImageFont.load_default()
            self.font_small = ImageFont.load_default()
        
        # Initialize serial port for GPS
        print("Initializing GPS...")
        try:
            self.serial = serial.Serial('/dev/serial0', 9600, timeout=1)
            self.gps = MB_GPSReader(self.serial)
        except Exception as e:
            print(f"Error initializing GPS: {e}")
            raise
        
        # Track last displayed values
        self.last_displayed_lat = None
        self.last_displayed_lon = None
        self.startup_message_shown = False
        
        print("GPS Display initialized successfully")
    


    def show_startup_message(self):
        """Display startup message while waiting for GPS fix"""
        self.draw.rectangle((0, 0, OLED_WIDTH, OLED_HEIGHT), outline=0, fill=0)
        
        # Title in yellow zone (top 16 pixels)
        self.draw.text((20, 0), "GPS TRACKER", font=self.font_large, fill=255)
        
        # Status in blue zone
        self.draw.text((15, 25), "Waiting for fix...", font=self.font_small, fill=255)
        self.draw.text((25, 40), "Please wait", font=self.font_small, fill=255)
        
        # Display the image
        self.oled.image(self.image)
        self.oled.show()
        self.startup_message_shown = True
    


    def display_gps_data(self, gps_data):
        """
        Display GPS data on OLED screen
        
        Args:
            gps_data: GPSData object from gpsParser
        """
        # Check if we have valid non-zero coordinates
        if not gps_data.is_valid():
            if not self.startup_message_shown:
                self.show_startup_message()
            return
        
        # Check if position has changed significantly
        if (self.last_displayed_lat is not None and 
            self.last_displayed_lon is not None):
            
            lat_changed = abs(gps_data.latitude - self.last_displayed_lat) > 0.0001
            lon_changed = abs(gps_data.longitude - self.last_displayed_lon) > 0.0001
            
            if not (lat_changed or lon_changed):
                return  # No significant change, don't update display
        
        # Clear the display buffer
        self.draw.rectangle((0, 0, OLED_WIDTH, OLED_HEIGHT), outline=0, fill=0)
        
        # Prepare display text
        fix_text = f"FIX: {gps_data.fix_type}"
        if gps_data.satellites_used:
            fix_text += f" ({gps_data.satellites_used})"
        
        lat_text = f"LAT: {gps_data.latitude:.{COORDINATE_PRECISION}f}"
        lon_text = f"LON: {gps_data.longitude:.{COORDINATE_PRECISION}f}"
        
        # Draw fix status in yellow zone (top 16 pixels)
        # Center the text
        bbox = self.draw.textbbox((0, 0), fix_text, font=self.font_large)
        text_width = bbox[2] - bbox[0]
        x_pos = (OLED_WIDTH - text_width) // 2
        self.draw.text((x_pos, 0), fix_text, font=self.font_large, fill=255)
        
        # Draw underline
        self.draw.line((10, 17, OLED_WIDTH-10, 17), fill=255, width=1)
        
        # Add blank line (spacing)
        y_position = 22
        
        # Draw latitude (with spacing)
        bbox = self.draw.textbbox((0, 0), lat_text, font=self.font_large)
        text_width = bbox[2] - bbox[0]
        x_pos = (OLED_WIDTH - text_width) // 2
        self.draw.text((x_pos, y_position), lat_text, font=self.font_large, fill=255)
        
        # Add spacing
        y_position += 20
        
        # Draw longitude
        bbox = self.draw.textbbox((0, 0), lon_text, font=self.font_large)
        text_width = bbox[2] - bbox[0]
        x_pos = (OLED_WIDTH - text_width) // 2
        self.draw.text((x_pos, y_position), lon_text, font=self.font_large, fill=255)
        
        # Update the display
        self.oled.image(self.image)
        self.oled.show()
        
        # Update last displayed values
        self.last_displayed_lat = gps_data.latitude
        self.last_displayed_lon = gps_data.longitude
        
        # Update the GPSData object's last valid position
        gps_data.last_valid_lat = gps_data.latitude
        gps_data.last_valid_lon = gps_data.longitude
        
        print(f"Display updated: {fix_text} | LAT: {gps_data.latitude:.{COORDINATE_PRECISION}f} | LON: {gps_data.longitude:.{COORDINATE_PRECISION}f}")
    


    def run(self):
        """Main loop to continuously read GPS and update display"""
        print("Starting GPS display loop...")
        print("Waiting for GPS fix with non-zero coordinates...")
        
        try:
            while True:
                # Read and parse GPS data
                gps_data = self.gps.read_and_parse(timeout=UPDATE_INTERVAL)
                
                # Update display if we have valid data
                self.display_gps_data(gps_data)
                
                # Small delay to prevent CPU overload
                time.sleep(0.1)
                
        except KeyboardInterrupt:
            print("\nShutting down GPS display...")
            self.cleanup()
        except Exception as e:
            print(f"Error in main loop: {e}")
            self.cleanup()
            raise
    

    
    def cleanup(self):
        """Clean up resources"""
        try:
            # Clear the display
            self.oled.fill(0)
            self.oled.show()
            
            # Close serial port
            if hasattr(self, 'serial') and self.serial.is_open:
                self.serial.close()
                
            print("Cleanup complete")
        except Exception as e:
            print(f"Error during cleanup: {e}")





def main():
    """Main entry point"""
    try:
        display = GPSDisplay()
        display.run()
    except Exception as e:
        print(f"Fatal error: {e}")
        return 1
    
    return 0



if __name__ == "__main__":
    exit(main())




































    
    
    
    
    
    
    
    