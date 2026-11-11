"""Sensors for K102 Thermo."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, EntityCategory, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import K102ConfigEntry, K102Coordinator
from homeassistant.util import dt as dt_util

from .entity import K102AccessoryEntity, K102RoomEntity, iter_accessories


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
    accessory_entities: list[SensorEntity] = []
    for mac, info in coordinator.data.items():
        for _room, acc in iter_accessories(info):
            acc_id = acc["id"]
            if acc.get("powerSupply") == "Battery" and "batteryLevel" in acc:
                accessory_entities.append(
                    K102AccessorySensor(coordinator, mac, acc_id, ACCESSORY_BATTERY)
                )
            if "temperature" in acc:
                accessory_entities.append(
                    K102AccessorySensor(coordinator, mac, acc_id, ACCESSORY_TEMPERATURE)
                )
            accessory_entities.append(
                K102AccessorySensor(coordinator, mac, acc_id, ACCESSORY_LAST_SEEN)
            )
    async_add_entities(accessory_entities)


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


@dataclass(frozen=True, kw_only=True)
class K102AccessorySensorDescription(SensorEntityDescription):
    """Describe an accessory sensor."""

    value_fn: Callable[[dict[str, Any]], Any]


def _last_seen(acc: dict[str, Any]) -> datetime | None:
    value = acc.get("lastConnection")
    return dt_util.parse_datetime(value) if value else None


ACCESSORY_BATTERY = K102AccessorySensorDescription(
    key="battery",
    translation_key="accessory_battery",
    device_class=SensorDeviceClass.BATTERY,
    native_unit_of_measurement=PERCENTAGE,
    state_class=SensorStateClass.MEASUREMENT,
    entity_category=EntityCategory.DIAGNOSTIC,
    value_fn=lambda a: a.get("batteryLevel"),
)
ACCESSORY_TEMPERATURE = K102AccessorySensorDescription(
    key="temperature",
    translation_key="accessory_temperature",
    device_class=SensorDeviceClass.TEMPERATURE,
    native_unit_of_measurement=UnitOfTemperature.CELSIUS,
    state_class=SensorStateClass.MEASUREMENT,
    value_fn=lambda a: None if a.get("temperature") is None else a["temperature"] / 10,
)
ACCESSORY_LAST_SEEN = K102AccessorySensorDescription(
    key="last_seen",
    translation_key="accessory_last_seen",
    device_class=SensorDeviceClass.TIMESTAMP,
    entity_category=EntityCategory.DIAGNOSTIC,
    entity_registry_enabled_default=False,
    value_fn=_last_seen,
)


class K102AccessorySensor(K102AccessoryEntity, SensorEntity):
    """A sensor of a valve / sensor / control unit."""

    entity_description: K102AccessorySensorDescription

    def __init__(
        self,
        coordinator: K102Coordinator,
        mac: str,
        acc_id: str,
        description: K102AccessorySensorDescription,
    ) -> None:
        super().__init__(coordinator, mac, acc_id)
        self.entity_description = description
        self._attr_unique_id = f"{mac}_acc_{acc_id}_{description.key}"

    @property
    def native_value(self) -> Any:
        acc = self.accessory
        return self.entity_description.value_fn(acc) if acc else None
