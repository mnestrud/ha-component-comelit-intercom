#!/usr/bin/env python3
"""
Comelit CLI - Simple command line interface for Comelit ICONA Bridge devices.

This tool implements the Comelit binary protocol to list and open doors.
Uses only asyncio (built-in) for async operations, compatible with Home Assistant.

Usage:
    export COMELIT_IP=10.0.1.49
    export COMELIT_TOKEN=your_token_here
    python comelit_cli.py
"""

import asyncio
import struct
import json
import os
import sys
import logging
from typing import Optional, List, Dict, Tuple

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Protocol constants
ICONA_BRIDGE_PORT = 64100
PROTOCOL_VERSION = 0xabcd
CHANNEL_TYPE_UAUT = 7  # Authentication channel
CHANNEL_TYPE_UCFG = 2  # Configuration channel
CHANNEL_TYPE_CTPP = 16 # Control channel
CHANNEL_TYPE_CSPB = 17 # Status channel


class ComelitClient:
    """Client for communicating with Comelit ICONA Bridge devices."""
    
    def __init__(self, host: str, token: str):
        self.host = host
        self.token = token
        self.port = ICONA_BRIDGE_PORT
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None
        self.request_id = 1000  # Starting request ID
        self.doors: List[Dict[str, str]] = []
        
    async def connect(self) -> bool:
        """Connect to the ICONA Bridge."""
        try:
            logger.info(f"Connecting to {self.host}:{self.port}")
            self.reader, self.writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port),
                timeout=10.0
            )
            logger.info("Connected successfully")
            return True
        except asyncio.TimeoutError:
            logger.error(f"Connection timeout to {self.host}:{self.port}")
            return False
        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from the ICONA Bridge."""
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()
            logger.info("Disconnected")
    
    def _create_header(self, body_length: int, request_id: int = 0) -> bytes:
        """Create protocol header."""
        header = b'\x00\x06'  # Magic bytes
        header += struct.pack('<H', body_length)  # Body length (little-endian)
        header += struct.pack('<H', request_id)  # Request ID
        header += b'\x00\x00'  # Padding
        return header
    
    async def _send_packet(self, body: bytes, request_id: int = 0) -> bool:
        """Send a packet with header and body."""
        if not self.writer:
            return False
            
        header = self._create_header(len(body), request_id)
        packet = header + body
        
        try:
            self.writer.write(packet)
            await self.writer.drain()
            logger.debug(f"Sent packet: {packet.hex()}")
            return True
        except Exception as e:
            logger.error(f"Failed to send packet: {e}")
            return False
    
    async def _read_response(self) -> Optional[Tuple[bytes, bytes]]:
        """Read response header and body."""
        if not self.reader:
            return None
            
        try:
            # Read 8-byte header
            header = await asyncio.wait_for(self.reader.readexactly(8), timeout=5.0)
            logger.debug(f"Received header: {header.hex()}")
            
            # Parse header
            body_length = struct.unpack('<H', header[2:4])[0]
            
            # Read body if present
            body = b''
            if body_length > 0:
                body = await asyncio.wait_for(self.reader.readexactly(body_length), timeout=5.0)
                logger.debug(f"Received body: {body.hex()}")
                
            return header, body
            
        except asyncio.TimeoutError:
            logger.error("Response timeout")
            return None
        except Exception as e:
            logger.error(f"Failed to read response: {e}")
            return None
    
    async def open_channel(self, channel_type: int, channel_name: str) -> bool:
        """Open a communication channel."""
        logger.info(f"Opening {channel_name} channel")
        
        # Create channel open request
        self.request_id += 1
        body = struct.pack('<HH', PROTOCOL_VERSION, 1)  # Protocol version and operation
        body += struct.pack('<I', channel_type)  # Channel type
        body += channel_name.encode('ascii') + b'\x00'  # Channel name (null-terminated)
        body += struct.pack('<H', self.request_id)  # Request ID
        body += b'\x00'  # Padding
        
        # Send request
        if not await self._send_packet(body):
            return False
        
        # Read response
        response = await self._read_response()
        if not response:
            return False
            
        logger.info(f"{channel_name} channel opened successfully")
        return True
    
    async def authenticate(self) -> bool:
        """Authenticate with the device."""
        logger.info("Authenticating")
        
        # First open UAUT channel
        if not await self.open_channel(CHANNEL_TYPE_UAUT, "UAUT"):
            return False
        
        # Send authentication request
        auth_data = {
            "message": "access",
            "user-token": self.token,
            "message-type": "request",
            "message-id": 1
        }
        
        auth_json = json.dumps(auth_data, separators=(',', ':'))
        auth_body = auth_json.encode('ascii')
        
        if not await self._send_packet(auth_body, self.request_id):
            return False
        
        # Read auth response
        response = await self._read_response()
        if not response:
            logger.error("No authentication response")
            return False
            
        header, body = response
        if body:
            try:
                auth_response = json.loads(body.decode('utf-8'))
                logger.info(f"Auth response: {auth_response}")
                
                if auth_response.get("message") == "access" and \
                   auth_response.get("response-status") == "done":
                    logger.info("Authentication successful")
                    return True
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON in auth response: {body}")
                
        return False
    
    async def list_doors(self) -> List[Dict[str, str]]:
        """Get list of available doors."""
        logger.info("Listing doors")
        
        # Open UCFG channel
        if not await self.open_channel(CHANNEL_TYPE_UCFG, "UCFG"):
            return []
        
        # Send list request
        list_data = {
            "message": "list",
            "class": "opener",
            "message-type": "request",
            "message-id": 2
        }
        
        list_json = json.dumps(list_data, separators=(',', ':'))
        list_body = list_json.encode('ascii')
        
        if not await self._send_packet(list_body, self.request_id):
            return []
        
        # Read response
        response = await self._read_response()
        if not response:
            return []
            
        header, body = response
        if body:
            try:
                list_response = json.loads(body.decode('utf-8'))
                logger.info(f"List response: {list_response}")
                
                if list_response.get("message") == "list" and \
                   list_response.get("response-status") == "done":
                    elements = list_response.get("response-data", {}).get("elements", [])
                    self.doors = [{"name": elem["name"], "id": elem["id"]} for elem in elements]
                    logger.info(f"Found {len(self.doors)} doors")
                    return self.doors
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON in list response: {body}")
                
        return []
    
    async def open_door(self, door_name: str) -> bool:
        """Open a specific door by name."""
        logger.info(f"Opening door: {door_name}")
        
        # Find door ID
        door_id = None
        for door in self.doors:
            if door["name"] == door_name:
                door_id = door["id"]
                break
                
        if not door_id:
            logger.error(f"Door '{door_name}' not found")
            return False
        
        # Open control channel
        if not await self.open_channel(CHANNEL_TYPE_CTPP, "CTPP"):
            return False
        
        # Send open command
        open_data = {
            "message": "action",
            "element-id": door_id,
            "element-type": "opener",
            "action-id": "open",
            "message-type": "request",
            "message-id": 3
        }
        
        open_json = json.dumps(open_data, separators=(',', ':'))
        open_body = open_json.encode('ascii')
        
        if not await self._send_packet(open_body, self.request_id):
            return False
        
        # Read response
        response = await self._read_response()
        if not response:
            return False
            
        header, body = response
        if body:
            try:
                open_response = json.loads(body.decode('utf-8'))
                logger.info(f"Open response: {open_response}")
                
                if open_response.get("message") == "action" and \
                   open_response.get("response-status") == "done":
                    logger.info(f"Door '{door_name}' opened successfully")
                    return True
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON in open response: {body}")
                
        return False


async def main():
    """Main CLI interface."""
    # Get configuration from environment
    host = os.environ.get('COMELIT_IP')
    token = os.environ.get('COMELIT_TOKEN')
    
    if not host or not token:
        print("Error: Please set COMELIT_IP and COMELIT_TOKEN environment variables")
        print("Example:")
        print("  export COMELIT_IP=10.0.1.49")
        print("  export COMELIT_TOKEN=your_token_here")
        sys.exit(1)
    
    # Create client
    client = ComelitClient(host, token)
    
    # Connect
    if not await client.connect():
        print("Failed to connect to device")
        sys.exit(1)
    
    try:
        # Authenticate
        if not await client.authenticate():
            print("Authentication failed")
            sys.exit(1)
        
        # List doors
        doors = await client.list_doors()
        
        if not doors:
            print("No doors found")
            sys.exit(1)
        
        # Display doors
        print("\nAvailable doors:")
        for i, door in enumerate(doors):
            print(f"  {i+1}. {door['name']}")
        
        # Interactive mode
        while True:
            print("\nOptions:")
            print("  1-{} - Open door".format(len(doors)))
            print("  l - List doors again")
            print("  q - Quit")
            
            choice = input("\nEnter choice: ").strip().lower()
            
            if choice == 'q':
                break
            elif choice == 'l':
                doors = await client.list_doors()
                print("\nAvailable doors:")
                for i, door in enumerate(doors):
                    print(f"  {i+1}. {door['name']}")
            elif choice.isdigit():
                door_num = int(choice)
                if 1 <= door_num <= len(doors):
                    door = doors[door_num - 1]
                    if await client.open_door(door['name']):
                        print(f"✓ Door '{door['name']}' opened")
                    else:
                        print(f"✗ Failed to open door '{door['name']}'")
                else:
                    print("Invalid door number")
            else:
                print("Invalid choice")
                
    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())