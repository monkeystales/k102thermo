"""Data update coordinator for K102 Thermo."""

from __future__ import annotations

import logging
import time
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import K102AuthError, K102Client, K102Error
from .const import CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)

# Accessories (valves, sensors) change slowly: refresh them less often.
STRUCTURE_REFRESH = 300

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
            update_interval=timedelta(
                seconds=entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
            ),
        )
        self.client = client
        # Per-room manual type chosen with the select entity: "timed" | "persistent".
        self.manual_types: dict[tuple[str, str], str] = {}
        self._structures: dict[str, tuple[float, Any]] = {}

    async def _async_update_data(self) -> dict[str, dict[str, Any]]:
        try:
            gateways = await self.client.async_get_gateways()
            data: dict[str, dict[str, Any]] = {}
            for gw in gateways:
                mac = gw["macAddress"]
                data[mac] = {
                    "gateway": gw,
                    "status": await self.client.async_get_rooms(mac),
                    "structure": await self._async_get_structure(mac),
                    "system": await self._async_get_system(mac),
                }
            return data
        except K102AuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except K102Error as err:
            raise UpdateFailed(f"Error communicating with Klima102: {err}") from err

    async def _async_get_structure(self, mac: str) -> dict[str, Any] | None:
        """Accessory list, cached; failures never break the main update."""
        cached = self._structures.get(mac)
        if cached and time.monotonic() - cached[0] < STRUCTURE_REFRESH:
            return cached[1]
        try:
            structure = await self.client.async_get_structure(mac)
        except K102AuthError:
            raise
        except K102Error as err:
            _LOGGER.debug("Accessory refresh failed: %s", err)
            return cached[1] if cached else None
        self._structures[mac] = (time.monotonic(), structure)
        return structure

    async def _async_get_system(self, mac: str) -> dict[str, Any] | None:
        """System status (on/off); failures never break the main update."""
        try:
            return await self.client.async_get_system(mac)
        except K102AuthError:
            raise
        except K102Error as err:
            _LOGGER.debug("System status refresh failed: %s", err)
            return None
