"""Binary sensors: accessory connectivity."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import K102ConfigEntry, K102Coordinator
from .entity import K102AccessoryEntity, iter_accessories


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
