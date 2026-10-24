#!/usr/bin/env python3
"""Test imports for the new stable discovery system"""

import sys
import os

# Add the path to the custom component
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'homeassistant', 'custom_components', 'generic_modbus'))

try:
    print("Testing imports...")
    
    # Test basic imports
    from device.device_identifiers import DeviceIdentifiers, StabilityLevel
    print("✅ DeviceIdentifiers imported successfully")
    
    from device.usb_utils import USBDeviceDetector
    print("✅ USBDeviceDetector imported successfully")
    
    from device.stable_device_discovery import StableDeviceDiscovery
    print("✅ StableDeviceDiscovery imported successfully")
    
    from device.device_locator import DeviceLocator
    print("✅ DeviceLocator imported successfully")
    
    from device.device_configuration_manager import DeviceConfigurationManager
    print("✅ DeviceConfigurationManager imported successfully")
    
    # Test creating objects
    identifiers = DeviceIdentifiers(current_tty_path="/dev/ttyUSB0")
    print(f"✅ DeviceIdentifiers object created: {identifiers.get_user_friendly_description()}")
    
    detector = USBDeviceDetector()
    print("✅ USBDeviceDetector object created")
    
    print("\n🎉 All imports successful!")
    
except Exception as e:
    print(f"❌ Import failed: {e}")
    import traceback
    traceback.print_exc()
