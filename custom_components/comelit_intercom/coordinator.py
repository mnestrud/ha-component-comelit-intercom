"""DataUpdateCoordinator for Comelit."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .comelit_client import IconaBridgeClient
from .const import CONF_HOST, CONF_TOKEN, DOMAIN, UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)


class ComelitDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Class to manage fetching Comelit data."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize."""
        self.entry = entry
        self.host = entry.data[CONF_HOST]
        self.token = entry.data[CONF_TOKEN]
        self.vip_config: dict[str, Any] = {}

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=UPDATE_INTERVAL),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from Comelit."""
        client = IconaBridgeClient(self.host)

        try:
            await client.connect()

            # Authenticate
            auth_code = await client.authenticate(self.token)
            if auth_code != 200:
                raise ConfigEntryAuthFailed(
                    f"Authentication failed with code {auth_code}"
                )

            # Get configuration
            config = await client.get_config("all")
            if not config or "vip" not in config:
                raise UpdateFailed("Failed to get configuration from device")

            self.vip_config = config["vip"]
            doors = self.vip_config.get("user-parameters", {}).get(
                "opendoor-address-book", []
            )

            return {"doors": doors, "vip": self.vip_config}

        except ConfigEntryAuthFailed:
            # Re-raise auth errors
            raise
        except Exception as err:
            _LOGGER.error("Error communicating with Comelit device: %s", err)
            raise UpdateFailed(f"Error communicating with device: {err}") from err
        finally:
            # Always close the connection after update
            await client.shutdown()

    async def async_open_door(self, door_name: str) -> None:
        """Open a specific door."""
        # Create a separate client instance for door operations
        # to avoid interfering with the coordinator's update cycle
        door_client = IconaBridgeClient(self.host)
        try:
            await door_client.connect()

            # Authenticate
            auth_code = await door_client.authenticate(self.token)
            if auth_code != 200:
                raise Exception(f"Authentication failed with code {auth_code}")

            # Find the door
            doors = self.data.get("doors", [])
            door = next((d for d in doors if d.get("name") == door_name), None)
            if not door:
                raise Exception(f"Door '{door_name}' not found")

            # Open the door
            await door_client.open_door(self.vip_config, door)

        except Exception as err:
            _LOGGER.error("Error opening door %s: %s", door_name, err)
            raise
        finally:
            # Always clean up the door client connection
            await door_client.shutdown()
