import time
# import serial
# from gps_parser import GPSReader
from luma.core.interface.serial import i2c
from luma.oled.device import ssd1306
from luma.core.render import canvas
from PIL import ImageFont


# I2C bus 1, address from i2cdetect (you saw 0x3C)
serial_i2c = i2c(port=1, address=0x3C)
device = ssd1306(serial_i2c, width=128, height=64)




try:
    # 16 px font (~2 rows).
    # font16 = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
    font16 = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)
except OSError:
    # 8 px font (~1 row).
    font16 = ImageFont.load_default()  # fallback if font not found


with canvas(device) as draw:
    # Top yellow band is ~16 px high (y=0..15). If it clips, reduce to 14.
    draw.text((0, 0),  "Hello World!", font=font16, fill=255)
    # Lower blue section; pick a y that leaves some spacing
    draw.text((0, 32), "Hello World!", font=font16, fill=255)
    


# Keep the image on screen
while True:
    time.sleep(1)
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    