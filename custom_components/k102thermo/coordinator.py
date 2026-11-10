"""Data update coordinator for K102 Thermo."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import K102AuthError, K102Client, K102Error
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)

type K102ConfigEntry = ConfigEntry[K102Coordinator]


class K102Coordinator(DataUpdateCoordinator[dict[str, dict[str, Any]]]):
    """Poll all gateways. data = {mac: {"gateway": {...}, "status": {...}}}."""

    config_entry: K102ConfigEntry

    def __init__(
        self, hass: HomeAssistant, entry: K102ConfigEntry, client: K102Client
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=DEFAULT_SCAN_INTERVAL,
        )
        self.client = client

    async def _async_update_data(self) -> dict[str, dict[str, Any]]:
        try:
            gateways = await self.client.async_get_gateways()
            data: dict[str, dict[str, Any]] = {}
            for gw in gateways:
                mac = gw["macAddress"]
                data[mac] = {
                    "gateway": gw,
                    "status": await self.client.async_get_rooms(mac),
                }
            return data
        except K102AuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except K102Error as err:
            raise UpdateFailed(f"Error communicating with Klima102: {err}") from err
