#!/usr/bin/env python3
"""
Device Identification System
Handles stable identification of USB serial devices across reboots
"""

import os
import glob
import logging
from dataclasses import dataclass, asdict
from typing import Optional, Dict, List, Any
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class StabilityLevel(Enum):
    """Device path stability levels"""
    HIGH = "high"      # Unique serial number, very stable
    MEDIUM = "medium"  # Physical port based, stable if not moved
    LOW = "low"        # Generic device, may change on reboot


@dataclass
class DeviceIdentifiers:
    """Complete device identification information"""
    # Current paths
    current_tty_path: str
    by_id_path: Optional[str] = None
    by_path_path: Optional[str] = None
    
    # USB hardware identifiers
    usb_vendor_id: Optional[str] = None
    usb_product_id: Optional[str] = None
    usb_serial: Optional[str] = None
    usb_manufacturer: Optional[str] = None
    usb_product_name: Optional[str] = None
    
    # Stability analysis
    has_unique_serial: bool = False
    stability_level: StabilityLevel = StabilityLevel.LOW
    stability_description: str = ""
    
    # Modbus validation signature
    modbus_signature: Optional[Dict[str, Any]] = None
    
    # Metadata
    configured_at: Optional[str] = None
    last_validated_at: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        data = asdict(self)
        # Convert enum to string for JSON serialization
        data['stability_level'] = self.stability_level.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DeviceIdentifiers':
        """Create from dictionary"""
        # Convert string back to enum
        if 'stability_level' in data:
            data['stability_level'] = StabilityLevel(data['stability_level'])
        return cls(**data)
    
    def get_user_friendly_description(self) -> str:
        """Get human-readable device description"""
        if self.usb_product_name and self.usb_serial:
            return f"{self.usb_product_name} (Serial: {self.usb_serial})"
        elif self.usb_product_name:
            return f"{self.usb_product_name}"
        elif self.by_id_path:
            # Extract meaningful part from by-id path
            filename = os.path.basename(self.by_id_path)
            return filename.replace('usb-', '').replace('-if00-port0', '')
        else:
            return f"Serial Device ({self.current_tty_path})"
    
    def get_stability_indicator(self) -> str:
        """Get emoji indicator for stability level"""
        if self.stability_level == StabilityLevel.HIGH:
            return "🟢"
        elif self.stability_level == StabilityLevel.MEDIUM:
            return "🟡"
        else:
            return "🔴"


@dataclass
class DeviceMatch:
    """Represents a potential match for a stored device"""
    device_path: str
    identifiers: DeviceIdentifiers
    confidence: float  # 0.0 to 1.0
    match_reasons: List[str]
    
    def get_confidence_description(self) -> str:
        """Get human-readable confidence description"""
        if self.confidence >= 0.9:
            return "Exact match"
        elif self.confidence >= 0.7:
            return "Likely match"
        elif self.confidence >= 0.5:
            return "Possible match"
        else:
            return "Unlikely match"


@dataclass
class ModbusSignature:
    """Modbus device signature for validation"""
    slave_id: int
    test_registers: List[Dict[str, Any]]
    device_profile_key: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ModbusSignature':
        """Create from dictionary"""
        return cls(**data)
