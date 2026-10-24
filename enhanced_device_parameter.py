@dataclass
class DeviceParameter:
    """Represents a configurable device parameter with full HA support"""
    # Core Modbus Properties
    address: int
    function_code: int
    name: str
    
    # Value Processing
    scale: float = 1.0
    offset: float = 0.0
    data_type: str = "uint16"
    
    # Home Assistant Entity Properties
    unique_id: str = ""                    # Globally unique identifier
    device_class: str = ""                 # HA device class
    state_class: str = ""                  # measurement/total/total_increasing
    unit: str = ""                         # Unit of measurement
    icon: str = ""                         # Material Design icon
    
    # Display and Organization
    description: str = ""                  # Human-readable description
    entity_category: str = ""              # config/diagnostic/None
    suggested_display_precision: int = None  # Decimal places
    
    # Behavior
    enabled: bool = True
    update_interval: int = 30              # seconds
    entity_registry_enabled_default: bool = True
    
    # Custom Attributes
    extra_attributes: Dict[str, Any] = None
    
    def __post_init__(self):
        """Generate unique_id if not provided"""
        if not self.unique_id:
            # Generate unique ID from address and function code
            self.unique_id = f"modbus_{self.function_code:02x}_{self.address:04x}"
        
        if self.extra_attributes is None:
            self.extra_attributes = {}
    
    def get_entity_unique_id(self, device_id: str) -> str:
        """Get globally unique entity ID"""
        return f"{device_id}_{self.unique_id}"
    
    def get_device_info(self, device: 'ManagedDevice') -> Dict[str, Any]:
        """Generate device info for HA entity"""
        return {
            "identifiers": {(DOMAIN, device.get_device_identifier())},
            "name": device.name,
            "manufacturer": device.manufacturer,
            "model": device.model,
            "sw_version": device.firmware_version,
            "configuration_url": f"http://{device.device_path}",  # If applicable
        }
