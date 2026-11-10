"""Climate entities (one per room)."""

from __future__ import annotations

import time
from datetime import datetime
from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import CALLBACK_TYPE, HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.event import async_call_later

from .api import K102Error
from .coordinator import K102ConfigEntry, K102Coordinator
from .entity import K102RoomEntity

PRESETS = ["comfort", "eco", "standby"]

# The cloud applies commands slowly: until the room reports the new state we
# show the requested one (optimistic) and poll faster, up to this timeout.
PENDING_TIMEOUT = 90
PENDING_POLL_INTERVAL = 5


async def async_setup_entry(
    hass: HomeAssistant,
    entry: K102ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up climate entities."""
    coordinator = entry.runtime_data
    async_add_entities(
        K102Climate(coordinator, mac, room["id"])
        for mac, info in coordinator.data.items()
        for room in info["status"].get("rooms", [])
    )


class K102Climate(K102RoomEntity, ClimateEntity):
    """A room thermostat."""

    _attr_name = None
    _attr_native_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_target_temperature_step = 0.1
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.PRESET_MODE
    )
    _attr_preset_modes = PRESETS
    _attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT, HVACMode.COOL, HVACMode.AUTO]

    # Defined at class level: the base __init__ reads `self.room` before ours runs.
    _pending: dict[str, Any] | None = None
    _unsub_poll: CALLBACK_TYPE | None = None

    def __init__(self, coordinator: K102Coordinator, mac: str, room_id: str) -> None:
        super().__init__(coordinator, mac, room_id)
        self._attr_unique_id = f"{mac}_{room_id}_climate"

    # --- room data, with the optimistic override applied -------------------

    @property
    def room(self) -> dict[str, Any] | None:
        base = super().room
        if base is None or self._pending is None:
            return base
        override = {"activeProgram": self._pending["program"]}
        if self._pending["temperature"] is not None:
            override["manualTemperature"] = self._pending["temperature"]
        return {**base, **override}

    @property
    def native_current_temperature(self) -> float | None:
        r = self.room
        if r and r.get("temperature") is not None:
            return r["temperature"] / 10
        return None

    @property
    def current_humidity(self) -> float | None:
        r = self.room
        return r.get("humidity") if r else None

    @property
    def hvac_mode(self) -> HVACMode:
        r = self.room or {}
        if r.get("enabled") is False:
            return HVACMode.OFF
        if r.get("activeProgram") == "auto":
            return HVACMode.AUTO
        return HVACMode.COOL if r.get("opMode") == "summer" else HVACMode.HEAT

    @property
    def hvac_action(self) -> HVACAction:
        r = self.room or {}
        if r.get("enabled") is False:
            return HVACAction.OFF
        if not r.get("powering"):
            return HVACAction.IDLE
        return HVACAction.COOLING if r.get("opMode") == "summer" else HVACAction.HEATING

    @property
    def preset_mode(self) -> str | None:
        prog = (self.room or {}).get("activeProgram")
        return prog if prog in PRESETS else None

    @property
    def native_target_temperature(self) -> float | None:
        r = self.room or {}
        temps = r.get("temperatures") or {}
        prog = r.get("activeProgram")
        if prog in temps:
            return temps[prog] / 10
        if r.get("manualTemperature") is not None:
            return r["manualTemperature"] / 10
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Program setpoints and pending-command flag (shown in the entity dialog)."""
        temps = (self.room or {}).get("temperatures") or {}
        attrs: dict[str, Any] = {"command_pending": self._pending is not None}
        for key in PRESETS:
            if temps.get(key) is not None:
                attrs[f"{key}_temperature"] = temps[key] / 10
        return attrs

    # --- commands ------------------------------------------------------------

    async def async_set_temperature(self, **kwargs: Any) -> None:
        if (temp := kwargs.get(ATTR_TEMPERATURE)) is None:
            return
        await self._async_command("manual", round(temp * 10))

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        await self._async_command(preset_mode)

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        # Winter/summer is gateway-wide and the API has no room on/off call:
        # only AUTO (follow the schedule) can be selected.
        if hvac_mode != HVACMode.AUTO:
            raise ServiceValidationError(
                "Only 'auto' can be selected; heat/cool follows the gateway mode"
            )
        await self._async_command("auto")

    async def _async_command(self, program: str, temperature: int | None = None) -> None:
        """Show the requested state at once, then send it and wait for the cloud."""
        self._pending = {
            "program": program,
            "temperature": temperature,
            "expires": time.monotonic() + PENDING_TIMEOUT,
        }
        self.async_write_ha_state()
        self._schedule_poll()
        try:
            await self.coordinator.client.async_set_program(
                self._mac, self._room_id, program, temperature
            )
        except K102Error as err:
            self._clear_pending()
            self.async_write_ha_state()
            raise HomeAssistantError(f"Command failed: {err}") from err
        await self.coordinator.async_request_refresh()

    # --- pending handling ----------------------------------------------------

    def _pending_satisfied(self) -> bool:
        base = super().room
        if not base or not self._pending:
            return True
        program = self._pending["program"]
        if program == "auto":
            return base.get("activeProgram") == base.get("scheduledProgram")
        if base.get("activeProgram") != program:
            return False
        temp = self._pending["temperature"]
        return temp is None or base.get("manualTemperature") == temp

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
        if time.monotonic() > self._pending["expires"]:
            self._clear_pending()
            self.async_write_ha_state()
            return
        await self.coordinator.async_request_refresh()
        if self._pending is not None:
            self._schedule_poll()

    def _handle_coordinator_update(self) -> None:
        if self._pending and (
            self._pending_satisfied() or time.monotonic() > self._pending["expires"]
        ):
            self._clear_pending()
        super()._handle_coordinator_update()

    async def async_will_remove_from_hass(self) -> None:
        self._clear_pending()
        await super().async_will_remove_from_hass()
