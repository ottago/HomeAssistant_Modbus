#!/usr/bin/env python3
"""
Generic Modbus RTU Client
Handles communication with a Modbus RTU device
"""

import logging
import struct
import time
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional

import serial

logger = logging.getLogger(__name__)

class FunctionCode(Enum):
    """Modbus function codes"""
    READ_COILS = 0x01
    READ_DISCRETE_INPUTS = 0x02
    READ_HOLDING_REGISTERS = 0x03
    READ_INPUT_REGISTERS = 0x04
    WRITE_SINGLE_COIL = 0x05
    WRITE_SINGLE_REGISTER = 0x06
    WRITE_MULTIPLE_COILS = 0x0F
    WRITE_MULTIPLE_REGISTERS = 0x10

@dataclass
class ModbusRegister:
    """Represents a Modbus register with metadata"""
    address: int
    function_code: FunctionCode
    name: str = ""
    description: str = ""
    unit: str = ""
    scale: float = 1.0
    offset: float = 0.0
    data_type: str = "uint16"  # uint16, int16, uint32, int32, float32
    device_class: str = ""
    state_class: str = ""
    icon: str = ""
    
class ModbusException(Exception):
    """Base exception for Modbus errors"""
    pass

class GenericModbusClient:
    """Generic Modbus RTU client for any device"""
    
    def __init__(self, device_path: str = None, baudrate: int = 115200, 
                 timeout: float = 2.0, parity: str = 'N', 
                 stopbits: int = 1, bytesize: int = 8, **kwargs):
        """Initialize Modbus client"""
        self.device_path = device_path
        self.baudrate = baudrate
        self.timeout = timeout
        self.parity = parity
        self.stopbits = stopbits
        self.bytesize = bytesize
        self.connection = None
        logger.debug(f"init device=[{self.device_path}] baudrate=[{baudrate}]")
        
    def test_slave_connectivity(self, slave_id: int) -> bool:
        """Test if a slave device responds at the given ID."""
        try:
            # Try common registers that most Modbus devices support
            test_registers = [
                (0x0000, FunctionCode.READ_HOLDING_REGISTERS),
                (0x0000, FunctionCode.READ_INPUT_REGISTERS),
                (0x0001, FunctionCode.READ_HOLDING_REGISTERS),
                (0x0001, FunctionCode.READ_INPUT_REGISTERS),
                (0x3100, FunctionCode.READ_INPUT_REGISTERS),  # Common for solar chargers
            ]
            
            for register, function_code in test_registers:
                try:
                    result = self.read_single_register(slave_id, register, function_code)
                    if result is not None:
                        logger.debug(f"Slave {slave_id} responded to register 0x{register:04X} with function {function_code.name}")
                        return True
                except Exception as e:
                    logger.debug(f"Slave {slave_id} register 0x{register:04X} test failed: {e}")
                    continue
            
            logger.debug(f"Slave {slave_id} did not respond to any test registers")
            return False
            
        except Exception as e:
            logger.debug(f"Slave {slave_id} connectivity test failed: {e}")
            return False
        
    def connect(self) -> bool:
        """Establish connection to Modbus device"""
        try:
            self.connection = serial.Serial(
                port=self.device_path,
                baudrate=self.baudrate,
                timeout=self.timeout,
                parity=self.parity,
                stopbits=self.stopbits,
                bytesize=self.bytesize
            )
            logger.info(f"Connected to Modbus device at {self.device_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to {self.device_path}: {e}")
            return False
    
    def disconnect(self):
        """Close connection"""
        if self.connection and self.connection.is_open:
            self.connection.close()
            logger.info("Modbus connection closed")
    
    def _calculate_crc(self, data: bytes) -> int:
        """Calculate CRC16 for Modbus RTU"""
        crc = 0xFFFF
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 0x0001:
                    crc = (crc >> 1) ^ 0xA001
                else:
                    crc >>= 1
        return crc
    
    def _send_request(self, slave_id: int, function_code: int, 
                     start_address: int, count: int) -> Optional[bytes]:
        """Send Modbus request and return response"""
        if not self.connection or not self.connection.is_open:
            raise ModbusException("Connection not established")
        
        # Build request frame
        request = struct.pack('>BBHH', slave_id, function_code, 
                             start_address, count)
        crc = self._calculate_crc(request)
        request += struct.pack('<H', crc)
        
        try:
            # Clear input buffer
            self.connection.reset_input_buffer()
            
            # Send request
            self.connection.write(request)
            
            # Read response header (slave_id + function_code + byte_count)
            response_header = self.connection.read(3)
            if len(response_header) != 3:
                raise ModbusException("Incomplete response header")
            
            slave_resp, func_resp, byte_count = struct.unpack('BBB', response_header)
            
            # Check for error response
            if func_resp & 0x80:
                error_code = self.connection.read(1)[0]
                crc_bytes = self.connection.read(2)
                raise ModbusException(f"Modbus error code: {error_code}")
            
            # Read data and CRC
            data = self.connection.read(byte_count)
            crc_bytes = self.connection.read(2)
            
            if len(data) != byte_count or len(crc_bytes) != 2:
                raise ModbusException("Incomplete response data")
            
            # Verify CRC
            response_frame = response_header + data
            expected_crc = self._calculate_crc(response_frame)
            received_crc = struct.unpack('<H', crc_bytes)[0]
            
            if expected_crc != received_crc:
                raise ModbusException("CRC mismatch")
            
            return data
            
        except Exception as e:
            logger.error(f"Modbus communication error: {e}")
            raise ModbusException(f"Communication error: {e}")
    
    def read_registers(self, slave_id: int, function_code: FunctionCode, 
                      start_address: int, count: int = 1) -> List[int]:
        """Read multiple registers"""
        try:
            data = self._send_request(slave_id, function_code.value, start_address, count)
            if not data:
                return []
            
            # Unpack 16-bit registers (big-endian)
            registers = []
            for i in range(0, len(data), 2):
                if i + 1 < len(data):
                    value = struct.unpack('>H', data[i:i+2])[0]
                    registers.append(value)
            
            return registers
            
        except Exception as e:
            logger.error(f"Failed to read registers {start_address}-{start_address+count-1} "
                        f"from slave {slave_id}: {e}")
            return []
    
    def read_single_register(self, slave_id: int, function_code: FunctionCode, 
                           address: int) -> Optional[int]:
        """Read a single register"""
        registers = self.read_registers(slave_id, function_code, address, 1)
        return registers[0] if registers else None
    
    def write_single_register(self, slave_id: int, address: int, 
                            value: int) -> bool:
        """Write a single holding register"""
        if not self.connection or not self.connection.is_open:
            raise ModbusException("Connection not established")
        
        try:
            # Build write request
            request = struct.pack('>BBHH', slave_id, 
                                FunctionCode.WRITE_SINGLE_REGISTER.value, 
                                address, value)
            crc = self._calculate_crc(request)
            request += struct.pack('<H', crc)
            
            # Send request
            self.connection.reset_input_buffer()
            self.connection.write(request)
            
            # Read response (should echo the request)
            response = self.connection.read(8)
            if len(response) != 8:
                raise ModbusException("Incomplete write response")
            
            # Verify response matches request
            if response[:-2] != request[:-2]:
                raise ModbusException("Write response mismatch")
            
            logger.info(f"Successfully wrote {value} to register {address} "
                       f"on slave {slave_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to write register {address} on slave {slave_id}: {e}")
            return False
    
    def test_connection(self, slave_id: int) -> bool:
        """Test if device responds at given slave ID"""
        # Try multiple common registers to find a responsive one
        test_registers = [
            # Common registers
            (FunctionCode.READ_INPUT_REGISTERS, 0x0000),
            (FunctionCode.READ_INPUT_REGISTERS, 0x0001),
            (FunctionCode.READ_HOLDING_REGISTERS, 0x0000),
            (FunctionCode.READ_HOLDING_REGISTERS, 0x0001),
            # Device info registers
            (FunctionCode.READ_INPUT_REGISTERS, 0x9000),
            (FunctionCode.READ_HOLDING_REGISTERS, 0x9000),
            # Solar charger registers
            (FunctionCode.READ_INPUT_REGISTERS, 0x3100),
            (FunctionCode.READ_INPUT_REGISTERS, 0x3104)
        ]
        
        for function_code, address in test_registers:
            try:
                result = self.read_single_register(slave_id, function_code, address)
                if result is not None:
                    return True
            except:
                continue
        
        return False
    
    def scan_registers(self, slave_id: int, function_code: FunctionCode,
                      start_address: int = 0, end_address: int = 100,
                      batch_size: int = 10) -> Dict[int, int]:
        """Scan a range of registers to find which ones respond"""
        found_registers = {}

        logger.debug(f"scan_registers slave_id={slave_id} range {start_address:04X}-{end_address:04X}")
        
        # Try individual registers first to avoid batch failures
        for addr in range(start_address, end_address + 1):
            try:
                value = self.read_single_register(slave_id, function_code, addr)
                if value is not None:
                    found_registers[addr] = value
                    logger.debug(f"Found register {addr:04X}: {value}")
                    
                # Small delay to avoid overwhelming the device
                time.sleep(0.05)
                
            except ModbusException as e:
                # Check if it's a "register not available" error
                if "error code: 192" in str(e) or "error code: 194" in str(e):
                    # These are expected for non-existent registers
                    logger.debug(f"Register {addr:04X} not available (expected)")
                else:
                    logger.debug(f"Register {addr:04X} error: {e}")
                continue
            except Exception as e:
                logger.debug(f"Register {addr:04X} failed: {e}")
                continue
        
        logger.info(f"Found {len(found_registers)} registers in range {start_address:04X}-{end_address:04X}")
        return found_registers
    
    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()
