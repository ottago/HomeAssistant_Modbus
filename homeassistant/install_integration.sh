#!/bin/bash
"""
Installation script for Generic Modbus Home Assistant Integration
"""

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Generic Modbus Integration Installer${NC}"
echo "========================================"

# Check if Home Assistant config directory exists
if [ -z "$1" ]; then
    echo -e "${YELLOW}Usage: $0 <home_assistant_config_directory>${NC}"
    echo "Example: $0 /config"
    echo "Example: $0 ~/.homeassistant"
    exit 1
fi

HA_CONFIG_DIR="$1"

if [ ! -d "$HA_CONFIG_DIR" ]; then
    echo -e "${RED}❌ Home Assistant config directory not found: $HA_CONFIG_DIR${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Found Home Assistant config directory: $HA_CONFIG_DIR${NC}"

# Create custom_components directory if it doesn't exist
CUSTOM_COMPONENTS_DIR="$HA_CONFIG_DIR/custom_components"
mkdir -p "$CUSTOM_COMPONENTS_DIR"

# Copy the integration (which now includes the embedded generic_modbus library)
INTEGRATION_DIR="$CUSTOM_COMPONENTS_DIR/generic_modbus"
echo -e "${BLUE}📦 Installing integration to: $INTEGRATION_DIR${NC}"

# Remove existing installation
if [ -d "$INTEGRATION_DIR" ]; then
    echo -e "${YELLOW}⚠️  Removing existing installation${NC}"
    rm -rf "$INTEGRATION_DIR"
fi

# Copy integration files (now self-contained)
cp -r "custom_components/generic_modbus" "$INTEGRATION_DIR"

echo -e "${GREEN}✅ Integration installed successfully!${NC}"
echo ""
echo -e "${BLUE}📋 Next Steps:${NC}"
echo "1. Restart Home Assistant"
echo "2. Go to Settings → Devices & Services"
echo "3. Click '+ Add Integration'"
echo "4. Search for 'Generic Modbus Device Integration'"
echo "5. Follow the configuration wizard"
echo ""
echo -e "${BLUE}📖 Configuration:${NC}"
echo "- Device Path: Your serial device (e.g., /dev/ttyUSB0)"
echo "- Baud Rate: Usually 115200 for modern devices"
echo "- Enable Discovery: Automatically find devices"
echo "- Slave ID Range: Range to scan (e.g., 1-10)"
echo ""
echo -e "${BLUE}🔧 Troubleshooting:${NC}"
echo "- Check Home Assistant logs for any errors"
echo "- Ensure your serial device has proper permissions"
echo "- Verify your Modbus device is connected and powered"
echo ""
echo -e "${GREEN}🎉 Installation complete!${NC}"
