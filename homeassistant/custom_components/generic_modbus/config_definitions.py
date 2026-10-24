"""Common configuration definitions for Generic Modbus Integration.

This module centralizes all configuration options, defaults, and UI definitions
to eliminate duplication between config_flow.py and device_config.py.
"""

import logging
from typing import Dict, List, Tuple, Any
import voluptuous as vol

from .const import *

_LOGGER = logging.getLogger(__name__)

# =============================================================================
# Connection Parameters
# =============================================================================

class ConnectionDefaults:
    """Default connection parameters."""
    DEVICE_PATH = "/dev/ttyUSB0"
    BAUDRATE = 115200
    TIMEOUT = 2.0
    PARITY = "N"
    STOPBITS = 1
    BYTESIZE = 8

class ConnectionOptions:
    """Available connection options for UI."""
    
    BAUDRATE = {
        300: "300 bps",
        600: "600 bps",
        1200: "1200 bps",
        2400: "2400 bps",
        4800: "4800 bps",
        9600: "9600 bps",
        14400: "14400 bps",
        19200: "19200 bps",
        38400: "38400 bps",
        57600: "57600 bps",
        115200: "115200 bps",
        230400: "230400 bps",
        460800: "460800 bps",
        921600: "921600 bps",
    }
    
    PARITY = {
        "N": "None",
        "E": "Even",
        "O": "Odd"
    }
    
    STOPBITS = {
        1: "1 bit",
        2: "2 bits"
    }
    
    BYTESIZE = {
        7: "7 bits",
        8: "8 bits"
    }

class ConnectionValidators:
    """Voluptuous validators for connection parameters."""
    
    BAUDRATE = vol.In(ConnectionOptions.BAUDRATE)
    TIMEOUT = vol.All(vol.Coerce(float), vol.Range(min=0.1, max=30.0))
    PARITY = vol.In(ConnectionOptions.PARITY)
    STOPBITS = vol.In(ConnectionOptions.STOPBITS)
    BYTESIZE = vol.In(ConnectionOptions.BYTESIZE)

# =============================================================================
# Discovery Parameters
# =============================================================================

class DiscoveryDefaults:
    """Default discovery parameters."""
    SLAVE_RANGE = (1, 10)
    BATCH_SIZE = 8
    SCAN_DELAY = 0.5
    UPDATE_INTERVAL = 30

class DiscoveryValidators:
    """Voluptuous validators for discovery parameters."""
    
    SLAVE_ID = vol.All(vol.Coerce(int), vol.Range(min=1, max=247))
    BATCH_SIZE = vol.All(vol.Coerce(int), vol.Range(min=1, max=50))
    SCAN_DELAY = vol.All(vol.Coerce(float), vol.Range(min=0.1, max=5.0))
    UPDATE_INTERVAL = vol.All(vol.Coerce(int), vol.Range(min=5, max=300))

# =============================================================================
# Binary Sensor Configuration
# =============================================================================

class BinarySensorDefaults:
    """Default binary sensor configuration."""
    
    KEYWORDS = [
        "status", "alarm", "fault", "error", "warning", "alert",
        "connected", "enabled", "active", "running", "charging",
        "discharging", "protection", "limit", "bit", "flag"
    ]
    
    DEVICE_CLASS_KEYWORDS = {
        "connectivity": ["connected", "connection"],
        "problem": ["fault", "error", "alarm"],
        "running": ["running", "active"],
        "power": ["charging", "discharging"],
        "safety": ["protection", "limit"]
    }

# =============================================================================
# Scan Ranges
# =============================================================================

class ScanRangeDefaults:
    """Default scan ranges for device discovery."""
    
    # Try to import FunctionCode, fall back to constants if not available
    try:
        from .device.modbus_client import FunctionCode
        INPUT_REGISTERS = FunctionCode.READ_INPUT_REGISTERS.value
        HOLDING_REGISTERS = FunctionCode.READ_HOLDING_REGISTERS.value
    except ImportError:
        INPUT_REGISTERS = 4
        HOLDING_REGISTERS = 3
    
    RANGES = {
        INPUT_REGISTERS: [
            (0x0000, 0x00FF),  # Common range
            (0x1000, 0x10FF),  # Extended range 1
            (0x3000, 0x31FF),  # Solar charger range
            (0x9000, 0x90FF),  # Device info range
        ],
        HOLDING_REGISTERS: [
            (0x0000, 0x00FF),  # Common range
            (0x1000, 0x10FF),  # Extended range 1
            (0x9000, 0x90FF),  # Configuration range
        ]
    }
    
    COMMON_ID_REGISTERS = [
        # Input registers
        (INPUT_REGISTERS, [0x0000, 0x0001, 0x0002, 0x0003]),
        (INPUT_REGISTERS, [0x9000, 0x9001, 0x9002, 0x9003]),
        (INPUT_REGISTERS, [0x1000, 0x1001, 0x1002, 0x1003]),
        # Holding registers  
        (HOLDING_REGISTERS, [0x0000, 0x0001, 0x0002, 0x0003]),
        (HOLDING_REGISTERS, [0x9000, 0x9001, 0x9002, 0x9003]),
        (HOLDING_REGISTERS, [0x1000, 0x1001, 0x1002, 0x1003]),
    ]

# =============================================================================
# Schema Builders
# =============================================================================

class SchemaBuilder:
    """Builds voluptuous schemas for different configuration steps."""
    
    @staticmethod
    def connection_schema(
        device_path_default: str = ConnectionDefaults.DEVICE_PATH,
        baudrate_default: int = None,
        timeout_default: float = None,
        parity_default: str = None,
        stopbits_default: int = None,
        bytesize_default: int = None,
        include_discovery: bool = True,
        slave_id_range_default: str = "1-10"
    ) -> vol.Schema:
        """Build connection configuration schema."""
        
        # Use defaults if not provided
        baudrate_default = baudrate_default or ConnectionDefaults.BAUDRATE
        timeout_default = timeout_default or ConnectionDefaults.TIMEOUT
        parity_default = parity_default or ConnectionDefaults.PARITY
        stopbits_default = stopbits_default or ConnectionDefaults.STOPBITS
        bytesize_default = bytesize_default or ConnectionDefaults.BYTESIZE
        
        schema_dict = {
            vol.Required(CONF_DEVICE_PATH, default=device_path_default): str,
            vol.Optional(CONF_BAUDRATE, default=baudrate_default): ConnectionValidators.BAUDRATE,
            vol.Optional(CONF_TIMEOUT, default=timeout_default): ConnectionValidators.TIMEOUT,
            vol.Optional(CONF_PARITY, default=parity_default): ConnectionValidators.PARITY,
            vol.Optional(CONF_STOPBITS, default=stopbits_default): ConnectionValidators.STOPBITS,
            vol.Optional(CONF_BYTESIZE, default=bytesize_default): ConnectionValidators.BYTESIZE,
        }
        
        if include_discovery:
            schema_dict.update({
                vol.Optional(CONF_DISCOVERY_ENABLED, default=True): bool,
                vol.Optional(CONF_SLAVE_ID_RANGE, default=slave_id_range_default): str,
            })
        
        return vol.Schema(schema_dict)
    
    @staticmethod
    def device_schema(
        device_name_default: str = "Modbus RTL Device",
        slave_id_default: int = 1,
        update_interval_default: int = None
    ) -> vol.Schema:
        """Build device configuration schema."""
        
        update_interval_default = update_interval_default or DiscoveryDefaults.UPDATE_INTERVAL
        
        return vol.Schema({
            vol.Required(CONF_DEVICE_NAME, default=device_name_default): str,
            vol.Required(CONF_SLAVE_ID, default=slave_id_default): DiscoveryValidators.SLAVE_ID,
            vol.Optional(CONF_UPDATE_INTERVAL, default=update_interval_default): DiscoveryValidators.UPDATE_INTERVAL,
        })
    
    @staticmethod
    def advanced_schema(
        binary_keywords_default: List[str] = None,
        batch_size_default: int = None,
        scan_delay_default: float = None,
        slave_range_start_default: int = None,
        slave_range_end_default: int = None
    ) -> vol.Schema:
        """Build advanced configuration schema."""
        
        # Use defaults if not provided
        binary_keywords_default = binary_keywords_default or BinarySensorDefaults.KEYWORDS
        batch_size_default = batch_size_default or DiscoveryDefaults.BATCH_SIZE
        scan_delay_default = scan_delay_default or DiscoveryDefaults.SCAN_DELAY
        slave_range_start_default = slave_range_start_default or DiscoveryDefaults.SLAVE_RANGE[0]
        slave_range_end_default = slave_range_end_default or DiscoveryDefaults.SLAVE_RANGE[1]
        
        return vol.Schema({
            vol.Optional(
                CONF_BINARY_KEYWORDS, 
                default=", ".join(binary_keywords_default)
            ): str,
            vol.Optional(CONF_BATCH_SIZE, default=batch_size_default): DiscoveryValidators.BATCH_SIZE,
            vol.Optional(CONF_SCAN_DELAY, default=scan_delay_default): DiscoveryValidators.SCAN_DELAY,
            vol.Optional(CONF_SLAVE_RANGE_START, default=slave_range_start_default): DiscoveryValidators.SLAVE_ID,
            vol.Optional(CONF_SLAVE_RANGE_END, default=slave_range_end_default): DiscoveryValidators.SLAVE_ID,
        })

# =============================================================================
# Configuration Utilities
# =============================================================================

class ConfigUtils:
    """Utility functions for configuration handling."""
    
    @staticmethod
    def parse_slave_id_range(range_str: str) -> Tuple[int, int]:
        """Parse slave ID range string like '1-10' or '5' into tuple."""
        range_str = range_str.strip()
        if '-' in range_str:
            start, end = range_str.split('-', 1)
            return int(start.strip()), int(end.strip())
        else:
            # Single slave ID
            slave_id = int(range_str)
            return slave_id, slave_id
    
    @staticmethod
    def format_slave_id_range(start: int, end: int) -> str:
        """Format slave ID range tuple into string."""
        if start == end:
            return str(start)
        else:
            return f"{start}-{end}"
    
    @staticmethod
    def parse_binary_keywords(keywords_str: str) -> List[str]:
        """Parse comma-separated binary keywords string into list."""
        return [k.strip() for k in keywords_str.split(",") if k.strip()]
    
    @staticmethod
    def format_binary_keywords(keywords: List[str]) -> str:
        """Format binary keywords list into comma-separated string."""
        return ", ".join(keywords)
    
    @staticmethod
    def _validate_field(config: Dict[str, Any], field_name: str, default_value: Any, 
                       validator: vol.Schema = None, required: bool = False) -> Any:
        """Validate a single configuration field."""
        if required and field_name not in config:
            raise vol.Invalid(f"Missing required parameter: {field_name}")
        
        value = config.get(field_name, default_value)
        if validator and value is not None:
            value = validator(value)
        return value
    
    @staticmethod
    def validate_connection_config(config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and normalize connection configuration."""
        _LOGGER.debug("validate_connection_config")
        
        return {
            CONF_DEVICE_PATH: ConfigUtils._validate_field(config, CONF_DEVICE_PATH, None, required=True),
            CONF_BAUDRATE: ConfigUtils._validate_field(config, CONF_BAUDRATE, ConnectionDefaults.BAUDRATE, ConnectionValidators.BAUDRATE),
            CONF_TIMEOUT: ConfigUtils._validate_field(config, CONF_TIMEOUT, ConnectionDefaults.TIMEOUT, ConnectionValidators.TIMEOUT),
            CONF_PARITY: ConfigUtils._validate_field(config, CONF_PARITY, ConnectionDefaults.PARITY, ConnectionValidators.PARITY),
            CONF_STOPBITS: ConfigUtils._validate_field(config, CONF_STOPBITS, ConnectionDefaults.STOPBITS, ConnectionValidators.STOPBITS),
            CONF_BYTESIZE: ConfigUtils._validate_field(config, CONF_BYTESIZE, ConnectionDefaults.BYTESIZE, ConnectionValidators.BYTESIZE),
            **{k: v for k, v in config.items() if k in [CONF_DISCOVERY_ENABLED, CONF_SLAVE_ID_RANGE]}
        }
    
    @staticmethod
    def get_connection_options() -> Dict[str, Dict]:
        """Get all connection options for UI building."""
        return {
            CONF_BAUDRATE: ConnectionOptions.BAUDRATE,
            CONF_PARITY: ConnectionOptions.PARITY,
            CONF_STOPBITS: ConnectionOptions.STOPBITS,
            CONF_BYTESIZE: ConnectionOptions.BYTESIZE,
        }
    
    @staticmethod
    def get_connection_defaults() -> Dict[str, Any]:
        """Get all connection defaults."""
        return {
            CONF_BAUDRATE: ConnectionDefaults.BAUDRATE,
            CONF_TIMEOUT: ConnectionDefaults.TIMEOUT,
            CONF_PARITY: ConnectionDefaults.PARITY,
            CONF_STOPBITS: ConnectionDefaults.STOPBITS,
            CONF_BYTESIZE: ConnectionDefaults.BYTESIZE,
        }
