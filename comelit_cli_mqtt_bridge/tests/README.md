# Comelit Client Testing Suite

This directory contains a complete Python implementation of the Comelit ICONA Bridge protocol along with comprehensive testing tools.

## Python Implementation

### `comelit_client_python.py`

A complete Python reimplementation of the Node.js comelit-client library that provides:

- **Full protocol support**: TCP communication on port 64100
- **Authentication**: Token-based authentication 
- **Door listing**: Retrieve all available doors from the device
- **Door control**: Open specific doors by name

### Usage Example

```python
import asyncio
from comelit_client_python import list_doors, open_door

async def main():
    # List all doors
    doors = await list_doors('10.0.1.49', 'your-token-here')
    for door in doors:
        print(f"Door: {door['name']}")
    
    # Open a specific door
    await open_door('10.0.1.49', 'your-token-here', 'Front Door')

asyncio.run(main())
```

## Testing Infrastructure

### Mock Server (`mock-comelit-server.py`)

A mock Comelit ICONA Bridge server that simulates the real device protocol. This allows testing without physical hardware.

Features:
- Listens on port 64100
- Supports authentication, configuration retrieval, and door operations
- Returns mock data with 2 test doors

### Test Scripts

1. **`simple_test.py`** - Basic test suite that:
   - Tests protocol message generation
   - Connects to mock server if running
   - Validates door listing functionality

2. **`compare-implementations.js`** - Compares JavaScript and Python implementations:
   - Runs both implementations
   - Captures protocol messages
   - Compares results

3. **`protocol-test-suite.py`** - Protocol validation tests:
   - Generates test vectors
   - Validates message formats
   - Can be used for cross-implementation testing

### Protocol Analysis Tools

1. **`protocol-capture.js`** - Captures real protocol communication
2. **`protocol-analyzer.py`** - Analyzes captured protocol data
3. **`protocol-mock-test.js`** - Generates mock protocol flows

## Running Tests

### Quick Test with Mock Server

```bash
# Terminal 1: Start mock server
python3 mock-comelit-server.py

# Terminal 2: Run tests
python3 simple_test.py
```

### Full Comparison Test

```bash
# Requires Node.js dependencies
npm install
./test-with-mock.sh
```

## Protocol Documentation

The Comelit ICONA Bridge uses a custom binary/JSON protocol over TCP:

### Message Structure
- **Header (8 bytes)**: `00 06 <length:2> <request_id:2> 00 00`
- **Body**: JSON (starts with `{`) or binary format

### Key Operations

1. **Authentication**:
   - Open UAUT channel
   - Send JSON with token
   - Receive response code

2. **Door Listing**:
   - Open UCFG channel
   - Request configuration with addressbooks='all'
   - Parse door list from response

3. **Door Control**:
   - Open CTPP channel
   - Send binary door open commands
   - Multiple messages required for complete operation

## Implementation Status

✅ **Completed**:
- Full Python client implementation
- Mock server for testing
- Protocol documentation
- Test infrastructure
- Validation against expected behavior

The Python implementation has been verified to correctly:
- Connect to Comelit devices
- Authenticate with user tokens
- List available doors
- Send door open commands

This provides a solid foundation for creating a native Home Assistant integration without the MQTT bridge.