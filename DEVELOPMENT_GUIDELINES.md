# Development Guidelines for Generic Modbus Integration

## 🚨 Preventing Compatibility Issues

This document outlines best practices to prevent "400: Bad Request" and other compatibility errors.

## 📋 Pre-Development Checklist

### Before Making Changes:
1. **Run compatibility check**: `python3 check_compatibility.py`
2. **Check current HA version**: Note what version you're targeting
3. **Review existing code**: Understand current patterns before changing

### Before Committing Changes:
1. **Run pre-commit checks**: `./pre_commit_check.sh`
2. **Test syntax**: `python3 test_integration.py`
3. **Validate structure**: `python3 validate_integration.py`

## 🔧 Safe Coding Practices

### 1. UI Components (Config Flow)

#### ❌ AVOID - Modern selectors without fallback:
```python
# This will fail on older HA versions
from homeassistant.helpers import selector

data_schema = vol.Schema({
    vol.Optional("baudrate"): selector.SelectSelector(...)
})
```

#### ✅ PREFER - Traditional approach with better labels:
```python
# This works across all HA versions
data_schema = vol.Schema({
    vol.Optional("baudrate", default=115200): vol.In({
        9600: "9600 bps",
        19200: "19200 bps", 
        38400: "38400 bps",
        57600: "57600 bps",
        115200: "115200 bps"
    })
})
```

#### ✅ BEST - Defensive coding with fallbacks:
```python
# Use the ui_utils.py helper
from .ui_utils import create_dropdown_field

# This automatically uses selectors if available, falls back if not
dropdown_field = create_dropdown_field(
    "baudrate", 
    115200, 
    {9600: "9600 bps", 19200: "19200 bps", ...}
)
```

### 2. Import Safety

#### ❌ AVOID - Direct imports of new features:
```python
from homeassistant.helpers import selector  # May not exist
```

#### ✅ PREFER - Try/except imports:
```python
try:
    from homeassistant.helpers import selector
    SELECTORS_AVAILABLE = True
except ImportError:
    SELECTORS_AVAILABLE = False
    selector = None
```

### 3. Translation Safety

#### ❌ AVOID - Placeholders without providing values:
```python
return self.async_show_form(
    description_placeholders={}  # Missing required placeholders
)
```

#### ✅ PREFER - Always provide required placeholders:
```python
return self.async_show_form(
    description_placeholders={
        "device_count": len(devices),
        "message": "Clear fallback message"
    }
)
```

### 4. Version-Specific Features

#### Check before using new features:
```python
# Check if a feature exists before using it
if hasattr(vol, 'Range'):
    # Use modern validation
    field = vol.All(vol.Coerce(int), vol.Range(min=1, max=247))
else:
    # Use basic validation
    field = vol.Coerce(int)
```

## 🧪 Testing Strategy

### 1. Automated Testing
- **Always run**: `./pre_commit_check.sh` before changes
- **Syntax check**: `python3 -m py_compile file.py` for each file
- **Integration test**: `python3 test_integration.py` for full validation

### 2. Manual Testing
- **Test in clean environment**: Use fresh HA installation
- **Test error scenarios**: What happens when discovery fails?
- **Test UI flow**: Complete the entire config flow

### 3. Compatibility Testing
- **Check feature availability**: `python3 check_compatibility.py`
- **Test fallback paths**: Disable modern features and test
- **Version matrix**: Test on different HA versions if possible

## 📚 Common Patterns

### Safe Dropdown Creation:
```python
# Always works - creates dropdown-like behavior
baudrate_options = {
    9600: "9600 bps",
    19200: "19200 bps",
    38400: "38400 bps",
    57600: "57600 bps", 
    115200: "115200 bps"
}

data_schema = vol.Schema({
    vol.Optional(CONF_BAUDRATE, default=DEFAULT_BAUDRATE): vol.In(baudrate_options)
})
```

### Safe Number Validation:
```python
# Works across versions
vol.Optional(CONF_TIMEOUT, default=2.0): vol.All(
    vol.Coerce(float), 
    vol.Range(min=0.1, max=30.0)
)
```

### Safe Translation Handling:
```python
# Always provide fallback messages
if devices_found:
    message = f"Found {len(devices)} device(s)"
else:
    message = "No devices found"

return self.async_show_form(
    description_placeholders={"message": message}
)
```

## 🚨 Red Flags to Watch For

### Code Smells:
- Direct imports of `selector` without try/except
- Using `{placeholders}` in translations without providing values
- Hardcoded version assumptions
- No fallback for new features

### Testing Gaps:
- Not testing error scenarios
- Not validating on clean HA installation
- Skipping syntax validation
- Not checking translation completeness

## 🔄 Development Workflow

### 1. Before Starting:
```bash
# Check current state
python3 check_compatibility.py
python3 validate_integration.py
```

### 2. During Development:
```bash
# Frequent syntax checks
python3 -m py_compile config_flow.py

# Test specific changes
python3 test_integration.py
```

### 3. Before Committing:
```bash
# Full validation
./pre_commit_check.sh

# Manual test in HA
./install_fixed_integration.sh /path/to/ha/config
# Restart HA and test UI
```

### 4. After Changes:
```bash
# Verify installation works
python3 validate_integration.py
./verify_installation.sh /path/to/ha/config
```

## 📞 When Things Go Wrong

### "400: Bad Request" Error:
1. **Check syntax**: `python3 -m py_compile config_flow.py`
2. **Check imports**: Look for missing/incompatible imports
3. **Check translations**: Verify all placeholders are provided
4. **Revert to known good**: Use git to revert problematic changes

### Translation Errors:
1. **Check placeholders**: Ensure all `{variables}` have values
2. **Validate JSON**: `python3 -c "import json; json.load(open('translations/en.json'))"`
3. **Use fallback messages**: Provide static messages when dynamic ones fail

### Import Errors:
1. **Use try/except**: Wrap new imports in error handling
2. **Check availability**: Use compatibility checker
3. **Provide fallbacks**: Always have a backup approach

## 🎯 Success Metrics

### Before Release:
- ✅ All pre-commit checks pass
- ✅ Integration loads without errors
- ✅ Config flow completes successfully
- ✅ Translations display correctly
- ✅ Works on target HA version

### Quality Indicators:
- Zero syntax errors
- No missing translations
- Graceful error handling
- Clear user messages
- Consistent UI behavior

---

**Remember**: It's better to use a simple, compatible approach than a fancy one that breaks! 🛡️
