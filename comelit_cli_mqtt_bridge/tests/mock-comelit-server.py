#!/usr/bin/env python3
"""
Mock Comelit ICONA Bridge server for testing client implementations.
This server simulates the protocol behavior without needing real hardware.
"""

import asyncio
import json
import struct
import logging
from typing import Dict, Optional


class MockComelitServer:
    """Mock server that simulates Comelit ICONA Bridge protocol"""
    
    def __init__(self, host: str = '127.0.0.1', port: int = 64100):
        self.host = host
        self.port = port
        self.logger = logging.getLogger(__name__)
        self.channels = {}
        self.sequence_counters = {}
        
        # Mock data
        self.mock_token = '9943a85362467c53586e3553d34f8a8d'
        self.mock_config = {
            "vip": {
                "apt-address": "100",
                "apt-subaddress": "1",
                "user-parameters": {
                    "opendoor-address-book": [
                        {
                            "name": "Front Door",
                            "apt-address": "100",
                            "output-index": "1"
                        },
                        {
                            "name": "Garage",
                            "apt-address": "100", 
                            "output-index": "2"
                        }
                    ]
                }
            }
        }
        
    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """Handle a client connection"""
        client_addr = writer.get_extra_info('peername')
        self.logger.info(f"Client connected from {client_addr}")
        
        try:
            while True:
                # Read header
                header = await reader.readexactly(8)
                if not header:
                    break
                    
                # Parse header
                magic = header[0:2]
                body_length = struct.unpack('<H', header[2:4])[0]
                request_id = struct.unpack('<H', header[4:6])[0]
                
                self.logger.debug(f"Header: magic={magic.hex()}, length={body_length}, req_id={request_id}")
                
                # Read body
                body = await reader.readexactly(body_length) if body_length > 0 else b''
                
                # Process message and generate response
                response = await self.process_message(request_id, body)
                if response:
                    writer.write(response)
                    await writer.drain()
                    
        except asyncio.IncompleteReadError:
            self.logger.info("Client disconnected")
        except Exception as e:
            self.logger.error(f"Error handling client: {e}")
        finally:
            writer.close()
            await writer.wait_closed()
            
    async def process_message(self, request_id: int, body: bytes) -> Optional[bytes]:
        """Process a message and generate appropriate response"""
        if not body:
            return None
            
        # Check if it's a JSON message
        if body[0] == 0x7b:  # '{'
            return self.process_json_message(request_id, body)
        else:
            return self.process_binary_message(request_id, body)
            
    def process_json_message(self, request_id: int, body: bytes) -> bytes:
        """Process JSON messages (auth, config requests)"""
        try:
            data = json.loads(body.decode('utf-8'))
            message_type = data.get('message')
            
            self.logger.info(f"JSON message: {message_type}")
            
            if message_type == 'access':
                # Authentication
                token = data.get('user-token')
                if token == self.mock_token:
                    response_data = {
                        "response-code": 200,
                        "message-type": "response"
                    }
                else:
                    response_data = {
                        "response-code": 401,
                        "message-type": "response"
                    }
                    
            elif message_type == 'get-configuration':
                # Configuration request
                response_data = self.mock_config
                response_data["message-type"] = "response"
                
            elif message_type == 'server-info':
                # Server info request
                response_data = {
                    "server-version": "1.0.0",
                    "message-type": "response"
                }
            else:
                response_data = {
                    "error": "Unknown message type",
                    "message-type": "response"
                }
                
            # Create response
            json_bytes = json.dumps(response_data, separators=(',', ':')).encode('utf-8')
            header = self.create_header(len(json_bytes), request_id)
            return header + json_bytes
            
        except Exception as e:
            self.logger.error(f"Error processing JSON: {e}")
            return b''
            
    def process_binary_message(self, request_id: int, body: bytes) -> bytes:
        """Process binary messages (channel operations, door commands)"""
        if len(body) < 4:
            return b''
            
        msg_type = struct.unpack('<H', body[0:2])[0]
        sequence = struct.unpack('<H', body[2:4])[0]
        
        self.logger.info(f"Binary message: type=0x{msg_type:04x}, seq={sequence}")
        
        if msg_type == 0xabcd:  # COMMAND - open channel
            # Extract channel name
            if len(body) > 8:
                channel_size = struct.unpack('<I', body[4:8])[0]
                if len(body) >= 8 + channel_size:
                    channel_end = 8 + channel_size - 3  # Minus requestId and null
                    channel_name = body[8:channel_end].decode('ascii')
                    self.logger.info(f"Opening channel: {channel_name}")
                    
                    # Store channel
                    self.channels[request_id] = channel_name
                    self.sequence_counters[request_id] = 2
                    
                    # Send acknowledgment
                    response_body = struct.pack('<HH', 0xabcd, 2)  # Echo with seq+1
                    header = self.create_header(len(response_body), 0)
                    return header + response_body
                    
        elif msg_type == 0x01ef:  # END - close channel
            if request_id in self.channels:
                channel = self.channels.pop(request_id)
                self.logger.info(f"Closing channel: {channel}")
                seq = self.sequence_counters.pop(request_id, sequence) + 1
                
                # Send acknowledgment
                response_body = struct.pack('<HH', 0x01ef, seq)
                header = self.create_header(len(response_body), 0)
                return header + response_body
                
        elif msg_type in [0x18c0, 0x1800, 0x1820, 0xc018]:  # Door operations
            self.logger.info(f"Door operation: 0x{msg_type:04x}")
            # Acknowledge door operations with simple response
            response_body = struct.pack('<HH', msg_type, sequence)
            header = self.create_header(len(response_body), request_id)
            return header + response_body
            
        return b''
        
    def create_header(self, body_length: int, request_id: int) -> bytes:
        """Create 8-byte message header"""
        header = bytearray(8)
        header[0:2] = b'\x00\x06'  # Magic
        header[2:4] = struct.pack('<H', body_length)
        header[4:6] = struct.pack('<H', request_id)
        header[6:8] = b'\x00\x00'  # Padding
        return bytes(header)
        
    async def start(self):
        """Start the mock server"""
        server = await asyncio.start_server(
            self.handle_client, self.host, self.port
        )
        
        addr = server.sockets[0].getsockname()
        self.logger.info(f'Mock Comelit server running on {addr[0]}:{addr[1]}')
        
        async with server:
            await server.serve_forever()


async def main():
    """Run the mock server"""
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] %(levelname)s: %(message)s'
    )
    
    server = MockComelitServer()
    
    print("Mock Comelit ICONA Bridge Server")
    print("=================================")
    print(f"Listening on {server.host}:{server.port}")
    print(f"Mock token: {server.mock_token}")
    print("\nPress Ctrl+C to stop")
    
    try:
        await server.start()
    except KeyboardInterrupt:
        print("\nShutting down...")


if __name__ == "__main__":
    asyncio.run(main())