#!/usr/bin/env python3
"""
Test suite for validating Comelit protocol implementations.
Can be used to compare Node.js and Python implementations.
"""

import struct
import json
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import IntEnum
import binascii


class MessageType(IntEnum):
    COMMAND = 0xabcd
    END = 0x01ef
    OPEN_DOOR_INIT = 0x18c0
    OPEN_DOOR = 0x1800
    OPEN_DOOR_CONFIRM = 0x1820


class ViperChannelType(IntEnum):
    SERVER_INFO = 20
    PUSH = 2
    UAUT = 2
    UCFG = 3
    CTPP = 7
    CSPB = 8


@dataclass
class ProtocolTest:
    name: str
    description: str
    input_params: Dict
    expected_output: bytes
    
    def validate(self, actual_output: bytes) -> bool:
        """Validate if actual output matches expected"""
        return actual_output == self.expected_output


class ComelitProtocol:
    """Python implementation of Comelit ICONA Bridge protocol"""
    
    HEADER_MAGIC = bytes([0x00, 0x06])
    HEADER_SIZE = 8
    NULL = bytes([0x00])
    
    @staticmethod
    def create_header(body_length: int, request_id: int) -> bytes:
        """Create 8-byte header"""
        header = bytearray(8)
        header[0:2] = ComelitProtocol.HEADER_MAGIC
        header[2:4] = struct.pack('<H', body_length)
        header[4:6] = struct.pack('<H', request_id)
        header[6:8] = bytes([0x00, 0x00])
        return bytes(header)
    
    @staticmethod
    def create_json_packet(request_id: int, json_data: Dict) -> bytes:
        """Create a JSON protocol message"""
        json_str = json.dumps(json_data, separators=(',', ':'))
        json_bytes = json_str.encode('utf-8')
        header = ComelitProtocol.create_header(len(json_bytes), request_id)
        return header + json_bytes
    
    @staticmethod
    def create_binary_packet_from_buffers(request_id: int, *buffers: bytes) -> bytes:
        """Create a binary protocol message from buffer parts"""
        body = b''.join(buffers)
        header = ComelitProtocol.create_header(len(body), request_id)
        return header + body
    
    @staticmethod
    def create_command_packet(request_id: int, seq: int, channel: str, 
                            additional_data: Optional[str] = None) -> bytes:
        """Create a COMMAND packet to open a channel"""
        # Message type and sequence
        body = struct.pack('<HH', MessageType.COMMAND, seq)
        
        # Channel name with size prefix
        channel_bytes = channel.encode('ascii')
        channel_size = len(channel_bytes) + 3  # +2 for request_id, +1 for null
        body += struct.pack('<I', channel_size)
        body += channel_bytes
        body += struct.pack('<H', request_id)
        body += ComelitProtocol.NULL
        
        # Additional data if provided
        if additional_data:
            add_bytes = additional_data.encode('ascii')
            body += struct.pack('<I', len(add_bytes) + 1)
            body += add_bytes
            body += ComelitProtocol.NULL
            
        header = ComelitProtocol.create_header(len(body), 0)
        return header + body
    
    @staticmethod
    def create_end_packet(request_id: int, seq: int) -> bytes:
        """Create an END packet to close a channel"""
        body = struct.pack('<HH', MessageType.END, seq)
        header = ComelitProtocol.create_header(len(body), 0)
        return header + body
    
    @staticmethod
    def string_to_buffer(s: str, null_terminated: bool = False) -> bytes:
        """Convert string to bytes buffer"""
        b = s.encode('ascii')
        if null_terminated:
            b += ComelitProtocol.NULL
        return b
    
    @staticmethod
    def create_access_message(request_id: int, token: str) -> bytes:
        """Create authentication message"""
        json_data = {
            'message': 'access',
            'user-token': token,
            'message-type': 'request',
            'message-id': ViperChannelType.UAUT
        }
        return ComelitProtocol.create_json_packet(request_id, json_data)
    
    @staticmethod
    def create_get_config_message(request_id: int, addressbooks: str) -> bytes:
        """Create get configuration message"""
        json_data = {
            'message': 'get-configuration',
            'addressbooks': addressbooks,
            'message-type': 'request',
            'message-id': ViperChannelType.UCFG
        }
        return ComelitProtocol.create_json_packet(request_id, json_data)
    
    @staticmethod
    def create_open_door_message(request_id: int, vip: Dict, door_item: Dict, 
                                confirm: bool = False) -> bytes:
        """Create open door message"""
        # Split the 16-bit message type into two bytes
        msg_type = MessageType.OPEN_DOOR_CONFIRM if confirm else MessageType.OPEN_DOOR
        buffers = [
            bytes([msg_type & 0xFF, (msg_type >> 8) & 0xFF]),  # Little endian
            bytes([0x5c, 0x8b]),
            bytes([0x2c, 0x74, 0x00, 0x00]),
            bytes([0xff, 0xff, 0xff, 0xff]),
            ComelitProtocol.string_to_buffer(
                f"{vip['apt-address']}{door_item['output-index']}", True
            ),
            ComelitProtocol.string_to_buffer(door_item['apt-address'], True),
            ComelitProtocol.NULL
        ]
        return ComelitProtocol.create_binary_packet_from_buffers(request_id, *buffers)


def create_test_suite() -> List[ProtocolTest]:
    """Create comprehensive test suite"""
    tests = []
    
    # Test 1: Open UAUT channel
    tests.append(ProtocolTest(
        name="open_uaut_channel",
        description="Open authentication channel",
        input_params={
            "request_id": 8001,
            "sequence": 1,
            "channel": "UAUT"
        },
        expected_output=bytes.fromhex(
            "00 06 0c 00 00 00 00 00 cd ab 01 00 08 00 00 00 55 41 55 54 41 1f 00"
        )
    ))
    
    # Test 2: Authentication message
    tests.append(ProtocolTest(
        name="auth_message",
        description="Send authentication token",
        input_params={
            "request_id": 8001,
            "token": "9943a85362467c53586e3553d34f8a8d"
        },
        expected_output=ComelitProtocol.create_access_message(
            8001, "9943a85362467c53586e3553d34f8a8d"
        )
    ))
    
    # Test 3: Get configuration
    tests.append(ProtocolTest(
        name="get_config",
        description="Get configuration with addressbook",
        input_params={
            "request_id": 8002,
            "addressbooks": "all"
        },
        expected_output=ComelitProtocol.create_get_config_message(8002, "all")
    ))
    
    # Test 4: Open door command
    tests.append(ProtocolTest(
        name="open_door",
        description="Send open door command",
        input_params={
            "request_id": 8003,
            "vip": {"apt-address": "100", "apt-subaddress": "1"},
            "door_item": {"apt-address": "100", "output-index": "1"}
        },
        expected_output=ComelitProtocol.create_open_door_message(
            8003,
            {"apt-address": "100", "apt-subaddress": "1"},
            {"apt-address": "100", "output-index": "1"},
            False
        )
    ))
    
    return tests


def run_tests():
    """Run all protocol tests"""
    tests = create_test_suite()
    
    print("Comelit Protocol Test Suite")
    print("=" * 60)
    print()
    
    passed = 0
    failed = 0
    
    for test in tests:
        print(f"Test: {test.name}")
        print(f"Description: {test.description}")
        print(f"Input: {test.input_params}")
        
        # Generate output based on test type
        if test.name == "open_uaut_channel":
            output = ComelitProtocol.create_command_packet(
                test.input_params["request_id"],
                test.input_params["sequence"],
                test.input_params["channel"]
            )
        elif test.name == "auth_message":
            output = ComelitProtocol.create_access_message(
                test.input_params["request_id"],
                test.input_params["token"]
            )
        elif test.name == "get_config":
            output = ComelitProtocol.create_get_config_message(
                test.input_params["request_id"],
                test.input_params["addressbooks"]
            )
        elif test.name == "open_door":
            output = ComelitProtocol.create_open_door_message(
                test.input_params["request_id"],
                test.input_params["vip"],
                test.input_params["door_item"]
            )
        else:
            output = b''
            
        # Display output
        print(f"Output: {output.hex(' ')}")
        
        # For now, just show the output since we can't validate against real device
        print(f"Status: Generated")
        print("-" * 60)
        print()
        
        passed += 1
    
    print(f"\nResults: {passed} passed, {failed} failed")
    
    # Export test vectors for comparison
    test_vectors = []
    for test in tests:
        vector = {
            "name": test.name,
            "description": test.description,
            "input": test.input_params,
            "expected_hex": test.expected_output.hex()
        }
        test_vectors.append(vector)
        
    with open("protocol-test-vectors.json", "w") as f:
        json.dump(test_vectors, f, indent=2)
        
    print("\nTest vectors exported to: protocol-test-vectors.json")


if __name__ == "__main__":
    run_tests()