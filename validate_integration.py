#!/usr/bin/env python3
"""Validate the Generic Modbus Integration structure and syntax."""

import json
import os
import sys
import py_compile
import tempfile

def validate_integration():
    """Validate the integration structure and files."""
    integration_path = "homeassistant/custom_components/generic_modbus"
    
    print("🔍 Validating Generic Modbus Integration...")
    print("=" * 50)
    
    # Check if integration directory exists
    if not os.path.exists(integration_path):
        print(f"❌ Integration directory not found: {integration_path}")
        return False
    
    # Required files
    required_files = [
        "__init__.py",
        "config_flow.py", 
        "const.py",
        "manifest.json",
        "sensor.py",
        "coordinator.py",
        "translations/en.json"
    ]
    
    print("📁 Checking required files...")
    for file_path in required_files:
        full_path = os.path.join(integration_path, file_path)
        if os.path.exists(full_path):
            print(f"  ✅ {file_path}")
        else:
            print(f"  ❌ {file_path} - MISSING")
            return False
    
    # Validate Python syntax
    print("\n🐍 Validating Python syntax...")
    python_files = [
        "__init__.py",
        "config_flow.py",
        "const.py", 
        "sensor.py",
        "coordinator.py"
    ]
    
    for py_file in python_files:
        full_path = os.path.join(integration_path, py_file)
        try:
            py_compile.compile(full_path, doraise=True)
            print(f"  ✅ {py_file}")
        except py_compile.PyCompileError as e:
            print(f"  ❌ {py_file} - SYNTAX ERROR: {e}")
            return False
    
    # Validate manifest.json
    print("\n📋 Validating manifest.json...")
    manifest_path = os.path.join(integration_path, "manifest.json")
    try:
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
        
        required_keys = ["domain", "name", "config_flow", "requirements", "version"]
        for key in required_keys:
            if key in manifest:
                print(f"  ✅ {key}: {manifest[key]}")
            else:
                print(f"  ❌ {key} - MISSING")
                return False
                
    except json.JSONDecodeError as e:
        print(f"  ❌ Invalid JSON: {e}")
        return False
    except Exception as e:
        print(f"  ❌ Error reading manifest: {e}")
        return False
    
    # Validate translations
    print("\n🌐 Validating translations...")
    translations_path = os.path.join(integration_path, "translations/en.json")
    try:
        with open(translations_path, 'r') as f:
            translations = json.load(f)
        
        # Check for required translation paths
        required_paths = [
            ["config", "step", "user", "title"],
            ["config", "step", "discovery", "title"],
            ["config", "step", "device_config", "title"],
        ]
        
        for path in required_paths:
            current = translations
            for key in path:
                if key not in current:
                    print(f"  ❌ Missing translation: {' -> '.join(path)}")
                    return False
                current = current[key]
            print(f"  ✅ {' -> '.join(path)}")
        
        # Check for translation fix
        if "{message}" in translations["config"]["step"]["discovery"]["description"]:
            print("  ✅ Translation fix present")
        else:
            print("  ❌ Translation fix missing")
            return False
            
    except json.JSONDecodeError as e:
        print(f"  ❌ Invalid translation JSON: {e}")
        return False
    except Exception as e:
        print(f"  ❌ Error reading translations: {e}")
        return False
    
    # Check for generic_modbus library
    print("\n📚 Checking generic_modbus library...")
    lib_path = os.path.join(integration_path, "generic_modbus")
    if os.path.exists(lib_path):
        lib_files = ["__init__.py", "device_discovery.py", "device_manager.py", "modbus_client.py"]
        for lib_file in lib_files:
            lib_file_path = os.path.join(lib_path, lib_file)
            if os.path.exists(lib_file_path):
                print(f"  ✅ {lib_file}")
            else:
                print(f"  ❌ {lib_file} - MISSING")
                return False
    else:
        print("  ❌ generic_modbus library directory missing")
        return False
    
    print("\n🎉 Integration validation completed successfully!")
    print("\n📊 Summary:")
    print("  ✅ All required files present")
    print("  ✅ Python syntax valid")
    print("  ✅ Manifest structure correct")
    print("  ✅ Translations complete")
    print("  ✅ Translation fix applied")
    print("  ✅ Generic modbus library present")
    
    return True

if __name__ == "__main__":
    success = validate_integration()
    if not success:
        print("\n💥 Integration validation failed!")
        sys.exit(1)
    else:
        print("\n✨ Integration is ready for installation!")
        sys.exit(0)
