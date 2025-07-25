#!/usr/bin/env python3
"""
Python implementation of the Comelit ICONA Bridge client.
This is a complete reimplementation of the Node.js comelit-client library.
"""

import asyncio
import json
import struct
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import IntEnum


# Constants
ICONA_BRIDGE_PORT = 64100
HEADER_MAGIC = b'\x00\x06'
HEADER_SIZE = 8
NULL = b'\x00'


class MessageType(IntEnum):
    """Binary message types"""
    COMMAND = 0xabcd
    END = 0x01ef
    OPEN_DOOR_INIT = 0x18c0
    OPEN_DOOR = 0x1800
    OPEN_DOOR_CONFIRM = 0x1820


class ViperChannelType(IntEnum):
    """Channel type IDs for JSON messages"""
    SERVER_INFO = 20
    PUSH = 2
    UAUT = 2
    UCFG = 3
    CTPP = 7
    CSPB = 8


class Channel:
    """Channel names"""
    UAUT = "UAUT"
    UCFG = "UCFG"
    INFO = "INFO"
    CTPP = "CTPP"
    CSPB = "CSPB"
    PUSH = "PUSH"


@dataclass
class ChannelData:
    """Tracks open channel state"""
    channel: str
    id: int
    sequence: int


class IconaBridgeClient:
    """Python implementation of Comelit ICONA Bridge client"""
    
    def __init__(self, host: str, port: int = ICONA_BRIDGE_PORT, logger: Optional[logging.Logger] = None):
        self.host = host
        self.port = port
        self.logger = logger or logging.getLogger(__name__)
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None
        self.open_channels: Dict[str, ChannelData] = {}
        self.request_id = 8000 + int(asyncio.get_event_loop().time() * 10) % 1000
        
    async def connect(self):
        """Connect to the ICONA Bridge"""
        self.logger.info(f"Connecting to {self.host}:{self.port}")
        self.reader, self.writer = await asyncio.open_connection(self.host, self.port)
        self.logger.info("Connected")
        
    async def shutdown(self):
        """Close the connection"""
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()
            self.logger.info("Connection closed")
            
    def _create_header(self, body_length: int, request_id: int = 0) -> bytes:
        """Create 8-byte message header"""
        header = bytearray(8)
        header[0:2] = HEADER_MAGIC
        header[2:4] = struct.pack('<H', body_length)
        header[4:6] = struct.pack('<H', request_id)
        header[6:8] = b'\x00\x00'
        return bytes(header)
        
    def _create_json_packet(self, request_id: int, data: Dict) -> bytes:
        """Create a JSON message packet"""
        json_str = json.dumps(data, separators=(',', ':'))
        json_bytes = json_str.encode('utf-8')
        header = self._create_header(len(json_bytes), request_id)
        return header + json_bytes
        
    def _create_binary_packet_from_buffers(self, request_id: int, *buffers: bytes) -> bytes:
        """Create a binary message packet from multiple buffers"""
        body = b''.join(buffers)
        header = self._create_header(len(body), request_id)
        return header + body
        
    def _create_command_packet(self, request_id: int, seq: int, msg_type: int, 
                              channel: Optional[str] = None, 
                              additional_data: Optional[str] = None) -> bytes:
        """Create a command packet (for opening/closing channels)"""
        # Start with message type and sequence
        body = struct.pack('<HH', msg_type, seq)
        
        # Add channel data if provided
        if channel:
            channel_bytes = channel.encode('ascii')
            # Size includes channel name + request_id (2) + null (1)
            channel_size = len(channel_bytes) + 3
            body += struct.pack('<I', channel_size)
            body += channel_bytes + NULL
            body += struct.pack('<H', request_id)
            body += NULL
            
        # Add additional data if provided
        if additional_data:
            add_bytes = additional_data.encode('ascii')
            body += struct.pack('<I', len(add_bytes) + 1)
            body += add_bytes + NULL
            
        header = self._create_header(len(body), 0)  # Request ID is 0 for command packets
        return header + body
        
    async def _write_packet(self, packet: bytes):
        """Write a packet to the socket"""
        self.logger.debug(f"Writing {len(packet)} bytes: {packet.hex(' ')}")
        self.writer.write(packet)
        await self.writer.drain()
        
    async def _read_response(self) -> Optional[Dict]:
        """Read and parse a response from the socket"""
        # Read header
        header = await self.reader.readexactly(HEADER_SIZE)
        body_length = struct.unpack('<H', header[2:4])[0]
        request_id = struct.unpack('<H', header[4:6])[0]
        
        # Read body
        if body_length > 0:
            body = await self.reader.readexactly(body_length)
            self.logger.debug(f"Read {len(body)} bytes: {body.hex(' ')}")
            
            # Parse response
            if request_id == 0:
                # Binary response with request ID at end
                msg_type = struct.unpack('<H', body[0:2])[0]
                sequence = struct.unpack('<H', body[2:4])[0]
                
                if msg_type == MessageType.COMMAND:
                    # For COMMAND responses, the body is just the 4 bytes we already read
                    # No additional data to extract
                    return {
                        'type': 'binary',
                        'message_type': msg_type,
                        'sequence': sequence,
                        'request_id': request_id
                    }
                elif msg_type == MessageType.END:
                    return {
                        'type': 'binary',
                        'message_type': msg_type,
                        'sequence': sequence,
                        'request_id': request_id
                    }
            else:
                # Check if it's JSON
                if body[0] == 0x7b:  # '{'
                    json_data = json.loads(body.decode('utf-8'))
                    return {
                        'type': 'json',
                        'request_id': request_id,
                        'data': json_data
                    }
                else:
                    # Binary data response
                    return {
                        'type': 'binary_data',
                        'request_id': request_id,
                        'data': body
                    }
                    
        return None
        
    async def _open_channel(self, channel: str, additional_data: Optional[str] = None) -> ChannelData:
        """Open a communication channel"""
        if channel in self.open_channels:
            return self.open_channels[channel]
            
        self.request_id += 1
        channel_data = ChannelData(channel=channel, id=self.request_id, sequence=1)
        
        # Send COMMAND to open channel
        packet = self._create_command_packet(
            self.request_id, 1, MessageType.COMMAND, channel, additional_data
        )
        await self._write_packet(packet)
        
        # Read response
        response = await self._read_response()
        if response and response['type'] == 'binary' and response['sequence'] == 2:
            channel_data.sequence = response['sequence']
            self.open_channels[channel] = channel_data
            self.logger.debug(f"Opened channel {channel} with ID {self.request_id}")
            return channel_data
        else:
            raise Exception(f"Failed to open channel {channel}")
            
    async def _close_channel(self, channel_data: ChannelData) -> bool:
        """Close a communication channel"""
        channel_data.sequence += 1
        packet = self._create_command_packet(
            channel_data.id, channel_data.sequence, MessageType.END
        )
        await self._write_packet(packet)
        
        response = await self._read_response()
        if response and response['type'] == 'binary':
            del self.open_channels[channel_data.channel]
            self.logger.debug(f"Closed channel {channel_data.channel}")
            return True
        return False
        
    async def authenticate(self, token: str) -> int:
        """Authenticate with the ICONA Bridge"""
        # Open authentication channel
        channel = await self._open_channel(Channel.UAUT)
        
        # Send authentication message
        auth_data = {
            'message': 'access',
            'user-token': token,
            'message-type': 'request',
            'message-id': ViperChannelType.UAUT
        }
        packet = self._create_json_packet(channel.id, auth_data)
        await self._write_packet(packet)
        
        # Read response
        response = await self._read_response()
        if response and response['type'] == 'json':
            code = response['data'].get('response-code', 500)
            await self._close_channel(channel)
            return code
        
        await self._close_channel(channel)
        return 500
        
    async def get_config(self, addressbooks: str = 'all') -> Optional[Dict]:
        """Get configuration from the device"""
        # Open config channel
        channel = await self._open_channel(Channel.UCFG)
        
        # Send get-configuration message
        config_data = {
            'message': 'get-configuration',
            'addressbooks': addressbooks,
            'message-type': 'request',
            'message-id': ViperChannelType.UCFG
        }
        packet = self._create_json_packet(channel.id, config_data)
        await self._write_packet(packet)
        
        # Read response
        response = await self._read_response()
        if response and response['type'] == 'json':
            await self._close_channel(channel)
            return response['data']
            
        await self._close_channel(channel)
        return None
        
    async def list_doors(self) -> List[Dict]:
        """List all available doors"""
        config = await self.get_config('all')
        if config and 'vip' in config:
            return config['vip'].get('user-parameters', {}).get('opendoor-address-book', [])
        return []
        
    def _string_to_buffer(self, s: str, null_terminated: bool = False) -> bytes:
        """Convert string to bytes buffer"""
        b = s.encode('ascii')
        if null_terminated:
            b += NULL
        return b
        
    async def _open_door_init(self, vip: Dict):
        """Initialize door opening sequence"""
        apt_address = f"{vip['apt-address']}{vip.get('apt-subaddress', '')}"
        channel = await self._open_channel(Channel.CTPP, apt_address)
        
        # Send unknown init message
        buffers = [
            bytes([0xc0, 0x18, 0x5c, 0x8b]),
            bytes([0x2b, 0x73, 0x00, 0x11]),
            bytes([0x00, 0x40, 0xac, 0x23]),
            self._string_to_buffer(apt_address, True),
            bytes([0x10, 0x0e]),
            bytes([0x00, 0x00, 0x00, 0x00]),
            bytes([0xff, 0xff, 0xff, 0xff]),
            self._string_to_buffer(apt_address, True),
            self._string_to_buffer(vip['apt-address'], True),
            NULL
        ]
        packet = self._create_binary_packet_from_buffers(channel.id, *buffers)
        await self._write_packet(packet)
        
        # Read two responses
        await self._read_response()
        await self._read_response()
        
    async def open_door(self, vip: Dict, door_item: Dict):
        """Open a specific door"""
        # Initialize if needed
        if Channel.CTPP not in self.open_channels:
            await self._open_door_init(vip)
            
        channel = self.open_channels[Channel.CTPP]
        
        # Helper function to create door messages
        def create_door_message(confirm: bool = False) -> bytes:
            msg_type = MessageType.OPEN_DOOR_CONFIRM if confirm else MessageType.OPEN_DOOR
            buffers = [
                struct.pack('<H', msg_type),
                bytes([0x5c, 0x8b]),
                bytes([0x2c, 0x74, 0x00, 0x00]),
                bytes([0xff, 0xff, 0xff, 0xff]),
                self._string_to_buffer(f"{vip['apt-address']}{door_item['output-index']}", True),
                self._string_to_buffer(door_item['apt-address'], True),
                NULL
            ]
            return self._create_binary_packet_from_buffers(channel.id, *buffers)
            
        # Send open door command and confirmation
        await self._write_packet(create_door_message(False))
        await self._write_packet(create_door_message(True))
        
        # Send init message for this specific door
        buffers = [
            bytes([0xc0, 0x18, 0x70, 0xab]),
            bytes([0x29, 0x9f, 0x00, 0x0d]),
            bytes([0x00, 0x2d]),
            self._string_to_buffer(door_item['apt-address'], True),
            NULL,
            bytes([int(door_item['output-index']), 0x00, 0x00, 0x00]),
            bytes([0xff, 0xff, 0xff, 0xff]),
            self._string_to_buffer(f"{vip['apt-address']}{door_item['output-index']}", True),
            self._string_to_buffer(door_item['apt-address'], True),
            NULL
        ]
        packet = self._create_binary_packet_from_buffers(channel.id, *buffers)
        await self._write_packet(packet)
        
        # Read responses
        await self._read_response()
        await self._read_response()
        
        # Send final open door command and confirmation
        await self._write_packet(create_door_message(False))
        await self._write_packet(create_door_message(True))
        
        self.logger.info(f"Door '{door_item.get('name', 'Unknown')}' opened")


# High-level convenience functions
async def list_doors(host: str, token: str) -> List[Dict]:
    """List all available doors from a Comelit device"""
    client = IconaBridgeClient(host)
    try:
        await client.connect()
        auth_code = await client.authenticate(token)
        if auth_code == 200:
            return await client.list_doors()
        else:
            raise Exception(f"Authentication failed with code {auth_code}")
    finally:
        await client.shutdown()
        

async def open_door(host: str, token: str, door_name: str) -> bool:
    """Open a specific door by name"""
    client = IconaBridgeClient(host)
    try:
        await client.connect()
        auth_code = await client.authenticate(token)
        if auth_code != 200:
            raise Exception(f"Authentication failed with code {auth_code}")
            
        # Get configuration
        config = await client.get_config('all')
        if not config or 'vip' not in config:
            raise Exception("Failed to get configuration")
            
        vip = config['vip']
        doors = vip.get('user-parameters', {}).get('opendoor-address-book', [])
        
        # Find the door by name
        door = next((d for d in doors if d.get('name') == door_name), None)
        if not door:
            available = [d.get('name', 'Unknown') for d in doors]
            raise Exception(f"Door '{door_name}' not found. Available: {', '.join(available)}")
            
        # Open the door
        await client.open_door(vip, door)
        return True
        
    finally:
        await client.shutdown()


if __name__ == "__main__":
    # Example usage
    import os
    
    async def main():
        host = os.getenv('COMELIT_IP_ADDRESS', '10.0.1.49')
        token = os.getenv('COMELIT_TOKEN', '9943a85362467c53586e3553d34f8a8d')
        
        # Configure logging
        logging.basicConfig(level=logging.INFO)
        
        print(f"Testing Comelit client with host: {host}")
        
        # List doors
        print("\nListing doors...")
        doors = await list_doors(host, token)
        for door in doors:
            print(f"  - {door.get('name', 'Unknown')} (address: {door.get('apt-address')})")
            
        # Open first door if available
        if doors:
            door_name = doors[0].get('name')
            print(f"\nOpening door: {door_name}")
            await open_door(host, token, door_name)
            print("Door opened successfully!")
            
    asyncio.run(main())