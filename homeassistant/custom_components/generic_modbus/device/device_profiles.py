#!/usr/bin/env python3
"""
Device Profile Templates
Defines parameter mappings for known Modbus devices
"""

from typing import Dict, Any
from .modbus_client import FunctionCode

# Solar Charger Parameter Definitions (from your original project)
TRACER3210AN_PARAMETERS = {
    # PV (Solar Panel) Data
    0x3100: {
        'name': 'pv_voltage',
        'description': 'PV Array Voltage',
        'unit': 'V',
        'scale': 0.01,
        'device_class': 'voltage',
        'state_class': 'measurement',
        'icon': 'mdi:solar-panel'
    },
    0x3101: {
        'name': 'pv_current',
        'description': 'PV Array Current',
        'unit': 'A',
        'scale': 0.01,
        'device_class': 'current',
        'state_class': 'measurement',
        'icon': 'mdi:current-dc'
    },
    0x3102: {
        'name': 'pv_power_low',
        'description': 'PV Power (Low Word)',
        'unit': 'W',
        'scale': 0.01,
        'device_class': 'power',
        'state_class': 'measurement',
        'icon': 'mdi:solar-power'
    },
    0x3103: {
        'name': 'pv_power_high',
        'description': 'PV Power (High Word)',
        'unit': 'W',
        'scale': 0.01,
        'device_class': 'power',
        'state_class': 'measurement',
        'icon': 'mdi:solar-power'
    },
    
    # Battery Data
    0x3104: {
        'name': 'battery_voltage',
        'description': 'Battery Voltage',
        'unit': 'V',
        'scale': 0.01,
        'device_class': 'voltage',
        'state_class': 'measurement',
        'icon': 'mdi:battery'
    },
    0x3105: {
        'name': 'battery_current',
        'description': 'Battery Charging Current',
        'unit': 'A',
        'scale': 0.01,
        'device_class': 'current',
        'state_class': 'measurement',
        'icon': 'mdi:current-dc'
    },
    0x3106: {
        'name': 'battery_power_low',
        'description': 'Battery Power (Low Word)',
        'unit': 'W',
        'scale': 0.01,
        'device_class': 'power',
        'state_class': 'measurement',
        'icon': 'mdi:battery-charging'
    },
    0x3107: {
        'name': 'battery_power_high',
        'description': 'Battery Power (High Word)',
        'unit': 'W',
        'scale': 0.01,
        'device_class': 'power',
        'state_class': 'measurement',
        'icon': 'mdi:battery-charging'
    },
    
    # Load Data
    0x310C: {
        'name': 'load_voltage',
        'description': 'Load Voltage',
        'unit': 'V',
        'scale': 0.01,
        'device_class': 'voltage',
        'state_class': 'measurement',
        'icon': 'mdi:flash'
    },
    0x310D: {
        'name': 'load_current',
        'description': 'Load Current',
        'unit': 'A',
        'scale': 0.01,
        'device_class': 'current',
        'state_class': 'measurement',
        'icon': 'mdi:current-ac'
    },
    0x310E: {
        'name': 'load_power_low',
        'description': 'Load Power (Low Word)',
        'unit': 'W',
        'scale': 0.01,
        'device_class': 'power',
        'state_class': 'measurement',
        'icon': 'mdi:power-plug'
    },
    0x310F: {
        'name': 'load_power_high',
        'description': 'Load Power (High Word)',
        'unit': 'W',
        'scale': 0.01,
        'device_class': 'power',
        'state_class': 'measurement',
        'icon': 'mdi:power-plug'
    },
    
    # System Status
    0x3110: {
        'name': 'battery_temp',
        'description': 'Battery Temperature',
        'unit': '°C',
        'scale': 0.01,
        'device_class': 'temperature',
        'state_class': 'measurement',
        'icon': 'mdi:thermometer'
    },
    0x3111: {
        'name': 'device_temp',
        'description': 'Device Temperature',
        'unit': '°C',
        'scale': 0.01,
        'device_class': 'temperature',
        'state_class': 'measurement',
        'icon': 'mdi:thermometer'
    },
    0x3112: {
        'name': 'battery_soc',
        'description': 'Battery State of Charge',
        'unit': '%',
        'scale': 1.0,
        'device_class': 'battery',
        'state_class': 'measurement',
        'icon': 'mdi:battery-50'
    },
    
    # Statistics (some examples)
    0x3300: {
        'name': 'generated_energy_today_low',
        'description': 'Generated Energy Today (Low)',
        'unit': 'kWh',
        'scale': 0.01,
        'device_class': 'energy',
        'state_class': 'total_increasing',
        'icon': 'mdi:solar-power'
    },
    0x3301: {
        'name': 'generated_energy_today_high',
        'description': 'Generated Energy Today (High)',
        'unit': 'kWh',
        'scale': 0.01,
        'device_class': 'energy',
        'state_class': 'total_increasing',
        'icon': 'mdi:solar-power'
    },
}

# Generic Power Meter Parameters
GENERIC_POWER_METER_PARAMETERS = {
    0x0000: {
        'name': 'voltage_l1',
        'description': 'Voltage L1',
        'unit': 'V',
        'scale': 0.1,
        'device_class': 'voltage',
        'state_class': 'measurement',
        'icon': 'mdi:flash'
    },
    0x0001: {
        'name': 'voltage_l2',
        'description': 'Voltage L2',
        'unit': 'V',
        'scale': 0.1,
        'device_class': 'voltage',
        'state_class': 'measurement',
        'icon': 'mdi:flash'
    },
    0x0002: {
        'name': 'voltage_l3',
        'description': 'Voltage L3',
        'unit': 'V',
        'scale': 0.1,
        'device_class': 'voltage',
        'state_class': 'measurement',
        'icon': 'mdi:flash'
    },
    0x0003: {
        'name': 'current_l1',
        'description': 'Current L1',
        'unit': 'A',
        'scale': 0.001,
        'device_class': 'current',
        'state_class': 'measurement',
        'icon': 'mdi:current-ac'
    },
    0x0004: {
        'name': 'current_l2',
        'description': 'Current L2',
        'unit': 'A',
        'scale': 0.001,
        'device_class': 'current',
        'state_class': 'measurement',
        'icon': 'mdi:current-ac'
    },
    0x0005: {
        'name': 'current_l3',
        'description': 'Current L3',
        'unit': 'A',
        'scale': 0.001,
        'device_class': 'current',
        'state_class': 'measurement',
        'icon': 'mdi:current-ac'
    },
}

# Device Profile Registry
DEVICE_PROFILES = {
    "tracer3210an": {
        "name": "Tracer 3210AN Solar Charger **HARD CODED**",
        "manufacturer": "EPSolar/EPEver",
        "model": "Tracer 3210AN",
        "parameters": TRACER3210AN_PARAMETERS,
        "signatures": [
            (FunctionCode.READ_INPUT_REGISTERS, 0x3100, (0, 5000)),
            (FunctionCode.READ_INPUT_REGISTERS, 0x3104, (1000, 1800)),
        ],
        "register_ranges": [
            (FunctionCode.READ_INPUT_REGISTERS, 0x3100, 0x311F),
            (FunctionCode.READ_INPUT_REGISTERS, 0x3200, 0x320F),
            (FunctionCode.READ_HOLDING_REGISTERS, 0x9000, 0x900F),
        ]
    },
    "generic_power_meter": {
        "name": "Generic Power Meter",
        "manufacturer": "Generic",
        "model": "Power Meter",
        "parameters": GENERIC_POWER_METER_PARAMETERS,
        "signatures": [
            (FunctionCode.READ_INPUT_REGISTERS, 0x0000, (0, 65535)),
            (FunctionCode.READ_HOLDING_REGISTERS, 0x0000, (0, 65535)),
        ],
        "register_ranges": [
            (FunctionCode.READ_INPUT_REGISTERS, 0x0000, 0x00FF),
            (FunctionCode.READ_HOLDING_REGISTERS, 0x0000, 0x00FF),
        ]
    }
}

def apply_device_profile(register_map: Dict[int, Dict], device_profile_key: str) -> Dict[int, Dict]:
    """Apply device profile parameters to discovered registers"""
    if device_profile_key not in DEVICE_PROFILES:
        return register_map
    
    profile = DEVICE_PROFILES[device_profile_key]
    parameters = profile.get("parameters", {})
    
    # Update register map with profile information
    for address, register_info in register_map.items():
        if address in parameters:
            param_def = parameters[address]
            register_info.update({
                'name': param_def['name'],
                'description': param_def['description'],
                'unit': param_def['unit'],
                'scale': param_def['scale'],
                'device_class': param_def.get('device_class', ''),
                'state_class': param_def.get('state_class', ''),
                'icon': param_def.get('icon', ''),
            })
    
    return register_map

def get_device_profile(device_profile_key: str) -> Dict[str, Any]:
    """Get device profile by key"""
    return DEVICE_PROFILES.get(device_profile_key, {})

def list_device_profiles() -> Dict[str, str]:
    """List available device profiles"""
    return {key: profile["name"] for key, profile in DEVICE_PROFILES.items()}
