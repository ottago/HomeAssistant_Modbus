#!/usr/bin/env python3
"""Test script to verify translation structure."""

import json
import os

def test_translations():
    """Test that translations are properly structured."""
    translation_file = "homeassistant/custom_components/generic_modbus/translations/en.json"
    
    if not os.path.exists(translation_file):
        print(f"❌ Translation file not found: {translation_file}")
        return False
    
    try:
        with open(translation_file, 'r') as f:
            translations = json.load(f)
        
        # Check required structure
        required_paths = [
            ["config", "step", "user", "title"],
            ["config", "step", "discovery", "title"],
            ["config", "step", "discovery", "description"],
            ["config", "step", "device_config", "title"],
        ]
        
        for path in required_paths:
            current = translations
            for key in path:
                if key not in current:
                    print(f"❌ Missing translation path: {' -> '.join(path)}")
                    return False
                current = current[key]
        
        print("✅ Translation structure is valid")
        
        # Test the dynamic message approach
        discovery_desc = translations["config"]["step"]["discovery"]["description"]
        if "{message}" in discovery_desc:
            print("✅ Dynamic message placeholder found")
        else:
            print("❌ Dynamic message placeholder missing")
            return False
        
        return True
        
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in translation file: {e}")
        return False
    except Exception as e:
        print(f"❌ Error reading translation file: {e}")
        return False

if __name__ == "__main__":
    print("Testing Generic Modbus Integration translations...")
    success = test_translations()
    if success:
        print("\n🎉 All translation tests passed!")
    else:
        print("\n💥 Translation tests failed!")
    exit(0 if success else 1)
