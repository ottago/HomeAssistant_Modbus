"""Device configuration system for Generic Modbus Integration."""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field

# Import common configuration definitions
from .config_definitions import (
    ConnectionDefaults,
    ConnectionOptions,
    DiscoveryDefaults,
    BinarySensorDefaults,
    ScanRangeDefaults,
)

# Try to import FunctionCode, fall back to enum if not available
try:
    from .device.modbus_client import FunctionCode
except ImportError:
    # Fallback for standalone testing
    from enum import Enum
    class FunctionCode(Enum):
        READ_INPUT_REGISTERS = 4
        READ_HOLDING_REGISTERS = 3

@dataclass
class BinarySensorConfig:
    """Configuration for binary sensor detection."""
    
    # Keywords that indicate a parameter should be a binary sensor
    binary_keywords: List[str] = field(default_factory=lambda: BinarySensorDefaults.KEYWORDS.copy())
    
    # Device class mapping based on parameter names
    device_class_keywords: Dict[str, List[str]] = field(default_factory=lambda: BinarySensorDefaults.DEVICE_CLASS_KEYWORDS.copy())
    
    # Custom binary sensor overrides (parameter_name -> force_binary)
    parameter_overrides: Dict[str, bool] = field(default_factory=dict)

@dataclass
class DiscoveryConfig:
    """Configuration for device discovery."""
    
    # Common registers to check for device identification
    common_id_registers: List[Tuple[int, List[int]]] = field(default_factory=lambda: ScanRangeDefaults.COMMON_ID_REGISTERS.copy())
    
    # Default scan ranges for unknown devices
    default_scan_ranges: Dict[int, List[Tuple[int, int]]] = field(default_factory=lambda: ScanRangeDefaults.RANGES.copy())
    
    # Default slave ID range for discovery
    default_slave_range: Tuple[int, int] = DiscoveryDefaults.SLAVE_RANGE
    
    # Scanning parameters
    batch_size: int = DiscoveryDefaults.BATCH_SIZE
    scan_delay: float = DiscoveryDefaults.SCAN_DELAY
    
    # Custom scan ranges for specific devices (device_key -> ranges)
    device_scan_ranges: Dict[str, Dict[int, List[Tuple[int, int]]]] = field(default_factory=dict)

@dataclass
class ConnectionConfig:
    """Configuration for Modbus connection parameters."""
    
    # Default connection parameters
    default_baudrate: int = ConnectionDefaults.BAUDRATE
    default_timeout: float = ConnectionDefaults.TIMEOUT
    default_parity: str = ConnectionDefaults.PARITY
    default_stopbits: int = ConnectionDefaults.STOPBITS
    default_bytesize: int = ConnectionDefaults.BYTESIZE
    
    # Available options for UI (reference to common definitions)
    baudrate_options: Dict[int, str] = field(default_factory=lambda: ConnectionOptions.BAUDRATE.copy())
    parity_options: Dict[str, str] = field(default_factory=lambda: ConnectionOptions.PARITY.copy())
    stopbits_options: Dict[int, str] = field(default_factory=lambda: ConnectionOptions.STOPBITS.copy())
    bytesize_options: Dict[int, str] = field(default_factory=lambda: ConnectionOptions.BYTESIZE.copy())

@dataclass
class DeviceConfig:
    """Complete device configuration."""
    
    # Device identification
    device_name: str = "Generic Modbus Device"
    manufacturer: str = "Unknown"
    model: str = "Unknown"
    
    # Configuration sections
    binary_sensor: BinarySensorConfig = field(default_factory=BinarySensorConfig)
    discovery: DiscoveryConfig = field(default_factory=DiscoveryConfig)
    connection: ConnectionConfig = field(default_factory=ConnectionConfig)
    
    # Parameter-specific overrides
    parameter_configs: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    # Update intervals
    default_update_interval: int = DiscoveryDefaults.UPDATE_INTERVAL
    parameter_update_intervals: Dict[str, int] = field(default_factory=dict)

class DeviceConfigManager:
    """Manages device configurations."""
    
    def __init__(self):
        self._configs: Dict[str, DeviceConfig] = {}
        self._default_config = DeviceConfig()
    
    def get_config(self, device_id: str) -> DeviceConfig:
        """Get configuration for a specific device."""
        return self._configs.get(device_id, self._default_config)
    
    def set_config(self, device_id: str, config: DeviceConfig) -> None:
        """Set configuration for a specific device."""
        self._configs[device_id] = config
    
    def update_binary_sensor_config(self, device_id: str, **kwargs) -> None:
        """Update binary sensor configuration for a device."""
        config = self.get_config(device_id)
        for key, value in kwargs.items():
            if hasattr(config.binary_sensor, key):
                setattr(config.binary_sensor, key, value)
        self._configs[device_id] = config
    
    def update_discovery_config(self, device_id: str, **kwargs) -> None:
        """Update discovery configuration for a device."""
        config = self.get_config(device_id)
        for key, value in kwargs.items():
            if hasattr(config.discovery, key):
                setattr(config.discovery, key, value)
        self._configs[device_id] = config
    
    def add_binary_keyword(self, device_id: str, keyword: str) -> None:
        """Add a binary sensor keyword for a device."""
        config = self.get_config(device_id)
        if keyword not in config.binary_sensor.binary_keywords:
            config.binary_sensor.binary_keywords.append(keyword)
        self._configs[device_id] = config
    
    def remove_binary_keyword(self, device_id: str, keyword: str) -> None:
        """Remove a binary sensor keyword for a device."""
        config = self.get_config(device_id)
        if keyword in config.binary_sensor.binary_keywords:
            config.binary_sensor.binary_keywords.remove(keyword)
        self._configs[device_id] = config
    
    def set_parameter_override(self, device_id: str, parameter_name: str, is_binary: bool) -> None:
        """Override binary sensor detection for a specific parameter."""
        config = self.get_config(device_id)
        config.binary_sensor.parameter_overrides[parameter_name] = is_binary
        self._configs[device_id] = config
    
    def add_scan_range(self, device_id: str, function_code: int, start_addr: int, end_addr: int) -> None:
        """Add a custom scan range for a device."""
        config = self.get_config(device_id)
        if device_id not in config.discovery.device_scan_ranges:
            config.discovery.device_scan_ranges[device_id] = {}
        if function_code not in config.discovery.device_scan_ranges[device_id]:
            config.discovery.device_scan_ranges[device_id][function_code] = []
        config.discovery.device_scan_ranges[device_id][function_code].append((start_addr, end_addr))
        self._configs[device_id] = config
    
    def export_config(self, device_id: str) -> Dict[str, Any]:
        """Export device configuration to dictionary."""
        config = self.get_config(device_id)
        return {
            "device_name": config.device_name,
            "manufacturer": config.manufacturer,
            "model": config.model,
            "binary_sensor": {
                "binary_keywords": config.binary_sensor.binary_keywords,
                "device_class_keywords": config.binary_sensor.device_class_keywords,
                "parameter_overrides": config.binary_sensor.parameter_overrides,
            },
            "discovery": {
                "default_slave_range": config.discovery.default_slave_range,
                "batch_size": config.discovery.batch_size,
                "scan_delay": config.discovery.scan_delay,
                "device_scan_ranges": config.discovery.device_scan_ranges,
            },
            "connection": {
                "default_baudrate": config.connection.default_baudrate,
                "default_timeout": config.connection.default_timeout,
                "default_parity": config.connection.default_parity,
                "default_stopbits": config.connection.default_stopbits,
                "default_bytesize": config.connection.default_bytesize,
            },
            "parameter_configs": config.parameter_configs,
            "default_update_interval": config.default_update_interval,
            "parameter_update_intervals": config.parameter_update_intervals,
        }
    
    def import_config(self, device_id: str, config_dict: Dict[str, Any]) -> None:
        """Import device configuration from dictionary."""
        config = DeviceConfig()
        
        # Basic device info
        config.device_name = config_dict.get("device_name", "Generic Modbus Device")
        config.manufacturer = config_dict.get("manufacturer", "Unknown")
        config.model = config_dict.get("model", "Unknown")
        
        # Binary sensor config
        if "binary_sensor" in config_dict:
            bs_config = config_dict["binary_sensor"]
            config.binary_sensor.binary_keywords = bs_config.get("binary_keywords", BinarySensorDefaults.KEYWORDS.copy())
            config.binary_sensor.device_class_keywords = bs_config.get("device_class_keywords", BinarySensorDefaults.DEVICE_CLASS_KEYWORDS.copy())
            config.binary_sensor.parameter_overrides = bs_config.get("parameter_overrides", {})
        
        # Discovery config
        if "discovery" in config_dict:
            disc_config = config_dict["discovery"]
            config.discovery.default_slave_range = tuple(disc_config.get("default_slave_range", DiscoveryDefaults.SLAVE_RANGE))
            config.discovery.batch_size = disc_config.get("batch_size", DiscoveryDefaults.BATCH_SIZE)
            config.discovery.scan_delay = disc_config.get("scan_delay", DiscoveryDefaults.SCAN_DELAY)
            config.discovery.device_scan_ranges = disc_config.get("device_scan_ranges", {})
        
        # Connection config
        if "connection" in config_dict:
            conn_config = config_dict["connection"]
            config.connection.default_baudrate = conn_config.get("default_baudrate", ConnectionDefaults.BAUDRATE)
            config.connection.default_timeout = conn_config.get("default_timeout", ConnectionDefaults.TIMEOUT)
            config.connection.default_parity = conn_config.get("default_parity", ConnectionDefaults.PARITY)
            config.connection.default_stopbits = conn_config.get("default_stopbits", ConnectionDefaults.STOPBITS)
            config.connection.default_bytesize = conn_config.get("default_bytesize", ConnectionDefaults.BYTESIZE)
        
        # Parameter configs
        config.parameter_configs = config_dict.get("parameter_configs", {})
        config.default_update_interval = config_dict.get("default_update_interval", DiscoveryDefaults.UPDATE_INTERVAL)
        config.parameter_update_intervals = config_dict.get("parameter_update_intervals", {})
        
        self._configs[device_id] = config

# Global config manager instance
config_manager = DeviceConfigManager()
