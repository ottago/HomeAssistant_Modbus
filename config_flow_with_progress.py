"""Config flow with progress feedback for Generic Modbus integration."""

import asyncio
import logging
from typing import Any, Dict, Optional

import voluptuous as vol
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.selector import selector

from homeassistant import config_entries
from homeassistant.custom_components.generic_modbus.config_definitions import ConfigUtils
from homeassistant.custom_components.generic_modbus.const import DOMAIN
from homeassistant.custom_components.generic_modbus.device.device_discovery import ModbusDeviceDiscovery

_LOGGER = logging.getLogger(__name__)

class GenericModbusConfigFlowWithProgress(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow with progress feedback."""

    VERSION = 1

    def __init__(self):
        """Initialize the config flow."""
        self.discovered_devices = []
        self.selected_device = None
        self.device_config = {}

    async def async_step_discovery(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        """Handle device discovery with progress feedback."""
        if user_input is not None:
            if "selected_device" in user_input:
                device_index = user_input["selected_device"]
                if 0 <= device_index < len(self.discovered_devices):
                    self.selected_device = self.discovered_devices[device_index]
                    return await self.async_step_device_config()
            elif user_input.get("manual_config"):
                return await self.async_step_device_config()

        # Show progress dialog and perform discovery
        return await self.async_show_progress(
            step_id="discovery",
            progress_action="discovery_progress",
        )

    async def async_show_progress_discovery(self, user_input: Dict[str, Any]) -> FlowResult:
        """Show progress during discovery."""
        # Start the discovery process with progress updates
        try:
            self.discovered_devices = await self._async_discover_devices_with_progress()
            
            if not self.discovered_devices:
                return self.async_show_progress_done(next_step_id="discovery_empty")
            
            return self.async_show_progress_done(next_step_id="discovery_results")
            
        except Exception as err:
            _LOGGER.error("Discovery failed: %s", err)
            return self.async_show_progress_done(next_step_id="discovery_failed")

    async def async_step_discovery_results(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        """Show discovery results."""
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

    async def async_step_discovery_empty(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        """Handle empty discovery results."""
        return self.async_show_form(
            step_id="discovery_empty",
            data_schema=vol.Schema({
                vol.Required("manual_config", default=True): bool,
            }),
            description_placeholders={
                "message": "No Modbus devices were found during discovery. Please proceed with manual configuration."
            }
        )

    async def async_step_discovery_failed(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        """Handle discovery failure."""
        return self.async_show_form(
            step_id="discovery_failed",
            data_schema=vol.Schema({
                vol.Required("manual_config", default=True): bool,
            }),
            errors={"base": "cannot_connect"},
            description_placeholders={
                "message": "Device discovery failed. Please proceed with manual configuration."
            }
        )

    async def _async_discover_devices_with_progress(self):
        """Discover devices with progress updates."""
        device_path = self.device_config["device_path"]
        connection_params = ConfigUtils.validate_connection_config(self.device_config)
        
        # Parse slave ID range
        slave_id_range_str = self.device_config.get("slave_id_range", "1-10")
        start_id, end_id = ConfigUtils.parse_slave_id_range(slave_id_range_str)
        slave_id_range = range(start_id, end_id + 1)
        
        discovery = ModbusDeviceDiscovery(device_path, **connection_params)
        
        # Update progress during discovery
        total_steps = len(slave_id_range) + 1  # +1 for final processing
        current_step = 0
        
        def update_progress(message: str):
            nonlocal current_step
            current_step += 1
            progress = int((current_step / total_steps) * 100)
            self.async_show_progress_update(
                progress=progress,
                status=message
            )
        
        # Custom discovery with progress updates
        discovered_devices = []
        
        def run_discovery_with_progress():
            with discovery.client:
                # Step 1: Scan for responsive slaves
                update_progress("Scanning for responsive devices...")
                responsive_slaves = []
                
                for slave_id in slave_id_range:
                    update_progress(f"Testing slave ID {slave_id}...")
                    if discovery.client.test_slave_connectivity(slave_id):
                        responsive_slaves.append(slave_id)
                
                if not responsive_slaves:
                    return []
                
                # Step 2: Process each responsive slave
                for slave_id in responsive_slaves:
                    update_progress(f"Identifying device at slave {slave_id}...")
                    
                    # Create discovered device
                    device = discovery._create_discovered_device(slave_id)
                    
                    # Try to identify the device
                    device_profile_key = discovery.identify_device(slave_id)
                    if device_profile_key:
                        device_info = discovery._get_device_profile(device_profile_key)
                        if device_info:
                            device.device_name = device_info["name"]
                            device.manufacturer = device_info["manufacturer"]
                            device.device_profile_key = device_profile_key
                    
                    update_progress(f"Discovering registers for {device.device_name}...")
                    
                    # Discover registers
                    device.register_map = discovery.discover_device_registers(
                        slave_id, device_profile_key
                    )
                    
                    discovered_devices.append(device)
                
                update_progress("Discovery complete!")
                return discovered_devices
        
        # Run discovery in executor with progress updates
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, run_discovery_with_progress)
