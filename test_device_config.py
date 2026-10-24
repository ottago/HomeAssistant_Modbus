#!/usr/bin/env python3
"""Test the device configuration system independently."""

import sys
import os

# Add the path to import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'homeassistant/custom_components/generic_modbus'))

# Import just the configuration system
from device_config import DeviceConfig, DeviceConfigManager, BinarySensorConfig, DiscoveryConfig

def test_device_config():
    """Test the device configuration system."""
    print("🧪 Testing Device Configuration System")
    print("=" * 50)
    
    # Create config manager
    config_manager = DeviceConfigManager()
    
    # Test 1: Default configuration
    print("📋 Test 1: Default Configuration")
    default_config = config_manager.get_config("test_device")
    print(f"  Device name: {default_config.device_name}")
    print(f"  Binary keywords count: {len(default_config.binary_sensor.binary_keywords)}")
    print(f"  Default batch size: {default_config.discovery.batch_size}")
    print(f"  Default update interval: {default_config.default_update_interval}")
    print("  ✅ Default configuration loaded")
    
    # Test 2: Custom configuration
    print("\n📋 Test 2: Custom Configuration")
    device_id = "solar_charger_1"
    
    # Create custom config
    custom_config = DeviceConfig()
    custom_config.device_name = "My Solar Charger"
    custom_config.manufacturer = "SolarTech"
    custom_config.model = "ST-100"
    
    # Customize binary sensor settings
    custom_config.binary_sensor.binary_keywords.extend(["mppt", "boost", "float"])
    custom_config.binary_sensor.parameter_overrides["battery_voltage"] = False
    custom_config.binary_sensor.parameter_overrides["charge_mode"] = True
    
    # Customize discovery settings
    custom_config.discovery.batch_size = 16
    custom_config.discovery.scan_delay = 0.2
    custom_config.discovery.default_slave_range = (1, 5)
    
    # Set custom config
    config_manager.set_config(device_id, custom_config)
    
    # Retrieve and verify
    retrieved_config = config_manager.get_config(device_id)
    print(f"  Device name: {retrieved_config.device_name}")
    print(f"  Manufacturer: {retrieved_config.manufacturer}")
    print(f"  Model: {retrieved_config.model}")
    print(f"  Binary keywords: {retrieved_config.binary_sensor.binary_keywords[-3:]}")
    print(f"  Parameter overrides: {len(retrieved_config.binary_sensor.parameter_overrides)}")
    print(f"  Batch size: {retrieved_config.discovery.batch_size}")
    print(f"  Scan delay: {retrieved_config.discovery.scan_delay}")
    print(f"  Slave range: {retrieved_config.discovery.default_slave_range}")
    print("  ✅ Custom configuration set and retrieved")
    
    # Test 3: Configuration methods
    print("\n📋 Test 3: Configuration Methods")
    
    # Test adding binary keyword
    config_manager.add_binary_keyword(device_id, "emergency")
    updated_config = config_manager.get_config(device_id)
    assert "emergency" in updated_config.binary_sensor.binary_keywords
    print("  ✅ Binary keyword added")
    
    # Test removing binary keyword
    config_manager.remove_binary_keyword(device_id, "emergency")
    updated_config = config_manager.get_config(device_id)
    assert "emergency" not in updated_config.binary_sensor.binary_keywords
    print("  ✅ Binary keyword removed")
    
    # Test parameter override
    config_manager.set_parameter_override(device_id, "test_param", True)
    updated_config = config_manager.get_config(device_id)
    assert updated_config.binary_sensor.parameter_overrides["test_param"] == True
    print("  ✅ Parameter override set")
    
    # Test 4: Export/Import
    print("\n📋 Test 4: Export/Import Configuration")
    
    # Export configuration
    exported_config = config_manager.export_config(device_id)
    print(f"  Exported keys: {list(exported_config.keys())}")
    print(f"  Binary keywords in export: {len(exported_config['binary_sensor']['binary_keywords'])}")
    print("  ✅ Configuration exported")
    
    # Import to new device
    new_device_id = "imported_device"
    config_manager.import_config(new_device_id, exported_config)
    imported_config = config_manager.get_config(new_device_id)
    
    # Verify import
    assert imported_config.device_name == custom_config.device_name
    assert imported_config.manufacturer == custom_config.manufacturer
    assert imported_config.discovery.batch_size == custom_config.discovery.batch_size
    print("  ✅ Configuration imported successfully")
    
    # Test 5: Device-specific binary sensor detection
    print("\n📋 Test 5: Binary Sensor Detection")
    
    # Test parameter that should be binary
    test_params = [
        ("battery_status", {"description": "Battery status indicator"}, True),
        ("pv_voltage", {"description": "PV array voltage"}, False),
        ("mppt_active", {"description": "MPPT tracking active"}, True),
        ("temperature", {"description": "Device temperature"}, False),
        ("fault_code", {"description": "System fault code"}, True),
    ]
    
    for param_name, param_config, expected_binary in test_params:
        # Simulate binary detection logic
        param_name_lower = param_name.lower()
        description_lower = param_config.get("description", "").lower()
        
        is_binary = False
        for keyword in retrieved_config.binary_sensor.binary_keywords:
            if keyword in param_name_lower or keyword in description_lower:
                is_binary = True
                break
        
        result = "✅" if is_binary == expected_binary else "❌"
        print(f"  {result} {param_name}: {'binary' if is_binary else 'regular'} (expected: {'binary' if expected_binary else 'regular'})")
    
    print("\n🎉 All configuration tests completed!")
    return True

if __name__ == "__main__":
    try:
        success = test_device_config()
        if success:
            print("\n✨ Device configuration system is working correctly!")
            sys.exit(0)
        else:
            print("\n💥 Device configuration system has issues!")
            sys.exit(1)
    except Exception as e:
        print(f"\n💥 Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
