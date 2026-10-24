# Generic Modbus Device Integration for Home Assistant

A powerful, auto-discovering Home Assistant integration for Modbus RTU devices. This integration automatically discovers Modbus devices on your network, identifies their capabilities, and creates appropriate Home Assistant entities with proper device classes, units, and scaling.

## ✨ Features

### 🔍 **Auto-Discovery**
- Automatically scans for Modbus devices on your serial network
- Identifies device types using signature matching
- Maps registers to meaningful parameter names
- Applies proper scaling, units, and Home Assistant device classes

### 🎛️ **UI Configuration**
- Complete configuration through Home Assistant UI
- No YAML configuration required
- Device discovery wizard
- Parameter customization options

### 📊 **Dynamic Entity Creation**
- Creates sensor entities for all discovered parameters
- Binary sensors for status/alarm parameters
- Proper device classes (voltage, current, power, temperature, etc.)
- State classes for energy dashboard integration

### 🔧 **Multi-Device Support**
- Support for multiple devices on the same serial network
- Individual configuration for each device
- Conflict detection and resolution

### ⚙️ **Flexible Configuration**
- Configurable update intervals
- Parameter enable/disable options
- Custom scaling and units
- Device-specific profiles

## 🚀 Installation

### Method 1: Manual Installation

1. **Download the integration**:
   ```bash
   # Clone or download this repository
   git clone <repository-url>
   cd generic-modbus-integration
   ```

2. **Run the installer**:
   ```bash
   ./install_integration.sh /path/to/your/homeassistant/config
   ```
   
   Examples:
   - Home Assistant OS: `./install_integration.sh /config`
   - Home Assistant Core: `./install_integration.sh ~/.homeassistant`

3. **Restart Home Assistant**

### Method 2: HACS (Coming Soon)

This integration will be available through HACS in the future.

## 📋 Configuration

### Initial Setup

1. **Go to Settings → Devices & Services**
2. **Click "+ Add Integration"**
3. **Search for "Generic Modbus Device Integration"**
4. **Follow the configuration wizard**:

#### Step 1: Connection Settings
- **Device Path**: Serial device path (e.g., `/dev/ttyUSB0`, `/dev/ttyAMA0`, `COM1`)
- **Baud Rate**: Communication speed (usually 115200)
- **Timeout**: Communication timeout in seconds
- **Parity**: Usually "None" (N)
- **Stop Bits**: Usually 1
- **Data Bits**: Usually 8

#### Step 2: Device Discovery
- **Enable Discovery**: Automatically scan for devices
- **Slave ID Range**: Range to scan (e.g., "1-10" or "1")

The integration will scan your network and show discovered devices.

#### Step 3: Device Selection
- Choose from automatically discovered devices, or
- Configure manually if discovery doesn't find your device

#### Step 4: Device Configuration
- **Device Name**: Friendly name in Home Assistant
- **Slave ID**: Modbus slave ID (1-247)
- **Update Interval**: How often to poll the device

### Supported Devices

The integration includes built-in profiles for:

#### ✅ **Solar Charge Controllers**
- **Tracer 3210AN** (EPSolar/EPEver)
  - PV voltage, current, and power
  - Battery voltage, current, SOC, and temperature
  - Load voltage, current, and power
  - System status and statistics
  - Configuration parameters

#### ✅ **Generic Power Meters**
- Voltage measurements (L1, L2, L3)
- Current measurements (L1, L2, L3)
- Power calculations
- Energy counters

#### 🔧 **Custom Devices**
- Auto-discovery for unknown devices
- Manual parameter configuration
- Custom scaling and units

## 📊 Entity Types

### Sensor Entities
- **Voltage**: Battery, PV, Load voltages with proper device class
- **Current**: Charging, load currents with amperage units
- **Power**: PV generation, load consumption, battery power
- **Temperature**: Battery, device temperatures
- **Energy**: Daily/total generation and consumption
- **Percentage**: Battery state of charge, efficiency metrics

### Binary Sensor Entities
- **Status Indicators**: Charging status, load status
- **Alarms**: Fault conditions, protection triggers
- **Connectivity**: Device connection status

### Device Information
- Manufacturer and model identification
- Firmware version (if available)
- Device configuration details

## ⚙️ Advanced Configuration

### Parameter Customization

Access **Settings → Devices & Services → Generic Modbus → Configure** to:

- **Enable/Disable Parameters**: Choose which parameters to monitor
- **Update Intervals**: Set different polling rates
- **Custom Names**: Rename parameters
- **Units and Scaling**: Adjust measurement units

### Multiple Devices

To add multiple devices:

1. **Add Integration** again for each device
2. **Use different slave IDs** for each device
3. **Configure unique names** to avoid conflicts

### Device Profiles

Create custom device profiles by:

1. **Discovering your device** with auto-discovery
2. **Exporting the configuration** using the service call
3. **Modifying the profile** for your specific needs
4. **Sharing profiles** with the community

## 🔧 Services

The integration provides several services for advanced users:

### `generic_modbus.discover_devices`
Manually trigger device discovery:
```yaml
service: generic_modbus.discover_devices
data:
  device_path: "/dev/ttyUSB0"
  baudrate: 115200
  slave_id_range: "1-10"
```

### `generic_modbus.read_parameter`
Read a specific parameter:
```yaml
service: generic_modbus.read_parameter
target:
  entity_id: sensor.solar_charger_pv_voltage
data:
  parameter_name: "pv_voltage"
```

### `generic_modbus.write_register`
Write to a Modbus register:
```yaml
service: generic_modbus.write_register
target:
  entity_id: sensor.solar_charger_battery_voltage
data:
  register_address: "0x9001"
  value: 1400
```

### `generic_modbus.export_device_config`
Export device configuration:
```yaml
service: generic_modbus.export_device_config
target:
  entity_id: sensor.solar_charger_pv_voltage
data:
  filename: "my_device_config.json"
```

## 🐛 Troubleshooting

### Connection Issues

**Problem**: "Cannot connect to device"
- ✅ Check device path (`ls /dev/tty*`)
- ✅ Verify permissions (`sudo chmod 666 /dev/ttyUSB0`)
- ✅ Ensure device is powered and connected
- ✅ Try different baud rates

**Problem**: "No devices found during discovery"
- ✅ Expand slave ID range (try 1-50)
- ✅ Check device documentation for correct slave ID
- ✅ Try manual configuration
- ✅ Verify Modbus RTU settings

### Entity Issues

**Problem**: "Entities not updating"
- ✅ Check Home Assistant logs
- ✅ Verify device is responding
- ✅ Adjust update interval
- ✅ Check parameter configuration

**Problem**: "Wrong values or units"
- ✅ Check parameter scaling in device options
- ✅ Verify device profile is correct
- ✅ Compare with device manual

### Performance Issues

**Problem**: "Slow updates or timeouts"
- ✅ Increase timeout value
- ✅ Reduce update frequency
- ✅ Disable unused parameters
- ✅ Check serial connection quality

## 📖 Technical Details

### Architecture
- **Discovery Engine**: Auto-detects devices and capabilities
- **Device Profiles**: Template system for known devices
- **Parameter Mapping**: Converts raw registers to meaningful data
- **Coordinator Pattern**: Efficient data updates and caching

### Communication
- **Protocol**: Modbus RTU over serial
- **Function Codes**: FC03 (Holding Registers), FC04 (Input Registers)
- **Error Handling**: Graceful handling of communication errors
- **Connection Management**: Automatic reconnection and cleanup

### Data Processing
- **Scaling**: Automatic application of scale factors
- **Units**: Proper unit assignment and conversion
- **Device Classes**: Home Assistant device class mapping
- **State Classes**: Energy dashboard integration

## 🤝 Contributing

We welcome contributions! Please:

1. **Report Issues**: Use GitHub issues for bugs and feature requests
2. **Device Profiles**: Share profiles for new devices
3. **Code Contributions**: Submit pull requests for improvements
4. **Documentation**: Help improve documentation and examples

### Adding Device Support

To add support for a new device:

1. **Use auto-discovery** to scan your device
2. **Export the configuration** using the service
3. **Create a device profile** in `device_profiles.py`
4. **Test thoroughly** with your device
5. **Submit a pull request** with the profile

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Built on the solid foundation of the original Tracer Solar Charger integration
- Inspired by the Home Assistant Modbus integration
- Thanks to the Home Assistant community for feedback and testing

## 📞 Support

- **GitHub Issues**: Report bugs and request features
- **Home Assistant Community**: Discuss in the forums
- **Documentation**: Check this README and inline documentation

---

**Made with ❤️ for the Home Assistant community**
