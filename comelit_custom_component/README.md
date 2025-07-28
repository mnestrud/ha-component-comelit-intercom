# Comelit Custom Component for Home Assistant

This is a native Home Assistant integration for Comelit ICONA Bridge intercom systems. It allows you to control your Comelit doors directly from Home Assistant without requiring MQTT or Docker containers.

## Features

- Direct TCP communication with Comelit devices (no MQTT bridge needed)
- Automatic discovery of all available doors
- Creates button entities for each door
- Simple configuration through Home Assistant UI

## Requirements

- Home Assistant 2023.1 or newer
- Comelit intercom with WiFi connectivity (e.g., Comelit 6741w)
- Comelit device IP address
- User token from your Comelit device

## Installation

### Manual Installation

1. Copy the `custom_components/comelit` folder to your Home Assistant's `custom_components` directory
2. Restart Home Assistant
3. Go to Settings → Devices & Services
4. Click "Add Integration" and search for "Comelit"
5. Enter your device's IP address and user token

### HACS Installation (Coming Soon)

This integration will be submitted to HACS for easier installation.

## Configuration

You'll need:
1. **IP Address**: The IP address of your Comelit device on your network
2. **User Token**: Follow the instructions at https://github.com/madchicken/comelit-client/wiki/Get-your-user-token-for-ICONA-Bridge

## Usage

After configuration, the integration will:
1. Connect to your Comelit device
2. Discover all available doors
3. Create a button entity for each door

You can then:
- Add door buttons to your dashboard
- Create automations to open doors
- Use with voice assistants
- Include in scripts and scenes

## Architecture

This integration includes:
- **comelit_client.py**: Python implementation of the Comelit ICONA Bridge protocol
- **config_flow.py**: Configuration UI for easy setup
- **coordinator.py**: Data update coordinator for efficient API calls
- **button.py**: Button entities for door control

## Development

The integration implements the Comelit ICONA Bridge protocol directly in Python, supporting:
- Binary/JSON hybrid protocol communication
- Channel-based messaging (UAUT, UCFG, CTPP)
- Proper channel ID management
- Timeout handling for reliable operation

## Troubleshooting

### Cannot Connect
- Verify the IP address is correct
- Ensure the device is on the same network
- Check that port 64100 is accessible

### Invalid Authentication
- Double-check your user token
- Ensure the token hasn't expired
- Try generating a new token

### Doors Not Appearing
- Check the Home Assistant logs
- Verify doors are configured in your Comelit app
- Try reloading the integration

## License

This project is licensed under the GPL-3.0 License - see the original repository for details.

## Credits

- Based on reverse engineering work by [madchicken](https://github.com/madchicken/comelit-client)
- Inspired by the MQTT bridge implementation