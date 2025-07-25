#!/usr/bin/env python3
"""
Protocol analyzer for Comelit ICONA Bridge protocol captures.
This script helps understand the binary protocol for future Python implementation.
"""

import json
import sys
from typing import Dict, List, Tuple
import struct
from dataclasses import dataclass
from enum import IntEnum


class MessageType(IntEnum):
    """Message types observed in the protocol"""
    COMMAND = 43981  # 0xabcd
    END = 495        # 0x01ef
    OPEN_DOOR_INIT = 6336  # 0x18c0
    OPEN_DOOR = 6144       # 0x1800
    OPEN_DOOR_CONFIRM = 6176  # 0x1820


class Channel:
    """Channel names used in the protocol"""
    UAUT = "UAUT"  # Authentication
    UCFG = "UCFG"  # Configuration
    INFO = "INFO"  # Server info
    CTPP = "CTPP"  # Control operations
    PUSH = "PUSH"  # Push notifications


@dataclass
class ProtocolMessage:
    """Represents a parsed protocol message"""
    operation: str  # WRITE or READ
    timestamp: int
    raw_bytes: str
    parsed: Dict
    
    def __str__(self):
        return f"{self.operation} @ {self.timestamp}ms:\n  Raw: {self.raw_bytes}\n  Parsed: {json.dumps(self.parsed, indent=2)}"


class ProtocolAnalyzer:
    def __init__(self, capture_file: str):
        with open(capture_file, 'r') as f:
            self.capture = json.load(f)
        self.messages = []
        
    def analyze(self):
        """Analyze all captured messages"""
        for entry in self.capture:
            if entry['level'] in ['WRITE', 'READ'] and 'bytes' in entry:
                msg = self._parse_message(entry)
                if msg:
                    self.messages.append(msg)
                    
    def _parse_message(self, entry: Dict) -> ProtocolMessage:
        """Parse a single message entry"""
        raw_bytes = entry['bytes']
        byte_array = bytes.fromhex(raw_bytes.replace(' ', ''))
        
        parsed = {}
        
        # All messages start with 8-byte header
        if len(byte_array) >= 8:
            # Header format: 00 06 XX XX RR RR 00 00
            # Where XX XX is the body length (little endian)
            # And RR RR is the request ID (little endian)
            header = byte_array[:8]
            parsed['header'] = {
                'magic': header[0:2].hex(),
                'body_length': struct.unpack('<H', header[2:4])[0],
                'request_id': struct.unpack('<H', header[4:6])[0],
                'padding': header[6:8].hex()
            }
            
            if len(byte_array) > 8:
                body = byte_array[8:]
                parsed['body'] = self._parse_body(body, parsed['header']['request_id'])
                
        return ProtocolMessage(
            operation=entry['level'],
            timestamp=entry['timestamp'],
            raw_bytes=raw_bytes,
            parsed=parsed
        )
        
    def _parse_body(self, body: bytes, request_id: int) -> Dict:
        """Parse message body based on content"""
        result = {}
        
        # Check if it's JSON (starts with '{')
        if body[0] == 0x7b:
            try:
                json_str = body.decode('utf-8')
                result['type'] = 'json'
                result['content'] = json.loads(json_str)
            except:
                result['type'] = 'json_error'
                result['raw'] = body.hex()
        else:
            # Binary message
            result['type'] = 'binary'
            
            # Try to parse known binary formats
            if len(body) >= 4:
                # First 4 bytes often contain message type info
                msg_type = struct.unpack('<H', body[0:2])[0]
                sequence = struct.unpack('<H', body[2:4])[0]
                
                result['message_type'] = f"0x{msg_type:04x} ({msg_type})"
                result['sequence'] = sequence
                
                # Known message types
                if msg_type == MessageType.COMMAND:
                    result['message_name'] = 'COMMAND'
                    if len(body) > 4:
                        # Next 4 bytes are sub-size
                        sub_size = struct.unpack('<I', body[4:8])[0]
                        result['sub_size'] = sub_size
                        # Extract channel name and other data
                        if len(body) > 8:
                            result['data'] = self._extract_strings(body[8:])
                            
                elif msg_type == MessageType.END:
                    result['message_name'] = 'END'
                    
                elif msg_type in [0xc018, 0x0018, 0x2018]:  # Door operations
                    result['message_name'] = 'DOOR_OPERATION'
                    result['subtype'] = body[1]
                    if len(body) > 4:
                        result['data'] = self._extract_strings(body[4:])
                        
                else:
                    # Unknown binary format, extract strings
                    result['strings'] = self._extract_strings(body)
                    
        return result
        
    def _extract_strings(self, data: bytes) -> List[str]:
        """Extract null-terminated strings from binary data"""
        strings = []
        current = []
        
        for byte in data:
            if byte == 0:
                if current:
                    try:
                        strings.append(bytes(current).decode('ascii'))
                    except:
                        strings.append(f"<binary: {bytes(current).hex()}>")
                    current = []
            elif 32 <= byte <= 126:  # Printable ASCII
                current.append(byte)
            else:
                if current:
                    try:
                        strings.append(bytes(current).decode('ascii'))
                    except:
                        strings.append(f"<binary: {bytes(current).hex()}>")
                    current = []
                    
        return strings
        
    def print_analysis(self):
        """Print analysis results"""
        print(f"Analyzed {len(self.messages)} messages\n")
        
        # Group by operation type
        writes = [m for m in self.messages if m.operation == 'WRITE']
        reads = [m for m in self.messages if m.operation == 'READ']
        
        print(f"Writes: {len(writes)}, Reads: {len(reads)}\n")
        
        # Print message flow
        print("Message Flow:")
        print("-" * 80)
        
        for msg in self.messages:
            direction = "→" if msg.operation == "WRITE" else "←"
            print(f"{msg.timestamp:6d}ms {direction} ", end="")
            
            if 'body' in msg.parsed:
                body = msg.parsed['body']
                if body['type'] == 'json':
                    content = body['content']
                    msg_type = content.get('message', 'unknown')
                    print(f"JSON: {msg_type}")
                    if msg_type == 'access':
                        print(f"          Token: {content.get('user-token', '')[:16]}...")
                    elif msg_type == 'get-configuration':
                        print(f"          Addressbooks: {content.get('addressbooks', '')}")
                elif body['type'] == 'binary':
                    print(f"BINARY: {body.get('message_name', 'UNKNOWN')}")
                    if 'data' in body:
                        print(f"          Data: {body['data']}")
            else:
                print("HEADER ONLY")
                
    def export_protocol_spec(self, output_file: str):
        """Export protocol specification for Python implementation"""
        spec = {
            'header_format': {
                'size': 8,
                'structure': [
                    {'name': 'magic', 'offset': 0, 'size': 2, 'value': '0x0006'},
                    {'name': 'body_length', 'offset': 2, 'size': 2, 'type': 'uint16_le'},
                    {'name': 'request_id', 'offset': 4, 'size': 2, 'type': 'uint16_le'},
                    {'name': 'padding', 'offset': 6, 'size': 2, 'value': '0x0000'}
                ]
            },
            'message_types': {
                'COMMAND': 0xabcd,
                'END': 0x01ef,
                'OPEN_DOOR_INIT': 0x18c0,
                'OPEN_DOOR': 0x1800,
                'OPEN_DOOR_CONFIRM': 0x1820
            },
            'channels': {
                'UAUT': 'Authentication',
                'UCFG': 'Configuration', 
                'INFO': 'Server info',
                'CTPP': 'Control operations',
                'PUSH': 'Push notifications'
            },
            'observed_sequences': []
        }
        
        # Extract observed message sequences
        for msg in self.messages:
            if 'body' in msg.parsed:
                seq_entry = {
                    'timestamp': msg.timestamp,
                    'direction': msg.operation,
                    'type': msg.parsed['body']['type']
                }
                
                if msg.parsed['body']['type'] == 'json':
                    seq_entry['message'] = msg.parsed['body']['content'].get('message', 'unknown')
                elif msg.parsed['body']['type'] == 'binary':
                    seq_entry['message'] = msg.parsed['body'].get('message_name', 'unknown')
                    
                spec['observed_sequences'].append(seq_entry)
                
        with open(output_file, 'w') as f:
            json.dump(spec, f, indent=2)
            
        print(f"\nProtocol specification exported to: {output_file}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python protocol-analyzer.py <capture-file.json>")
        sys.exit(1)
        
    analyzer = ProtocolAnalyzer(sys.argv[1])
    analyzer.analyze()
    analyzer.print_analysis()
    
    # Export protocol spec
    output_file = sys.argv[1].replace('.json', '-spec.json')
    analyzer.export_protocol_spec(output_file)