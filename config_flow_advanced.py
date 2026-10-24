"""Advanced configuration flow steps for Generic Modbus integration."""

from typing import Any, Dict, Optional

import voluptuous as vol
from homeassistant.data_entry_flow import FlowResult

from homeassistant.custom_components.generic_modbus.config_definitions import (
    SchemaBuilder,
    DiscoveryValidators,
    ConfigUtils,
)
from homeassistant.custom_components.generic_modbus.device_config import config_manager


class AdvancedConfigMixin:
    """Mixin for advanced configuration steps."""
    
    async def async_step_advanced_config(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        """Configure advanced device settings."""
        errors = {}
        
        if user_input is not None:
            # Store advanced configuration
            device_id = self.device_config.get("device_name", "default")
            
            # Update binary sensor configuration
            if "binary_keywords" in user_input:
                keywords = ConfigUtils.parse_binary_keywords(user_input["binary_keywords"])
                config_manager.update_binary_sensor_config(
                    device_id, 
                    binary_keywords=keywords
                )
            
            # Update discovery configuration
            discovery_updates = {}
            if "scan_batch_size" in user_input:
                discovery_updates["batch_size"] = user_input["scan_batch_size"]
            if "scan_delay" in user_input:
                discovery_updates["scan_delay"] = user_input["scan_delay"]
            if "slave_range_start" in user_input and "slave_range_end" in user_input:
                discovery_updates["default_slave_range"] = (
                    user_input["slave_range_start"], 
                    user_input["slave_range_end"]
                )
            
            if discovery_updates:
                config_manager.update_discovery_config(device_id, **discovery_updates)
            
            # Continue to device config or finish
            return await self.async_step_device_config()
        
        # Get current configuration
        device_id = self.device_config.get("device_name", "default")
        device_config = config_manager.get_config(device_id)
        
        # Use centralized schema builder for advanced configuration
        data_schema = SchemaBuilder.advanced_schema(
            binary_keywords_default=device_config.binary_sensor.binary_keywords,
            batch_size_default=device_config.discovery.batch_size,
            scan_delay_default=device_config.discovery.scan_delay,
            slave_range_start_default=device_config.discovery.default_slave_range[0],
            slave_range_end_default=device_config.discovery.default_slave_range[1]
        )
        
        return self.async_show_form(
            step_id="advanced_config",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "current_keywords": ", ".join(device_config.binary_sensor.binary_keywords[:5]) + "...",
                "current_batch_size": str(device_config.discovery.batch_size),
                "current_delay": str(device_config.discovery.scan_delay),
            }
        )
    
    async def async_step_parameter_config(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        """Configure individual parameters."""
        errors = {}
        
        if user_input is not None:
            device_id = self.device_config.get("device_name", "default")
            
            # Process parameter overrides
            for key, value in user_input.items():
                if key.startswith("binary_override_"):
                    param_name = key.replace("binary_override_", "")
                    config_manager.set_parameter_override(device_id, param_name, value)
                elif key.startswith("update_interval_"):
                    param_name = key.replace("update_interval_", "")
                    device_config = config_manager.get_config(device_id)
                    device_config.parameter_update_intervals[param_name] = value
                    config_manager.set_config(device_id, device_config)
            
            # Finish configuration
            return self.async_create_entry(
                title=self.device_config.get("device_name", "Modbus Device"), 
                data=self.device_config
            )
        
        # Get discovered parameters if available
        if not hasattr(self, 'selected_device') or not self.selected_device:
            # No parameters to configure, skip to finish
            return self.async_create_entry(
                title=self.device_config.get("device_name", "Modbus Device"), 
                data=self.device_config
            )
        
        # Create form for parameter configuration using centralized validators
        schema_dict = {}
        device_id = self.device_config.get("device_name", "default")
        device_config = config_manager.get_config(device_id)
        
        # Add binary sensor overrides for discovered parameters
        for addr, reg_info in list(self.selected_device.register_map.items())[:10]:  # Limit to first 10
            param_name = reg_info.get('name', f'register_{addr:04X}')
            
            # Binary sensor override
            current_override = device_config.binary_sensor.parameter_overrides.get(param_name)
            if current_override is None:
                # Determine default based on keywords
                from .binary_sensor import _is_binary_parameter
                current_override = _is_binary_parameter(param_name, reg_info, device_config)
            
            schema_dict[vol.Optional(
                f"binary_override_{param_name}", 
                default=current_override
            )] = bool
            
            # Update interval override - use centralized validator
            current_interval = device_config.parameter_update_intervals.get(
                param_name, device_config.default_update_interval
            )
            schema_dict[vol.Optional(
                f"update_interval_{param_name}", 
                default=current_interval
            )] = DiscoveryValidators.UPDATE_INTERVAL  # Use centralized validator instead of duplicated vol.Range
        
        if not schema_dict:
            # No parameters to configure
            return self.async_create_entry(
                title=self.device_config.get("device_name", "Modbus Device"), 
                data=self.device_config
            )
        
        data_schema = vol.Schema(schema_dict)
        
        return self.async_show_form(
            step_id="parameter_config",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "parameter_count": str(len(self.selected_device.register_map)),
                "showing_count": str(min(10, len(self.selected_device.register_map))),
            }
        )
