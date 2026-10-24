"""Constants for the Generic Modbus integration."""

from homeassistant.const import Platform


# Integration domain
DOMAIN = "generic_modbus"

# Platforms supported by this integration
PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR]

# Configuration keys
CONF_DEVICE_PATH = "device_path"
CONF_BAUDRATE = "baudrate"
CONF_SLAVE_ID = "slave_id"
CONF_TIMEOUT = "timeout"
CONF_PARITY = "parity"
CONF_STOPBITS = "stopbits"
CONF_BYTESIZE = "bytesize"
CONF_DEVICE_NAME = "device_name"
CONF_DEVICE_PROFILE = "device_profile"
CONF_PARAMETERS = "parameters"
CONF_UPDATE_INTERVAL = "update_interval"

# Discovery configuration
CONF_DISCOVERY_ENABLED = "discovery_enabled"
CONF_SLAVE_ID_RANGE = "slave_id_range"

# Advanced fields
CONF_BINARY_KEYWORDS = "binary_keywords"
CONF_BATCH_SIZE = "batch_size"
CONF_SCAN_DELAY = "scan_delay"
CONF_SLAVE_RANGE_START = "slave_range_start"
CONF_SLAVE_RANGE_END = "slave_range_end"

# Parameter configuration keys
CONF_PARAM_ENABLED = "enabled"
CONF_PARAM_NAME = "name"
CONF_PARAM_UNIT = "unit"
CONF_PARAM_SCALE = "scale"
CONF_PARAM_OFFSET = "offset"
CONF_PARAM_DEVICE_CLASS = "device_class"
CONF_PARAM_STATE_CLASS = "state_class"
CONF_PARAM_ICON = "icon"

# Error messages
ERROR_CANNOT_CONNECT = "cannot_connect"
ERROR_INVALID_DEVICE = "invalid_device"
ERROR_NO_DEVICES_FOUND = "no_devices_found"
ERROR_DEVICE_TIMEOUT = "device_timeout"

# Step IDs for config flow
STEP_USER = "user"
STEP_DISCOVERY = "discovery"
STEP_DEVICE_SELECT = "device_select"
STEP_DEVICE_CONFIG = "device_config"
STEP_PARAMETER_CONFIG = "parameter_config"
