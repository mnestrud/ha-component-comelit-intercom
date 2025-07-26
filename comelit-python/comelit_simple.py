#!/usr/bin/env python3
"""
Simplified Comelit CLI for testing basic connectivity.

This is a minimal implementation focusing on the core protocol.
"""

import asyncio
import struct
import json
import os
import sys
import logging

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def test_connection():
    """Test basic connection and authentication."""
    host = os.environ.get('COMELIT_IP', '10.0.1.49')
    token = os.environ.get('COMELIT_TOKEN', '9943a85362467c53586e3553d34f8a8d')
    port = 64100
    
    logger.info(f"Connecting to {host}:{port}")
    
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port),
            timeout=10.0
        )
        logger.info("Connected!")
        
        # Step 1: Open UAUT channel
        logger.info("Opening UAUT channel...")
        request_id = 8761
        
        # Build channel open body
        body = struct.pack('<HH', 0xabcd, 1)  # Protocol version, operation
        body += struct.pack('<I', 7)  # Channel type (UAUT)
        body += b'UAUT\x00'  # Channel name
        body += struct.pack('<H', request_id)  # Request ID
        body += b'\x00'  # Padding
        
        # Build header
        header = b'\x00\x06'  # Magic bytes
        header += struct.pack('<H', len(body))  # Body length
        header += b'\x00\x00\x00\x00'  # Request ID in header is 0
        
        # Send packet
        packet = header + body
        logger.debug(f"Sending: {packet.hex()}")
        writer.write(packet)
        await writer.drain()
        
        # Read response
        resp_header = await reader.readexactly(8)
        logger.debug(f"Response header: {resp_header.hex()}")
        
        body_len = struct.unpack('<H', resp_header[2:4])[0]
        if body_len > 0:
            resp_body = await reader.readexactly(body_len)
            logger.debug(f"Response body: {resp_body.hex()}")
            logger.info("UAUT channel opened")
        
        # Step 2: Send authentication
        logger.info("Sending authentication...")
        auth_data = {
            "message": "access",
            "user-token": token,
            "message-type": "request",
            "message-id": 1
        }
        
        auth_json = json.dumps(auth_data, separators=(',', ':'))
        auth_body = auth_json.encode('ascii')
        
        # For auth, we send JSON directly after channel is open
        auth_header = b'\x00\x06'
        auth_header += struct.pack('<H', len(auth_body))
        auth_header += struct.pack('<H', request_id)  # Use same request ID
        auth_header += b'\x00\x00'
        
        auth_packet = auth_header + auth_body
        logger.debug(f"Sending auth: {auth_packet.hex()}")
        writer.write(auth_packet)
        await writer.drain()
        
        # Wait for auth response
        logger.info("Waiting for auth response...")
        try:
            auth_resp_header = await asyncio.wait_for(reader.readexactly(8), timeout=5.0)
            logger.debug(f"Auth response header: {auth_resp_header.hex()}")
            
            auth_body_len = struct.unpack('<H', auth_resp_header[2:4])[0]
            if auth_body_len > 0:
                auth_resp_body = await reader.readexactly(auth_body_len)
                logger.debug(f"Auth response body: {auth_resp_body.hex()}")
                
                # Try to parse as JSON
                try:
                    auth_response = json.loads(auth_resp_body.decode('utf-8'))
                    logger.info(f"Auth response JSON: {auth_response}")
                except:
                    logger.info(f"Auth response (raw): {auth_resp_body}")
                    
        except asyncio.TimeoutError:
            logger.error("Authentication timeout - no response from device")
            
        # Step 3: Try to list doors
        logger.info("Opening UCFG channel...")
        request_id += 1
        
        # Build UCFG channel open body
        body = struct.pack('<HH', 0xabcd, 1)  # Protocol version, operation
        body += struct.pack('<I', 2)  # Channel type (UCFG)
        body += b'UCFG\x00'  # Channel name
        body += struct.pack('<H', request_id)  # Request ID
        body += b'\x00'  # Padding
        
        # Build header
        header = b'\x00\x06'  # Magic bytes
        header += struct.pack('<H', len(body))  # Body length
        header += b'\x00\x00\x00\x00'  # Request ID in header is 0
        
        # Send packet
        packet = header + body
        logger.debug(f"Sending: {packet.hex()}")
        writer.write(packet)
        await writer.drain()
        
        # Read response
        try:
            resp_header = await asyncio.wait_for(reader.readexactly(8), timeout=5.0)
            logger.debug(f"UCFG response header: {resp_header.hex()}")
            
            body_len = struct.unpack('<H', resp_header[2:4])[0]
            if body_len > 0:
                resp_body = await reader.readexactly(body_len)
                logger.debug(f"UCFG response body: {resp_body.hex()}")
                logger.info("UCFG channel opened")
                
            # Send list request
            logger.info("Sending list request...")
            list_data = {
                "message": "list",
                "class": "opener",
                "message-type": "request",
                "message-id": 2
            }
            
            list_json = json.dumps(list_data, separators=(',', ':'))
            list_body = list_json.encode('ascii')
            
            list_header = b'\x00\x06'
            list_header += struct.pack('<H', len(list_body))
            list_header += struct.pack('<H', request_id)
            list_header += b'\x00\x00'
            
            list_packet = list_header + list_body
            logger.debug(f"Sending list: {list_packet.hex()}")
            writer.write(list_packet)
            await writer.drain()
            
            # Read list response
            list_resp_header = await asyncio.wait_for(reader.readexactly(8), timeout=5.0)
            logger.debug(f"List response header: {list_resp_header.hex()}")
            
            list_body_len = struct.unpack('<H', list_resp_header[2:4])[0]
            if list_body_len > 0:
                list_resp_body = await reader.readexactly(list_body_len)
                logger.debug(f"List response body: {list_resp_body.hex()}")
                
                try:
                    list_response = json.loads(list_resp_body.decode('utf-8'))
                    logger.info(f"List response JSON: {list_response}")
                    
                    if "response-data" in list_response:
                        doors = list_response["response-data"].get("elements", [])
                        logger.info(f"Found {len(doors)} doors:")
                        for door in doors:
                            logger.info(f"  - {door['name']} (ID: {door['id']})")
                except:
                    logger.info(f"List response (raw): {list_resp_body}")
                    
        except asyncio.TimeoutError:
            logger.error("Timeout waiting for UCFG/list response")
        
        # Close connection
        writer.close()
        await writer.wait_closed()
        logger.info("Connection closed")
        
    except Exception as e:
        logger.error(f"Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_connection())