#!/usr/bin/env python3
"""
Stable Device Discovery Service
Enhanced device discovery with stability analysis and comprehensive identification
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from .device_identifiers import DeviceIdentifiers, StabilityLevel, ModbusSignature
from .usb_utils import USBDeviceDetector
# Import serial-dependent modules only when needed
# from .device_discovery import DiscoveredDevice
# from .modbus_client import GenericModbusClient, FunctionCode

logger = logging.getLogger(__name__)


class StableDeviceDiscovery:
    """Enhanced device discovery with stability analysis"""
    
    def __init__(self, **connection_params):
        """Initialize discovery with connection parameters"""
        self.connection_params = connection_params
        self.usb_detector = USBDeviceDetector()
    
    async def discover_all_devices_with_stability(self) -> List[Dict[str, Any]]:
        """Discover all serial devices with stability analysis"""
        discovered_devices = []
        
        # Get all available serial devices
        serial_devices = self.usb_detector.get_all_serial_devices()
        logger.info(f"Found {len(serial_devices)} serial devices to analyze")
        
        for device_path in serial_devices:
            try:
                # Get comprehensive device identification
                identifiers = self.get_device_identifiers(device_path)
                
                # Test if it's a Modbus device
                modbus_info = await self._test_modbus_connectivity(device_path)
                
                device_info = {
                    'device_path': device_path,
                    'identifiers': identifiers,
                    'modbus_info': modbus_info,
                    'is_modbus_device': modbus_info is not None,
                    'user_description': identifiers.get_user_friendly_description(),
                    'stability_indicator': identifiers.get_stability_indicator(),
                    'stability_description': identifiers.stability_description
                }
                
                discovered_devices.append(device_info)
                logger.debug(f"Analyzed device {device_path}: {device_info['user_description']}")
                
            except Exception as e:
                logger.debug(f"Error analyzing device {device_path}: {e}")
                continue
        
        # Sort by stability level (high to low) and then by description
        discovered_devices.sort(key=lambda x: (
            x['identifiers'].stability_level.value,  # high, medium, low
            x['user_description']
        ))
        
        logger.info(f"Discovered {len(discovered_devices)} devices with stability analysis")
        return discovered_devices
    
    def get_device_identifiers(self, device_path: str) -> DeviceIdentifiers:
        """Get comprehensive device identification"""
        # Get USB paths
        by_id_path = self.usb_detector.find_by_id_path(device_path)
        by_path_path = self.usb_detector.find_by_path_path(device_path)
        
        # Get USB attributes
        usb_attrs = self.usb_detector.get_comprehensive_usb_attributes(device_path)
        
        # Analyze stability
        stability_info = self._analyze_device_stability(by_id_path, by_path_path, usb_attrs)
        
        # Create identifiers object
        identifiers = DeviceIdentifiers(
            current_tty_path=device_path,
            by_id_path=by_id_path,
            by_path_path=by_path_path,
            usb_vendor_id=usb_attrs.get('usb_vendor_id'),
            usb_product_id=usb_attrs.get('usb_product_id'),
            usb_serial=usb_attrs.get('usb_serial'),
            usb_manufacturer=usb_attrs.get('usb_manufacturer'),
            usb_product_name=usb_attrs.get('usb_product_name'),
            has_unique_serial=stability_info['has_unique_serial'],
            stability_level=stability_info['stability_level'],
            stability_description=stability_info['description'],
            configured_at=datetime.now().isoformat()
        )
        
        return identifiers
    
    def _analyze_device_stability(self, by_id_path: Optional[str], by_path_path: Optional[str], 
                                 usb_attrs: Dict[str, Optional[str]]) -> Dict[str, Any]:
        """Analyze how stable a device path will be"""
        
        # Check if device has unique serial number
        has_unique_serial = False
        if usb_attrs.get('usb_serial'):
            # Consider it unique if it's not a common generic serial
            serial = usb_attrs['usb_serial']
            generic_serials = ['0000', '1234', 'SERIAL', 'DEFAULT']
            has_unique_serial = serial not in generic_serials and len(serial) >= 6
        
        # Determine stability level
        if by_id_path and has_unique_serial:
            stability_level = StabilityLevel.HIGH
            description = "High - Unique serial number"
        elif by_path_path:
            stability_level = StabilityLevel.MEDIUM
            description = "Medium - Stable if not moved"
        else:
            stability_level = StabilityLevel.LOW
            description = "Low - May change on reboot"
        
        return {
            'has_unique_serial': has_unique_serial,
            'stability_level': stability_level,
            'description': description
        }
    
    async def _test_modbus_connectivity(self, device_path: str) -> Optional[Dict[str, Any]]:
        """Test if device responds to Modbus communication"""
        try:
            # Import here to avoid serial dependency at module import time
            from .modbus_client import GenericModbusClient
            
            # Create temporary client for testing
            client_params = {
                'device_path': device_path,
                **self.connection_params
            }
            
            client = GenericModbusClient(**client_params)
            
            # Test common slave IDs
            test_slave_ids = [1, 2, 3, 4, 5]
            responsive_slaves = []
            
            with client:
                for slave_id in test_slave_ids:
                    if client.test_slave_connectivity(slave_id):
                        responsive_slaves.append(slave_id)
                        logger.debug(f"Device {device_path} responds at slave ID {slave_id}")
            
            if responsive_slaves:
                return {
                    'responsive_slave_ids': responsive_slaves,
                    'primary_slave_id': responsive_slaves[0]
                }
            
        except Exception as e:
            logger.debug(f"Modbus connectivity test failed for {device_path}: {e}")
        
        return None
    
    async def create_modbus_signature(self, device_path: str, slave_id: int, 
                                    device_profile_key: Optional[str] = None) -> Optional[ModbusSignature]:
        """Create a Modbus signature for device validation"""
        try:
            # Import here to avoid serial dependency at module import time
            from .modbus_client import GenericModbusClient, FunctionCode
            
            client_params = {
                'device_path': device_path,
                **self.connection_params
            }
            
            client = GenericModbusClient(**client_params)
            test_registers = []
            
            with client:
                # Test common registers to create signature
                common_test_registers = [
                    (0x0000, FunctionCode.READ_HOLDING_REGISTERS),
                    (0x0001, FunctionCode.READ_HOLDING_REGISTERS),
                    (0x3100, FunctionCode.READ_INPUT_REGISTERS),
                    (0x3101, FunctionCode.READ_INPUT_REGISTERS),
                ]
                
                for address, function_code in common_test_registers:
                    try:
                        value = client.read_single_register(slave_id, address, function_code)
                        if value is not None:
                            test_registers.append({
                                'address': address,
                                'function': function_code.value,
                                'expected_range': [max(0, value - 100), value + 100]  # Allow some variance
                            })
                            
                            # Limit to 3 test registers for efficiency
                            if len(test_registers) >= 3:
                                break
                                
                    except Exception as e:
                        logger.debug(f"Failed to read register 0x{address:04X}: {e}")
                        continue
            
            if test_registers:
                signature = ModbusSignature(
                    slave_id=slave_id,
                    test_registers=test_registers,
                    device_profile_key=device_profile_key
                )
                logger.debug(f"Created Modbus signature for {device_path} slave {slave_id}: {len(test_registers)} registers")
                return signature
            
        except Exception as e:
            logger.debug(f"Error creating Modbus signature for {device_path}: {e}")
        
        return None
    
    def create_user_friendly_description(self, identifiers: DeviceIdentifiers) -> str:
        """Create human-readable device description with stability info"""
        base_description = identifiers.get_user_friendly_description()
        stability_indicator = identifiers.get_stability_indicator()
        
        return f"{stability_indicator} {base_description}"
