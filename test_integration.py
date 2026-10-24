#!/usr/bin/env python3
"""Comprehensive testing framework for the Generic Modbus Integration."""

import os
import sys
import json
import py_compile
import tempfile
import importlib.util
from typing import List, Dict, Any

class IntegrationTester:
    """Test the integration for common issues."""
    
    def __init__(self, integration_path: str):
        self.integration_path = integration_path
        self.errors = []
        self.warnings = []
        
    def log_error(self, message: str):
        """Log an error."""
        self.errors.append(message)
        print(f"❌ ERROR: {message}")
        
    def log_warning(self, message: str):
        """Log a warning."""
        self.warnings.append(message)
        print(f"⚠️  WARNING: {message}")
        
    def log_success(self, message: str):
        """Log a success."""
        print(f"✅ {message}")
    
    def test_file_structure(self) -> bool:
        """Test that all required files exist."""
        print("\n📁 Testing file structure...")
        
        required_files = [
            "__init__.py",
            "config_flow.py",
            "const.py", 
            "manifest.json",
            "sensor.py",
            "coordinator.py",
            "translations/en.json"
        ]
        
        success = True
        for file_path in required_files:
            full_path = os.path.join(self.integration_path, file_path)
            if os.path.exists(full_path):
                self.log_success(f"Required file: {file_path}")
            else:
                self.log_error(f"Missing required file: {file_path}")
                success = False
                
        return success
    
    def test_python_syntax(self) -> bool:
        """Test Python syntax for all .py files."""
        print("\n🐍 Testing Python syntax...")
        
        python_files = []
        for root, dirs, files in os.walk(self.integration_path):
            for file in files:
                if file.endswith('.py'):
                    python_files.append(os.path.join(root, file))
        
        success = True
        for py_file in python_files:
            try:
                py_compile.compile(py_file, doraise=True)
                rel_path = os.path.relpath(py_file, self.integration_path)
                self.log_success(f"Syntax valid: {rel_path}")
            except py_compile.PyCompileError as e:
                rel_path = os.path.relpath(py_file, self.integration_path)
                self.log_error(f"Syntax error in {rel_path}: {e}")
                success = False
                
        return success
    
    def test_imports(self) -> bool:
        """Test that imports work correctly."""
        print("\n📦 Testing imports...")
        
        # Test config_flow imports specifically
        config_flow_path = os.path.join(self.integration_path, "config_flow.py")
        if not os.path.exists(config_flow_path):
            self.log_error("config_flow.py not found")
            return False
            
        try:
            # Read the file and check for problematic imports
            with open(config_flow_path, 'r') as f:
                content = f.read()
                
            # Check for selector imports
            if "from homeassistant.helpers import selector" in content:
                self.log_warning("Uses selector imports - may not work in all HA versions")
                
            # Check for fallback patterns
            if "vol.In(" in content:
                self.log_success("Uses vol.In() for dropdowns - good fallback")
            else:
                self.log_warning("No vol.In() fallback found")
                
            self.log_success("Import analysis completed")
            return True
            
        except Exception as e:
            self.log_error(f"Error analyzing imports: {e}")
            return False
    
    def test_manifest(self) -> bool:
        """Test manifest.json structure."""
        print("\n📋 Testing manifest.json...")
        
        manifest_path = os.path.join(self.integration_path, "manifest.json")
        try:
            with open(manifest_path, 'r') as f:
                manifest = json.load(f)
            
            required_keys = ["domain", "name", "config_flow", "requirements", "version"]
            success = True
            
            for key in required_keys:
                if key in manifest:
                    self.log_success(f"Manifest key: {key} = {manifest[key]}")
                else:
                    self.log_error(f"Missing manifest key: {key}")
                    success = False
            
            # Check for common issues
            if manifest.get("config_flow") != True:
                self.log_warning("config_flow should be true")
                
            if not isinstance(manifest.get("requirements"), list):
                self.log_warning("requirements should be a list")
                
            return success
            
        except json.JSONDecodeError as e:
            self.log_error(f"Invalid JSON in manifest: {e}")
            return False
        except Exception as e:
            self.log_error(f"Error reading manifest: {e}")
            return False
    
    def test_translations(self) -> bool:
        """Test translation structure."""
        print("\n🌐 Testing translations...")
        
        translations_path = os.path.join(self.integration_path, "translations/en.json")
        try:
            with open(translations_path, 'r') as f:
                translations = json.load(f)
            
            # Check required paths
            required_paths = [
                ["config", "step", "user", "title"],
                ["config", "step", "discovery", "title"],
                ["config", "step", "device_config", "title"],
            ]
            
            success = True
            for path in required_paths:
                current = translations
                for key in path:
                    if key not in current:
                        self.log_error(f"Missing translation: {' -> '.join(path)}")
                        success = False
                        break
                    current = current[key]
                else:
                    self.log_success(f"Translation path: {' -> '.join(path)}")
            
            # Check for translation fix
            discovery_desc = translations.get("config", {}).get("step", {}).get("discovery", {}).get("description", "")
            if "{message}" in discovery_desc:
                self.log_success("Translation fix present (dynamic messages)")
            elif "{device_count}" in discovery_desc:
                self.log_warning("Old device_count pattern found - may cause errors")
            else:
                self.log_warning("No dynamic message pattern found")
                
            return success
            
        except json.JSONDecodeError as e:
            self.log_error(f"Invalid translation JSON: {e}")
            return False
        except Exception as e:
            self.log_error(f"Error reading translations: {e}")
            return False
    
    def test_version_compatibility(self) -> bool:
        """Test version compatibility."""
        print("\n🔄 Testing version compatibility...")
        
        try:
            # Check if selector is available
            from homeassistant.helpers import selector
            self.log_success("Selectors available - can use modern UI")
            modern_ui = True
        except ImportError:
            self.log_warning("Selectors not available - using fallback UI")
            modern_ui = False
        
        # Check config_flow for compatibility
        config_flow_path = os.path.join(self.integration_path, "config_flow.py")
        if os.path.exists(config_flow_path):
            with open(config_flow_path, 'r') as f:
                content = f.read()
            
            if "selector." in content and not modern_ui:
                self.log_error("Config flow uses selectors but they're not available")
                return False
            elif "vol.In(" in content:
                self.log_success("Config flow uses compatible vol.In() approach")
            else:
                self.log_warning("Config flow approach unclear")
        
        return True
    
    def run_all_tests(self) -> bool:
        """Run all tests."""
        print("🧪 Running Integration Tests")
        print("=" * 50)
        
        tests = [
            self.test_file_structure,
            self.test_python_syntax,
            self.test_imports,
            self.test_manifest,
            self.test_translations,
            self.test_version_compatibility,
        ]
        
        all_passed = True
        for test in tests:
            if not test():
                all_passed = False
        
        print("\n📊 Test Summary")
        print("=" * 30)
        print(f"Errors: {len(self.errors)}")
        print(f"Warnings: {len(self.warnings)}")
        
        if self.errors:
            print("\n❌ Errors found:")
            for error in self.errors:
                print(f"  • {error}")
        
        if self.warnings:
            print("\n⚠️  Warnings:")
            for warning in self.warnings:
                print(f"  • {warning}")
        
        if all_passed and not self.errors:
            print("\n🎉 All tests passed!")
            return True
        else:
            print("\n💥 Some tests failed!")
            return False

def main():
    """Main test runner."""
    integration_path = "homeassistant/custom_components/generic_modbus"
    
    if not os.path.exists(integration_path):
        print(f"❌ Integration path not found: {integration_path}")
        sys.exit(1)
    
    tester = IntegrationTester(integration_path)
    success = tester.run_all_tests()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
