"""Config flow for Generic Modbus integration."""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, Optional

import voluptuous as vol
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult

from homeassistant import config_entries
# Import common configuration definitions
from .config_definitions import (
    SchemaBuilder,
    ConfigUtils,
    ConnectionDefaults,
    DiscoveryDefaults,
)
from .const import *
# Import our generic modbus modules (now local to the integration)
from .device.device_discovery import ModbusDeviceDiscovery

_LOGGER = logging.getLogger(__name__)


class GenericModbusOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for Generic Modbus integration."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry
        self.coordinator = None
        self.discovered_devices_for_reconfig = []
        self.new_device_info = {}

    async def async_step_init(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        """Manage the options."""
        _LOGGER.debug("Initializing generic modbus options flow")

        # Get the coordinator to access current parameters
        if self.hass.data.get(DOMAIN) and self.config_entry.entry_id in self.hass.data[DOMAIN]:
            self.coordinator = self.hass.data[DOMAIN][self.config_entry.entry_id]

        if user_input is not None:
            if user_input.get("configure_device"):
                return await self.async_step_device_reconfiguration()
            elif user_input.get("configure_parameters"):
                return await self.async_step_parameter_config()

        # Show main options menu
        data_schema = vol.Schema({
            vol.Optional("configure_device", default=False): bool,
            vol.Optional("configure_parameters", default=False): bool,
        })

        return self.async_show_form(
            step_id="init",
            data_schema=data_schema,
            description_placeholders={
                "device_name": self.config_entry.data.get("device_name", "Unknown Device"),
                "current_path": self.config_entry.data.get(CONF_DEVICE_PATH, "Unknown"),
            }
        )

    async def async_step_parameter_config(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        """Configure parameter scaling and offsets."""
        _LOGGER.debug("Configuring generic modbus options")

        errors = {}

        if user_input is not None:
            # Update parameter configurations
            updated_config = dict(self.config_entry.data)
            
            # Update parameters with new scaling/offset values
            if CONF_PARAMETERS in updated_config:
                for param_name, param_config in updated_config[CONF_PARAMETERS].items():
                    if f"scale_{param_name}" in user_input:
                        param_config["scale"] = user_input[f"scale_{param_name}"]
                    if f"offset_{param_name}" in user_input:
                        param_config["offset"] = user_input[f"offset_{param_name}"]
                    if f"enabled_{param_name}" in user_input:
                        param_config["enabled"] = user_input[f"enabled_{param_name}"]

            # Update the config entry
            self.hass.config_entries.async_update_entry(
                self.config_entry, data=updated_config
            )

            # Reload the integration to apply changes
            await self.hass.config_entries.async_reload(self.config_entry.entry_id)

            return self.async_create_entry(title="", data={})

        # Build form schema for parameter configuration
        schema_dict = {}
        
        if self.coordinator and hasattr(self.coordinator, 'get_all_parameters'):
            parameters = self.coordinator.get_all_parameters()
            
            for param_name, param_info in list(parameters.items())[:10]:  # Limit to first 10 for UI
                # Get current values from config
                current_config = self.config_entry.data.get(CONF_PARAMETERS, {}).get(param_name, {})
                current_scale = current_config.get("scale", 1.0)
                current_offset = current_config.get("offset", 0.0)
                current_enabled = current_config.get("enabled", True)
                
                # Add fields for this parameter
                schema_dict[vol.Optional(f"scale_{param_name}", default=current_scale)] = vol.All(
                    vol.Coerce(float), vol.Range(min=0.001, max=1000.0)
                )
                schema_dict[vol.Optional(f"offset_{param_name}", default=current_offset)] = vol.All(
                    vol.Coerce(float), vol.Range(min=-1000.0, max=1000.0)
                )
                schema_dict[vol.Optional(f"enabled_{param_name}", default=current_enabled)] = bool

        if not schema_dict:
            # No parameters to configure
            return self.async_show_form(
                step_id="parameter_config",
                data_schema=vol.Schema({}),
                description_placeholders={
                    "message": "No parameters available for configuration."
                }
            )

        data_schema = vol.Schema(schema_dict)

        return self.async_show_form(
            step_id="parameter_config",
            data_schema=data_schema,
            description_placeholders={
                "message": "Configure scaling and offset values for your Modbus parameters. Changes will be applied after saving."
            }
        )

    async def async_step_device_reconfiguration(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        """Handle device reconfiguration."""
        errors = {}

        if user_input is not None:
            if user_input.get("discover_devices"):
                # Discover available devices
                return await self.async_step_device_discovery()
            elif user_input.get("manual_path") and user_input.get("device_path"):
                # Manual device path entry
                new_device_path = user_input["device_path"]
                new_slave_id = user_input.get("slave_id")
                
                # Validate the new device
                from .device.device_configuration_manager import DeviceConfigurationManager
                config_manager = DeviceConfigurationManager(self.hass)
                
                validation = await config_manager.validate_device_change(
                    self.config_entry.entry_id, new_device_path, new_slave_id
                )
                
                if validation["valid"]:
                    # Store validation info for confirmation
                    self.new_device_info = {
                        "device_path": new_device_path,
                        "slave_id": new_slave_id,
                        "validation": validation
                    }
                    return await self.async_step_device_confirmation()
                else:
                    errors["base"] = "device_validation_failed"
                    errors["device_path"] = "; ".join(validation["errors"])

        # Get current device info
        current_identification = self.config_entry.data.get("device_identification", {})
        current_description = "Unknown Device"
        current_stability = "Unknown"
        
        if current_identification:
            try:
                from .device.device_identifiers import DeviceIdentifiers
                identifiers = DeviceIdentifiers.from_dict(current_identification)
                current_description = identifiers.get_user_friendly_description()
                current_stability = identifiers.get_stability_indicator() + " " + identifiers.stability_description
            except Exception as e:
                _LOGGER.debug(f"Error parsing current device identification: {e}")

        data_schema = vol.Schema({
            vol.Optional("discover_devices", default=False): bool,
            vol.Optional("manual_path", default=False): bool,
            vol.Optional("device_path"): str,
            vol.Optional("slave_id"): vol.All(vol.Coerce(int), vol.Range(min=1, max=247)),
        })

        return self.async_show_form(
            step_id="device_reconfiguration",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "current_device": current_description,
                "current_stability": current_stability,
                "current_path": self.config_entry.data.get(CONF_DEVICE_PATH, "Unknown"),
            }
        )

    async def async_step_device_discovery(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        """Discover available devices for reconfiguration."""
        if user_input is not None:
            if "selected_device" in user_input:
                device_index = user_input["selected_device"]
                if 0 <= device_index < len(self.discovered_devices_for_reconfig):
                    selected_device = self.discovered_devices_for_reconfig[device_index]
                    
                    # Store selected device info
                    self.new_device_info = {
                        "device_path": selected_device["device_path"],
                        "slave_id": selected_device["modbus_info"]["primary_slave_id"],
                        "device_info": selected_device
                    }
                    return await self.async_step_device_confirmation()
            elif user_input.get("manual_config"):
                return await self.async_step_device_reconfiguration()

        # Discover devices
        try:
            from .device.stable_device_discovery import StableDeviceDiscovery
            from .config.config_utils import ConfigUtils
            
            # Use current connection parameters
            connection_params = ConfigUtils.validate_connection_config(self.config_entry.data)
            stable_discovery = StableDeviceDiscovery(**connection_params)
            
            # Discover all devices with stability analysis
            all_devices = await stable_discovery.discover_all_devices_with_stability()
            
            # Filter for Modbus devices and find likely matches
            modbus_devices = [device for device in all_devices if device['is_modbus_device']]
            
            # Find likely matches with current device
            from .device.device_locator import DeviceLocator
            locator = DeviceLocator(**connection_params)
            
            current_identification = self.config_entry.data.get("device_identification", {})
            if current_identification:
                likely_matches = locator.find_likely_matches(current_identification)
                
                # Add match confidence to device info
                for device in modbus_devices:
                    device["match_confidence"] = 0.0
                    device["match_reasons"] = []
                    
                    for match in likely_matches:
                        if match.device_path == device["device_path"]:
                            device["match_confidence"] = match.confidence
                            device["match_reasons"] = match.match_reasons
                            break
                
                # Sort by match confidence, then stability
                modbus_devices.sort(key=lambda x: (x["match_confidence"], x["identifiers"].stability_level.value), reverse=True)
            
            self.discovered_devices_for_reconfig = modbus_devices
            
            if not modbus_devices:
                return self.async_show_form(
                    step_id="device_discovery",
                    data_schema=vol.Schema({
                        vol.Required("manual_config", default=True): bool,
                    }),
                    description_placeholders={
                        "message": "No Modbus devices found. You can return to manual configuration."
                    }
                )
            
            # Build device options with match indicators
            device_options = {}
            for i, device in enumerate(modbus_devices):
                stability_indicator = device["stability_indicator"]
                description = device["user_description"]
                slave_ids = device["modbus_info"]["responsive_slave_ids"]
                slave_text = f"Slave {slave_ids[0]}" if len(slave_ids) == 1 else f"Slaves {', '.join(map(str, slave_ids))}"
                
                # Add match indicator
                match_indicator = ""
                if device["match_confidence"] >= 0.9:
                    match_indicator = "🎯 "  # Exact match
                elif device["match_confidence"] >= 0.7:
                    match_indicator = "✅ "  # Likely match
                elif device["match_confidence"] >= 0.5:
                    match_indicator = "❓ "  # Possible match
                
                option_text = f"{match_indicator}{stability_indicator} {description} ({slave_text})"
                device_options[i] = option_text

            data_schema = vol.Schema({
                vol.Required("selected_device"): vol.In(device_options),
                vol.Optional("manual_config", default=False): bool,
            })

            return self.async_show_form(
                step_id="device_discovery",
                data_schema=data_schema,
                description_placeholders={
                    "device_count": str(len(modbus_devices)),
                    "message": f"Found {len(modbus_devices)} Modbus devices. Devices with match indicators (🎯✅❓) are likely the same as your current device."
                }
            )

        except Exception as e:
            _LOGGER.error(f"Error during device discovery for reconfiguration: {e}")
            return self.async_show_form(
                step_id="device_discovery",
                data_schema=vol.Schema({
                    vol.Required("manual_config", default=True): bool,
                }),
                errors={"base": "discovery_failed"},
                description_placeholders={
                    "message": "Device discovery failed. You can return to manual configuration."
                }
            )

    async def async_step_device_confirmation(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        """Confirm device change before applying."""
        if user_input is not None:
            if user_input.get("confirm_change"):
                # Apply the device change
                from .device.device_configuration_manager import DeviceConfigurationManager
                config_manager = DeviceConfigurationManager(self.hass)
                
                success = await config_manager.update_device_selection(
                    self.config_entry.entry_id,
                    self.new_device_info["device_path"],
                    self.new_device_info.get("slave_id")
                )
                
                if success:
                    return self.async_create_entry(title="", data={})
                else:
                    return self.async_show_form(
                        step_id="device_confirmation",
                        data_schema=vol.Schema({
                            vol.Required("confirm_change", default=False): bool,
                        }),
                        errors={"base": "update_failed"},
                        description_placeholders=self._get_confirmation_placeholders()
                    )
            else:
                # User cancelled, go back to device reconfiguration
                return await self.async_step_device_reconfiguration()

        data_schema = vol.Schema({
            vol.Required("confirm_change", default=False): bool,
        })

        return self.async_show_form(
            step_id="device_confirmation",
            data_schema=data_schema,
            description_placeholders=self._get_confirmation_placeholders()
        )

    def _get_confirmation_placeholders(self) -> Dict[str, str]:
        """Get placeholders for device confirmation step."""
        # Current device info
        current_identification = self.config_entry.data.get("device_identification", {})
        current_description = "Unknown Device"
        if current_identification:
            try:
                from .device.device_identifiers import DeviceIdentifiers
                identifiers = DeviceIdentifiers.from_dict(current_identification)
                current_description = identifiers.get_user_friendly_description()
            except Exception:
                pass

        # New device info
        new_description = "Unknown Device"
        new_stability = "Unknown"
        warnings = ""
        
        if hasattr(self, 'new_device_info'):
            if "device_info" in self.new_device_info:
                # From discovery
                device_info = self.new_device_info["device_info"]
                new_description = device_info["user_description"]
                new_stability = device_info["stability_description"]
                
                if device_info.get("match_reasons"):
                    warnings = f"Match reasons: {', '.join(device_info['match_reasons'])}"
                    
            elif "validation" in self.new_device_info:
                # From manual entry
                validation = self.new_device_info["validation"]
                if validation.get("device_info"):
                    new_description = validation["device_info"]["description"]
                    new_stability = validation["device_info"]["stability"]
                
                if validation.get("warnings"):
                    warnings = "\\n".join([f"⚠️ {w}" for w in validation["warnings"]])

        return {
            "current_device": current_description,
            "new_device": new_description,
            "new_stability": new_stability,
            "new_path": self.new_device_info.get("device_path", "Unknown"),
            "new_slave_id": str(self.new_device_info.get("slave_id", "Unknown")),
            "warnings": warnings,
        }


class GenericModbusConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Generic Modbus."""

    VERSION = 1

    @staticmethod
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> GenericModbusOptionsFlow:
        """Get the options flow for this handler."""
        return GenericModbusOptionsFlow(config_entry)

    def __init__(self):
        """Initialize the config flow."""
        self.discovered_devices = []
        self.discovered_devices_with_stability = []
        self.modbus_devices = []
        self.selected_device = None
        self.selected_device_info = None
        self.device_config = {}
        self.final_config = {}
        self.final_title = ""

    async def async_step_user(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        """Handle the initial step."""
        errors = {}

        _LOGGER.debug("async_step_user")
        if user_input is not None:
            # Store the connection parameters
            self.device_config.update(user_input)
            
            if user_input.get(CONF_DISCOVERY_ENABLED, True):
                return await self.async_step_discovery()
            else:
                # Skip discovery, go directly to manual configuration
                return await self.async_step_device_config()

        # Use common schema builder for consistent UI
        data_schema = SchemaBuilder.connection_schema(
            device_path_default=ConnectionDefaults.DEVICE_PATH,
            include_discovery=True,
            slave_id_range_default="1-10"
        )

        return self.async_show_form(
            step_id=STEP_USER,
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                CONF_DEVICE_PATH: self.device_config.get(CONF_DEVICE_PATH, ConnectionDefaults.DEVICE_PATH)
            }
        )

    async def async_step_discovery(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        """Handle device discovery."""
        _LOGGER.debug(f"async_step_discovery user_input={user_input}")
        if user_input is not None:
            if user_input.get("manual_config"):
                # User chose manual configuration
                return await self.async_step_device_config()

        # Perform device discovery with stability analysis
        try:
            _LOGGER.error("🔍 STARTING STABLE DEVICE DISCOVERY - NEW IMPLEMENTATION")
            
            # Use the new stable discovery service
            from .device.stable_device_discovery import StableDeviceDiscovery
            
            # Create discovery service with connection parameters
            connection_params = ConfigUtils.validate_connection_config(self.device_config)
            _LOGGER.error(f"🔧 Connection params: {connection_params}")
            
            stable_discovery = StableDeviceDiscovery(**connection_params)
            
            # Discover devices with stability analysis
            self.discovered_devices_with_stability = await stable_discovery.discover_all_devices_with_stability()
            
            # Filter for Modbus devices only
            self.modbus_devices = [
                device for device in self.discovered_devices_with_stability 
                if device['is_modbus_device']
            ]
            
            _LOGGER.error(f"🎯 STABLE DISCOVERY RESULTS: Found {len(self.modbus_devices)} Modbus devices out of {len(self.discovered_devices_with_stability)} total devices")
            
            for i, device in enumerate(self.modbus_devices):
                _LOGGER.error(f"📱 Device {i}: {device['stability_indicator']} {device['user_description']}")
            
            if not self.modbus_devices:
                # No Modbus devices found - show all devices with explanation
                _LOGGER.error("❌ No Modbus devices found, showing manual config option")
                return self.async_show_form(
                    step_id="discovery",
                    data_schema=vol.Schema({
                        vol.Required("manual_config", default=True): bool,
                    }),
                    errors={},
                    description_placeholders={
                        "message": f"No Modbus devices found among {len(self.discovered_devices_with_stability)} serial devices. You can proceed with manual configuration."
                    }
                )

            # Show discovered Modbus devices with stability indicators
            _LOGGER.error("✅ Proceeding to device selection with stability indicators")
            return await self.async_step_device_selection()

        except Exception as err:
            _LOGGER.error("Discovery failed: %s", err)
            return self.async_show_form(
                step_id="discovery",
                data_schema=vol.Schema({
                    vol.Required("manual_config", default=True): bool,
                }),
                errors={"base": ERROR_CANNOT_CONNECT},
                description_placeholders={
                    "message": "Device discovery failed. Please proceed with manual configuration."
                }
            )

    async def async_step_device_config(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        """Configure the selected or manual device."""

        _LOGGER.debug(f"async_step_device_config user_input={user_input}")
        errors = {}

        if user_input is not None:
            # Check for existing entries with same device path and slave ID
            device_path = self.device_config[CONF_DEVICE_PATH]
            slave_id = user_input[CONF_SLAVE_ID]
            _LOGGER.debug(f"async_step_device_config device_path={device_path} slave_id={slave_id}")
            
            for entry in self._async_current_entries():
                if (entry.data.get(CONF_DEVICE_PATH) == device_path and 
                    entry.data.get(CONF_SLAVE_ID) == slave_id):
                    return self.async_abort(reason="already_configured")
            
            # Test the connection
            test_config = {**self.device_config, **user_input}
            
            try:
                await self._async_test_connection(test_config)
                
                # Create the config entry
                title = user_input.get(CONF_DEVICE_NAME, "Modbus Device")
                
                # If we have a discovered device, include its parameters
                if self.selected_device:
                    # Convert discovered device to parameter configuration
                    parameters = {}
                    for addr, reg_info in self.selected_device.register_map.items():
                        param_name = reg_info.get('name', f'register_{addr:04X}')
                        parameters[param_name] = {
                            "address": addr,
                            "function_code": reg_info['function_code'],
                            "name": reg_info.get('name', param_name),
                            "description": reg_info.get('description', ''),
                            "unit": reg_info.get('unit', ''),
                            "scale": reg_info.get('scale', 1.0),
                            "offset": reg_info.get('offset', 0.0),
                            "device_class": reg_info.get('device_class', ''),
                            "state_class": reg_info.get('state_class', ''),
                            "icon": reg_info.get('icon', ''),
                            "enabled": True,
                        }
                    test_config[CONF_PARAMETERS] = parameters
                    test_config[CONF_DEVICE_PROFILE] = self.selected_device.device_profile_key

                # Store config for summary step
                self.final_config = test_config
                self.final_title = title
                
                # Add comprehensive device identification if we have selected device info
                if hasattr(self, 'selected_device_info'):
                    device_identifiers = self.selected_device_info['identifiers']
                    
                    # Create Modbus signature for validation
                    from .device.stable_device_discovery import StableDeviceDiscovery
                    stable_discovery = StableDeviceDiscovery(**ConfigUtils.validate_connection_config(test_config))
                    modbus_signature = await stable_discovery.create_modbus_signature(
                        device_identifiers.current_tty_path,
                        test_config[CONF_SLAVE_ID],
                        self.selected_device.device_profile_key if hasattr(self.selected_device, 'device_profile_key') else None
                    )
                    
                    if modbus_signature:
                        device_identifiers.modbus_signature = modbus_signature.to_dict()
                    
                    # Update last validated timestamp
                    device_identifiers.last_validated_at = datetime.now().isoformat()
                    
                    # Store comprehensive device identification
                    self.final_config["device_identification"] = device_identifiers.to_dict()
                    
                    _LOGGER.debug(f"Stored comprehensive device identification: {device_identifiers.get_user_friendly_description()}")
                
                # Show summary before creating entry
                return await self.async_step_summary()

            except Exception as err:
                _LOGGER.error("Connection test failed: %s", err)
                errors["base"] = ERROR_CANNOT_CONNECT

        # Prepare the form schema using common schema builder
        if self.selected_device:
            # Pre-fill with discovered device info
            default_name = self.selected_device.device_name
            default_slave_id = self.selected_device.slave_id
        else:
            default_name = "Modbus RTL Device"
            default_slave_id = 1

        data_schema = SchemaBuilder.device_schema(
            device_name_default=default_name,
            slave_id_default=default_slave_id,
            update_interval_default=DiscoveryDefaults.UPDATE_INTERVAL
        )

        return self.async_show_form(
            step_id=STEP_DEVICE_CONFIG,
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "device_name": default_name,
                "slave_id": default_slave_id,
            }
        )

    async def async_step_summary(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        """Show summary of configuration before creating entry."""
        _LOGGER.debug(f"async_step_summary user_input={user_input}")

        if user_input is not None:
            # User confirmed, create the entry
            return self.async_create_entry(title=self.final_title, data=self.final_config)

        # Build summary information
        device_path = self.final_config.get(CONF_DEVICE_PATH, "Unknown")
        slave_id = self.final_config.get(CONF_SLAVE_ID, "Unknown")
        device_name = self.final_config.get(CONF_DEVICE_NAME, "Modbus Device")
        
        # Count parameters
        parameters = self.final_config.get(CONF_PARAMETERS, {})
        param_count = len(parameters)
        
        # Get device profile info
        device_profile = self.final_config.get(CONF_DEVICE_PROFILE, "Generic")
        
        # Get device identification info if available
        device_identification = self.final_config.get("device_identification", {})
        stability_info = ""
        if device_identification:
            from .device.device_identifiers import DeviceIdentifiers
            try:
                identifiers = DeviceIdentifiers.from_dict(device_identification)
                stability_indicator = identifiers.get_stability_indicator()
                stability_desc = identifiers.stability_description
                stability_info = f"{stability_indicator} {stability_desc}"
            except Exception as e:
                _LOGGER.debug(f"Error parsing device identification for summary: {e}")
        
        summary_info = {
            "device_name": device_name,
            "device_path": device_path,
            "slave_id": str(slave_id),
            "device_profile": device_profile,
            "parameter_count": str(param_count),
            "stability_info": stability_info,
        }

        return self.async_show_form(
            step_id="summary",
            data_schema=vol.Schema({
                vol.Required("confirm", default=True): bool,
            }),
            description_placeholders=summary_info
        )

    def async_show_progress_update(self, progress: int, status: str) -> None:
        """Update progress dialog with current status."""
        # This method is called during discovery to update the progress dialog
        # Home Assistant will handle the UI updates automatically
        _LOGGER.debug(f"Progress update: {progress}% - {status}")
        
        # Store the current progress for potential use
        if not hasattr(self, '_current_progress'):
            self._current_progress = {}
        
        self._current_progress.update({
            'progress': progress,
            'status': status
        })

    async def async_step_device_selection(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        """Show device selection with stability indicators."""
        if user_input is not None:
            if "selected_device" in user_input:
                device_index = user_input["selected_device"]
                if 0 <= device_index < len(self.modbus_devices):
                    selected_device_info = self.modbus_devices[device_index]
                    
                    # Store the selected device information
                    self.selected_device_info = selected_device_info
                    
                    # Create a legacy DiscoveredDevice for compatibility
                    from .device.device_discovery import DiscoveredDevice
                    legacy_device = DiscoveredDevice(
                        slave_id=selected_device_info['modbus_info']['primary_slave_id'],
                        device_path=selected_device_info['device_path']
                    )
                    legacy_device.device_name = selected_device_info['user_description']
                    legacy_device.register_map = {}  # Will be populated later
                    
                    self.selected_device = legacy_device
                    return await self.async_step_device_config()
                    
            elif user_input.get("manual_config"):
                return await self.async_step_device_config()

        # Build device selection options with stability indicators
        device_options = {}
        stability_descriptions = []
        
        for i, device_info in enumerate(self.modbus_devices):
            # Create option text with stability indicator
            stability_indicator = device_info['stability_indicator']
            description = device_info['user_description']
            slave_ids = device_info['modbus_info']['responsive_slave_ids']
            slave_text = f"Slave {slave_ids[0]}" if len(slave_ids) == 1 else f"Slaves {', '.join(map(str, slave_ids))}"
            
            option_text = f"{stability_indicator} {description} ({slave_text})"
            device_options[i] = option_text
            
            # Add stability description for the help text
            stability_desc = device_info['stability_description']
            stability_descriptions.append(f"{stability_indicator} {stability_desc}")

        # Create help message about stability levels
        stability_help = "\\n".join(set(stability_descriptions))  # Remove duplicates
        
        data_schema = vol.Schema({
            vol.Required("selected_device"): vol.In(device_options),
            vol.Optional("manual_config", default=False): bool,
        })

        return self.async_show_form(
            step_id="device_selection",
            data_schema=data_schema,
            description_placeholders={
                "device_count": str(len(self.modbus_devices)),
                "stability_help": stability_help,
                "message": f"Found {len(self.modbus_devices)} Modbus device(s). Choose a device with higher stability for better reliability."
            }
        )

    async def async_show_progress_discovery_progress(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        """Handle the progress action for discovery."""
        try:
            # Perform discovery with stability analysis and progress updates
            from .device.stable_device_discovery import StableDeviceDiscovery
            
            # Create discovery service with connection parameters
            connection_params = ConfigUtils.validate_connection_config(self.device_config)
            stable_discovery = StableDeviceDiscovery(**connection_params)
            
            # Discover devices with stability analysis
            self.discovered_devices_with_stability = await stable_discovery.discover_all_devices_with_stability()
            
            # Filter for Modbus devices only
            self.modbus_devices = [
                device for device in self.discovered_devices_with_stability 
                if device['is_modbus_device']
            ]
            
            # For backward compatibility, also populate the old discovered_devices list
            self.discovered_devices = []
            for device_info in self.modbus_devices:
                # Create legacy DiscoveredDevice for compatibility
                from .device.device_discovery import DiscoveredDevice
                legacy_device = DiscoveredDevice(
                    slave_id=device_info['modbus_info']['primary_slave_id'],
                    device_path=device_info['device_path']
                )
                legacy_device.device_name = device_info['user_description']
                legacy_device.register_map = {}  # Will be populated later if needed
                self.discovered_devices.append(legacy_device)
            
            # Discovery completed successfully
            if not self.modbus_devices:
                return self.async_show_progress_done(next_step_id="discovery_no_devices")
            else:
                return self.async_show_progress_done(next_step_id="device_selection")
                
        except Exception as err:
            _LOGGER.error("Discovery failed: %s", err)
            return self.async_show_progress_done(next_step_id="discovery_failed")

    async def async_step_discovery_results(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        """Handle discovery results after progress completion."""
        if user_input is not None:
            if "selected_device" in user_input:
                device_index = user_input["selected_device"]
                if 0 <= device_index < len(self.discovered_devices):
                    self.selected_device = self.discovered_devices[device_index]
                    return await self.async_step_device_config()
            elif user_input.get("manual_config"):
                return await self.async_step_device_config()

        # Show discovered devices
        device_options = {}
        for i, device in enumerate(self.discovered_devices):
            device_options[i] = f"{device.device_name} (Slave ID: {device.slave_id})"

        data_schema = vol.Schema({
            vol.Required("selected_device"): vol.In(device_options),
            vol.Optional("manual_config", default=False): bool,
        })

        return self.async_show_form(
            step_id="discovery_results",
            data_schema=data_schema,
            description_placeholders={
                "message": f"Found {len(self.discovered_devices)} Modbus device(s). Select a device to configure or choose manual setup."
            }
        )

    async def async_step_discovery_no_devices(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        """Handle case when no devices are found after progress."""
        if user_input is not None and user_input.get("manual_config"):
            return await self.async_step_device_config()

        return self.async_show_form(
            step_id="discovery_no_devices",
            data_schema=vol.Schema({
                vol.Required("manual_config", default=True): bool,
            }),
            description_placeholders={
                "message": "No Modbus devices were found during discovery. Please proceed with manual configuration."
            }
        )

    async def async_step_discovery_failed(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        """Handle discovery failure after progress."""
        if user_input is not None and user_input.get("manual_config"):
            return await self.async_step_device_config()

        return self.async_show_form(
            step_id="discovery_failed",
            data_schema=vol.Schema({
                vol.Required("manual_config", default=True): bool,
            }),
            errors={"base": ERROR_CANNOT_CONNECT},
            description_placeholders={
                "message": "Device discovery failed. Please proceed with manual configuration."
            }
        )

    async def _async_discover_devices_with_progress(self):
        """Discover devices with progress updates."""
        device_path = self.device_config[CONF_DEVICE_PATH]
        
        # Use common configuration utilities
        connection_params = ConfigUtils.validate_connection_config(self.device_config)
        
        # Parse slave ID range
        slave_id_range_str = self.device_config.get(CONF_SLAVE_ID_RANGE, "1-10")
        start_id, end_id = ConfigUtils.parse_slave_id_range(slave_id_range_str)
        slave_id_range = range(start_id, end_id + 1)
        
        discovery = ModbusDeviceDiscovery(**connection_params)
        
        # Calculate total steps for progress
        total_slaves = len(slave_id_range)
        current_step = 0
        
        def update_progress(message: str, step_increment: int = 1):
            nonlocal current_step
            current_step += step_increment
            progress = min(int((current_step / (total_slaves + 2)) * 100), 95)  # +2 for setup and finalization
            _LOGGER.debug(f"Progress: {progress} current_step={current_step} total_slaves={total_slaves}: {message}")
            self.async_show_progress_update(
                progress=progress,
                status=message
            )
        
        def run_discovery_with_progress():
            discovered_devices = []
            
            try:
                update_progress("Initializing Modbus connection...")
                
                # Step 1: Find responsive slaves with progress
                responsive_slaves = []
                for slave_id in slave_id_range:
                    update_progress(f"Testing slave ID {slave_id}...")
                    
                    # Test connectivity using discovery's scan method
                    if discovery.client.test_slave_connectivity(slave_id):
                        responsive_slaves.append(slave_id)
                        _LOGGER.info(f"Found responsive device at slave ID {slave_id}")
                
                if not responsive_slaves:
                    update_progress("No responsive devices found", 0)
                    return []
                
                # Step 2: Process each responsive slave
                for i, slave_id in enumerate(responsive_slaves):
                    update_progress(f"Identifying device at slave {slave_id}... ({i+1}/{len(responsive_slaves)})")
                    
                    # Create discovered device
                    from .device.device_discovery import DiscoveredDevice
                    device = DiscoveredDevice(slave_id=slave_id, device_path=device_path)
                    
                    # Try to identify the device
                    device_profile_key = discovery.identify_device(slave_id)
                    if device_profile_key:
                        from .device.device_profiles import get_device_profile
                        device_info = get_device_profile(device_profile_key)
                        if device_info:
                            device.device_name = device_info["name"]
                            device.manufacturer = device_info["manufacturer"]
                            device.model = device_info.get("model", "Unknown")
                            device.device_profile_key = device_profile_key
                    
                    update_progress(f"Discovering registers for {device.device_name}...")
                    
                    # Discover registers
                    device.register_map = discovery.discover_device_registers(
                        slave_id, device_profile_key
                    )
                    
                    discovered_devices.append(device)
                    _LOGGER.info(f"Completed discovery for {device.device_name} (slave {slave_id}) - {len(device.register_map)} registers")
                
                update_progress("Discovery complete!")
                return discovered_devices
                
            except Exception as e:
                _LOGGER.error(f"Discovery error: {e}")
                update_progress(f"Discovery failed: {str(e)}", 0)
                raise
        
        # Run discovery in executor with progress updates
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, run_discovery_with_progress)

    async def _async_test_connection(self, config):
        """Test connection to the device."""
        device_path = config[CONF_DEVICE_PATH]
        slave_id = config[CONF_SLAVE_ID]
        
        # Log test connection parameters
        _LOGGER.debug(
            "_async_test_connection starting with config: "
            f"device_path='{device_path}', "
            f"slave_id={slave_id}"
        )
        
        # Use common configuration utilities
        connection_params = ConfigUtils.validate_connection_config(config)
        _LOGGER.debug(f"Validated connection params: {connection_params}")
        
        discovery = ModbusDeviceDiscovery(**connection_params)
        
        def test_connection():
            _LOGGER.debug(f"Opening connection to test slave {slave_id}")
            with discovery.client:
                # Try to read a common register to test connectivity
                result = discovery.client.test_connection(slave_id)
                _LOGGER.debug(f"Connectivity test result for slave {slave_id}: {result}")
                return result
        
        # Run test in executor
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, test_connection)
        
        if not result:
            _LOGGER.error(f"Device at slave ID {slave_id} not responding")
            raise Exception("Device not responding")
        
        _LOGGER.debug(f"Connection test successful for slave {slave_id}")
        return True
