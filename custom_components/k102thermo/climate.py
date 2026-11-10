"""Climate entities (one per room)."""

from __future__ import annotations

from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import K102ConfigEntry, K102Coordinator
from .entity import K102RoomEntity

PRESETS = ["comfort", "eco", "standby"]


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
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_target_temperature_step = 0.1
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.PRESET_MODE
    )
    _attr_preset_modes = PRESETS
    _attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT, HVACMode.COOL, HVACMode.AUTO]

    def __init__(self, coordinator: K102Coordinator, mac: str, room_id: str) -> None:
        super().__init__(coordinator, mac, room_id)
        self._attr_unique_id = f"{mac}_{room_id}_climate"

    @property
    def current_temperature(self) -> float | None:
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
    def target_temperature(self) -> float | None:
        r = self.room or {}
        temps = r.get("temperatures") or {}
        prog = r.get("activeProgram")
        if prog in temps:
            return temps[prog] / 10
        if r.get("manualTemperature") is not None:
            return r["manualTemperature"] / 10
        return None

    async def async_set_temperature(self, **kwargs: Any) -> None:
        if (temp := kwargs.get(ATTR_TEMPERATURE)) is None:
            return
        await self.coordinator.client.async_set_program(
            self._mac, self._room_id, "manual", round(temp * 10)
        )
        await self.coordinator.async_request_refresh()

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        await self.coordinator.client.async_set_program(
            self._mac, self._room_id, preset_mode
        )
        await self.coordinator.async_request_refresh()

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        # Winter/summer is gateway-wide and the API has no room on/off call:
        # only AUTO (follow the schedule) can be selected.
        if hvac_mode != HVACMode.AUTO:
            raise ServiceValidationError(
                "Only 'auto' can be selected; heat/cool follows the gateway mode"
            )
        await self.coordinator.client.async_set_program(
            self._mac, self._room_id, "auto"
        )
        await self.coordinator.async_request_refresh()
