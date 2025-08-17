#!/usr/bin/env python3
"""
GPS Parser Module for SAM-M8Q GPS Module
Parses NMEA sentences and provides human-readable GPS data
"""

import time
from dataclasses import dataclass, field
from typing import Optional, List, Tuple
from datetime import datetime, timezone, timedelta


@dataclass
class GPSData:
    """
    Dataclass to store parsed GPS information
    """
    # Position data
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    altitude: Optional[float] = None  # meters above sea level
    
    # Time data
    utc_time: Optional[str] = None  # HH:MM:SS format
    local_time: Optional[str] = None  # HH:MM:SS format (US Central Time)
    date: Optional[str] = None  # DD/MM/YYYY format
    timestamp: Optional[float] = None  # Unix timestamp
    
    # Status data
    fix_quality: Optional[int] = None  # 0=invalid, 1=GPS, 2=DGPS
    fix_type: Optional[str] = None  # "No Fix", "2D", "3D"
    satellites_used: Optional[int] = None
    satellites_in_view: Optional[int] = None
    satellite_info: List[dict] = field(default_factory=list)  # From GSV
    
    # Accuracy data
    hdop: Optional[float] = None  # Horizontal dilution of precision
    vdop: Optional[float] = None  # Vertical dilution of precision
    pdop: Optional[float] = None  # Position dilution of precision
    
    # Motion data
    speed_knots: Optional[float] = None
    speed_kmh: Optional[float] = None
    course: Optional[float] = None  # True course in degrees
    
    # Additional info
    mode: Optional[str] = None  # A=Autonomous, D=Differential, N=Not valid
    status: Optional[str] = None  # A=Active, V=Void
    
    # Raw NMEA sentences for debugging
    last_rmc: Optional[str] = None
    last_gga: Optional[str] = None
    last_gsa: Optional[str] = None
    last_gsv: Optional[str] = None
    last_gll: Optional[str] = None
    
    # Update tracking
    last_update: Optional[float] = field(default_factory=time.time)
    last_valid_lat: Optional[float] = None
    last_valid_lon: Optional[float] = None
    
    def get_position_string(self) -> str:
        """Return formatted position string"""
        if self.latitude is not None and self.longitude is not None:
            lat_dir = 'N' if self.latitude >= 0 else 'S'
            lon_dir = 'E' if self.longitude >= 0 else 'W'
            return f"{abs(self.latitude):.6f}°{lat_dir}, {abs(self.longitude):.6f}°{lon_dir}"
        return "No Position"
    
    def get_time_string(self) -> str:
        """Return formatted time string with local time"""
        if self.local_time and self.date:
            return f"{self.date} {self.local_time} CST"
        elif self.local_time:
            return f"{self.local_time} CST"
        return "No Time"
    
    def get_status_string(self) -> str:
        """Return formatted status string"""
        if self.fix_type:
            return f"{self.fix_type} Fix ({self.satellites_used or 0} sats)"
        return "No Fix"
    
    def is_valid(self) -> bool:
        """Check if GPS data is valid"""
        return (self.status == 'A' and 
                self.latitude is not None and 
                self.longitude is not None and
                self.latitude != 0.0 and
                self.longitude != 0.0)
    
    def has_position_changed(self, threshold: float = 0.00001) -> bool:
        """Check if position has changed significantly from last valid position"""
        if not self.is_valid():
            return False
            
        if self.last_valid_lat is None or self.last_valid_lon is None:
            return True
            
        lat_change = abs(self.latitude - self.last_valid_lat)
        lon_change = abs(self.longitude - self.last_valid_lon)
        
        return lat_change > threshold or lon_change > threshold


class GPSReader:
    """
    GPS Reader class for parsing NMEA sentences from SAM-M8Q module
    """
    
    def __init__(self, serial_port):
        """
        Initialize GPS Reader
        
        Args:
            serial_port: Serial port object for GPS communication
        """
        self.serial = serial_port
        self.gps_data = GPSData()
        self.sentence_buffer = ""
        self.gsv_buffer = {}  # Buffer for multi-part GSV messages
        
        # US Central Time offset (adjust for DST as needed)
        # CST = UTC-6, CDT = UTC-5
        self.utc_offset_hours = -6  # Change to -5 for daylight saving time
        
    def read_and_parse(self, timeout: float = 1.0) -> GPSData:
        """
        Read data from GPS and parse NMEA sentences
        
        Args:
            timeout: Maximum time to wait for data
            
        Returns:
            Updated GPSData object
        """
        start_time = time.time()
        
        while (time.time() - start_time) < timeout:
            if self.serial.in_waiting:
                try:
                    # Read available data
                    data = self.serial.read(self.serial.in_waiting)
                    self.sentence_buffer += data.decode('ascii', errors='ignore')
                    
                    # Process complete sentences
                    while '\n' in self.sentence_buffer:
                        line, self.sentence_buffer = self.sentence_buffer.split('\n', 1)
                        line = line.strip()
                        
                        if line.startswith('$'):
                            self._parse_nmea_sentence(line)
                            
                except Exception as e:
                    # Continue on decode errors
                    pass
            else:
                time.sleep(0.01)  # Small delay to prevent CPU spinning
                
        return self.gps_data
    
    def _parse_nmea_sentence(self, sentence: str) -> None:
        """
        Parse a complete NMEA sentence
        
        Args:
            sentence: Complete NMEA sentence starting with $
        """
        if not self._verify_checksum(sentence):
            return
            
        # Remove checksum for parsing
        if '*' in sentence:
            sentence = sentence.split('*')[0]
            
        parts = sentence.split(',')
        sentence_type = parts[0]
        
        try:
            if sentence_type in ['$GPRMC', '$GNRMC']:
                self.parse_rmc(parts)
                self.gps_data.last_rmc = sentence
            elif sentence_type in ['$GPGGA', '$GNGGA']:
                self.parse_gga(parts)
                self.gps_data.last_gga = sentence
            elif sentence_type in ['$GPGSA', '$GNGSA']:
                self.parse_gsa(parts)
                self.gps_data.last_gsa = sentence
            elif sentence_type in ['$GPGSV', '$GNGSV']:
                self.parse_gsv(parts)
                self.gps_data.last_gsv = sentence
            elif sentence_type in ['$GPGLL', '$GNGLL']:
                self.parse_gll(parts)
                self.gps_data.last_gll = sentence
        except Exception:
            # Skip malformed sentences
            pass
    
    def _verify_checksum(self, sentence: str) -> bool:
        """
        Verify NMEA sentence checksum
        
        Args:
            sentence: NMEA sentence with checksum
            
        Returns:
            True if checksum is valid
        """
        if '*' not in sentence:
            return False
            
        try:
            data, checksum = sentence[1:].split('*')
            calculated = 0
            for char in data:
                calculated ^= ord(char)
            return int(checksum, 16) == calculated
        except:
            return False
    
    def parse_rmc(self, parts: List[str]) -> None:
        """
        Parse RMC (Recommended Minimum Course) sentence
        
        Format: $GPRMC,time,status,lat,NS,lon,EW,speed,course,date,mag_var,EW,mode*CS
        """
        if len(parts) < 12:
            return
            
        # Time
        if parts[1]:
            self.gps_data.utc_time = self._parse_time(parts[1])
            self.gps_data.local_time = self._convert_to_local_time(parts[1])
            
        # Status
        self.gps_data.status = parts[2] if parts[2] else None
        
        # Position
        if parts[3] and parts[4] and parts[5] and parts[6]:
            lat = self._parse_coordinate(parts[3], parts[4])
            lon = self._parse_coordinate(parts[5], parts[6])
            if lat is not None and lon is not None and lat != 0.0 and lon != 0.0:
                self.gps_data.latitude = lat
                self.gps_data.longitude = lon
            
        # Speed
        if parts[7]:
            try:
                self.gps_data.speed_knots = float(parts[7])
                self.gps_data.speed_kmh = self.gps_data.speed_knots * 1.852
            except ValueError:
                pass
                
        # Course
        if parts[8]:
            try:
                self.gps_data.course = float(parts[8])
            except ValueError:
                pass
                
        # Date
        if parts[9]:
            self.gps_data.date = self._parse_date(parts[9])
            
        # Mode (if available)
        if len(parts) > 12 and parts[12]:
            self.gps_data.mode = parts[12]
            
        # Update timestamp
        self.gps_data.last_update = time.time()
    
    def parse_gga(self, parts: List[str]) -> None:
        """
        Parse GGA (Global Positioning System Fix Data) sentence
        
        Format: $GPGGA,time,lat,NS,lon,EW,quality,sats,hdop,alt,M,sep,M,age,station*CS
        """
        if len(parts) < 14:
            return
            
        # Time
        if parts[1]:
            self.gps_data.utc_time = self._parse_time(parts[1])
            self.gps_data.local_time = self._convert_to_local_time(parts[1])
            
        # Position
        if parts[2] and parts[3] and parts[4] and parts[5]:
            lat = self._parse_coordinate(parts[2], parts[3])
            lon = self._parse_coordinate(parts[4], parts[5])
            if lat is not None and lon is not None and lat != 0.0 and lon != 0.0:
                self.gps_data.latitude = lat
                self.gps_data.longitude = lon
            
        # Fix quality
        if parts[6]:
            try:
                self.gps_data.fix_quality = int(parts[6])
            except ValueError:
                pass
                
        # Satellites used
        if parts[7]:
            try:
                self.gps_data.satellites_used = int(parts[7])
            except ValueError:
                pass
                
        # HDOP
        if parts[8]:
            try:
                self.gps_data.hdop = float(parts[8])
            except ValueError:
                pass
                
        # Altitude
        if parts[9]:
            try:
                self.gps_data.altitude = float(parts[9])
            except ValueError:
                pass
                
        # Update timestamp
        self.gps_data.last_update = time.time()
    
    def parse_gsa(self, parts: List[str]) -> None:
        """
        Parse GSA (Satellite status) sentence
        
        Format: $GPGSA,mode1,mode2,sat1,...,sat12,pdop,hdop,vdop*CS
        """
        if len(parts) < 18:
            return
            
        # Fix type
        if parts[2]:
            fix_types = {'1': 'No Fix', '2': '2D', '3': '3D'}
            self.gps_data.fix_type = fix_types.get(parts[2], 'Unknown')
            
        # DOP values
        if parts[15]:  # PDOP
            try:
                self.gps_data.pdop = float(parts[15])
            except ValueError:
                pass
                
        if parts[16]:  # HDOP
            try:
                self.gps_data.hdop = float(parts[16])
            except ValueError:
                pass
                
        if parts[17]:  # VDOP
            try:
                self.gps_data.vdop = float(parts[17])
            except ValueError:
                pass
                
        # Update timestamp
        self.gps_data.last_update = time.time()
    
    def parse_gsv(self, parts: List[str]) -> None:
        """
        Parse GSV (Satellites in View) sentence
        
        Format: $GPGSV,total_msgs,msg_num,sats_in_view,sat_num,elev,azim,snr,...*CS
        """
        if len(parts) < 4:
            return
            
        try:
            total_msgs = int(parts[1])
            msg_num = int(parts[2])
            sats_in_view = int(parts[3])
            
            # Store satellites in view
            self.gps_data.satellites_in_view = sats_in_view
            
            # Parse satellite information (up to 4 satellites per message)
            if msg_num == 1:
                self.gps_data.satellite_info = []
                
            for i in range(4, min(len(parts) - 1, 20), 4):
                if parts[i]:  # Satellite number exists
                    sat_info = {
                        'prn': int(parts[i]) if parts[i] else None,
                        'elevation': int(parts[i+1]) if i+1 < len(parts) and parts[i+1] else None,
                        'azimuth': int(parts[i+2]) if i+2 < len(parts) and parts[i+2] else None,
                        'snr': int(parts[i+3]) if i+3 < len(parts) and parts[i+3] else None
                    }
                    self.gps_data.satellite_info.append(sat_info)
        except (ValueError, IndexError):
            pass
    
    def parse_gll(self, parts: List[str]) -> None:
        """
        Parse GLL (Geographic Position - Latitude/Longitude) sentence
        Used as fallback when other sentences are invalid
        
        Format: $GPGLL,lat,NS,lon,EW,time,status,mode*CS
        """
        if len(parts) < 7:
            return
            
        # Position (use as fallback if main position data is invalid)
        if parts[1] and parts[2] and parts[3] and parts[4]:
            lat = self._parse_coordinate(parts[1], parts[2])
            lon = self._parse_coordinate(parts[3], parts[4])
            
            # Only use GLL data if we don't have valid position from RMC/GGA
            if (lat is not None and lon is not None and 
                lat != 0.0 and lon != 0.0 and
                (self.gps_data.latitude is None or self.gps_data.latitude == 0.0)):
                self.gps_data.latitude = lat
                self.gps_data.longitude = lon
                
        # Time
        if parts[5] and not self.gps_data.utc_time:
            self.gps_data.utc_time = self._parse_time(parts[5])
            self.gps_data.local_time = self._convert_to_local_time(parts[5])
            
        # Status
        if parts[6] and not self.gps_data.status:
            self.gps_data.status = parts[6]
            
        # Mode (if available)
        if len(parts) > 7 and parts[7] and not self.gps_data.mode:
            self.gps_data.mode = parts[7]
    
    def _convert_to_local_time(self, time_str: str) -> Optional[str]:
        """
        Convert UTC time to US Central Time
        
        Args:
            time_str: Time string in HHMMSS.SSS format
            
        Returns:
            Formatted local time string
        """
        try:
            if len(time_str) >= 6:
                hours = int(time_str[0:2])
                minutes = int(time_str[2:4])
                seconds = int(time_str[4:6])
                
                # Create a datetime object for today with UTC time
                utc_time = datetime.now(timezone.utc).replace(
                    hour=hours, minute=minutes, second=seconds, microsecond=0
                )
                
                # Convert to Central Time
                local_time = utc_time + timedelta(hours=self.utc_offset_hours)
                
                return local_time.strftime("%H:%M:%S")
        except:
            pass
        return None
    
    def _parse_coordinate(self, coord: str, direction: str) -> Optional[float]:
        """
        Parse NMEA coordinate to decimal degrees
        
        Args:
            coord: Coordinate string (DDMM.MMMM or DDDMM.MMMM)
            direction: N/S for latitude, E/W for longitude
            
        Returns:
            Decimal degrees (negative for S/W)
        """
        try:
            # Determine if latitude (2 digits) or longitude (3 digits) for degrees
            if len(coord.split('.')[0]) == 4:  # Latitude DDMM.MMMM
                degrees = float(coord[:2])
                minutes = float(coord[2:])
            else:  # Longitude DDDMM.MMMM
                degrees = float(coord[:3])
                minutes = float(coord[3:])
                
            decimal = degrees + (minutes / 60.0)
            
            # Apply direction
            if direction in ['S', 'W']:
                decimal = -decimal
                
            return decimal
        except:
            return None
    
    def _parse_time(self, time_str: str) -> Optional[str]:
        """
        Parse NMEA time to HH:MM:SS format
        
        Args:
            time_str: Time string in HHMMSS.SSS format
            
        Returns:
            Formatted time string
        """
        try:
            if len(time_str) >= 6:
                hours = time_str[0:2]
                minutes = time_str[2:4]
                seconds = time_str[4:6]
                return f"{hours}:{minutes}:{seconds}"
        except:
            pass
        return None
    
    def _parse_date(self, date_str: str) -> Optional[str]:
        """
        Parse NMEA date to DD/MM/YYYY format
        
        Args:
            date_str: Date string in DDMMYY format
            
        Returns:
            Formatted date string
        """
        try:
            if len(date_str) == 6:
                day = date_str[0:2]
                month = date_str[2:4]
                year = int(date_str[4:6])
                # Assume 2000s for years 00-99
                year += 2000
                return f"{day}/{month}/{year}"
        except:
            pass
        return None
    
    def get_summary(self) -> str:
        """
        Get a human-readable summary of current GPS status
        
        Returns:
            Multi-line string with GPS information
        """
        lines = [
            "GPS Status Summary",
            "-" * 20,
            f"Status: {self.gps_data.get_status_string()}",
            f"Position: {self.gps_data.get_position_string()}",
            f"Altitude: {self.gps_data.altitude:.1f}m" if self.gps_data.altitude else "Altitude: N/A",
            f"Time: {self.gps_data.get_time_string()}",
            f"Speed: {self.gps_data.speed_kmh:.1f} km/h" if self.gps_data.speed_kmh else "Speed: N/A",
            f"HDOP: {self.gps_data.hdop:.1f}" if self.gps_data.hdop else "HDOP: N/A",
            f"Sats in view: {self.gps_data.satellites_in_view}" if self.gps_data.satellites_in_view else "Sats: N/A",
        ]
        return "\n".join(lines)




































































































# #!/usr/bin/env python3
# """
# gpsParser.py - GPS NMEA sentence parser for SAM-M8Q module
# Parses NMEA sentences into human-readable data structures.
# """

# import time
# from dataclasses import dataclass, field
# from typing import Optional, List, Any


# @dataclass
# class GPSData:
#     """
#     Stores parsed GPS data from various NMEA sentences.
#     All coordinates are in decimal degrees format.
#     """
#     # Position data
#     latitude: Optional[float] = None
#     longitude: Optional[float] = None
#     altitude: Optional[float] = None  # meters above sea level
    
#     # Fix and quality data
#     fix_type: int = 0  # 0=invalid, 1=GPS fix, 2=DGPS fix
#     fix_quality: Optional[str] = None  # "No Fix", "2D", "3D"
#     satellites_used: int = 0
#     satellites_in_view: int = 0
    
#     # Dilution of precision
#     hdop: Optional[float] = None  # Horizontal dilution
#     vdop: Optional[float] = None  # Vertical dilution
#     pdop: Optional[float] = None  # Position dilution
    
#     # Time data
#     utc_time: Optional[str] = None  # HH:MM:SS format
#     utc_date: Optional[str] = None  # DD/MM/YYYY format
    
#     # Motion data
#     speed_knots: Optional[float] = None
#     speed_kmh: Optional[float] = None
#     course: Optional[float] = None  # Track angle in degrees
    
#     # Status
#     is_valid: bool = False
#     last_update: float = field(default_factory=time.time)
    
#     def __str__(self) -> str:
#         """Return human-readable string representation."""
#         if not self.is_valid:
#             return "GPS Data: No valid fix"
        
#         lat_dir = "N" if self.latitude >= 0 else "S"
#         lon_dir = "E" if self.longitude >= 0 else "W"
        
#         output = f"GPS Data (Valid Fix):\n"
#         output += f"  Position: {abs(self.latitude):.6f}°{lat_dir}, {abs(self.longitude):.6f}°{lon_dir}\n"
        
#         if self.altitude is not None:
#             output += f"  Altitude: {self.altitude:.1f} m\n"
        
#         output += f"  Fix: {self.fix_quality} ({self.satellites_used} satellites)\n"
        
#         if self.speed_kmh is not None:
#             output += f"  Speed: {self.speed_kmh:.1f} km/h\n"
        
#         if self.utc_time:
#             output += f"  Time: {self.utc_time}"
#             if self.utc_date:
#                 output += f" {self.utc_date}"
        
#         return output
    
#     def get_coordinates_string(self) -> str:
#         """Return a simple coordinate string for display."""
#         if not self.is_valid:
#             return "No GPS Fix"
        
#         lat_dir = "N" if self.latitude >= 0 else "S"
#         lon_dir = "E" if self.longitude >= 0 else "W"
        
#         return f"{abs(self.latitude):.6f}°{lat_dir}, {abs(self.longitude):.6f}°{lon_dir}"


# class MB_GPSReader:
#     """
#     Reads and parses NMEA sentences from a GPS module connected via serial/UART.
#     """
    
#     def __init__(self, serial_port: Any):
#         """
#         Initialize GPS reader with a serial port object.
        
#         Args:
#             serial_port: An open serial port object (e.g., from pyserial)
#         """
#         self.serial = serial_port
#         self.gps_data = GPSData()
#         self.buffer = ""
        
#     def update(self) -> bool:
#         """
#         Read available data from GPS and update the GPSData object.
        
#         Returns:
#             True if data was successfully parsed, False otherwise
#         """
#         parsed_any = False
        
#         try:
#             # Read available bytes
#             if self.serial.in_waiting > 0:
#                 raw_data = self.serial.read(self.serial.in_waiting)
#                 self.buffer += raw_data.decode('utf-8', errors='ignore')
                
#                 # Process complete lines
#                 while '\n' in self.buffer:
#                     line, self.buffer = self.buffer.split('\n', 1)
#                     line = line.strip()
                    
#                     if line.startswith('$'):
#                         if self._parse_nmea_sentence(line):
#                             parsed_any = True
#                             self.gps_data.last_update = time.time()
#         except Exception as e:
#             print(f"Error reading GPS data: {e}")
            
#         return parsed_any
    
#     def _parse_nmea_sentence(self, sentence: str) -> bool:
#         """
#         Parse a single NMEA sentence.
        
#         Args:
#             sentence: Complete NMEA sentence starting with $
            
#         Returns:
#             True if sentence was successfully parsed
#         """
#         if not self._verify_checksum(sentence):
#             return False
        
#         # Remove checksum for parsing
#         if '*' in sentence:
#             sentence = sentence.split('*')[0]
        
#         parts = sentence.split(',')
#         sentence_type = parts[0]
        
#         try:
#             if sentence_type in ['$GPRMC', '$GNRMC']:
#                 return self._parse_rmc(parts)
#             elif sentence_type in ['$GPGGA', '$GNGGA']:
#                 return self._parse_gga(parts)
#             elif sentence_type in ['$GPGSA', '$GNGSA']:
#                 return self._parse_gsa(parts)
#             elif sentence_type in ['$GPGSV', '$GNGSV']:
#                 return self._parse_gsv(parts)
#         except (IndexError, ValueError) as e:
#             print(f"Error parsing {sentence_type}: {e}")
#             return False
        
#         return False
    
#     def _verify_checksum(self, sentence: str) -> bool:
#         """
#         Verify NMEA sentence checksum.
        
#         Args:
#             sentence: Complete NMEA sentence with checksum
            
#         Returns:
#             True if checksum is valid or not present
#         """
#         if '*' not in sentence:
#             return True  # No checksum to verify
        
#         try:
#             data, checksum = sentence.split('*')
#             # Calculate XOR checksum of all chars between $ and *
#             calc_checksum = 0
#             for char in data[1:]:  # Skip the $
#                 calc_checksum ^= ord(char)
            
#             return calc_checksum == int(checksum, 16)
#         except:
#             return False
    
#     def _parse_rmc(self, parts: List[str]) -> bool:
#         """
#         Parse RMC (Recommended Minimum) sentence.
#         Contains position, velocity, and time.
        
#         Format: $GPRMC,time,status,lat,lat_dir,lon,lon_dir,speed,course,date,mag_var,mag_var_dir
#         """
#         if len(parts) < 12:
#             return False
        
#         # Check validity
#         status = parts[2]
#         self.gps_data.is_valid = (status == 'A')
        
#         if not self.gps_data.is_valid:
#             return False
        
#         # Parse time (HHMMSS.sss)
#         if parts[1]:
#             time_str = parts[1]
#             self.gps_data.utc_time = f"{time_str[0:2]}:{time_str[2:4]}:{time_str[4:6]}"
        
#         # Parse date (DDMMYY)
#         if parts[9]:
#             date_str = parts[9]
#             day = date_str[0:2]
#             month = date_str[2:4]
#             year = "20" + date_str[4:6]
#             self.gps_data.utc_date = f"{day}/{month}/{year}"
        
#         # Parse latitude
#         if parts[3] and parts[4]:
#             lat = self._parse_coordinate(parts[3], parts[4], is_latitude=True)
#             if lat is not None:
#                 self.gps_data.latitude = lat
        
#         # Parse longitude
#         if parts[5] and parts[6]:
#             lon = self._parse_coordinate(parts[5], parts[6], is_latitude=False)
#             if lon is not None:
#                 self.gps_data.longitude = lon
        
#         # Parse speed (knots)
#         if parts[7]:
#             try:
#                 self.gps_data.speed_knots = float(parts[7])
#                 self.gps_data.speed_kmh = self.gps_data.speed_knots * 1.852
#             except ValueError:
#                 pass
        
#         # Parse course
#         if parts[8]:
#             try:
#                 self.gps_data.course = float(parts[8])
#             except ValueError:
#                 pass
        
#         return True
    
#     def _parse_gga(self, parts: List[str]) -> bool:
#         """
#         Parse GGA (Global Positioning System Fix Data) sentence.
#         Contains position and fix quality.
        
#         Format: $GPGGA,time,lat,lat_dir,lon,lon_dir,quality,satellites,hdop,altitude,alt_units,
#                 geoid_height,geoid_units,dgps_time,dgps_station_id
#         """
#         if len(parts) < 15:
#             return False
        
#         # Parse fix quality
#         if parts[6]:
#             try:
#                 self.gps_data.fix_type = int(parts[6])
#                 self.gps_data.is_valid = (self.gps_data.fix_type > 0)
#             except ValueError:
#                 return False
        
#         if not self.gps_data.is_valid:
#             return False
        
#         # Parse time
#         if parts[1]:
#             time_str = parts[1]
#             self.gps_data.utc_time = f"{time_str[0:2]}:{time_str[2:4]}:{time_str[4:6]}"
        
#         # Parse latitude
#         if parts[2] and parts[3]:
#             lat = self._parse_coordinate(parts[2], parts[3], is_latitude=True)
#             if lat is not None:
#                 self.gps_data.latitude = lat
        
#         # Parse longitude
#         if parts[4] and parts[5]:
#             lon = self._parse_coordinate(parts[4], parts[5], is_latitude=False)
#             if lon is not None:
#                 self.gps_data.longitude = lon
        
#         # Parse satellites used
#         if parts[7]:
#             try:
#                 self.gps_data.satellites_used = int(parts[7])
#             except ValueError:
#                 pass
        
#         # Parse HDOP
#         if parts[8]:
#             try:
#                 self.gps_data.hdop = float(parts[8])
#             except ValueError:
#                 pass
        
#         # Parse altitude (meters)
#         if parts[9] and parts[10] == 'M':
#             try:
#                 self.gps_data.altitude = float(parts[9])
#             except ValueError:
#                 pass
        
#         return True
    
#     def _parse_gsa(self, parts: List[str]) -> bool:
#         """
#         Parse GSA (GPS DOP and active satellites) sentence.
#         Contains DOP values and fix mode.
        
#         Format: $GPGSA,mode1,mode2,sat1,sat2,...,sat12,pdop,hdop,vdop
#         """
#         if len(parts) < 18:
#             return False
        
#         # Parse fix mode
#         if parts[2]:
#             fix_mode = parts[2]
#             if fix_mode == '1':
#                 self.gps_data.fix_quality = "No Fix"
#             elif fix_mode == '2':
#                 self.gps_data.fix_quality = "2D"
#             elif fix_mode == '3':
#                 self.gps_data.fix_quality = "3D"
        
#         # Count active satellites
#         satellites = 0
#         for i in range(3, 15):
#             if parts[i]:
#                 satellites += 1
#         self.gps_data.satellites_used = satellites
        
#         # Parse PDOP
#         if parts[15]:
#             try:
#                 self.gps_data.pdop = float(parts[15])
#             except ValueError:
#                 pass
        
#         # Parse HDOP
#         if parts[16]:
#             try:
#                 self.gps_data.hdop = float(parts[16])
#             except ValueError:
#                 pass
        
#         # Parse VDOP
#         if parts[17]:
#             try:
#                 self.gps_data.vdop = float(parts[17])
#             except ValueError:
#                 pass
        
#         return True
    
#     def _parse_gsv(self, parts: List[str]) -> bool:
#         """
#         Parse GSV (Satellites in view) sentence.
        
#         Format: $GPGSV,total_msgs,msg_num,satellites_in_view,sat_data...
#         """
#         if len(parts) < 4:
#             return False
        
#         # Parse satellites in view
#         if parts[3]:
#             try:
#                 self.gps_data.satellites_in_view = int(parts[3])
#             except ValueError:
#                 pass
        
#         return True
    
#     def _parse_coordinate(self, coord_str: str, direction: str, is_latitude: bool) -> Optional[float]:
#         """
#         Convert NMEA coordinate format to decimal degrees.
        
#         Args:
#             coord_str: Coordinate string in NMEA format
#             direction: N/S for latitude, E/W for longitude
#             is_latitude: True if parsing latitude
            
#         Returns:
#             Decimal degrees or None if parsing fails
#         """
#         try:
#             if is_latitude:
#                 # Format: DDMM.MMMM
#                 degrees = float(coord_str[:2])
#                 minutes = float(coord_str[2:])
#             else:
#                 # Format: DDDMM.MMMM
#                 degrees = float(coord_str[:3])
#                 minutes = float(coord_str[3:])
            
#             decimal = degrees + (minutes / 60.0)
            
#             # Apply direction
#             if direction in ['S', 'W']:
#                 decimal = -decimal
            
#             return decimal
#         except (ValueError, IndexError):
#             return None
    
#     def get_data(self) -> GPSData:
#         """
#         Get the current GPS data object.
        
#         Returns:
#             Current GPSData object
#         """
#         self.update()
#         return self.gps_data
    
#     def has_fix(self) -> bool:
#         """
#         Check if GPS has a valid fix.
        
#         Returns:
#             True if GPS has valid position fix
#         """
#         return self.gps_data.is_valid
    
#     def get_age(self) -> float:
#         """
#         Get age of last GPS update in seconds.
        
#         Returns:
#             Seconds since last update
#         """
#         return time.time() - self.gps_data.last_update
    



















