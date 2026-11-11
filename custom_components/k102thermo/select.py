"""Select: which kind of manual a temperature change creates."""

from __future__ import annotations

import time
from datetime import datetime
from typing import Any

from homeassistant.components.select import SelectEntity
from homeassistant.core import CALLBACK_TYPE, HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .api import K102Error
from .coordinator import K102ConfigEntry, K102Coordinator
from .entity import K102GatewayEntity, K102RoomEntity

OPTIONS = ["timed", "persistent"]
DEFAULT = "timed"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: K102ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        K102ManualTypeSelect(coordinator, mac, room["id"])
        for mac, info in coordinator.data.items()
        for room in info["status"].get("rooms", [])
    )
    async_add_entities(
        cls(coordinator, mac)
        for mac in coordinator.data
        for cls in (K102WorkingModeSelect, K102SeasonSelect)
    )


class K102ManualTypeSelect(K102RoomEntity, SelectEntity, RestoreEntity):
    """Timed manual (until the next schedule change) or persistent manual."""

    _attr_translation_key = "manual_type"
    _attr_options = OPTIONS
    _attr_icon = "mdi:timer-cog-outline"

    def __init__(self, coordinator: K102Coordinator, mac: str, room_id: str) -> None:
        super().__init__(coordinator, mac, room_id)
        self._attr_unique_id = f"{mac}_{room_id}_manual_type"

    @property
    def _key(self) -> tuple[str, str]:
        return (self._mac, self._room_id)

    @property
    def current_option(self) -> str:
        return self.coordinator.manual_types.get(self._key, DEFAULT)

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if (last := await self.async_get_last_state()) and last.state in OPTIONS:
            self.coordinator.manual_types[self._key] = last.state
            self.async_write_ha_state()

    async def async_select_option(self, option: str) -> None:
        self.coordinator.manual_types[self._key] = option
        # Refresh every entity of the entry so climate shows the new choice too.
        self.coordinator.async_update_listeners()


PENDING_TIMEOUT = 90
PENDING_POLL_INTERVAL = 5


class _K102GatewaySelect(K102GatewayEntity, SelectEntity):
    """System-wide select with optimistic state until the cloud confirms."""

    _status_key: str
    _to_api: dict[str, str]
    _pending: str | None = None
    _pending_expires = 0.0
    _unsub_poll: CALLBACK_TYPE | None = None

    def __init__(self, coordinator: K102Coordinator, mac: str) -> None:
        super().__init__(coordinator, mac)
        self._from_api = {v: k for k, v in self._to_api.items()}
        self._attr_options = list(self._to_api)
        self._attr_unique_id = f"{mac}_{self._status_key}"

    @property
    def _reported(self) -> str | None:
        return self.coordinator.data[self._mac]["status"].get(self._status_key)

    @property
    def current_option(self) -> str | None:
        return self._from_api.get(self._pending or self._reported)

    async def _async_send(self, api_value: str) -> None:
        raise NotImplementedError

    async def async_select_option(self, option: str) -> None:
        api_value = self._to_api[option]
        self._pending = api_value
        self._pending_expires = time.monotonic() + PENDING_TIMEOUT
        self.async_write_ha_state()
        self._schedule_poll()
        try:
            await self._async_send(api_value)
        except K102Error as err:
            self._clear_pending()
            self.async_write_ha_state()
            raise HomeAssistantError(f"Command failed: {err}") from err
        await self.coordinator.async_request_refresh()

    def _clear_pending(self) -> None:
        self._pending = None
        if self._unsub_poll:
            self._unsub_poll()
            self._unsub_poll = None

    def _schedule_poll(self) -> None:
        if self._unsub_poll:
            self._unsub_poll()
        self._unsub_poll = async_call_later(
            self.hass, PENDING_POLL_INTERVAL, self._async_poll
        )

    async def _async_poll(self, _now: datetime) -> None:
        self._unsub_poll = None
        if self._pending is None:
            return
        if time.monotonic() > self._pending_expires:
            self._clear_pending()
            self.async_write_ha_state()
            return
        await self.coordinator.async_request_refresh()
        if self._pending is not None:
            self._schedule_poll()

    def _handle_coordinator_update(self) -> None:
        if self._pending and (
            self._reported == self._pending or time.monotonic() > self._pending_expires
        ):
            self._clear_pending()
        super()._handle_coordinator_update()

    async def async_will_remove_from_hass(self) -> None:
        self._clear_pending()
        await super().async_will_remove_from_hass()


class K102WorkingModeSelect(_K102GatewaySelect):
    """Working mode: normal or vacation (no-freeze)."""

    _attr_translation_key = "working_mode"
    _attr_icon = "mdi:beach"
    _status_key = "workingMode"
    _to_api = {"normal": "normal", "vacation_no_freeze": "vacationNoFreeze"}

    async def _async_send(self, api_value: str) -> None:
        await self.coordinator.client.async_set_working_mode(self._mac, api_value)


class K102SeasonSelect(_K102GatewaySelect):
    """Winter / summer. EXPERIMENTAL write: sent through the room setpoints API."""

    _attr_translation_key = "season"
    _attr_icon = "mdi:sun-snowflake-variant"
    _status_key = "opMode"
    _to_api = {"winter": "winter", "summer": "summer"}

    async def _async_send(self, api_value: str) -> None:
        rooms: list[dict[str, Any]] = self.coordinator.data[self._mac]["status"].get(
            "rooms", []
        )
        await self.coordinator.client.async_set_op_mode(
            self._mac, [r["id"] for r in rooms], api_value
        )
