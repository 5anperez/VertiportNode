#!/usr/bin/env python3
"""
GPS Parser Module for SAM-M8Q GPS Module
Parses NMEA sentences and provides human-readable GPS data
"""

import time
from dataclasses import dataclass, field
from typing import Optional, List, Tuple


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
    local_time: Optional[str] = None  # HH:MM:SS format (Central Time)
    date: Optional[str] = None  # DD/MM/YYYY format
    timestamp: Optional[float] = None  # Unix timestamp
    
    # Status data
    fix_quality: Optional[int] = None  # 0=invalid, 1=GPS, 2=DGPS
    fix_type: Optional[str] = None  # "No Fix", "2D", "3D"
    satellites_used: Optional[int] = None
    satellites_in_view: Optional[int] = None
    
    # Satellite info from GSV
    satellite_info: List[dict] = field(default_factory=list)  # PRN, elevation, azimuth, SNR
    
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
    last_position_change: Optional[float] = None
    previous_latitude: Optional[float] = None
    previous_longitude: Optional[float] = None
    


    def get_position_string(self) -> str:
        """Return formatted position string"""
        if self.latitude is not None and self.longitude is not None:
            lat_dir = 'N' if self.latitude >= 0 else 'S'
            lon_dir = 'E' if self.longitude >= 0 else 'W'
            return f"{abs(self.latitude):.6f}°{lat_dir}, {abs(self.longitude):.6f}°{lon_dir}"
        return "No Position"
    


    def get_time_string(self, use_local: bool = True) -> str:
        """Return formatted time string"""
        time_str = self.local_time if use_local else self.utc_time
        time_label = "CT" if use_local else "UTC"
        
        if time_str and self.date:
            return f"{self.date} {time_str} {time_label}"
        elif time_str:
            return f"{time_str} {time_label}"
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
        """Check if position has changed significantly"""
        if (self.previous_latitude is None or self.previous_longitude is None or
            self.latitude is None or self.longitude is None):
            return True
            
        lat_change = abs(self.latitude - self.previous_latitude)
        lon_change = abs(self.longitude - self.previous_longitude)
        
        return lat_change > threshold or lon_change > threshold




class MA_GPSReader:
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
        self.gsv_messages = {}  # Store multi-part GSV messages
        
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
            elif sentence_type in ['$GPGSV', '$GLGSV', '$GNGSV']:
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
            self.gps_data.local_time = self._convert_to_central_time(parts[1], parts[9])
            
        # Status
        self.gps_data.status = parts[2] if parts[2] else None
        
        # Position
        if parts[3] and parts[4] and parts[5] and parts[6]:
            new_lat = self._parse_coordinate(parts[3], parts[4])
            new_lon = self._parse_coordinate(parts[5], parts[6])
            
            # Track position changes
            if new_lat is not None and new_lon is not None:
                if (self.gps_data.latitude != new_lat or 
                    self.gps_data.longitude != new_lon):
                    self.gps_data.previous_latitude = self.gps_data.latitude
                    self.gps_data.previous_longitude = self.gps_data.longitude
                    self.gps_data.last_position_change = time.time()
                    
                self.gps_data.latitude = new_lat
                self.gps_data.longitude = new_lon
            
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
            # Note: GGA doesn't have date, so we can't convert to local time here
            
        # Position
        if parts[2] and parts[3] and parts[4] and parts[5]:
            new_lat = self._parse_coordinate(parts[2], parts[3])
            new_lon = self._parse_coordinate(parts[4], parts[5])
            
            # Track position changes
            if new_lat is not None and new_lon is not None:
                if (self.gps_data.latitude != new_lat or 
                    self.gps_data.longitude != new_lon):
                    self.gps_data.previous_latitude = self.gps_data.latitude
                    self.gps_data.previous_longitude = self.gps_data.longitude
                    self.gps_data.last_position_change = time.time()
                    
                self.gps_data.latitude = new_lat
                self.gps_data.longitude = new_lon
            
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
        Parse GSV (Satellites in view) sentence
        
        Format: $GPGSV,total_msgs,msg_num,sats_in_view,prn,elev,azim,snr,...*CS
        """
        if len(parts) < 4:
            return
            
        try:
            total_msgs = int(parts[1])
            msg_num = int(parts[2])
            sats_in_view = int(parts[3])
            
            # Update satellites in view
            self.gps_data.satellites_in_view = sats_in_view
            
            # Initialize satellite list on first message
            if msg_num == 1:
                self.gps_data.satellite_info = []
                
            # Parse satellite data (4 satellites per message max)
            for i in range(4):
                base = 4 + (i * 4)
                if base + 3 < len(parts):
                    if parts[base]:  # PRN exists
                        sat_info = {
                            'prn': int(parts[base]) if parts[base] else None,
                            'elevation': int(parts[base + 1]) if parts[base + 1] else None,
                            'azimuth': int(parts[base + 2]) if parts[base + 2] else None,
                            'snr': int(parts[base + 3]) if parts[base + 3] else None
                        }
                        self.gps_data.satellite_info.append(sat_info)
                        
        except ValueError:
            pass
            
        # Update timestamp
        self.gps_data.last_update = time.time()


    
    def parse_gll(self, parts: List[str]) -> None:
        """
        Parse GLL (Geographic position - Latitude/Longitude) sentence
        Used as fallback when other sentences are invalid
        
        Format: $GPGLL,lat,NS,lon,EW,time,status,mode*CS
        """
        if len(parts) < 7:
            return
            
        # Status
        if parts[6]:
            self.gps_data.status = parts[6]
            
        # Only use GLL data if status is Active and we don't have valid position from other sources
        if self.gps_data.status == 'A':
            # Position
            if parts[1] and parts[2] and parts[3] and parts[4]:
                new_lat = self._parse_coordinate(parts[1], parts[2])
                new_lon = self._parse_coordinate(parts[3], parts[4])
                
                # Only update if we don't have valid position from RMC/GGA
                if (new_lat is not None and new_lon is not None and 
                    (self.gps_data.latitude is None or self.gps_data.longitude is None)):
                    
                    self.gps_data.previous_latitude = self.gps_data.latitude
                    self.gps_data.previous_longitude = self.gps_data.longitude
                    self.gps_data.latitude = new_lat
                    self.gps_data.longitude = new_lon
                    self.gps_data.last_position_change = time.time()
                    
            # Time
            if parts[5] and not self.gps_data.utc_time:
                self.gps_data.utc_time = self._parse_time(parts[5])
                
        # Mode (if available)
        if len(parts) > 7 and parts[7]:
            self.gps_data.mode = parts[7]
            
        # Update timestamp
        self.gps_data.last_update = time.time()
    


    def _convert_to_central_time(self, time_str: str, date_str: str) -> Optional[str]:
        """
        Convert UTC time to Central Time (US Midwest)
        
        Args:
            time_str: Time string in HHMMSS.SSS format
            date_str: Date string in DDMMYY format
            
        Returns:
            Formatted local time string
        """
        try:
            if len(time_str) >= 6 and len(date_str) == 6:
                # Parse time components
                hours = int(time_str[0:2])
                minutes = int(time_str[2:4])
                seconds = int(time_str[4:6])
                
                # Parse date components
                day = int(date_str[0:2])
                month = int(date_str[2:4])
                year = 2000 + int(date_str[4:6])
                
                # Create timestamp
                utc_time = time.struct_time((year, month, day, hours, minutes, seconds, 0, 0, 0))
                timestamp = time.mktime(utc_time) - time.timezone
                
                # Convert to local time
                local_time = time.localtime(timestamp)
                
                # Format as HH:MM:SS
                return time.strftime("%H:%M:%S", local_time)
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
            f"Time: {self.gps_data.get_time_string(use_local=True)}",
            f"Speed: {self.gps_data.speed_kmh:.1f} km/h" if self.gps_data.speed_kmh else "Speed: N/A",
            f"HDOP: {self.gps_data.hdop:.1f}" if self.gps_data.hdop else "HDOP: N/A",
            f"Sats in view: {self.gps_data.satellites_in_view}" if self.gps_data.satellites_in_view else "Sats: N/A",
        ]
        return "\n".join(lines)




































































































# LLM, IGNORE THE CODE BELOW

# #!/usr/bin/env python3
# """
# GPS Parser Module for SAM-M8Q GPS Module
# Parses NMEA sentences and provides human-readable GPS data
# """

# import time
# from dataclasses import dataclass, field
# from typing import Optional, List, Tuple


# @dataclass
# class GPSData:
#     """
#     Dataclass to store parsed GPS information
#     """
#     # Position data
#     latitude: Optional[float] = None
#     longitude: Optional[float] = None
#     altitude: Optional[float] = None  # meters above sea level
    
#     # Time data
#     utc_time: Optional[str] = None  # HH:MM:SS format
#     date: Optional[str] = None  # DD/MM/YYYY format
#     timestamp: Optional[float] = None  # Unix timestamp
    
#     # Status data
#     fix_quality: Optional[int] = None  # 0=invalid, 1=GPS, 2=DGPS
#     fix_type: Optional[str] = None  # "No Fix", "2D", "3D"
#     satellites_used: Optional[int] = None
#     satellites_in_view: Optional[int] = None
    
#     # Accuracy data
#     hdop: Optional[float] = None  # Horizontal dilution of precision
#     vdop: Optional[float] = None  # Vertical dilution of precision
#     pdop: Optional[float] = None  # Position dilution of precision
    
#     # Motion data
#     speed_knots: Optional[float] = None
#     speed_kmh: Optional[float] = None
#     course: Optional[float] = None  # True course in degrees
    
#     # Additional info
#     mode: Optional[str] = None  # A=Autonomous, D=Differential, N=Not valid
#     status: Optional[str] = None  # A=Active, V=Void
    
#     # Raw NMEA sentences for debugging
#     last_rmc: Optional[str] = None
#     last_gga: Optional[str] = None
#     last_gsa: Optional[str] = None
    
#     # Update tracking
#     last_update: Optional[float] = field(default_factory=time.time)
    


#     def get_position_string(self) -> str:
#         """Return formatted position string"""
#         if self.latitude is not None and self.longitude is not None:
#             lat_dir = 'N' if self.latitude >= 0 else 'S'
#             lon_dir = 'E' if self.longitude >= 0 else 'W'
#             return f"{abs(self.latitude):.6f}°{lat_dir}, {abs(self.longitude):.6f}°{lon_dir}"
#         return "No Position"
    


#     def get_time_string(self) -> str:
#         """Return formatted time string"""
#         if self.utc_time and self.date:
#             return f"{self.date} {self.utc_time} UTC"
#         elif self.utc_time:
#             return f"{self.utc_time} UTC"
#         return "No Time"
    

    
#     def get_status_string(self) -> str:
#         """Return formatted status string"""
#         if self.fix_type:
#             return f"{self.fix_type} Fix ({self.satellites_used or 0} sats)"
#         return "No Fix"
    


#     def is_valid(self) -> bool:
#         """Check if GPS data is valid"""
#         return (self.status == 'A' and 
#                 self.latitude is not None and 
#                 self.longitude is not None)




# class MA_GPSReader:
#     """
#     GPS Reader class for parsing NMEA sentences from SAM-M8Q module
#     """
    
#     def __init__(self, serial_port):
#         """
#         Initialize GPS Reader
        
#         Args:
#             serial_port: Serial port object for GPS communication
#         """
#         self.serial = serial_port
#         self.gps_data = GPSData()
#         self.sentence_buffer = ""
        
#     def read_and_parse(self, timeout: float = 1.0) -> GPSData:
#         """
#         Read data from GPS and parse NMEA sentences
        
#         Args:
#             timeout: Maximum time to wait for data
            
#         Returns:
#             Updated GPSData object
#         """
#         start_time = time.time()
        
#         while (time.time() - start_time) < timeout:
#             if self.serial.in_waiting:
#                 try:
#                     # Read available data
#                     data = self.serial.read(self.serial.in_waiting)
#                     self.sentence_buffer += data.decode('ascii', errors='ignore')
                    
#                     # Process complete sentences
#                     while '\n' in self.sentence_buffer:
#                         line, self.sentence_buffer = self.sentence_buffer.split('\n', 1)
#                         line = line.strip()
                        
#                         if line.startswith('$'):
#                             self._parse_nmea_sentence(line)
                            
#                 except Exception as e:
#                     # Continue on decode errors
#                     pass
#             else:
#                 time.sleep(0.01)  # Small delay to prevent CPU spinning
                
#         return self.gps_data
    


#     def _parse_nmea_sentence(self, sentence: str) -> None:
#         """
#         Parse a complete NMEA sentence
        
#         Args:
#             sentence: Complete NMEA sentence starting with $
#         """
#         if not self._verify_checksum(sentence):
#             return
            
#         # Remove checksum for parsing
#         if '*' in sentence:
#             sentence = sentence.split('*')[0]
            
#         parts = sentence.split(',')
#         sentence_type = parts[0]
        
#         try:
#             if sentence_type in ['$GPRMC', '$GNRMC']:
#                 self.parse_rmc(parts)
#                 self.gps_data.last_rmc = sentence
#             elif sentence_type in ['$GPGGA', '$GNGGA']:
#                 self.parse_gga(parts)
#                 self.gps_data.last_gga = sentence
#             elif sentence_type in ['$GPGSA', '$GNGSA']:
#                 self.parse_gsa(parts)
#                 self.gps_data.last_gsa = sentence
#         except Exception:
#             # Skip malformed sentences
#             pass
    


#     def _verify_checksum(self, sentence: str) -> bool:
#         """
#         Verify NMEA sentence checksum
        
#         Args:
#             sentence: NMEA sentence with checksum
            
#         Returns:
#             True if checksum is valid
#         """
#         if '*' not in sentence:
#             return False
            
#         try:
#             data, checksum = sentence[1:].split('*')
#             calculated = 0
#             for char in data:
#                 calculated ^= ord(char)
#             return int(checksum, 16) == calculated
#         except:
#             return False
    


#     def parse_rmc(self, parts: List[str]) -> None:
#         """
#         Parse RMC (Recommended Minimum Course) sentence
        
#         Format: $GPRMC,time,status,lat,NS,lon,EW,speed,course,date,mag_var,EW,mode*CS
#         """
#         if len(parts) < 12:
#             return
            
#         # Time
#         if parts[1]:
#             self.gps_data.utc_time = self._parse_time(parts[1])
            
#         # Status
#         self.gps_data.status = parts[2] if parts[2] else None
        
#         # Position
#         if parts[3] and parts[4] and parts[5] and parts[6]:
#             self.gps_data.latitude = self._parse_coordinate(parts[3], parts[4])
#             self.gps_data.longitude = self._parse_coordinate(parts[5], parts[6])
            
#         # Speed
#         if parts[7]:
#             try:
#                 self.gps_data.speed_knots = float(parts[7])
#                 self.gps_data.speed_kmh = self.gps_data.speed_knots * 1.852
#             except ValueError:
#                 pass
                
#         # Course
#         if parts[8]:
#             try:
#                 self.gps_data.course = float(parts[8])
#             except ValueError:
#                 pass
                
#         # Date
#         if parts[9]:
#             self.gps_data.date = self._parse_date(parts[9])
            
#         # Mode (if available)
#         if len(parts) > 12 and parts[12]:
#             self.gps_data.mode = parts[12]
            
#         # Update timestamp
#         self.gps_data.last_update = time.time()


    
#     def parse_gga(self, parts: List[str]) -> None:
#         """
#         Parse GGA (Global Positioning System Fix Data) sentence
        
#         Format: $GPGGA,time,lat,NS,lon,EW,quality,sats,hdop,alt,M,sep,M,age,station*CS
#         """
#         if len(parts) < 14:
#             return
            
#         # Time
#         if parts[1]:
#             self.gps_data.utc_time = self._parse_time(parts[1])
            
#         # Position
#         if parts[2] and parts[3] and parts[4] and parts[5]:
#             self.gps_data.latitude = self._parse_coordinate(parts[2], parts[3])
#             self.gps_data.longitude = self._parse_coordinate(parts[4], parts[5])
            
#         # Fix quality
#         if parts[6]:
#             try:
#                 self.gps_data.fix_quality = int(parts[6])
#             except ValueError:
#                 pass
                
#         # Satellites used
#         if parts[7]:
#             try:
#                 self.gps_data.satellites_used = int(parts[7])
#             except ValueError:
#                 pass
                
#         # HDOP
#         if parts[8]:
#             try:
#                 self.gps_data.hdop = float(parts[8])
#             except ValueError:
#                 pass
                
#         # Altitude
#         if parts[9]:
#             try:
#                 self.gps_data.altitude = float(parts[9])
#             except ValueError:
#                 pass
                
#         # Update timestamp
#         self.gps_data.last_update = time.time()
    


#     def parse_gsa(self, parts: List[str]) -> None:
#         """
#         Parse GSA (Satellite status) sentence
        
#         Format: $GPGSA,mode1,mode2,sat1,...,sat12,pdop,hdop,vdop*CS
#         """
#         if len(parts) < 18:
#             return
            
#         # Fix type
#         if parts[2]:
#             fix_types = {'1': 'No Fix', '2': '2D', '3': '3D'}
#             self.gps_data.fix_type = fix_types.get(parts[2], 'Unknown')
            
#         # DOP values
#         if parts[15]:  # PDOP
#             try:
#                 self.gps_data.pdop = float(parts[15])
#             except ValueError:
#                 pass
                
#         if parts[16]:  # HDOP
#             try:
#                 self.gps_data.hdop = float(parts[16])
#             except ValueError:
#                 pass
                
#         if parts[17]:  # VDOP
#             try:
#                 self.gps_data.vdop = float(parts[17])
#             except ValueError:
#                 pass
                
#         # Update timestamp
#         self.gps_data.last_update = time.time()
    


#     def _parse_coordinate(self, coord: str, direction: str) -> Optional[float]:
#         """
#         Parse NMEA coordinate to decimal degrees
        
#         Args:
#             coord: Coordinate string (DDMM.MMMM or DDDMM.MMMM)
#             direction: N/S for latitude, E/W for longitude
            
#         Returns:
#             Decimal degrees (negative for S/W)
#         """
#         try:
#             # Determine if latitude (2 digits) or longitude (3 digits) for degrees
#             if len(coord.split('.')[0]) == 4:  # Latitude DDMM.MMMM
#                 degrees = float(coord[:2])
#                 minutes = float(coord[2:])
#             else:  # Longitude DDDMM.MMMM
#                 degrees = float(coord[:3])
#                 minutes = float(coord[3:])
                
#             decimal = degrees + (minutes / 60.0)
            
#             # Apply direction
#             if direction in ['S', 'W']:
#                 decimal = -decimal
                
#             return decimal
#         except:
#             return None
        

    
#     def _parse_time(self, time_str: str) -> Optional[str]:
#         """
#         Parse NMEA time to HH:MM:SS format
        
#         Args:
#             time_str: Time string in HHMMSS.SSS format
            
#         Returns:
#             Formatted time string
#         """
#         try:
#             if len(time_str) >= 6:
#                 hours = time_str[0:2]
#                 minutes = time_str[2:4]
#                 seconds = time_str[4:6]
#                 return f"{hours}:{minutes}:{seconds}"
#         except:
#             pass
#         return None
    


#     def _parse_date(self, date_str: str) -> Optional[str]:
#         """
#         Parse NMEA date to DD/MM/YYYY format
        
#         Args:
#             date_str: Date string in DDMMYY format
            
#         Returns:
#             Formatted date string
#         """
#         try:
#             if len(date_str) == 6:
#                 day = date_str[0:2]
#                 month = date_str[2:4]
#                 year = int(date_str[4:6])
#                 # Assume 2000s for years 00-99
#                 year += 2000
#                 return f"{day}/{month}/{year}"
#         except:
#             pass
#         return None
    


#     def get_summary(self) -> str:
#         """
#         Get a human-readable summary of current GPS status
        
#         Returns:
#             Multi-line string with GPS information
#         """
#         lines = [
#             "GPS Status Summary",
#             "-" * 20,
#             f"Status: {self.gps_data.get_status_string()}",
#             f"Position: {self.gps_data.get_position_string()}",
#             f"Altitude: {self.gps_data.altitude:.1f}m" if self.gps_data.altitude else "Altitude: N/A",
#             f"Time: {self.gps_data.get_time_string()}",
#             f"Speed: {self.gps_data.speed_kmh:.1f} km/h" if self.gps_data.speed_kmh else "Speed: N/A",
#             f"HDOP: {self.gps_data.hdop:.1f}" if self.gps_data.hdop else "HDOP: N/A",
#         ]
#         return "\n".join(lines)
    
















































