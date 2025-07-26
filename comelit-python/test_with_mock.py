#!/usr/bin/env python3
"""Test the Comelit CLI with a mock server."""

import asyncio
import json
import logging
import struct
from typing import Optional, Tuple

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MockComelitServer:
    """Mock Comelit ICONA Bridge server for testing."""
    
    def __init__(self, host='127.0.0.1', port=64100):
        self.host = host
        self.port = port
        self.server = None
        self.clients = []
        
    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """Handle client connections."""
        client_addr = writer.get_extra_info('peername')
        logger.info(f"Client connected from {client_addr}")
        self.clients.append((reader, writer))
        
        try:
            while True:
                # Read header
                header = await reader.readexactly(8)
                if not header:
                    break
                    
                logger.debug(f"Received header: {header.hex()}")
                
                # Parse header
                magic = header[0:2]
                body_length = struct.unpack('<H', header[2:4])[0]
                request_id = struct.unpack('<H', header[4:6])[0]
                
                # Read body
                body = b''
                if body_length > 0:
                    body = await reader.readexactly(body_length)
                    logger.debug(f"Received body: {body.hex()}")
                    logger.info(f"Body as text: {body}")
                
                # Handle different message types
                response_body = await self.process_message(body, request_id)
                
                if response_body:
                    # Send response
                    response_header = b'\x00\x06'
                    response_header += struct.pack('<H', len(response_body))
                    response_header += struct.pack('<H', request_id)
                    response_header += b'\x00\x00'
                    
                    writer.write(response_header + response_body)
                    await writer.drain()
                    logger.debug(f"Sent response: {(response_header + response_body).hex()}")
                    
        except asyncio.IncompleteReadError:
            logger.info("Client disconnected")
        except Exception as e:
            logger.error(f"Error handling client: {e}")
        finally:
            writer.close()
            await writer.wait_closed()
            self.clients.remove((reader, writer))
    
    async def process_message(self, body: bytes, request_id: int) -> Optional[bytes]:
        """Process incoming messages and generate responses."""
        # Channel open requests
        if len(body) > 4 and body[0:2] == b'\xcd\xab':  # Protocol version
            channel_type = struct.unpack('<I', body[4:8])[0]
            channel_names = {7: "UAUT", 2: "UCFG", 16: "CTPP", 17: "CSPB"}
            channel_name = channel_names.get(channel_type, "UNKNOWN")
            logger.info(f"Channel open request for {channel_name} (type {channel_type})")
            
            # Send channel open response
            response = struct.pack('<HH', 0xabcd, 2)  # Protocol version and status
            response += struct.pack('<I', channel_type)
            response += channel_name.encode('ascii') + b'\x00'
            response += struct.pack('<H', request_id)
            response += b'\x00'
            return response
            
        # JSON messages
        try:
            message = json.loads(body.decode('utf-8'))
            logger.info(f"JSON message: {message}")
            
            if message.get("message") == "access":
                # Authentication response
                return json.dumps({
                    "message": "access",
                    "response-status": "done",
                    "message-id": message.get("message-id", 1)
                }).encode('utf-8')
                
            elif message.get("message") == "list":
                # Door list response
                return json.dumps({
                    "message": "list",
                    "response-status": "done",
                    "response-data": {
                        "elements": [
                            {"id": "door1", "name": "Front Door"},
                            {"id": "door2", "name": "Back Door"},
                            {"id": "door3", "name": "Garage"}
                        ]
                    },
                    "message-id": message.get("message-id", 2)
                }).encode('utf-8')
                
            elif message.get("message") == "action":
                # Door open response
                door_id = message.get("element-id")
                logger.info(f"Opening door: {door_id}")
                return json.dumps({
                    "message": "action",
                    "response-status": "done",
                    "message-id": message.get("message-id", 3)
                }).encode('utf-8')
                
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass
            
        return None
    
    async def start(self):
        """Start the mock server."""
        self.server = await asyncio.start_server(
            self.handle_client,
            self.host,
            self.port
        )
        
        addrs = ', '.join(str(sock.getsockname()) for sock in self.server.sockets)
        logger.info(f'Mock server listening on {addrs}')
        
        async with self.server:
            await self.server.serve_forever()
    
    async def stop(self):
        """Stop the mock server."""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            logger.info("Mock server stopped")


async def test_cli():
    """Test the CLI with mock server."""
    # Start mock server on different port to avoid conflicts
    mock = MockComelitServer(port=64101)
    server_task = asyncio.create_task(mock.start())
    
    # Wait for server to start
    await asyncio.sleep(0.5)
    
    try:
        # Set up environment
        import os
        os.environ['COMELIT_IP'] = '127.0.0.1'
        os.environ['COMELIT_TOKEN'] = 'test_token'
        
        # Import and test the CLI
        from comelit_cli import ComelitClient
        
        client = ComelitClient('127.0.0.1', 'test_token')
        client.port = 64101  # Use mock server port
        
        # Test connection
        assert await client.connect(), "Failed to connect"
        
        # Test authentication
        assert await client.authenticate(), "Failed to authenticate"
        
        # Test listing doors
        doors = await client.list_doors()
        assert len(doors) == 3, f"Expected 3 doors, got {len(doors)}"
        assert doors[0]['name'] == 'Front Door', "Wrong door name"
        
        # Test opening door
        assert await client.open_door('Front Door'), "Failed to open door"
        
        # Disconnect
        await client.disconnect()
        
        logger.info("All tests passed!")
        
    finally:
        # Stop server
        server_task.cancel()
        try:
            await server_task
        except asyncio.CancelledError:
            pass


if __name__ == "__main__":
    asyncio.run(test_cli())