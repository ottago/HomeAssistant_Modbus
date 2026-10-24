#!/usr/bin/env python3
"""
Device Locator Service
Locates devices using stored identifiers with hybrid identification approach
"""

import os
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

from .device_identifiers import DeviceIdentifiers, DeviceMatch, ModbusSignature, StabilityLevel
from .usb_utils import USBDeviceDetector
# Import serial-dependent modules only when needed
# from .modbus_client import GenericModbusClient, FunctionCode

logger = logging.getLogger(__name__)


class DeviceLocator:
    """Locate devices using stored identifiers"""
    
    def __init__(self, **connection_params):
        """Initialize locator with connection parameters"""
        self.connection_params = connection_params
        self.usb_detector = USBDeviceDetector()
    
    def find_device(self, device_identification: Dict[str, Any]) -> Optional[str]:
        """Find device using hybrid identification approach"""
        logger.debug(f"Attempting to locate device using stored identification")
        
        # Convert dict to DeviceIdentifiers if needed
        if isinstance(device_identification, dict):
            try:
                identifiers = DeviceIdentifiers.from_dict(device_identification)
            except Exception as e:
                logger.error(f"Error parsing device identification: {e}")
                return None
        else:
            identifiers = device_identification
        
        # Method 1: Try by-id path if it was unique
        if identifiers.has_unique_serial and identifiers.by_id_path:
            device_path = self._try_by_id_path(identifiers.by_id_path)
            if device_path:
                logger.info(f"Found device via by-id path: {device_path}")
                return device_path
        
        # Method 2: Try by-path (physical location)
        if identifiers.by_path_path:
            device_path = self._try_by_path_path(identifiers.by_path_path)
            if device_path:
                logger.info(f"Found device via by-path: {device_path}")
                return device_path
        
        # Method 3: Search by USB attributes + Modbus validation
        if identifiers.usb_vendor_id and identifiers.usb_product_id:
            candidates = self._find_by_usb_attributes(
                identifiers.usb_vendor_id,
                identifiers.usb_product_id,
                identifiers.usb_serial
            )
            
            for candidate in candidates:
                if identifiers.modbus_signature:
                    if self.validate_device_connection(candidate, identifiers.modbus_signature):
                        logger.info(f"Found device via USB attributes + Modbus validation: {candidate}")
                        return candidate
                else:
                    # No Modbus signature available, return first USB match
                    logger.info(f"Found device via USB attributes (no Modbus validation): {candidate}")
                    return candidate
        
        # Method 4: Last resort - scan all devices with Modbus validation
        if identifiers.modbus_signature:
            device_path = self._scan_all_devices_for_signature(identifiers.modbus_signature)
            if device_path:
                logger.info(f"Found device via full scan with Modbus validation: {device_path}")
                return device_path
        
        logger.warning("Could not locate device using any identification method")
        return None
    
    def _try_by_id_path(self, by_id_path: str) -> Optional[str]:
        """Try to find device using by-id path"""
        try:
            if os.path.exists(by_id_path) and os.path.islink(by_id_path):
                real_path = os.path.realpath(by_id_path)
                if os.path.exists(real_path):
                    logger.debug(f"by-id path {by_id_path} -> {real_path}")
                    return real_path
        except Exception as e:
            logger.debug(f"Error checking by-id path {by_id_path}: {e}")
        
        return None
    
    def _try_by_path_path(self, by_path_path: str) -> Optional[str]:
        """Try to find device using by-path path"""
        try:
            if os.path.exists(by_path_path) and os.path.islink(by_path_path):
                real_path = os.path.realpath(by_path_path)
                if os.path.exists(real_path):
                    logger.debug(f"by-path path {by_path_path} -> {real_path}")
                    return real_path
        except Exception as e:
            logger.debug(f"Error checking by-path path {by_path_path}: {e}")
        
        return None
    
    def _find_by_usb_attributes(self, vendor_id: str, product_id: str, 
                               serial: Optional[str] = None) -> List[str]:
        """Find devices matching USB attributes"""
        matching_devices = []
        
        try:
            all_devices = self.usb_detector.get_all_serial_devices()
            
            for device_path in all_devices:
                usb_attrs = self.usb_detector.get_comprehensive_usb_attributes(device_path)
                
                # Check vendor and product ID match
                if (usb_attrs.get('usb_vendor_id') == vendor_id and 
                    usb_attrs.get('usb_product_id') == product_id):
                    
                    # If serial is specified, it must match
                    if serial is None or usb_attrs.get('usb_serial') == serial:
                        matching_devices.append(device_path)
                        logger.debug(f"USB attribute match: {device_path}")
            
        except Exception as e:
            logger.debug(f"Error finding devices by USB attributes: {e}")
        
        return matching_devices
    
    def _scan_all_devices_for_signature(self, modbus_signature: Dict[str, Any]) -> Optional[str]:
        """Scan all serial devices for Modbus signature match"""
        try:
            all_devices = self.usb_detector.get_all_serial_devices()
            
            for device_path in all_devices:
                if self.validate_device_connection(device_path, modbus_signature):
                    return device_path
                    
        except Exception as e:
            logger.debug(f"Error scanning devices for signature: {e}")
        
        return None
    
    def validate_device_connection(self, device_path: str, 
                                 modbus_signature: Dict[str, Any]) -> bool:
        """Validate device responds correctly via Modbus"""
        try:
            # Import here to avoid serial dependency at module import time
            from .modbus_client import GenericModbusClient, FunctionCode
            
            # Convert dict to ModbusSignature if needed
            if isinstance(modbus_signature, dict):
                signature = ModbusSignature.from_dict(modbus_signature)
            else:
                signature = modbus_signature
            
            client_params = {
                'device_path': device_path,
                **self.connection_params
            }
            
            client = GenericModbusClient(**client_params)
            
            with client:
                # Test each register in the signature
                for test_reg in signature.test_registers:
                    try:
                        address = test_reg['address']
                        function_code = FunctionCode(test_reg['function'])
                        expected_range = test_reg['expected_range']
                        
                        value = client.read_single_register(signature.slave_id, address, function_code)
                        
                        if value is None:
                            logger.debug(f"Signature validation failed: no response from register 0x{address:04X}")
                            return False
                        
                        # Check if value is within expected range
                        if not (expected_range[0] <= value <= expected_range[1]):
                            logger.debug(f"Signature validation failed: register 0x{address:04X} value {value} not in range {expected_range}")
                            return False
                        
                        logger.debug(f"Signature validation passed: register 0x{address:04X} = {value}")
                        
                    except Exception as e:
                        logger.debug(f"Error testing signature register 0x{address:04X}: {e}")
                        return False
                
                logger.debug(f"Device signature validation passed for {device_path}")
                return True
                
        except Exception as e:
            logger.debug(f"Error validating device connection for {device_path}: {e}")
            return False
    
    def find_likely_matches(self, stored_identification: Dict[str, Any]) -> List[DeviceMatch]:
        """Find devices that might be the same as stored config"""
        matches = []
        
        try:
            # Convert dict to DeviceIdentifiers if needed
            if isinstance(stored_identification, dict):
                stored_identifiers = DeviceIdentifiers.from_dict(stored_identification)
            else:
                stored_identifiers = stored_identification
            
            all_devices = self.usb_detector.get_all_serial_devices()
            
            for device_path in all_devices:
                # Get current device identifiers
                from .stable_device_discovery import StableDeviceDiscovery
                discovery = StableDeviceDiscovery(**self.connection_params)
                current_identifiers = discovery.get_device_identifiers(device_path)
                
                # Calculate match confidence
                confidence, reasons = self._calculate_match_confidence(
                    stored_identifiers, current_identifiers
                )
                
                if confidence > 0.3:  # Only include reasonable matches
                    match = DeviceMatch(
                        device_path=device_path,
                        identifiers=current_identifiers,
                        confidence=confidence,
                        match_reasons=reasons
                    )
                    matches.append(match)
            
            # Sort by confidence (highest first)
            matches.sort(key=lambda x: x.confidence, reverse=True)
            
        except Exception as e:
            logger.error(f"Error finding likely matches: {e}")
        
        return matches
    
    def _calculate_match_confidence(self, stored: DeviceIdentifiers, 
                                  current: DeviceIdentifiers) -> tuple[float, List[str]]:
        """Calculate confidence that current device matches stored device"""
        confidence = 0.0
        reasons = []
        
        # Exact serial number match (highest confidence)
        if (stored.usb_serial and current.usb_serial and 
            stored.usb_serial == current.usb_serial):
            confidence += 0.9
            reasons.append(f"Exact serial match: {stored.usb_serial}")
        
        # USB vendor/product ID match
        if (stored.usb_vendor_id and current.usb_vendor_id and
            stored.usb_product_id and current.usb_product_id and
            stored.usb_vendor_id == current.usb_vendor_id and
            stored.usb_product_id == current.usb_product_id):
            confidence += 0.6
            reasons.append("Same USB vendor/product ID")
        
        # Product name match
        if (stored.usb_product_name and current.usb_product_name and
            stored.usb_product_name == current.usb_product_name):
            confidence += 0.4
            reasons.append("Same product name")
        
        # Manufacturer match
        if (stored.usb_manufacturer and current.usb_manufacturer and
            stored.usb_manufacturer == current.usb_manufacturer):
            confidence += 0.2
            reasons.append("Same manufacturer")
        
        # Physical path match (medium confidence)
        if (stored.by_path_path and current.by_path_path and
            stored.by_path_path == current.by_path_path):
            confidence += 0.7
            reasons.append("Same physical USB port")
        
        # Ensure confidence doesn't exceed 1.0
        confidence = min(confidence, 1.0)
        
        return confidence, reasons
