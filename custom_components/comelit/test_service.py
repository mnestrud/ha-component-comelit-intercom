"""Test service for Comelit connection."""

import logging
from homeassistant.core import HomeAssistant, ServiceCall

from .comelit_client import IconaBridgeClient

_LOGGER = logging.getLogger(__name__)

async def async_setup_test_service(hass: HomeAssistant):
    """Set up test service."""
    
    async def handle_test_connection(call: ServiceCall):
        """Handle test connection service."""
        ip = call.data.get("ip")
        token = call.data.get("token")
        
        if not ip:
            _LOGGER.error("IP address is required")
            hass.states.async_set(
                "comelit.test_result",
                "error",
                {"message": "IP address is required"}
            )
            return
            
        if not token:
            _LOGGER.error("Token is required")
            hass.states.async_set(
                "comelit.test_result",
                "error",
                {"message": "Token is required"}
            )
            return
        
        _LOGGER.info(f"Testing connection to {ip}")
        
        client = IconaBridgeClient(ip, token)
        try:
            await client.connect()
            _LOGGER.info("Connected successfully!")
            
            if await client.authenticate():
                _LOGGER.info("Authenticated successfully!")
                doors = await client.list_doors()
                _LOGGER.info(f"Found {len(doors)} doors: {doors}")
                
                hass.states.async_set(
                    "comelit.test_result",
                    "success",
                    {"doors": doors, "message": f"Found {len(doors)} doors"}
                )
            else:
                _LOGGER.error("Authentication failed")
                hass.states.async_set(
                    "comelit.test_result",
                    "auth_failed",
                    {"message": "Authentication failed"}
                )
                
            await client.shutdown()
            
        except Exception as e:
            _LOGGER.error(f"Connection failed: {e}")
            hass.states.async_set(
                "comelit.test_result",
                "connection_failed",
                {"message": str(e)}
            )
    
    hass.services.async_register(
        "comelit",
        "test_connection",
        handle_test_connection,
        schema=None
    )
    
    _LOGGER.info("Test service registered")