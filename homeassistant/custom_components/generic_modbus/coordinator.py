"""Data update coordinator for Generic Modbus integration."""

import logging
from datetime import timedelta
from typing import Dict, Any, Optional

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .config_definitions import DiscoveryDefaults
from .const import *
# Import our generic modbus modules (now local to the integration)
from .device.device_manager import ModbusDeviceManager

_LOGGER = logging.getLogger(__name__)

class GenericModbusCoordinator(DataUpdateCoordinator):
    """Coordinator to manage data updates from Modbus devices."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        self.entry = entry
        self.device_manager = ModbusDeviceManager()
        self.device_id: Optional[str] = None
        
        # Get update interval from config
        update_interval = entry.data.get(CONF_UPDATE_INTERVAL, DiscoveryDefaults.UPDATE_INTERVAL)
        
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=update_interval),
        )
        
        # Set up the device from config entry
        self._setup_device()

    def _setup_device(self) -> None:
        """Set up the Modbus device from config entry data."""
        config = self.entry.data
        
        # Create device configuration
        device_config = {
            CONF_BAUDRATE: config.get(CONF_BAUDRATE),
            CONF_TIMEOUT: config.get(CONF_TIMEOUT),
            CONF_PARITY: config.get(CONF_PARITY),
            CONF_STOPBITS: config.get(CONF_STOPBITS),
            CONF_BYTESIZE: config.get(CONF_BYTESIZE),
        }
        
        # Add device to manager
        self.device_id = self.device_manager.add_device_manual(
            slave_id=config[CONF_SLAVE_ID],
            device_path=config[CONF_DEVICE_PATH],
            name=config.get(CONF_DEVICE_NAME, "Modbus RTL Device"),
            connection_config=device_config
        )
        
        # Configure parameters if provided
        if CONF_PARAMETERS in config:
            self._configure_parameters(config[CONF_PARAMETERS])

    def _configure_parameters(self, parameters_config: Dict[str, Any]) -> None:
        """Configure device parameters from config."""
        if not self.device_id:
            return
            
        for param_name, param_config in parameters_config.items():
            if param_config.get("enabled", True):
                # Prepare kwargs excluding fields that are passed as explicit parameters
                kwargs = {
                    "description": param_config.get("description", ""),
                    "unit": param_config.get("unit", ""),
                    "scale": param_config.get("scale", 1.0),
                    "offset": param_config.get("offset", 0.0),
                    "device_class": param_config.get("device_class", ""),
                    "state_class": param_config.get("state_class", ""),
                    "icon": param_config.get("icon", ""),
                    "enabled": param_config.get("enabled", True),
                }
                
                # Add update_interval if present
                if "update_interval" in param_config:
                    kwargs["update_interval"] = param_config["update_interval"]
                
                # Add the parameter (address, function_code, and name are explicit parameters)
                success = self.device_manager.add_custom_parameter(
                    self.device_id,
                    param_name,  # parameter_name -> becomes 'name' field
                    address=param_config["address"],
                    function_code=param_config["function_code"],
                    **kwargs
                )
                
                if success:
                    _LOGGER.debug(f"Added parameter {param_name} to device {self.device_id}")
                else:
                    _LOGGER.warning(f"Failed to add parameter {param_name} to device {self.device_id}")

    async def _async_update_data(self) -> Dict[str, Any]:
        """Fetch data from the Modbus device."""
        if not self.device_id:
            raise UpdateFailed("Device not configured")

        try:
            # Run the blocking Modbus operations in executor
            data = await self.hass.async_add_executor_job(
                self.device_manager.read_all_parameters,
                self.device_id
            )
            
            if not data:
                raise UpdateFailed("No data received from device")
                
            _LOGGER.debug("Updated data for device %s: %s", self.device_id, data)
            return data
            
        except Exception as err:
            _LOGGER.error(f"Error communicating with device {self.device_id}: {err}")
            raise UpdateFailed(f"Error communicating with device: {err}") from err

    async def async_shutdown(self) -> None:
        """Shutdown the coordinator and clean up resources."""
        if self.device_manager:
            await self.hass.async_add_executor_job(self.device_manager.cleanup)

    @property
    def device_info(self) -> Dict[str, Any]:
        """Return device information for device registry."""
        if not self.device_id:
            return {}
            
        device = self.device_manager.get_device(self.device_id)
        if not device:
            return {}
            
        return {
            "identifiers": {(DOMAIN, self.device_id)},
            "name": device.name,
            "manufacturer": device.manufacturer,
            "model": device.model,
            "sw_version": device.firmware_version,
            "configuration_url": None,
        }

    def get_parameter_config(self, parameter_name: str) -> Optional[Dict[str, Any]]:
        """Get configuration for a specific parameter."""
        if not self.device_id:
            return None
            
        device = self.device_manager.get_device(self.device_id)
        if not device or parameter_name not in device.parameters:
            return None
            
        param = device.parameters[parameter_name]
        return {
            "name": param.name,
            "description": param.description,
            "unit": param.unit,
            "scale": param.scale,
            "offset": param.offset,
            "device_class": param.device_class,
            "state_class": param.state_class,
            "icon": param.icon,
            "enabled": param.enabled,
        }

    def get_all_parameters(self) -> Dict[str, Dict[str, Any]]:
        """Get configuration for all parameters."""
        if not self.device_id:
            return {}
            
        device = self.device_manager.get_device(self.device_id)
        if not device:
            return {}
            
        parameters = {}
        for param_name, param in device.parameters.items():
            parameters[param_name] = {
                "name": param.name,
                "description": param.description,
                "unit": param.unit,
                "scale": param.scale,
                "offset": param.offset,
                "device_class": param.device_class,
                "state_class": param.state_class,
                "icon": param.icon,
                "enabled": param.enabled,
                "address": param.address,
                "function_code": param.function_code,
            }
            
        return parameters

    def update_parameter_scaling(self, param_name: str, scale: float = None, offset: float = None, enabled: bool = None) -> bool:
        """Update parameter scaling and offset values."""
        if not self.device_id:
            return False
        
        device = self.device_manager.get_device(self.device_id)
        if not device or param_name not in device.parameters:
            return False
        
        param = device.parameters[param_name]
        
        # Update values if provided
        if scale is not None:
            param.scale = scale
        if offset is not None:
            param.offset = offset
        if enabled is not None:
            param.enabled = enabled
        
        _LOGGER.debug(f"Updated parameter {param_name}: scale={param.scale}, offset={param.offset}, enabled={param.enabled}")
        return True
