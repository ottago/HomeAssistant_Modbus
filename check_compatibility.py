#!/usr/bin/env python3
"""Check Home Assistant compatibility for features used in the integration."""

import sys
import importlib.util

def check_ha_version():
    """Check if we can determine Home Assistant version."""
    try:
        import homeassistant
        if hasattr(homeassistant, '__version__'):
            return homeassistant.__version__
        else:
            return "Unknown"
    except ImportError:
        return "Not available"

def check_selector_support():
    """Check if selector module is available."""
    try:
        from homeassistant.helpers import selector
        return True, "Available"
    except ImportError:
        return False, "Not available - use vol.In() instead"

def check_feature_compatibility():
    """Check compatibility of various Home Assistant features."""
    print("🔍 Home Assistant Feature Compatibility Check")
    print("=" * 50)
    
    # Check HA version
    ha_version = check_ha_version()
    print(f"📦 Home Assistant Version: {ha_version}")
    
    # Check selector support
    selector_available, selector_msg = check_selector_support()
    if selector_available:
        print(f"✅ Selectors: {selector_msg}")
    else:
        print(f"❌ Selectors: {selector_msg}")
    
    # Check other common imports
    features = [
        ("homeassistant.config_entries", "Config Entries"),
        ("homeassistant.data_entry_flow", "Data Entry Flow"),
        ("homeassistant.helpers.config_validation", "Config Validation"),
        ("voluptuous", "Voluptuous"),
    ]
    
    print("\n📚 Core Dependencies:")
    for module_name, display_name in features:
        try:
            importlib.import_module(module_name)
            print(f"  ✅ {display_name}")
        except ImportError:
            print(f"  ❌ {display_name} - MISSING")
    
    print("\n💡 Recommendations:")
    if not selector_available:
        print("  • Use vol.In() with dictionaries for dropdown-like behavior")
        print("  • Use vol.Range() for numeric validation")
        print("  • Avoid modern selector APIs")
    else:
        print("  • Modern selector APIs are available")
        print("  • Can use advanced UI components")
    
    return selector_available

if __name__ == "__main__":
    selector_available = check_feature_compatibility()
    
    print(f"\n🎯 Integration should use: {'Modern selectors' if selector_available else 'Traditional vol.In()'}")
