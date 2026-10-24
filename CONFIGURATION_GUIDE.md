# Generic Modbus Integration - Configuration Guide

This guide explains all the configurable values in the Generic Modbus Integration, making it truly generic and adaptable to any Modbus device.

## 🎯 Overview

The integration now supports per-device configuration of:
- **Binary sensor detection keywords**
- **Device class mappings**
- **Discovery scan ranges**
- **Connection parameters**
- **Update intervals**
- **Parameter-specific overrides**

## 📋 Configuration Categories

### 1. Binary Sensor Configuration

#### **Binary Keywords**
Controls which parameters are treated as binary sensors (on/off) vs regular sensors (numeric).

**Default Keywords:**
```python
[
    "status", "alarm", "fault", "error", "warning", "alert",
    "connected", "enabled", "active", "running", "charging",
    "discharging", "protection", "limit", "bit", "flag"
]
```

**How to Configure:**
- **UI**: Advanced Configuration → Binary Sensor Keywords
- **Code**: `config_manager.update_binary_sensor_config(device_id, binary_keywords=new_list)`

**Examples:**
- Add "emergency": Parameters with "emergency" become binary sensors
- Remove "charging": Parameters with "charging" become regular sensors
- Device-specific: Solar controllers might add "mppt", "boost"

#### **Device Class Keywords**
Maps parameter names to Home Assistant device classes for better UI representation.

**Default Mappings:**
```python
{
    "connectivity": ["connected", "connection"],
    "problem": ["fault", "error", "alarm"],
    "running": ["running", "active"],
    "power": ["charging", "discharging"],
    "safety": ["protection", "limit"]
}
```

**How to Configure:**
```python
config_manager.get_config(device_id).binary_sensor.device_class_keywords["problem"].append("failure")
```

#### **Parameter Overrides**
Force specific parameters to be binary or regular sensors, regardless of keywords.

**How to Configure:**
```python
# Force "battery_voltage" to be a regular sensor even if it contains "status"
config_manager.set_parameter_override(device_id, "battery_voltage", False)

# Force "system_ok" to be a binary sensor even if it doesn't match keywords
config_manager.set_parameter_override(device_id, "system_ok", True)
```

### 2. Discovery Configuration

#### **Common ID Registers**
Registers checked to identify if a device is responsive.

**Default Registers:**
```python
[
    # Input registers
    (FunctionCode.READ_INPUT_REGISTERS, [0x0000, 0x0001, 0x0002, 0x0003]),
    (FunctionCode.READ_INPUT_REGISTERS, [0x9000, 0x9001, 0x9002, 0x9003]),
    (FunctionCode.READ_INPUT_REGISTERS, [0x1000, 0x1001, 0x1002, 0x1003]),
    # Holding registers  
    (FunctionCode.READ_HOLDING_REGISTERS, [0x0000, 0x0001, 0x0002, 0x0003]),
    (FunctionCode.READ_HOLDING_REGISTERS, [0x9000, 0x9001, 0x9002, 0x9003]),
    (FunctionCode.READ_HOLDING_REGISTERS, [0x1000, 0x1001, 0x1002, 0x1003]),
]
```

#### **Default Scan Ranges**
Address ranges scanned when discovering unknown devices.

**Default Ranges:**
```python
{
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
```

**How to Configure:**
```python
# Add custom scan range for a specific device
config_manager.add_scan_range(device_id, FunctionCode.READ_INPUT_REGISTERS.value, 0x2000, 0x20FF)
```

#### **Discovery Parameters**

| Parameter | Default | Description | Range |
|-----------|---------|-------------|-------|
| `default_slave_range` | (1, 10) | Slave IDs to scan | (1, 247) |
| `batch_size` | 8 | Registers per scan batch | 1-50 |
| `scan_delay` | 0.5 | Delay between scans (seconds) | 0.1-5.0 |

**How to Configure:**
- **UI**: Advanced Configuration → Scan settings
- **Code**: `config_manager.update_discovery_config(device_id, batch_size=16, scan_delay=0.2)`

### 3. Connection Configuration

#### **Default Connection Parameters**

| Parameter | Default | Options |
|-----------|---------|---------|
| `default_baudrate` | 115200 | 9600, 19200, 38400, 57600, 115200 |
| `default_timeout` | 2.0 | 0.1-30.0 seconds |
| `default_parity` | 'N' | 'N' (None), 'E' (Even), 'O' (Odd) |
| `default_stopbits` | 1 | 1, 2 |
| `default_bytesize` | 8 | 7, 8 |

### 4. Update Intervals

#### **Global Update Interval**
Default polling frequency for all parameters.

**Default**: 30 seconds
**Range**: 5-300 seconds

#### **Parameter-Specific Intervals**
Override update frequency for individual parameters.

**Example Use Cases:**
- Fast-changing values (current, power): 5-10 seconds
- Slow-changing values (temperature, SOC): 60-120 seconds
- Status parameters: 15-30 seconds

**How to Configure:**
```python
device_config = config_manager.get_config(device_id)
device_config.parameter_update_intervals["battery_current"] = 5  # 5 seconds
device_config.parameter_update_intervals["battery_temp"] = 60   # 60 seconds
```

## 🔧 Device-Specific Examples

### Solar Charge Controller
```python
# Add solar-specific binary keywords
config_manager.add_binary_keyword(device_id, "mppt")
config_manager.add_binary_keyword(device_id, "boost")
config_manager.add_binary_keyword(device_id, "float")

# Add solar-specific scan range
config_manager.add_scan_range(device_id, FunctionCode.READ_INPUT_REGISTERS.value, 0x3100, 0x31FF)

# Configure update intervals
device_config = config_manager.get_config(device_id)
device_config.parameter_update_intervals.update({
    "pv_power": 5,      # Fast updates for power
    "battery_temp": 60, # Slow updates for temperature
    "daily_energy": 300 # Very slow for daily totals
})
```

### Power Meter
```python
# Add power meter keywords
config_manager.add_binary_keyword(device_id, "overload")
config_manager.add_binary_keyword(device_id, "phase_loss")

# Add power meter scan ranges
config_manager.add_scan_range(device_id, FunctionCode.READ_INPUT_REGISTERS.value, 0x0000, 0x00FF)
config_manager.add_scan_range(device_id, FunctionCode.READ_INPUT_REGISTERS.value, 0x0100, 0x01FF)

# Configure for 3-phase monitoring
device_config = config_manager.get_config(device_id)
device_config.discovery.batch_size = 16  # Larger batches for many registers
device_config.discovery.scan_delay = 0.1  # Faster scanning
```

### Industrial Sensor
```python
# Add industrial-specific keywords
config_manager.add_binary_keyword(device_id, "interlock")
config_manager.add_binary_keyword(device_id, "maintenance")
config_manager.add_binary_keyword(device_id, "calibration")

# Configure for slow, reliable communication
device_config = config_manager.get_config(device_id)
device_config.discovery.batch_size = 4    # Small batches
device_config.discovery.scan_delay = 1.0  # Slow scanning
device_config.connection.default_timeout = 5.0  # Long timeout
```

## 🛠️ Configuration Methods

### 1. Through Home Assistant UI
1. **Initial Setup**: Configure basic settings during integration setup
2. **Advanced Setup**: Use "Configure Advanced Settings" option
3. **Options**: Modify settings through Integration Options

### 2. Through Services
```yaml
# Update binary keywords
service: generic_modbus.update_binary_keywords
data:
  device_id: "solar_charger_1"
  keywords: ["status", "alarm", "fault", "mppt", "boost"]

# Export configuration
service: generic_modbus.export_device_config
data:
  device_id: "solar_charger_1"
  filename: "solar_charger_config.json"
```

### 3. Through Code/Automation
```python
from custom_components.generic_modbus.device_config import config_manager

# Get current configuration
device_config = config_manager.get_config("my_device")

# Modify configuration
device_config.binary_sensor.binary_keywords.append("custom_status")
device_config.discovery.batch_size = 12
device_config.default_update_interval = 15

# Save configuration
config_manager.set_config("my_device", device_config)
```

### 4. Through Configuration Files
```json
{
  "device_name": "My Solar Charger",
  "manufacturer": "Custom",
  "model": "SC-100",
  "binary_sensor": {
    "binary_keywords": ["status", "alarm", "fault", "mppt", "boost", "float"],
    "device_class_keywords": {
      "connectivity": ["connected", "communication"],
      "problem": ["fault", "error", "alarm", "failure"],
      "running": ["running", "active", "mppt"],
      "power": ["charging", "discharging", "boost", "float"],
      "safety": ["protection", "limit", "overload"]
    },
    "parameter_overrides": {
      "system_voltage": false,
      "charge_status": true
    }
  },
  "discovery": {
    "default_slave_range": [1, 5],
    "batch_size": 8,
    "scan_delay": 0.3,
    "device_scan_ranges": {
      "my_device": {
        "4": [
          [12544, 12799]
        ]
      }
    }
  },
  "connection": {
    "default_baudrate": 115200,
    "default_timeout": 2.5,
    "default_parity": "N",
    "default_stopbits": 1,
    "default_bytesize": 8
  },
  "parameter_configs": {},
  "default_update_interval": 20,
  "parameter_update_intervals": {
    "pv_power": 5,
    "battery_temp": 60,
    "daily_energy": 300
  }
}
```

## 📊 Best Practices

### 1. Binary Sensor Keywords
- **Start with defaults**: The default keywords cover most common cases
- **Add device-specific terms**: Include terminology specific to your device type
- **Test thoroughly**: Verify parameters are classified correctly
- **Use overrides sparingly**: Only override when keyword matching fails

### 2. Discovery Configuration
- **Start conservative**: Use small batch sizes and longer delays for unknown devices
- **Optimize gradually**: Increase batch size and reduce delays once stable
- **Device-specific ranges**: Define specific ranges for known device types
- **Monitor logs**: Watch for timeout errors and adjust accordingly

### 3. Update Intervals
- **Match data volatility**: Fast intervals for changing data, slow for static
- **Consider network load**: Too many fast updates can overwhelm the bus
- **Balance responsiveness**: Find the sweet spot between updates and performance
- **Use parameter-specific intervals**: Different parameters need different frequencies

### 4. Connection Parameters
- **Match device specs**: Use the exact settings from device documentation
- **Start with defaults**: 115200 baud, 2s timeout work for most modern devices
- **Adjust for distance**: Longer cables may need slower baud rates
- **Test thoroughly**: Verify stable communication before deploying

## 🔍 Troubleshooting Configuration

### Binary Sensors Not Detected
1. Check if parameter name contains binary keywords
2. Add device-specific keywords
3. Use parameter override as last resort
4. Check logs for detection logic

### Discovery Issues
1. Verify scan ranges cover device registers
2. Increase timeout for slow devices
3. Reduce batch size for unreliable communication
4. Check slave ID range includes your device

### Performance Problems
1. Reduce update frequencies
2. Increase scan delays
3. Use smaller batch sizes
4. Optimize parameter selection

### Connection Problems
1. Verify baud rate matches device
2. Increase timeout for slow responses
3. Check parity/stop bits configuration
4. Test with minimal scan ranges

## 📝 Migration from Hardcoded Values

If you're upgrading from a version with hardcoded values:

1. **Export current config**: Use the export service to save current settings
2. **Review defaults**: Check if new defaults work for your setup
3. **Customize gradually**: Start with defaults, then customize as needed
4. **Test thoroughly**: Verify all parameters work as expected
5. **Document changes**: Keep track of customizations for future reference

---

This configuration system makes the Generic Modbus Integration truly generic and adaptable to any Modbus device while maintaining reasonable defaults for common use cases.
