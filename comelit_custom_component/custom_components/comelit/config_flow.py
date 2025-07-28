"""Config flow for Comelit integration."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_TOKEN
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .comelit_client import IconaBridgeClient
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_TOKEN): str,
    }
)


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect."""
    _LOGGER.info("Starting validation for Comelit device at %s", data[CONF_HOST])
    client = IconaBridgeClient(data[CONF_HOST])
    
    try:
        # Add timeout to prevent hanging
        _LOGGER.info("Attempting to connect to Comelit device at %s", data[CONF_HOST])
        await asyncio.wait_for(client.connect(), timeout=10.0)
        _LOGGER.info("Successfully connected to device")
    except asyncio.TimeoutError:
        _LOGGER.error("Connection timeout to device at %s", data[CONF_HOST])
        raise CannotConnect("Connection timeout - device not responding")
    except OSError as err:
        # Special handling for macOS "No route to host" error
        if err.errno == 65:  # EHOSTUNREACH on macOS
            _LOGGER.error("Cannot reach device at %s:%s - possible firewall or wrong port", 
                         data[CONF_HOST], 64100)
            raise CannotConnect("Cannot reach device - check firewall settings")
        _LOGGER.error("Network error connecting to device: %s", err)
        raise CannotConnect(f"Network error: {err}")
    except Exception as err:
        _LOGGER.error("Cannot connect to device: %s", err)
        raise CannotConnect from err
        
    try:
        _LOGGER.info("Authenticating with device")
        auth_code = await asyncio.wait_for(
            client.authenticate(data[CONF_TOKEN]), 
            timeout=15.0
        )
        
        if auth_code != 200:
            _LOGGER.error("Authentication failed with code %s", auth_code)
            raise InvalidAuth(f"Authentication failed with code {auth_code}")
            
        _LOGGER.info("Authentication successful, getting configuration")
        
        # Get configuration to verify everything works
        config = await asyncio.wait_for(
            client.get_config('all'),
            timeout=15.0
        )
        
        if not config:
            raise CannotConnect("Failed to get configuration")
            
        _LOGGER.info("Configuration retrieved successfully")
        await client.shutdown()
        
        # Return info that you want to store in the config entry
        return {"title": f"Comelit ({data[CONF_HOST]})"}
        
    except asyncio.TimeoutError as e:
        _LOGGER.error("Operation timeout while communicating with device: %s", e)
        _LOGGER.error("This could be during connect, auth, or config retrieval")
        await client.shutdown()
        raise CannotConnect("Device communication timeout")
    except InvalidAuth:
        await client.shutdown()
        raise
    except CannotConnect:
        await client.shutdown()
        raise
    except Exception as err:
        _LOGGER.exception("Unexpected error during validation: %s", err)
        await client.shutdown()
        raise CannotConnect(f"Unexpected error: {err}")


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Comelit."""
    
    VERSION = 1
    
    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA
            )
            
        errors = {}
        
        try:
            info = await validate_input(self.hass, user_input)
        except CannotConnect:
            errors["base"] = "cannot_connect"
        except InvalidAuth:
            errors["base"] = "invalid_auth"
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception")
            errors["base"] = "unknown"
        else:
            # Check if already configured
            await self.async_set_unique_id(user_input[CONF_HOST])
            self._abort_if_unique_id_configured()
            
            return self.async_create_entry(title=info["title"], data=user_input)
            
        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )