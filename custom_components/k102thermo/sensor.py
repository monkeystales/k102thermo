"""Sensors for K102 Thermo."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import K102ConfigEntry, K102Coordinator
from .entity import K102RoomEntity


@dataclass(frozen=True, kw_only=True)
class K102SensorDescription(SensorEntityDescription):
    """Describe a room sensor."""

    value_fn: Callable[[dict[str, Any]], float | None]


SENSORS = (
    K102SensorDescription(
        key="temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda r: None if r.get("temperature") is None else r["temperature"] / 10,
    ),
    K102SensorDescription(
        key="humidity",
        device_class=SensorDeviceClass.HUMIDITY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda r: r.get("humidity"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: K102ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up sensors."""
    coordinator = entry.runtime_data
    async_add_entities(
        K102Sensor(coordinator, mac, room["id"], desc)
        for mac, info in coordinator.data.items()
        for room in info["status"].get("rooms", [])
        for desc in SENSORS
    )


class K102Sensor(K102RoomEntity, SensorEntity):
    """A room sensor."""

    entity_description: K102SensorDescription

    def __init__(
        self,
        coordinator: K102Coordinator,
        mac: str,
        room_id: str,
        description: K102SensorDescription,
    ) -> None:
        super().__init__(coordinator, mac, room_id)
        self.entity_description = description
        self._attr_unique_id = f"{mac}_{room_id}_{description.key}"

    @property
    def native_value(self) -> float | None:
        room = self.room
        return self.entity_description.value_fn(room) if room else None
