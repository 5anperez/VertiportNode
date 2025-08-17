#!/usr/bin/env python3
"""
gpsParser.py - GPS NMEA sentence parser for SAM-M8Q module
Parses NMEA sentences into human-readable data structures.
"""

import time
from dataclasses import dataclass, field
from typing import Optional, List, Any


@dataclass
class GPSData:
    """
    Stores parsed GPS data from various NMEA sentences.
    All coordinates are in decimal degrees format.
    """
    # Position data
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    altitude: Optional[float] = None  # meters above sea level
    
    # Fix and quality data
    fix_type: int = 0  # 0=invalid, 1=GPS fix, 2=DGPS fix
    fix_quality: Optional[str] = None  # "No Fix", "2D", "3D"
    satellites_used: int = 0
    satellites_in_view: int = 0
    
    # Dilution of precision
    hdop: Optional[float] = None  # Horizontal dilution
    vdop: Optional[float] = None  # Vertical dilution
    pdop: Optional[float] = None  # Position dilution
    
    # Time data
    utc_time: Optional[str] = None  # HH:MM:SS format
    utc_date: Optional[str] = None  # DD/MM/YYYY format
    
    # Motion data
    speed_knots: Optional[float] = None
    speed_kmh: Optional[float] = None
    course: Optional[float] = None  # Track angle in degrees
    
    # Status
    is_valid: bool = False
    last_update: float = field(default_factory=time.time)
    
    def __str__(self) -> str:
        """Return human-readable string representation."""
        if not self.is_valid:
            return "GPS Data: No valid fix"
        
        lat_dir = "N" if self.latitude >= 0 else "S"
        lon_dir = "E" if self.longitude >= 0 else "W"
        
        output = f"GPS Data (Valid Fix):\n"
        output += f"  Position: {abs(self.latitude):.6f}°{lat_dir}, {abs(self.longitude):.6f}°{lon_dir}\n"
        
        if self.altitude is not None:
            output += f"  Altitude: {self.altitude:.1f} m\n"
        
        output += f"  Fix: {self.fix_quality} ({self.satellites_used} satellites)\n"
        
        if self.speed_kmh is not None:
            output += f"  Speed: {self.speed_kmh:.1f} km/h\n"
        
        if self.utc_time:
            output += f"  Time: {self.utc_time}"
            if self.utc_date:
                output += f" {self.utc_date}"
        
        return output
    
    def get_coordinates_string(self) -> str:
        """Return a simple coordinate string for display."""
        if not self.is_valid:
            return "No GPS Fix"
        
        lat_dir = "N" if self.latitude >= 0 else "S"
        lon_dir = "E" if self.longitude >= 0 else "W"
        
        return f"{abs(self.latitude):.6f}°{lat_dir}, {abs(self.longitude):.6f}°{lon_dir}"


class GPSReader:
    """
    Reads and parses NMEA sentences from a GPS module connected via serial/UART.
    """
    
    def __init__(self, serial_port: Any):
        """
        Initialize GPS reader with a serial port object.
        
        Args:
            serial_port: An open serial port object (e.g., from pyserial)
        """
        self.serial = serial_port
        self.gps_data = GPSData()
        self.buffer = ""
        
    def update(self) -> bool:
        """
        Read available data from GPS and update the GPSData object.
        
        Returns:
            True if data was successfully parsed, False otherwise
        """
        parsed_any = False
        
        try:
            # Read available bytes
            if self.serial.in_waiting > 0:
                raw_data = self.serial.read(self.serial.in_waiting)
                self.buffer += raw_data.decode('utf-8', errors='ignore')
                
                # Process complete lines
                while '\n' in self.buffer:
                    line, self.buffer = self.buffer.split('\n', 1)
                    line = line.strip()
                    
                    if line.startswith('$'):
                        if self._parse_nmea_sentence(line):
                            parsed_any = True
                            self.gps_data.last_update = time.time()
        except Exception as e:
            print(f"Error reading GPS data: {e}")
            
        return parsed_any
    
    def _parse_nmea_sentence(self, sentence: str) -> bool:
        """
        Parse a single NMEA sentence.
        
        Args:
            sentence: Complete NMEA sentence starting with $
            
        Returns:
            True if sentence was successfully parsed
        """
        if not self._verify_checksum(sentence):
            return False
        
        # Remove checksum for parsing
        if '*' in sentence:
            sentence = sentence.split('*')[0]
        
        parts = sentence.split(',')
        sentence_type = parts[0]
        
        try:
            if sentence_type in ['$GPRMC', '$GNRMC']:
                return self._parse_rmc(parts)
            elif sentence_type in ['$GPGGA', '$GNGGA']:
                return self._parse_gga(parts)
            elif sentence_type in ['$GPGSA', '$GNGSA']:
                return self._parse_gsa(parts)
            elif sentence_type in ['$GPGSV', '$GNGSV']:
                return self._parse_gsv(parts)
        except (IndexError, ValueError) as e:
            print(f"Error parsing {sentence_type}: {e}")
            return False
        
        return False
    
    def _verify_checksum(self, sentence: str) -> bool:
        """
        Verify NMEA sentence checksum.
        
        Args:
            sentence: Complete NMEA sentence with checksum
            
        Returns:
            True if checksum is valid or not present
        """
        if '*' not in sentence:
            return True  # No checksum to verify
        
        try:
            data, checksum = sentence.split('*')
            # Calculate XOR checksum of all chars between $ and *
            calc_checksum = 0
            for char in data[1:]:  # Skip the $
                calc_checksum ^= ord(char)
            
            return calc_checksum == int(checksum, 16)
        except:
            return False
    
    def _parse_rmc(self, parts: List[str]) -> bool:
        """
        Parse RMC (Recommended Minimum) sentence.
        Contains position, velocity, and time.
        
        Format: $GPRMC,time,status,lat,lat_dir,lon,lon_dir,speed,course,date,mag_var,mag_var_dir
        """
        if len(parts) < 12:
            return False
        
        # Check validity
        status = parts[2]
        self.gps_data.is_valid = (status == 'A')
        
        if not self.gps_data.is_valid:
            return False
        
        # Parse time (HHMMSS.sss)
        if parts[1]:
            time_str = parts[1]
            self.gps_data.utc_time = f"{time_str[0:2]}:{time_str[2:4]}:{time_str[4:6]}"
        
        # Parse date (DDMMYY)
        if parts[9]:
            date_str = parts[9]
            day = date_str[0:2]
            month = date_str[2:4]
            year = "20" + date_str[4:6]
            self.gps_data.utc_date = f"{day}/{month}/{year}"
        
        # Parse latitude
        if parts[3] and parts[4]:
            lat = self._parse_coordinate(parts[3], parts[4], is_latitude=True)
            if lat is not None:
                self.gps_data.latitude = lat
        
        # Parse longitude
        if parts[5] and parts[6]:
            lon = self._parse_coordinate(parts[5], parts[6], is_latitude=False)
            if lon is not None:
                self.gps_data.longitude = lon
        
        # Parse speed (knots)
        if parts[7]:
            try:
                self.gps_data.speed_knots = float(parts[7])
                self.gps_data.speed_kmh = self.gps_data.speed_knots * 1.852
            except ValueError:
                pass
        
        # Parse course
        if parts[8]:
            try:
                self.gps_data.course = float(parts[8])
            except ValueError:
                pass
        
        return True
    
    def _parse_gga(self, parts: List[str]) -> bool:
        """
        Parse GGA (Global Positioning System Fix Data) sentence.
        Contains position and fix quality.
        
        Format: $GPGGA,time,lat,lat_dir,lon,lon_dir,quality,satellites,hdop,altitude,alt_units,
                geoid_height,geoid_units,dgps_time,dgps_station_id
        """
        if len(parts) < 15:
            return False
        
        # Parse fix quality
        if parts[6]:
            try:
                self.gps_data.fix_type = int(parts[6])
                self.gps_data.is_valid = (self.gps_data.fix_type > 0)
            except ValueError:
                return False
        
        if not self.gps_data.is_valid:
            return False
        
        # Parse time
        if parts[1]:
            time_str = parts[1]
            self.gps_data.utc_time = f"{time_str[0:2]}:{time_str[2:4]}:{time_str[4:6]}"
        
        # Parse latitude
        if parts[2] and parts[3]:
            lat = self._parse_coordinate(parts[2], parts[3], is_latitude=True)
            if lat is not None:
                self.gps_data.latitude = lat
        
        # Parse longitude
        if parts[4] and parts[5]:
            lon = self._parse_coordinate(parts[4], parts[5], is_latitude=False)
            if lon is not None:
                self.gps_data.longitude = lon
        
        # Parse satellites used
        if parts[7]:
            try:
                self.gps_data.satellites_used = int(parts[7])
            except ValueError:
                pass
        
        # Parse HDOP
        if parts[8]:
            try:
                self.gps_data.hdop = float(parts[8])
            except ValueError:
                pass
        
        # Parse altitude (meters)
        if parts[9] and parts[10] == 'M':
            try:
                self.gps_data.altitude = float(parts[9])
            except ValueError:
                pass
        
        return True
    
    def _parse_gsa(self, parts: List[str]) -> bool:
        """
        Parse GSA (GPS DOP and active satellites) sentence.
        Contains DOP values and fix mode.
        
        Format: $GPGSA,mode1,mode2,sat1,sat2,...,sat12,pdop,hdop,vdop
        """
        if len(parts) < 18:
            return False
        
        # Parse fix mode
        if parts[2]:
            fix_mode = parts[2]
            if fix_mode == '1':
                self.gps_data.fix_quality = "No Fix"
            elif fix_mode == '2':
                self.gps_data.fix_quality = "2D"
            elif fix_mode == '3':
                self.gps_data.fix_quality = "3D"
        
        # Count active satellites
        satellites = 0
        for i in range(3, 15):
            if parts[i]:
                satellites += 1
        self.gps_data.satellites_used = satellites
        
        # Parse PDOP
        if parts[15]:
            try:
                self.gps_data.pdop = float(parts[15])
            except ValueError:
                pass
        
        # Parse HDOP
        if parts[16]:
            try:
                self.gps_data.hdop = float(parts[16])
            except ValueError:
                pass
        
        # Parse VDOP
        if parts[17]:
            try:
                self.gps_data.vdop = float(parts[17])
            except ValueError:
                pass
        
        return True
    
    def _parse_gsv(self, parts: List[str]) -> bool:
        """
        Parse GSV (Satellites in view) sentence.
        
        Format: $GPGSV,total_msgs,msg_num,satellites_in_view,sat_data...
        """
        if len(parts) < 4:
            return False
        
        # Parse satellites in view
        if parts[3]:
            try:
                self.gps_data.satellites_in_view = int(parts[3])
            except ValueError:
                pass
        
        return True
    
    def _parse_coordinate(self, coord_str: str, direction: str, is_latitude: bool) -> Optional[float]:
        """
        Convert NMEA coordinate format to decimal degrees.
        
        Args:
            coord_str: Coordinate string in NMEA format
            direction: N/S for latitude, E/W for longitude
            is_latitude: True if parsing latitude
            
        Returns:
            Decimal degrees or None if parsing fails
        """
        try:
            if is_latitude:
                # Format: DDMM.MMMM
                degrees = float(coord_str[:2])
                minutes = float(coord_str[2:])
            else:
                # Format: DDDMM.MMMM
                degrees = float(coord_str[:3])
                minutes = float(coord_str[3:])
            
            decimal = degrees + (minutes / 60.0)
            
            # Apply direction
            if direction in ['S', 'W']:
                decimal = -decimal
            
            return decimal
        except (ValueError, IndexError):
            return None
    
    def get_data(self) -> GPSData:
        """
        Get the current GPS data object.
        
        Returns:
            Current GPSData object
        """
        return self.gps_data
    
    def has_fix(self) -> bool:
        """
        Check if GPS has a valid fix.
        
        Returns:
            True if GPS has valid position fix
        """
        return self.gps_data.is_valid
    
    def get_age(self) -> float:
        """
        Get age of last GPS update in seconds.
        
        Returns:
            Seconds since last update
        """
        return time.time() - self.gps_data.last_update
    



















