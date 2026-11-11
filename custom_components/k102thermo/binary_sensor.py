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


class K102ConnectivitySensor(K102AccessoryEntity, BinarySensorEntity):
    """Accessory connected to the gateway."""

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC

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
