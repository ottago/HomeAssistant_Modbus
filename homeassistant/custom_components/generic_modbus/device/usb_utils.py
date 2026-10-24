#!/usr/bin/env python3
"""
USB Device Detection Utilities
Handles USB device attribute detection and path resolution
"""

import os
import glob
import logging
import re
from typing import Optional, Dict, List
from pathlib import Path

logger = logging.getLogger(__name__)


class USBDeviceDetector:
    """Detects and analyzes USB serial devices"""
    
    @staticmethod
    def get_all_serial_devices() -> List[str]:
        """Get all available serial device paths"""
        devices = []
        
        # Common serial device patterns
        patterns = [
            '/dev/ttyUSB*',
            '/dev/ttyACM*',
            '/dev/ttyAMA*',
            '/dev/cu.usbserial*',  # macOS
            '/dev/cu.usbmodem*',   # macOS
        ]
        
        for pattern in patterns:
            devices.extend(glob.glob(pattern))
        
        # Sort for consistent ordering
        devices.sort()
        logger.debug(f"Found {len(devices)} serial devices: {devices}")
        return devices
    
    @staticmethod
    def find_by_id_path(tty_path: str) -> Optional[str]:
        """Find the by-id path for a tty device"""
        try:
            by_id_dir = Path('/dev/serial/by-id')
            if not by_id_dir.exists():
                logger.debug("No /dev/serial/by-id directory found")
                return None
            
            # Resolve the real path of the tty device
            real_tty_path = os.path.realpath(tty_path)
            
            # Search through by-id symlinks
            for by_id_path in by_id_dir.iterdir():
                if by_id_path.is_symlink():
                    target = os.path.realpath(str(by_id_path))
                    if target == real_tty_path:
                        logger.debug(f"Found by-id path for {tty_path}: {by_id_path}")
                        return str(by_id_path)
            
            logger.debug(f"No by-id path found for {tty_path}")
            return None
            
        except Exception as e:
            logger.debug(f"Error finding by-id path for {tty_path}: {e}")
            return None
    
    @staticmethod
    def find_by_path_path(tty_path: str) -> Optional[str]:
        """Find the by-path path for a tty device"""
        try:
            by_path_dir = Path('/dev/serial/by-path')
            if not by_path_dir.exists():
                logger.debug("No /dev/serial/by-path directory found")
                return None
            
            # Resolve the real path of the tty device
            real_tty_path = os.path.realpath(tty_path)
            
            # Search through by-path symlinks
            for by_path_path in by_path_dir.iterdir():
                if by_path_path.is_symlink():
                    target = os.path.realpath(str(by_path_path))
                    if target == real_tty_path:
                        logger.debug(f"Found by-path path for {tty_path}: {by_path_path}")
                        return str(by_path_path)
            
            logger.debug(f"No by-path path found for {tty_path}")
            return None
            
        except Exception as e:
            logger.debug(f"Error finding by-path path for {tty_path}: {e}")
            return None
    
    @staticmethod
    def extract_usb_attributes_from_by_id(by_id_path: str) -> Dict[str, Optional[str]]:
        """Extract USB attributes from by-id path"""
        attributes = {
            'usb_manufacturer': None,
            'usb_product_name': None,
            'usb_serial': None,
            'usb_vendor_id': None,
            'usb_product_id': None
        }
        
        try:
            filename = os.path.basename(by_id_path)
            
            # Parse by-id filename format: usb-Manufacturer_Product_Serial-if00-port0
            # Example: usb-FTDI_FT232R_USB_UART_A50285BI-if00-port0
            if filename.startswith('usb-'):
                # Remove usb- prefix and -if00-port0 suffix
                clean_name = filename[4:]  # Remove 'usb-'
                clean_name = re.sub(r'-if\d+-port\d+$', '', clean_name)
                
                # Split by underscores, last part is usually serial if present
                parts = clean_name.split('_')
                
                if len(parts) >= 2:
                    # Try to identify serial number (usually alphanumeric at the end)
                    potential_serial = parts[-1]
                    if re.match(r'^[A-Z0-9]{6,}$', potential_serial):
                        attributes['usb_serial'] = potential_serial
                        product_parts = parts[:-1]
                    else:
                        product_parts = parts
                    
                    # First part is usually manufacturer
                    attributes['usb_manufacturer'] = parts[0].replace('_', ' ')
                    
                    # Remaining parts form product name
                    if len(product_parts) > 1:
                        attributes['usb_product_name'] = '_'.join(product_parts[1:]).replace('_', ' ')
                    else:
                        attributes['usb_product_name'] = clean_name.replace('_', ' ')
            
            logger.debug(f"Extracted USB attributes from {by_id_path}: {attributes}")
            
        except Exception as e:
            logger.debug(f"Error extracting USB attributes from {by_id_path}: {e}")
        
        return attributes
    
    @staticmethod
    def get_usb_attributes_via_sysfs(tty_path: str) -> Dict[str, Optional[str]]:
        """Get USB attributes via sysfs (Linux only)"""
        attributes = {
            'usb_manufacturer': None,
            'usb_product_name': None,
            'usb_serial': None,
            'usb_vendor_id': None,
            'usb_product_id': None
        }
        
        try:
            # Find the USB device in sysfs
            device_name = os.path.basename(tty_path)
            
            # Look for the device in sysfs
            sysfs_paths = [
                f'/sys/class/tty/{device_name}/device',
                f'/sys/class/tty/{device_name}/../..',
            ]
            
            usb_device_path = None
            for path in sysfs_paths:
                if os.path.exists(path):
                    # Walk up the directory tree to find USB device info
                    current_path = os.path.realpath(path)
                    while current_path != '/':
                        if os.path.exists(os.path.join(current_path, 'idVendor')):
                            usb_device_path = current_path
                            break
                        current_path = os.path.dirname(current_path)
                    if usb_device_path:
                        break
            
            if usb_device_path:
                # Read USB attributes from sysfs
                attr_files = {
                    'usb_vendor_id': 'idVendor',
                    'usb_product_id': 'idProduct',
                    'usb_manufacturer': 'manufacturer',
                    'usb_product_name': 'product',
                    'usb_serial': 'serial'
                }
                
                for attr_key, filename in attr_files.items():
                    file_path = os.path.join(usb_device_path, filename)
                    if os.path.exists(file_path):
                        try:
                            with open(file_path, 'r') as f:
                                value = f.read().strip()
                                if value:
                                    attributes[attr_key] = value
                        except Exception as e:
                            logger.debug(f"Error reading {file_path}: {e}")
                
                logger.debug(f"Got USB attributes via sysfs for {tty_path}: {attributes}")
            
        except Exception as e:
            logger.debug(f"Error getting USB attributes via sysfs for {tty_path}: {e}")
        
        return attributes
    
    @classmethod
    def get_comprehensive_usb_attributes(cls, tty_path: str) -> Dict[str, Optional[str]]:
        """Get USB attributes using all available methods"""
        attributes = {
            'usb_manufacturer': None,
            'usb_product_name': None,
            'usb_serial': None,
            'usb_vendor_id': None,
            'usb_product_id': None
        }
        
        # Method 1: Try by-id path
        by_id_path = cls.find_by_id_path(tty_path)
        if by_id_path:
            by_id_attrs = cls.extract_usb_attributes_from_by_id(by_id_path)
            # Update attributes with non-None values
            for key, value in by_id_attrs.items():
                if value is not None:
                    attributes[key] = value
        
        # Method 2: Try sysfs (Linux only)
        if os.path.exists('/sys'):
            sysfs_attrs = cls.get_usb_attributes_via_sysfs(tty_path)
            # Update attributes with non-None values, prefer sysfs for accuracy
            for key, value in sysfs_attrs.items():
                if value is not None:
                    attributes[key] = value
        
        return attributes
