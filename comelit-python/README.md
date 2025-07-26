# Comelit Python CLI

A simple Python command-line interface for controlling Comelit ICONA Bridge devices. This implementation uses only Python's built-in `asyncio` library, making it compatible with Home Assistant's architecture.

## Features

- Connect to Comelit ICONA Bridge devices
- Authenticate using device token
- List available doors
- Open doors remotely
- Interactive command-line interface

## Requirements

- Python 3.9 or higher
- No external dependencies (uses only built-in libraries)

## Usage

1. Set environment variables:
```bash
export COMELIT_IP=10.0.1.49
export COMELIT_TOKEN=your_token_here
```

2. Run the CLI:
```bash
python comelit_cli.py
```

3. Use the interactive menu to:
   - View available doors
   - Open a specific door
   - Refresh the door list
   - Quit the application

## Protocol Details

This implementation follows the Comelit ICONA Bridge binary protocol:

- **Port**: 64100 (TCP)
- **Header**: 8 bytes
  - Bytes 0-1: Magic bytes `0x00 0x06`
  - Bytes 2-3: Body length (little-endian)
  - Bytes 4-5: Request ID (little-endian)
  - Bytes 6-7: Padding `0x00 0x00`

- **Channels**:
  - UAUT (7): Authentication channel
  - UCFG (2): Configuration channel
  - CTPP (16): Control channel
  - CSPB (17): Status channel

- **Message Flow**:
  1. Open UAUT channel
  2. Authenticate with token
  3. Open UCFG channel
  4. List available doors
  5. Open CTPP channel
  6. Send door open command

## Home Assistant Integration

This CLI serves as the foundation for a Home Assistant custom component. The code structure is designed to be easily adapted into a HA integration:

- Uses `asyncio` for async operations (HA requirement)
- No external dependencies beyond Python standard library
- Clean separation of protocol logic
- Proper error handling and logging

## Debugging

Set logging level to DEBUG for detailed protocol information:
```python
logging.basicConfig(level=logging.DEBUG)
```

This will show:
- Raw packet data (hex)
- JSON message contents
- Connection status
- Protocol flow