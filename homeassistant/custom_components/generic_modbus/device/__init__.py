"""
Generic Modbus Integration for Home Assistant
A flexible, auto-discovering Modbus device integration
"""

__version__ = "1.0.0"
__author__ = "Nicholas Klopfer-Webber"

# Don't import modules that require serial at package level
# They will be imported when needed in the actual code

__all__ = [
    "ModbusDeviceDiscovery",
    "GenericModbusClient", 
    "ModbusDeviceManager"
]
