"""Binary sensors: accessory connectivity."""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import K102ConfigEntry, K102Coordinator
from .entity import K102AccessoryEntity, K102GatewayEntity, iter_accessories


async def async_setup_entry(
    hass: HomeAssistant,
    entry: K102ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        K102ConnectivitySensor(coordinator, mac, acc["id"])
        for mac, info in coordinator.data.items()
        for _room, acc in iter_accessories(info)
    )
    async_add_entities(K102SystemActiveSensor(coordinator, mac) for mac in coordinator.data)
    async_add_entities(
        K102BoilerDemandSensor(coordinator, mac, acc["id"])
        for mac, info in coordinator.data.items()
        for _room, acc in iter_accessories(info)
        if acc.get("type") == "Switch1"
    )


class K102ConnectivitySensor(K102AccessoryEntity, BinarySensorEntity):
    """Accessory connected to the gateway."""

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_translation_key = "accessory_connectivity"

    def __init__(self, coordinator: K102Coordinator, mac: str, acc_id: str) -> None:
        super().__init__(coordinator, mac, acc_id)
        self._attr_unique_id = f"{mac}_acc_{acc_id}_connectivity"

    @property
    def is_on(self) -> bool | None:
        acc = self.accessory
        return acc.get("connected") if acc else None


class K102SystemActiveSensor(K102GatewayEntity, BinarySensorEntity):
    """Thermoregulation on/off (read only: the API has no way to change it)."""

    _attr_translation_key = "system_active"

    def __init__(self, coordinator: K102Coordinator, mac: str) -> None:
        super().__init__(coordinator, mac)
        self._attr_unique_id = f"{mac}_system_active"

    @property
    def _raw(self) -> Any:
        system = self.coordinator.data[self._mac].get("system") or {}
        return system.get("sysStatus")

    @property
    def is_on(self) -> bool | None:
        raw = self._raw
        if raw is None:
            return None
        return str(raw).strip().lower() in ("on", "true", "1", "enabled", "active")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"sys_status": self._raw}


class K102BoilerDemandSensor(K102AccessoryEntity, BinarySensorEntity):
    """Heat demand sent to the boiler actuator.

    DERIVED: the API does not expose the relay state, so this is on when at
    least one enabled room is heating/cooling ("powering").
    """

    _attr_device_class = BinarySensorDeviceClass.RUNNING
    _attr_translation_key = "boiler_demand"

    def __init__(self, coordinator: K102Coordinator, mac: str, acc_id: str) -> None:
        super().__init__(coordinator, mac, acc_id)
        self._attr_unique_id = f"{mac}_acc_{acc_id}_boiler_demand"

    @property
    def _calling_rooms(self) -> list[str]:
        rooms = self.coordinator.data[self._mac]["status"].get("rooms", [])
        return [
            r.get("name") or r["id"]
            for r in rooms
            if r.get("powering") and r.get("enabled", True)
        ]

    @property
    def is_on(self) -> bool:
        return bool(self._calling_rooms)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"derived_from_rooms": True, "rooms_calling": self._calling_rooms}
