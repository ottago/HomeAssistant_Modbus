"""Sensor platform for Generic Modbus integration."""

import logging
from typing import Any, Dict, Optional

from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import GenericModbusCoordinator

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Generic Modbus sensor entities."""
    coordinator: GenericModbusCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    
    # Get all parameters from the coordinator
    parameters = coordinator.get_all_parameters()
    
    # Create sensor entities for each enabled parameter
    entities = []
    for param_name, param_config in parameters.items():
        if param_config.get("enabled", True):
            entities.append(
                GenericModbusSensor(
                    coordinator=coordinator,
                    parameter_name=param_name,
                    parameter_config=param_config,
                )
            )
    
    _LOGGER.info("Setting up %d sensor entities", len(entities))
    async_add_entities(entities)


class GenericModbusSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Generic Modbus sensor."""

    def __init__(
        self,
        coordinator: GenericModbusCoordinator,
        parameter_name: str,
        parameter_config: Dict[str, Any],
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        
        self._parameter_name = parameter_name
        self._parameter_config = parameter_config
        self._attr_unique_id = f"{coordinator.device_id}_{parameter_name}"
        
        # Set entity attributes from parameter configuration
        self._attr_name = parameter_config.get("name", parameter_name)
        self._attr_native_unit_of_measurement = parameter_config.get("unit")
        self._attr_icon = parameter_config.get("icon")

        _LOGGER.debug(f"GenericModbusSensor parameter_name={parameter_name} device_id={coordinator.device_id}")
        
        # Set device class if specified
        device_class_str = parameter_config.get("device_class")
        if device_class_str:
            try:
                self._attr_device_class = SensorDeviceClass(device_class_str)
            except ValueError:
                _LOGGER.warning("Invalid device class: %s", device_class_str)
        
        # Set state class if specified
        state_class_str = parameter_config.get("state_class")
        if state_class_str:
            try:
                self._attr_state_class = SensorStateClass(state_class_str)
            except ValueError:
                _LOGGER.warning("Invalid state class: %s", state_class_str)
        
        # Set entity category for diagnostic sensors
        if parameter_name.startswith("register_") or "status" in parameter_name.lower():
            self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.device_id)},
            name=self.coordinator.entry.data.get("device_name", "Modbus Device"),
            manufacturer=self._get_device_manufacturer(),
            model=self._get_device_model(),
            sw_version=self._get_device_firmware(),
        )

    def _get_device_manufacturer(self) -> str:
        """Get device manufacturer."""
        device = self.coordinator.device_manager.get_device(self.coordinator.device_id)
        return device.manufacturer if device else "Unknown"

    def _get_device_model(self) -> str:
        """Get device model."""
        device = self.coordinator.device_manager.get_device(self.coordinator.device_id)
        return device.model if device else "Unknown"

    def _get_device_firmware(self) -> str:
        """Get device firmware version."""
        device = self.coordinator.device_manager.get_device(self.coordinator.device_id)
        return device.firmware_version if device else "Unknown"

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        if not self.coordinator.data:
            return None
            
        return self.coordinator.data.get(self._parameter_name)

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional state attributes."""
        attributes = {
            "parameter_name": self._parameter_name,
            "modbus_address": f"0x{self._parameter_config.get('address', 0):04X}",
            "function_code": f"0x{self._parameter_config.get('function_code', 0):02X}",
            "scale_factor": self._parameter_config.get("scale", 1.0),
            "offset": self._parameter_config.get("offset", 0.0),
        }
        
        # Add raw value if scaling is applied
        if self.coordinator.data and self._parameter_name in self.coordinator.data:
            scale = self._parameter_config.get("scale", 1.0)
            offset = self._parameter_config.get("offset", 0.0)
            if scale != 1.0 or offset != 0.0:
                scaled_value = self.coordinator.data[self._parameter_name]
                raw_value = (scaled_value - offset) / scale
                attributes["raw_value"] = int(raw_value)
        
        return attributes

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return (
            self.coordinator.last_update_success
            and self.coordinator.data is not None
            and self._parameter_name in self.coordinator.data
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass()
        _LOGGER.debug("Added sensor entity: %s", self.entity_id)
