# Generic Modbus Integration - Application Flow

This document explains the complete process flow through the Generic Modbus Integration code, from plugin loading to scheduled data collection.

## 🔄 Complete Process Flow

### **1. Plugin Loading & Registration**

#### **`__init__.py`** - Integration Entry Point
```python
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Generic Modbus from a config entry."""
```

**Flow:**
1. **Home Assistant loads the integration** from `custom_components/generic_modbus/`
2. **Manifest validation** - HA reads `manifest.json` to understand integration capabilities
3. **Platform registration** - HA registers `sensor` and `binary_sensor` platforms
4. **Domain data initialization** - Creates `hass.data[DOMAIN]` storage

---

### **2. User Adds Device - Config Flow**

#### **`config_flow.py`** - User Interface Flow

**Step 1: Initial Connection Setup**
```python
async def async_step_user(self, user_input: Optional[Dict[str, Any]] = None):
```
- User enters serial device path (`/dev/ttyUSB0`)
- Selects connection parameters (baudrate, parity, etc.) using **centralized `SchemaBuilder`**
- Chooses whether to enable auto-discovery

**Step 2: Device Discovery (if enabled)**
```python
async def async_step_discovery(self, user_input: Optional[Dict[str, Any]] = None):
```
- **Creates `ModbusDeviceDiscovery`** instance with connection parameters
- **Scans slave ID range** using `ConfigUtils.parse_slave_id_range()`
- **Identifies devices** using signature matching from `device_profiles.py`
- **Discovers registers** by scanning configured address ranges
- **Presents discovered devices** to user or falls back to manual config

**Step 3: Device Configuration**
```python
async def async_step_device_config(self, user_input: Optional[Dict[str, Any]] = None):
```
- User sets device name and slave ID
- **Tests connection** using `ModbusDeviceDiscovery._async_test_connection()`
- **Creates config entry** with all parameters and discovered register map

---

### **3. Device Setup & Coordinator Creation**

#### **`__init__.py`** - Device Initialization
```python
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
```

**Flow:**
1. **Extract config data** from the config entry
2. **Create coordinator** - Instantiates `GenericModbusCoordinator`
3. **Store coordinator** in `hass.data[DOMAIN][entry.entry_id]`
4. **Setup platforms** - Calls `async_forward_entry_setups()` for sensor/binary_sensor

#### **`coordinator.py`** - Data Coordination Setup
```python
class GenericModbusCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, config: Dict[str, Any]):
```

**Initialization:**
1. **Creates device manager** - `ModbusDeviceManager` instance
2. **Configures connection** - Serial parameters from config
3. **Registers device** - Adds device to manager with slave ID and parameters
4. **Sets update interval** - From config or default (30 seconds)
5. **Configures parameters** - Processes discovered/configured register map

---

### **4. Entity Creation**

#### **`sensor.py`** - Regular Sensor Entities
```python
async def async_setup_entry(hass, config_entry, async_add_entities):
```

**Flow:**
1. **Gets coordinator** from `hass.data[DOMAIN][config_entry.entry_id]`
2. **Retrieves all parameters** via `coordinator.get_all_parameters()`
3. **Filters for regular sensors** - Excludes binary parameters
4. **Creates sensor entities** - One `GenericModbusSensor` per parameter
5. **Registers entities** with Home Assistant

#### **`binary_sensor.py`** - Binary Sensor Entities
```python
async def async_setup_entry(hass, config_entry, async_add_entities):
```

**Flow:**
1. **Gets device configuration** using `config_manager.get_config()`
2. **Filters for binary parameters** using `_is_binary_parameter()`:
   - Checks **configurable binary keywords** from `device_config.binary_sensor.binary_keywords`
   - Applies **parameter overrides** from `device_config.binary_sensor.parameter_overrides`
3. **Creates binary sensor entities** - One `GenericModbusBinarySensor` per binary parameter
4. **Registers entities** with Home Assistant

---

### **5. Scheduled Data Collection**

#### **`coordinator.py`** - Data Update Orchestration
```python
async def _async_update_data(self) -> Dict[str, Any]:
```

**Update Cycle (every 30 seconds by default):**

1. **Coordinator triggers update** - Home Assistant calls `_async_update_data()`
2. **Device manager fetches data**:
   ```python
   device = self.device_manager.get_device(self.device_id)
   return await self.hass.async_add_executor_job(device.read_all_parameters)
   ```

#### **`generic_modbus/device_manager.py`** - Device Communication
```python
def read_all_parameters(self) -> Dict[str, Any]:
```

**Data Collection Process:**
1. **Opens Modbus connection** using configured serial parameters
2. **Iterates through all enabled parameters**
3. **For each parameter**:
   - Gets register address and function code
   - **Reads register** via `ModbusClient.read_single_register()`
   - **Applies scaling** - `(raw_value * scale) + offset`
   - **Stores processed value**
4. **Closes connection**
5. **Returns data dictionary** - `{parameter_name: processed_value}`

#### **`generic_modbus/modbus_client.py`** - Low-Level Communication
```python
def read_single_register(self, slave_id: int, function_code: FunctionCode, address: int):
```

**Modbus Communication:**
1. **Builds Modbus RTU frame** - Slave ID + Function Code + Address + CRC
2. **Sends request** over serial connection
3. **Receives response** with timeout handling
4. **Validates CRC** and response format
5. **Extracts register value** from response
6. **Returns raw integer value**

---

### **6. Entity Updates & State Management**

#### **Entity Update Flow:**
1. **Coordinator receives new data** from device manager
2. **Coordinator notifies all entities** via `async_write_ha_state()`
3. **Each entity processes its data**:

#### **`sensor.py`** - Regular Sensor Updates
```python
@property
def native_value(self) -> Optional[float]:
    if not self.coordinator.data:
        return None
    return self.coordinator.data.get(self._parameter_name)
```

#### **`binary_sensor.py`** - Binary Sensor Updates  
```python
@property
def is_on(self) -> Optional[bool]:
    value = self.coordinator.data.get(self._parameter_name)
    return bool(value)  # 0 = off, non-zero = on
```

4. **Home Assistant updates UI** with new sensor values

---

## 🔄 Configuration System Integration

Throughout this flow, the **centralized configuration system** is used:

### **During Setup:**
- **`config_definitions.py`** provides all validation rules and UI options
- **`SchemaBuilder`** creates consistent forms across all config steps
- **`ConfigUtils`** parse user input (slave ID ranges, binary keywords)

### **During Runtime:**
- **`device_config.py`** manages per-device configuration
- **`config_manager`** provides device-specific settings
- **Binary sensor detection** uses configurable keywords and overrides
- **Discovery parameters** use configurable scan ranges and timing

---

## 📊 Data Flow Summary

```
User Input → Config Flow → Device Discovery → Coordinator Setup
     ↓              ↓              ↓                ↓
Schema Builder → ModbusDiscovery → DeviceManager → Entity Creation
     ↓              ↓              ↓                ↓
Validation → Register Scanning → Connection Setup → Sensor/Binary Setup
     ↓              ↓              ↓                ↓
Config Entry → Parameter Map → Scheduled Updates → State Updates → UI
```

---

## 🎯 Key Integration Points

1. **Configuration Centralization** - All settings flow through `config_definitions.py`
2. **Device Abstraction** - `ModbusDeviceManager` handles all device communication
3. **Coordinator Pattern** - Single point for data updates and entity coordination
4. **Configurable Detection** - Binary sensors use per-device keyword configuration
5. **Error Handling** - Graceful degradation at each level with proper logging

---

## 📁 File Responsibilities

### **Core Integration Files:**
- **`__init__.py`** - Integration entry point, coordinator setup
- **`config_flow.py`** - User interface for device configuration
- **`coordinator.py`** - Data update coordination and caching
- **`sensor.py`** - Regular sensor entity implementation
- **`binary_sensor.py`** - Binary sensor entity implementation
- **`const.py`** - Constants and configuration keys

### **Configuration System:**
- **`config_definitions.py`** - Centralized configuration definitions
- **`device_config.py`** - Per-device configuration management
- **`config_flow_advanced.py`** - Advanced configuration options

### **Modbus Communication:**
- **`generic_modbus/modbus_client.py`** - Low-level Modbus RTU communication
- **`generic_modbus/device_manager.py`** - Device abstraction and parameter management
- **`generic_modbus/device_discovery.py`** - Auto-discovery and device identification
- **`generic_modbus/device_profiles.py`** - Known device definitions

### **UI and Translations:**
- **`translations/en.json`** - User interface text and descriptions
- **`ui_utils.py`** - UI utility functions with version compatibility

---

## 🔄 Lifecycle Summary

1. **Installation** - Integration loaded by Home Assistant
2. **Configuration** - User configures device through UI flow
3. **Discovery** - Optional auto-discovery of device capabilities
4. **Setup** - Coordinator and entities created
5. **Operation** - Scheduled data collection and entity updates
6. **Maintenance** - Configuration changes through options flow

This architecture ensures the integration is truly generic, maintainable, and extensible while providing a smooth user experience from initial setup through ongoing operation.

---

## 🚀 Extension Points

### **Adding New Device Types:**
1. Add device profile to `device_profiles.py`
2. Configure binary keywords in `device_config.py`
3. Optionally add custom scan ranges

### **Adding New Configuration Options:**
1. Extend `config_definitions.py` with new validators
2. Update `SchemaBuilder` with new schema methods
3. Modify config flow steps as needed

### **Adding New Entity Types:**
1. Create new platform file (e.g., `switch.py`)
2. Add platform to `PLATFORMS` in `const.py`
3. Implement entity setup in `__init__.py`

This modular architecture makes the integration highly extensible while maintaining clean separation of concerns.
