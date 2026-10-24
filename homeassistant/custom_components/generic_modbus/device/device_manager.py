#!/usr/bin/env python3
"""
Modbus Device Manager
Manages multiple Modbus devices and their configurations
"""

import json
import logging
import time
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any

from .device_discovery import DiscoveredDevice
from .modbus_client import GenericModbusClient, FunctionCode
from ..config_definitions import ConnectionDefaults
from ..const import *

logger = logging.getLogger(__name__)

@dataclass
class DeviceParameter:
    """Represents a configurable device parameter"""
    address: int
    function_code: int
    name: str
    description: str = ""
    unit: str = ""
    scale: float = 1.0
    offset: float = 0.0
    data_type: str = "uint16"
    device_class: str = ""
    state_class: str = ""
    icon: str = ""
    enabled: bool = True
    update_interval: int = 30  # seconds

@dataclass 
class ManagedDevice:
    """Represents a managed Modbus device with configuration"""
    slave_id: int
    device_path: str
    name: str
    manufacturer: str = "Unknown"
    model: str = "Unknown"
    parameters: Dict[str, DeviceParameter] = None
    connection_config: Dict[str, Any] = None
    enabled: bool = True
    firmware_version = None

    def __post_init__(self):
        if self.parameters is None:
            self.parameters = {}
        if self.connection_config is None:
            self.connection_config = {
                CONF_BAUDRATE: ConnectionDefaults.BAUDRATE,
                CONF_TIMEOUT: ConnectionDefaults.TIMEOUT,
                CONF_PARITY: ConnectionDefaults.PARITY,
                CONF_STOPBITS: ConnectionDefaults.STOPBITS,
                CONF_BYTESIZE: ConnectionDefaults.BYTESIZE
            }

class ModbusDeviceManager:
    """Manages multiple Modbus devices and their configurations"""
    
    def __init__(self):
        self.devices: Dict[str, ManagedDevice] = {}
        self.clients: Dict[str, GenericModbusClient] = {}
    
    def add_device_from_discovery(self, discovered: DiscoveredDevice, 
                                 custom_name: Optional[str] = None) -> str:
        """Add a device from discovery results"""
        device_id = f"{discovered.device_path}_{discovered.slave_id}"
        
        # Convert discovered registers to parameters
        parameters = {}
        for addr, reg_info in discovered.register_map.items():
            param_name = reg_info.get('name', f'register_{addr:04X}')
            parameters[param_name] = DeviceParameter(
                address=addr,
                function_code=reg_info['function_code'],
                name=param_name,
                description=reg_info.get('description', ''),
                unit=reg_info.get('unit', ''),
                scale=reg_info.get('scale', 1.0)
            )
        
        device = ManagedDevice(
            slave_id=discovered.slave_id,
            device_path=discovered.device_path,
            name=custom_name or discovered.device_name,
            manufacturer=discovered.manufacturer,
            model=discovered.model,
            parameters=parameters
        )
        
        self.devices[device_id] = device
        logger.info(f"Added device {device.name} with ID {device_id}")
        return device_id
    
    def add_device_manual(self, slave_id: int, device_path: str, 
                         name: str, **kwargs) -> str:
        """Manually add a device"""
        device_id = f"{device_path}_{slave_id}"
        
        device = ManagedDevice(
            device_path=device_path,
            slave_id=slave_id,
            name=name,
            **kwargs
        )
        
        self.devices[device_id] = device
        logger.info(f"Manually added device {name} with ID {device_id}")
        return device_id
    
    def get_device(self, device_id: str) -> Optional[ManagedDevice]:
        """Get a managed device by ID"""
        return self.devices.get(device_id)
    
    def list_devices(self) -> List[str]:
        """List all managed device IDs"""
        return list(self.devices.keys())
    
    def get_client(self, device_id: str) -> Optional[GenericModbusClient]:
        """Get or create a Modbus client for a device"""
        if device_id not in self.devices:
            return None
        
        if device_id not in self.clients:
            device = self.devices[device_id]
            # Include device_path in the client configuration
            client_config = {
                "device_path": device.device_path,
                **device.connection_config
            }
            self.clients[device_id] = GenericModbusClient(**client_config)
        
        return self.clients[device_id]
    
    def read_parameter(self, device_id: str, parameter_name: str) -> Optional[float]:
        """Read a specific parameter from a device"""
        device = self.get_device(device_id)
        if not device or parameter_name not in device.parameters:
            return None
        
        parameter = device.parameters[parameter_name]
        if not parameter.enabled:
            return None
        
        client = self.get_client(device_id)
        if not client:
            return None
        
        try:
            with client:
                raw_value = client.read_single_register(
                    device.slave_id,
                    FunctionCode(parameter.function_code),
                    parameter.address
                )
                
                if raw_value is not None:
                    # Apply scaling and offset
                    scaled_value = (raw_value * parameter.scale) + parameter.offset
                    return round(scaled_value, 2)
                
        except Exception as e:
            logger.error(f"Failed to read parameter {parameter_name} "
                        f"from device {device_id}: {e}")
        
        return None
    
    def read_all_parameters(self, device_id: str) -> Dict[str, float]:
        """Read all enabled parameters from a device"""
        logger.debug(f"Reading all enabled parameters from device {device_id}")
        device = self.get_device(device_id)
        if not device:
            logger.debug(f"Device {device_id} not found.")
            return {}

        client = self.get_client(device_id)
        if not client:
            logger.debug(f"Client for {device_id} not found.")
            return {}
        
        results = {}
        
        try:
            with client:
                for param_name, parameter in device.parameters.items():
                    logger.debug(f"Reading parameter '{param_name}' from device {device_id}")
                    if not parameter.enabled:
                        continue
                    
                    try:
                        raw_value = client.read_single_register(
                            device.slave_id,
                            FunctionCode(parameter.function_code),
                            parameter.address
                        )
                        
                        if raw_value is not None:
                            scaled_value = (raw_value * parameter.scale) + parameter.offset
                            results[param_name] = round(scaled_value, 2)
                        else:
                            logger.debug(f"Failed to read parameter '{param_name}'")
                    
                    except Exception as e:
                        logger.debug(f"Failed to read parameter {param_name}: {e}")
                        continue
        
        except Exception as e:
            logger.error(f"Failed to connect to device {device_id}: {e}")
        
        return results
    
    def update_parameter_config(self, device_id: str, parameter_name: str, 
                              **updates) -> bool:
        """Update parameter configuration"""
        device = self.get_device(device_id)
        if not device or parameter_name not in device.parameters:
            return False
        
        parameter = device.parameters[parameter_name]
        
        # Update allowed fields
        allowed_updates = ['name', 'description', 'unit', 'scale', 'offset', 
                          'device_class', 'state_class', 'icon', 'enabled', 
                          'update_interval']
        
        for key, value in updates.items():
            if key in allowed_updates:
                setattr(parameter, key, value)
        
        logger.info(f"Updated parameter {parameter_name} configuration for device {device_id}")
        return True
    
    def add_custom_parameter(self, device_id: str, parameter_name: str,
                           address: int, function_code: int, **kwargs) -> bool:
        """Add a custom parameter to a device"""
        device = self.get_device(device_id)
        if not device:
            return False
        
        parameter = DeviceParameter(
            address=address,
            function_code=function_code,
            name=parameter_name,
            **kwargs
        )
        
        device.parameters[parameter_name] = parameter
        logger.info(f"Added custom parameter {parameter_name} to device {device_id}")
        return True
    
    def remove_parameter(self, device_id: str, parameter_name: str) -> bool:
        """Remove a parameter from a device"""
        device = self.get_device(device_id)
        if not device or parameter_name not in device.parameters:
            return False
        
        del device.parameters[parameter_name]
        logger.info(f"Removed parameter {parameter_name} from device {device_id}")
        return True
    
    def export_device_config(self, device_id: str, filename: str) -> bool:
        """Export device configuration to JSON"""
        device = self.get_device(device_id)
        if not device:
            return False
        
        try:
            # Convert to serializable format
            config_data = {
                'device': asdict(device),
                'export_timestamp': time.time(),
                'version': '1.0'
            }
            
            with open(filename, 'w') as f:
                json.dump(config_data, f, indent=2)
            
            logger.info(f"Exported device configuration to {filename}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export device configuration: {e}")
            return False
    
    def import_device_config(self, filename: str) -> Optional[str]:
        """Import device configuration from JSON"""
        try:
            with open(filename, 'r') as f:
                config_data = json.load(f)
            
            device_data = config_data['device']
            
            # Reconstruct DeviceParameter objects
            parameters = {}
            for param_name, param_data in device_data['parameters'].items():
                parameters[param_name] = DeviceParameter(**param_data)
            
            device_data['parameters'] = parameters
            device = ManagedDevice(**device_data)
            
            device_id = f"{device.device_path}_{device.slave_id}"
            self.devices[device_id] = device
            
            logger.info(f"Imported device configuration from {filename}")
            return device_id
            
        except Exception as e:
            logger.error(f"Failed to import device configuration: {e}")
            return None
    
    def get_device_status(self, device_id: str) -> Dict[str, Any]:
        """Get device status and basic info"""
        device = self.get_device(device_id)
        if not device:
            return {}
        
        client = self.get_client(device_id)
        is_connected = False
        
        if client:
            try:
                with client:
                    is_connected = client.test_connection(device.slave_id)
            except:
                pass
        
        return {
            'device_id': device_id,
            'name': device.name,
            'manufacturer': device.manufacturer,
            'model': device.model,
            'slave_id': device.slave_id,
            'device_path': device.device_path,
            'enabled': device.enabled,
            'connected': is_connected,
            'parameter_count': len(device.parameters),
            'enabled_parameters': sum(1 for p in device.parameters.values() if p.enabled)
        }
    
    def cleanup(self):
        """Clean up resources"""
        for client in self.clients.values():
            try:
                client.disconnect()
            except:
                pass
        self.clients.clear()
        logger.info("Device manager cleanup completed")
