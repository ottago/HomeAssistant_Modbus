"""Binary sensor platform for Generic Modbus integration."""

import logging
from typing import Any, Dict, Optional

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorDeviceClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import GenericModbusCoordinator
from .device_config import config_manager

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Generic Modbus binary sensor entities."""
    coordinator: GenericModbusCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    
    # Get all parameters from the coordinator
    parameters = coordinator.get_all_parameters()
    
    # Get device configuration
    device_config = config_manager.get_config(coordinator.device_id or "default")
    
    # Create binary sensor entities for status/alarm parameters
    entities = []
    for param_name, param_config in parameters.items():
        if param_config.get("enabled", True) and _is_binary_parameter(param_name, param_config, device_config):
            entities.append(
                GenericModbusBinarySensor(
                    coordinator=coordinator,
                    parameter_name=param_name,
                    parameter_config=param_config,
                )
            )
    
    if entities:
        _LOGGER.info("Setting up %d binary sensor entities", len(entities))
        async_add_entities(entities)


def _is_binary_parameter(param_name: str, param_config: Dict[str, Any], device_config) -> bool:
    """Determine if a parameter should be a binary sensor using device configuration."""
    
    # Check for explicit parameter override first
    if param_name in device_config.binary_sensor.parameter_overrides:
        return device_config.binary_sensor.parameter_overrides[param_name]
    
    # Use configurable binary keywords
    binary_keywords = device_config.binary_sensor.binary_keywords
    
    param_name_lower = param_name.lower()
    description_lower = param_config.get("description", "").lower()
    
    # Check if parameter name or description contains binary keywords
    for keyword in binary_keywords:
        if keyword in param_name_lower or keyword in description_lower:
            return True
    
    return False


class GenericModbusBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Representation of a Generic Modbus binary sensor."""

    def __init__(
        self,
        coordinator: GenericModbusCoordinator,
        parameter_name: str,
        parameter_config: Dict[str, Any],
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        
        self._parameter_name = parameter_name
        self._parameter_config = parameter_config
        self._attr_unique_id = f"{coordinator.device_id}_{parameter_name}_binary"
        
        # Set entity properties
        self._attr_name = parameter_config.get("name", parameter_name.replace("_", " ").title())
        self._attr_icon = parameter_config.get("icon")
        
        # Set device class using configurable mapping
        self._attr_device_class = self._get_device_class()

        _LOGGER.debug(f"GenericModbusBinarySensor parameter_name={parameter_name} device_id={coordinator.device_id}")
        
        # Set entity category if it's a diagnostic parameter
        if any(word in parameter_name.lower() for word in ["temp", "voltage", "current"]):
            self._attr_entity_category = EntityCategory.DIAGNOSTIC

    def _get_device_class(self) -> Optional[BinarySensorDeviceClass]:
        """Get device class based on parameter type using configurable mapping."""
        param_name_lower = self._parameter_name.lower()
        
        # Get device configuration
        device_config = config_manager.get_config(self.coordinator.device_id or "default")
        device_class_keywords = device_config.binary_sensor.device_class_keywords
        
        # Check each device class mapping
        for device_class, keywords in device_class_keywords.items():
            if any(keyword in param_name_lower for keyword in keywords):
                # Map string to actual device class
                if device_class == "connectivity":
                    return BinarySensorDeviceClass.CONNECTIVITY
                elif device_class == "problem":
                    return BinarySensorDeviceClass.PROBLEM
                elif device_class == "running":
                    return BinarySensorDeviceClass.RUNNING
                elif device_class == "power":
                    return BinarySensorDeviceClass.POWER
                elif device_class == "safety":
                    return BinarySensorDeviceClass.SAFETY
        
        return None

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return self.coordinator.device_info

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.coordinator.last_update_success

    @property
    def sw_version(self) -> Optional[str]:
        """Return the software version."""
        device = self.coordinator.device_manager.get_device(self.coordinator.device_id)
        return device.firmware_version if device else "Unknown"

    @property
    def is_on(self) -> Optional[bool]:
        """Return true if the binary sensor is on."""
        if not self.coordinator.data:
            return None
            
        value = self.coordinator.data.get(self._parameter_name)
        if value is None:
            return None
        
        # Convert numeric value to boolean
        # Most Modbus devices use 0 = off/false, non-zero = on/true
        return bool(value)

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return extra state attributes."""
        attributes = {
            "parameter_name": self._parameter_name,
            "modbus_address": f"0x{self._parameter_config.get('address', 0):04X}",
            "function_code": f"0x{self._parameter_config.get('function_code', 0):02X}",
        }
        
        # Add raw value if available
        if self.coordinator.data and self._parameter_name in self.coordinator.data:
            attributes["raw_value"] = self.coordinator.data[self._parameter_name]
        
        return attributes

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass()
        _LOGGER.debug("Added binary sensor entity: %s", self.entity_id)
