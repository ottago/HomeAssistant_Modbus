"""UI utilities with fallback support for different Home Assistant versions."""

from typing import Dict, Any, Union

import voluptuous as vol

# Try to import selectors, fall back to traditional methods
try:
    from homeassistant.helpers import selector
    SELECTORS_AVAILABLE = True
except ImportError:
    SELECTORS_AVAILABLE = False
    selector = None

def create_dropdown_field(
    key: str, 
    default: Any, 
    options: Dict[Any, str], 
    required: bool = False
) -> Dict[str, Any]:
    """Create a dropdown field that works across HA versions."""
    
    if SELECTORS_AVAILABLE and selector:
        # Use modern selector API
        selector_options = [
            {"value": value, "label": label} 
            for value, label in options.items()
        ]
        
        field_def = selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=selector_options,
                mode=selector.SelectSelectorMode.DROPDOWN,
            )
        )
    else:
        # Fall back to traditional vol.In()
        field_def = vol.In(options)
    
    if required:
        return {vol.Required(key, default=default): field_def}
    else:
        return {vol.Optional(key, default=default): field_def}

def create_number_field(
    key: str,
    default: Union[int, float],
    min_val: Union[int, float] = None,
    max_val: Union[int, float] = None,
    step: Union[int, float] = None,
    required: bool = False
) -> Dict[str, Any]:
    """Create a number field that works across HA versions."""
    
    if SELECTORS_AVAILABLE and selector:
        # Use modern selector API
        config = selector.NumberSelectorConfig(
            mode=selector.NumberSelectorMode.BOX
        )
        if min_val is not None:
            config.min = min_val
        if max_val is not None:
            config.max = max_val
        if step is not None:
            config.step = step
            
        field_def = selector.NumberSelector(config)
    else:
        # Fall back to traditional validation
        validators = [vol.Coerce(type(default))]
        if min_val is not None or max_val is not None:
            validators.append(vol.Range(min=min_val, max=max_val))
        field_def = vol.All(*validators)
    
    if required:
        return {vol.Required(key, default=default): field_def}
    else:
        return {vol.Optional(key, default=default): field_def}

def create_text_field(
    key: str,
    default: str = "",
    required: bool = False
) -> Dict[str, Any]:
    """Create a text field that works across HA versions."""
    
    if SELECTORS_AVAILABLE and selector:
        # Use modern selector API
        field_def = selector.TextSelector(
            selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
        )
    else:
        # Fall back to simple string
        field_def = str
    
    if required:
        return {vol.Required(key, default=default): field_def}
    else:
        return {vol.Optional(key, default=default): field_def}

def create_boolean_field(
    key: str,
    default: bool = False,
    required: bool = False
) -> Dict[str, Any]:
    """Create a boolean field that works across HA versions."""
    
    if SELECTORS_AVAILABLE and selector:
        # Use modern selector API
        field_def = selector.BooleanSelector()
    else:
        # Fall back to simple bool
        field_def = bool
    
    if required:
        return {vol.Required(key, default=default): field_def}
    else:
        return {vol.Optional(key, default=default): field_def}

def get_ui_capabilities() -> Dict[str, bool]:
    """Get information about available UI capabilities."""
    return {
        "selectors_available": SELECTORS_AVAILABLE,
        "modern_ui": SELECTORS_AVAILABLE,
        "fallback_mode": not SELECTORS_AVAILABLE
    }
