#!/usr/bin/env python3
"""
Device Configuration Manager
Manages device configuration updates while preserving existing settings
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from .device_identifiers import DeviceIdentifiers
from .stable_device_discovery import StableDeviceDiscovery
from ..const import CONF_DEVICE_PATH, CONF_SLAVE_ID, CONF_PARAMETERS

logger = logging.getLogger(__name__)


class DeviceConfigurationManager:
    """Manage device configuration updates"""
    
    def __init__(self, hass: HomeAssistant):
        """Initialize the configuration manager"""
        self.hass = hass
    
    async def update_device_selection(self, entry_id: str, new_device_path: str, 
                                    new_slave_id: Optional[int] = None) -> bool:
        """Update device selection without affecting other settings"""
        try:
            # Get current config entry
            entry = self.hass.config_entries.async_get_entry(entry_id)
            if not entry:
                logger.error(f"Config entry {entry_id} not found")
                return False
            
            current_config = dict(entry.data)
            logger.info(f"Updating device selection for {entry.title} to {new_device_path}")
            
            # Get connection parameters from current config
            from ..config.config_utils import ConfigUtils
            connection_params = ConfigUtils.validate_connection_config(current_config)
            
            # Analyze new device
            stable_discovery = StableDeviceDiscovery(**connection_params)
            new_identifiers = stable_discovery.get_device_identifiers(new_device_path)
            
            # Update device path and slave ID
            current_config[CONF_DEVICE_PATH] = new_device_path
            if new_slave_id is not None:
                current_config[CONF_SLAVE_ID] = new_slave_id
            
            # Create Modbus signature for the new device
            slave_id = new_slave_id or current_config.get(CONF_SLAVE_ID, 1)
            modbus_signature = await stable_discovery.create_modbus_signature(
                new_device_path, slave_id
            )
            
            if modbus_signature:
                new_identifiers.modbus_signature = modbus_signature.to_dict()
            
            # Update timestamps
            new_identifiers.configured_at = datetime.now().isoformat()
            new_identifiers.last_validated_at = datetime.now().isoformat()
            
            # Store previous device identification for reference
            previous_identification = current_config.get("device_identification", {})
            
            # Update device identification section
            current_config["device_identification"] = new_identifiers.to_dict()
            current_config["device_identification"]["previous_device"] = previous_identification
            
            # Preserve all other settings (parameters, intervals, device_name, etc.)
            # These remain completely unchanged
            
            logger.debug(f"Preserved settings: parameters={len(current_config.get(CONF_PARAMETERS, {}))}, "
                        f"device_name={current_config.get('device_name', 'Unknown')}")
            
            # Update config entry
            self.hass.config_entries.async_update_entry(entry, data=current_config)
            
            # Reload integration with new device
            await self.hass.config_entries.async_reload(entry_id)
            
            logger.info(f"Successfully updated device selection for {entry.title}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating device selection for {entry_id}: {e}")
            return False
    
    def preserve_existing_config(self, old_config: Dict[str, Any], 
                               new_identification: Dict[str, Any]) -> Dict[str, Any]:
        """Merge new device info with existing configuration"""
        # Start with old config
        updated_config = dict(old_config)
        
        # Update only device identification
        updated_config["device_identification"] = new_identification
        
        # Preserve all other settings:
        # - parameters (CONF_PARAMETERS)
        # - update_interval
        # - device_name
        # - slave_id (unless explicitly changed)
        # - device_profile
        # - Any custom settings
        
        logger.debug("Preserved all existing configuration except device identification")
        return updated_config
    
    async def validate_device_change(self, entry_id: str, new_device_path: str, 
                                   new_slave_id: Optional[int] = None) -> Dict[str, Any]:
        """Validate that a device change is possible and safe"""
        validation_result = {
            "valid": False,
            "errors": [],
            "warnings": [],
            "device_info": None
        }
        
        try:
            # Get current config entry
            entry = self.hass.config_entries.async_get_entry(entry_id)
            if not entry:
                validation_result["errors"].append("Config entry not found")
                return validation_result
            
            current_config = dict(entry.data)
            
            # Test new device connectivity
            from ..config.config_utils import ConfigUtils
            connection_params = ConfigUtils.validate_connection_config(current_config)
            connection_params[CONF_DEVICE_PATH] = new_device_path
            
            stable_discovery = StableDeviceDiscovery(**connection_params)
            
            # Test Modbus connectivity
            slave_id = new_slave_id or current_config.get(CONF_SLAVE_ID, 1)
            
            # Get device identifiers
            new_identifiers = stable_discovery.get_device_identifiers(new_device_path)
            validation_result["device_info"] = {
                "description": new_identifiers.get_user_friendly_description(),
                "stability": new_identifiers.get_stability_indicator() + " " + new_identifiers.stability_description,
                "identifiers": new_identifiers.to_dict()
            }
            
            # Test Modbus communication
            modbus_info = await stable_discovery._test_modbus_connectivity(new_device_path)
            if not modbus_info:
                validation_result["errors"].append("Device does not respond to Modbus communication")
                return validation_result
            
            # Check if requested slave ID is available
            if slave_id not in modbus_info["responsive_slave_ids"]:
                validation_result["errors"].append(f"Slave ID {slave_id} not responsive on this device")
                validation_result["warnings"].append(f"Available slave IDs: {modbus_info['responsive_slave_ids']}")
                return validation_result
            
            # Compare with previous device
            old_identification = current_config.get("device_identification", {})
            if old_identification:
                try:
                    old_identifiers = DeviceIdentifiers.from_dict(old_identification)
                    
                    # Warn if stability is decreasing
                    if (new_identifiers.stability_level.value > old_identifiers.stability_level.value):
                        validation_result["warnings"].append(
                            f"New device has lower stability ({new_identifiers.stability_description}) "
                            f"than previous device ({old_identifiers.stability_description})"
                        )
                    
                    # Warn if it's a completely different device type
                    if (old_identifiers.usb_vendor_id and new_identifiers.usb_vendor_id and
                        old_identifiers.usb_vendor_id != new_identifiers.usb_vendor_id):
                        validation_result["warnings"].append(
                            "New device is from a different manufacturer - ensure it's compatible"
                        )
                        
                except Exception as e:
                    logger.debug(f"Error comparing with old device identification: {e}")
            
            validation_result["valid"] = True
            logger.debug(f"Device change validation passed for {new_device_path}")
            
        except Exception as e:
            validation_result["errors"].append(f"Validation error: {str(e)}")
            logger.error(f"Error validating device change: {e}")
        
        return validation_result
