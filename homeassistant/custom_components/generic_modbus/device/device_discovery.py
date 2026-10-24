#!/usr/bin/env python3
"""
Modbus Device Discovery
Auto-discovers Modbus devices and their register maps
"""

import logging
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from .modbus_client import GenericModbusClient, FunctionCode
from .device_profiles import DEVICE_PROFILES, get_device_profile

logger = logging.getLogger(__name__)

@dataclass
class DiscoveredDevice:
    """Represents a discovered Modbus device"""
    device_path: None
    slave_id: int
    device_name: str = "Unknown Device"
    manufacturer: str = "Unknown"
    model: str = "Unknown"
    firmware_version: str = "Unknown"
    register_map: Dict[int, Dict] = None
    device_profile_key: Optional[str] = None
    
    def __post_init__(self):
        if self.register_map is None:
            self.register_map = {}

class ModbusDeviceDiscovery:
    """Discovers Modbus devices and their capabilities"""
    
    def __init__(self, **connection_params):
        """Initialize discovery for a specific serial device"""
        self.connection_params = connection_params
        self.client = GenericModbusClient(**connection_params)
        logger.info(f"ModbusDeviceDiscovery device=[{self.client.device_path}]")
    
    def get_common_id_registers(self, device_config=None) -> List[Tuple[FunctionCode, List[int]]]:
        """Get common ID registers from configuration or defaults."""
        if device_config and hasattr(device_config.discovery, 'common_id_registers'):
            return device_config.discovery.common_id_registers
        
        # Default common ID registers
        return [
            # Input registers
            (FunctionCode.READ_INPUT_REGISTERS, [0x0000, 0x0001, 0x0002, 0x0003]),
            (FunctionCode.READ_INPUT_REGISTERS, [0x9000, 0x9001, 0x9002, 0x9003]),
            (FunctionCode.READ_INPUT_REGISTERS, [0x1000, 0x1001, 0x1002, 0x1003]),
            # Holding registers  
            (FunctionCode.READ_HOLDING_REGISTERS, [0x0000, 0x0001, 0x0002, 0x0003]),
            (FunctionCode.READ_HOLDING_REGISTERS, [0x9000, 0x9001, 0x9002, 0x9003]),
            (FunctionCode.READ_HOLDING_REGISTERS, [0x1000, 0x1001, 0x1002, 0x1003]),
        ]
    
    def scan_slave_ids(self, slave_id_range: range = None, device_config=None) -> List[int]:
        """Scan for responsive slave IDs"""
        logger.debug("scan_slave_ids")
        if slave_id_range is None:
            if device_config and hasattr(device_config.discovery, 'default_slave_range'):
                start, end = device_config.discovery.default_slave_range
                slave_id_range = range(start, end + 1)
            else:
                slave_id_range = range(1, 248)
        
        logger.info(f"Scanning for Modbus devices on {self.client.device_path} from {slave_id_range.start} to {slave_id_range.stop-1}")
        responsive_slaves = []
        
        with self.client:
            common_registers = self.get_common_id_registers(device_config)
            
            for slave_id in slave_id_range:
                logger.debug(f"Testing slave ID {slave_id}")
                
                # Try to read from common identification registers
                for function_code, addresses in common_registers:
                    for address in addresses:
                        try:
                            value = self.client.read_single_register(slave_id, function_code, address)
                            if value is not None:
                                logger.info(f"Found responsive device at slave ID {slave_id}")
                                responsive_slaves.append(slave_id)
                                break
                        except Exception:
                            continue
                    if slave_id in responsive_slaves:
                        break
                
                # Small delay between slave ID tests
                time.sleep(0.1)
        
        logger.info(f"Found {len(responsive_slaves)} responsive slave IDs: {responsive_slaves}")
        return responsive_slaves
    
    def identify_device(self, slave_id: int) -> Optional[str]:
        """Try to identify device type using signature matching"""
        logger.info(f"Attempting to identify device at slave ID {slave_id}")
        
        for device_key, device_info in DEVICE_PROFILES.items():
            if "signatures" not in device_info:
                continue
            
            logger.debug(f"Testing device profile: {device_key}")
            matches = 0
            total_tests = len(device_info["signatures"])
            
            for function_code, address, value_range in device_info["signatures"]:
                try:
                    value = self.client.read_single_register(slave_id, function_code, address)
                    if value is not None and value_range[0] <= value <= value_range[1]:
                        matches += 1
                        logger.debug(f"Signature match for {device_key}: "
                                   f"register {address:04X} = {value}")
                except Exception:
                    continue
            
            # Require at least 50% of signatures to match
            match_ratio = matches / total_tests if total_tests > 0 else 0
            logger.debug(f"Device {device_key}: {matches}/{total_tests} signatures matched ({match_ratio:.1%})")
            
            if match_ratio >= 0.5:
                logger.info(f"Identified device as {device_key} with {match_ratio:.1%} confidence")
                return device_key
        
        logger.info(f"Could not identify device at slave ID {slave_id}")
        return None
    
    def discover_device_registers(self, slave_id: int, device_profile_key: Optional[str] = None, 
                                device_config=None) -> Dict[int, Dict]:
        """Discover available registers for a device"""
        logger.info(f"Discovering registers for slave ID {slave_id}")
        
        register_map = {}
        device_info = get_device_profile(device_profile_key) if device_profile_key else None
        
        # Get supported function codes
        supported_functions = [
            FunctionCode.READ_INPUT_REGISTERS.value,
            FunctionCode.READ_HOLDING_REGISTERS.value
        ]
        
        # Use device-specific register ranges if available
        if device_info and "register_ranges" in device_info:
            logger.info(f"Using device-specific register ranges for {device_info['name']}")
            for function_code, start_addr, end_addr in device_info["register_ranges"]:
                if function_code.value in supported_functions:
                    logger.info(f"Scanning {function_code.name} registers {start_addr:04X}-{end_addr:04X}")
                    
                    batch_size = device_config.discovery.batch_size if device_config else 8
                    found_registers = self.client.scan_registers(
                        slave_id, function_code, start_addr, end_addr, batch_size=batch_size
                    )
                    
                    for addr, value in found_registers.items():
                        register_map[addr] = {
                            'function_code': function_code.value,
                            'value': value,
                            'name': f'register_{addr:04X}',
                            'description': f'Register at address {addr:04X}',
                            'unit': '',
                            'scale': 1.0,
                            'offset': 0.0,
                            'device_class': '',
                            'state_class': 'measurement'
                        }
                    
                    # Delay between function code scans
                    scan_delay = device_config.discovery.scan_delay if device_config else 0.5
                    time.sleep(scan_delay)
        
        else:
            # Fall back to configurable or default scanning
            scan_ranges = self._get_scan_ranges(device_config)
            
            for func_code in supported_functions:
                if func_code in scan_ranges:
                    function_code = FunctionCode(func_code)
                    logger.info(f"Scanning registers for function code {func_code:02X}")
                    
                    for start_addr, end_addr in scan_ranges[func_code]:
                        batch_size = device_config.discovery.batch_size if device_config else 8
                        found_registers = self.client.scan_registers(
                            slave_id, function_code, start_addr, end_addr, batch_size=batch_size
                        )
                        
                        for addr, value in found_registers.items():
                            register_map[addr] = {
                                'function_code': function_code.value,
                                'value': value,
                                'name': f'register_{addr:04X}',
                                'description': f'Register at address {addr:04X}',
                                'unit': '',
                                'scale': 1.0,
                                'offset': 0.0,
                                'device_class': '',
                                'state_class': 'measurement'
                            }
                        
                        # Delay between range scans
                        scan_delay = device_config.discovery.scan_delay if device_config else 0.5
                        time.sleep(scan_delay)
        
        logger.info(f"Found {len(register_map)} registers for slave {slave_id}")
        return register_map

    @staticmethod
    def _get_scan_ranges(device_config=None) -> Dict[int, List[Tuple[int, int]]]:
        """Get scan ranges from configuration or defaults."""
        if device_config and hasattr(device_config.discovery, 'default_scan_ranges'):
            return device_config.discovery.default_scan_ranges

        # Default scan ranges
        return {
            FunctionCode.READ_INPUT_REGISTERS.value: [
                (0x0000, 0x00FF),  # Common range
                (0x1000, 0x10FF),  # Extended range 1
                (0x3000, 0x31FF),  # Solar charger range
                (0x9000, 0x90FF),  # Device info range
            ],
            FunctionCode.READ_HOLDING_REGISTERS.value: [
                (0x0000, 0x00FF),  # Common range
                (0x1000, 0x10FF),  # Extended range 1
                (0x9000, 0x90FF),  # Configuration range
            ]
        }

    def discover_all_devices(self, slave_id_range: range = None, device_config=None) -> List[DiscoveredDevice]:
        """Discover and identify all devices on the network"""
        logger.info(f"Starting full device discovery on {self.client.device_path}")

        if slave_id_range is None:
            if device_config and hasattr(device_config.discovery, 'default_slave_range'):
                start, end = device_config.discovery.default_slave_range
                slave_id_range = range(start, end + 1)
            else:
                slave_id_range = range(1, 10)
        
        # First, find all responsive slave IDs
        responsive_slaves = self.scan_slave_ids(slave_id_range, device_config)
        
        if not responsive_slaves:
            logger.warning("No responsive Modbus devices found")
            return []
        
        discovered_devices = []
        
        with self.client:
            for slave_id in responsive_slaves:
                logger.info(f"Processing device at slave ID {slave_id}")
                
                # Try to identify the device
                device_profile_key = self.identify_device(slave_id)
                
                # Create discovered device
                device = DiscoveredDevice(device_path=self.client.device_path, slave_id=slave_id)
                
                # Set device info from profile if identified
                if device_profile_key:
                    device_info = get_device_profile(device_profile_key)
                    if device_info:
                        device.device_name = device_info["name"]
                        device.manufacturer = device_info["manufacturer"]
                        device.model = device_info.get("model", "Unknown")
                        device.device_profile_key = device_profile_key
                
                # Discover registers
                device.register_map = self.discover_device_registers(
                    slave_id, device_profile_key, device_config
                )
                
                discovered_devices.append(device)
                logger.info(f"Completed discovery for {device.device_name} "
                          f"(slave {slave_id}) - {len(device.register_map)} registers")
        
        logger.info(f"Discovery complete: found {len(discovered_devices)} devices")
        return discovered_devices
