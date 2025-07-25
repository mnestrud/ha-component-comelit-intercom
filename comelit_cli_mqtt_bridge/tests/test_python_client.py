#!/usr/bin/env python3
"""
Test the Python Comelit client implementation
"""

import asyncio
import subprocess
import time
import os
import signal


async def test_client():
    """Test the Python client against mock server"""
    # Import the client
    from comelit_client_python import list_doors, open_door
    
    try:
        print("Testing door listing...")
        doors = await list_doors('127.0.0.1', '9943a85362467c53586e3553d34f8a8d')
        print(f"Found {len(doors)} doors:")
        for door in doors:
            print(f"  - {door.get('name')} (address: {door.get('apt-address')}, index: {door.get('output-index')})")
        
        if doors:
            print(f"\nTesting door opening: {doors[0].get('name')}...")
            result = await open_door('127.0.0.1', '9943a85362467c53586e3553d34f8a8d', doors[0].get('name'))
            print(f"Door open result: {result}")
            
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run test with mock server"""
    print("Starting mock server...")
    
    # Start mock server
    server_proc = subprocess.Popen(
        ['python3', 'mock-comelit-server.py'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Wait for server to start
    time.sleep(2)
    
    try:
        print("\nRunning client tests...")
        print("-" * 40)
        
        # Run the test
        success = asyncio.run(test_client())
        
        if success:
            print("\n✓ All tests passed!")
        else:
            print("\n✗ Tests failed!")
            
    finally:
        # Stop server
        print("\nStopping mock server...")
        server_proc.terminate()
        server_proc.wait(timeout=5)
        

if __name__ == "__main__":
    main()