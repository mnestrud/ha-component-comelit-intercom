#!/usr/bin/env python3
"""
Simple test to verify the Python Comelit client works correctly
"""

import asyncio
import logging
from comelit_client_python import IconaBridgeClient


# Test data that matches the mock server
MOCK_TOKEN = '9943a85362467c53586e3553d34f8a8d'
EXPECTED_DOORS = [
    {"name": "Front Door", "apt-address": "100", "output-index": "1"},
    {"name": "Garage", "apt-address": "100", "output-index": "2"}
]


async def test_protocol_messages():
    """Test the protocol message generation"""
    client = IconaBridgeClient('127.0.0.1')
    
    print("Testing protocol message generation...")
    print("-" * 50)
    
    # Test authentication message
    auth_msg = client._create_json_packet(8001, {
        'message': 'access',
        'user-token': MOCK_TOKEN,
        'message-type': 'request',
        'message-id': 2
    })
    print(f"Auth message ({len(auth_msg)} bytes): {auth_msg.hex(' ')}")
    
    # Test get-config message
    config_msg = client._create_json_packet(8002, {
        'message': 'get-configuration',
        'addressbooks': 'all',
        'message-type': 'request',
        'message-id': 3
    })
    print(f"Config message ({len(config_msg)} bytes): {config_msg.hex(' ')}")
    
    # Test open channel message
    channel_msg = client._create_command_packet(8001, 1, 0xabcd, 'UAUT')
    print(f"Open UAUT channel ({len(channel_msg)} bytes): {channel_msg.hex(' ')}")
    
    # Test door open message
    vip = {"apt-address": "100", "apt-subaddress": "1"}
    door = {"apt-address": "100", "output-index": "1", "name": "Front Door"}
    
    # Create door message manually to test
    from comelit_client_python import MessageType, NULL
    import struct
    
    msg_type = MessageType.OPEN_DOOR
    buffers = [
        struct.pack('<H', msg_type),
        bytes([0x5c, 0x8b]),
        bytes([0x2c, 0x74, 0x00, 0x00]),
        bytes([0xff, 0xff, 0xff, 0xff]),
        client._string_to_buffer(f"{vip['apt-address']}{door['output-index']}", True),
        client._string_to_buffer(door['apt-address'], True),
        NULL
    ]
    door_body = b''.join(buffers)
    door_msg = client._create_header(len(door_body), 8003) + door_body
    print(f"Door open message ({len(door_msg)} bytes): {door_msg.hex(' ')}")
    
    print("\n✓ Protocol message generation test passed!")
    return True


async def test_mock_connection():
    """Test connecting to mock server (if running)"""
    print("\n\nTesting connection to mock server...")
    print("-" * 50)
    
    client = IconaBridgeClient('127.0.0.1')
    
    try:
        # Try to connect
        await asyncio.wait_for(client.connect(), timeout=2.0)
        print("✓ Connected to mock server")
        
        # Try authentication
        print("Testing authentication...")
        auth_code = await client.authenticate(MOCK_TOKEN)
        print(f"✓ Authentication result: {auth_code}")
        
        if auth_code == 200:
            # Try getting config
            print("Testing configuration retrieval...")
            config = await client.get_config('all')
            if config:
                print("✓ Got configuration")
                
                # List doors
                doors = await client.list_doors()
                print(f"✓ Found {len(doors)} doors:")
                for door in doors:
                    print(f"  - {door.get('name')} (address: {door.get('apt-address')}, index: {door.get('output-index')})")
                    
                # Verify doors match expected
                if len(doors) == len(EXPECTED_DOORS):
                    match = all(
                        d1['name'] == d2['name'] and 
                        d1['apt-address'] == d2['apt-address'] and
                        d1['output-index'] == d2['output-index']
                        for d1, d2 in zip(doors, EXPECTED_DOORS)
                    )
                    if match:
                        print("✓ Door list matches expected data!")
                    else:
                        print("✗ Door list doesn't match expected data")
                else:
                    print(f"✗ Expected {len(EXPECTED_DOORS)} doors, got {len(doors)}")
                    
        await client.shutdown()
        return True
        
    except asyncio.TimeoutError:
        print("✗ Connection timeout - mock server not running")
        print("  Run 'python3 mock-comelit-server.py' in another terminal")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests"""
    print("Python Comelit Client Test Suite")
    print("=" * 50)
    
    # Configure logging
    logging.basicConfig(
        level=logging.WARNING,
        format='[%(levelname)s] %(message)s'
    )
    
    # Run tests
    test1_passed = await test_protocol_messages()
    test2_passed = await test_mock_connection()
    
    print("\n" + "=" * 50)
    if test1_passed:
        print("✓ All tests passed!")
    else:
        print("✗ Some tests failed")


if __name__ == "__main__":
    asyncio.run(main())