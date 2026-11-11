"""Base entity."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import K102Coordinator


class K102RoomEntity(CoordinatorEntity[K102Coordinator]):
    """Entity bound to one room of one gateway."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: K102Coordinator, mac: str, room_id: str) -> None:
        super().__init__(coordinator)
        self._mac = mac
        self._room_id = room_id
        room = self.room or {}
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{mac}_{room_id}")},
            name=room.get("name", room_id),
            manufacturer="Klima102",
        )

    @property
    def room(self) -> dict[str, Any] | None:
        gw = self.coordinator.data.get(self._mac)
        if not gw:
            return None
        status = gw["status"]
        for room in status.get("rooms", []):
            if room["id"] == self._room_id:
                # opMode / workingMode live at gateway level only
                return {
                    "opMode": status.get("opMode"),
                    "workingMode": status.get("workingMode"),
                    **room,
                }
        return None

    @property
    def available(self) -> bool:
        gw = self.coordinator.data.get(self._mac)
        return super().available and bool(gw and gw["status"].get("connected", True))


ACCESSORY_LABELS = {
    "ThermostaticValve": "Valvola",
    "SensTU": "Sensore",
    "Switch1": "Centralina",
    "SmartPlug": "Presa smart",
}


def iter_accessories(
    gateway_data: dict[str, Any] | None,
) -> Iterator[tuple[dict[str, Any] | None, dict[str, Any]]]:
    """Yield (room | None, accessory) for the control unit and every room."""
    structure = (gateway_data or {}).get("structure") or {}
    for acc in (structure.get("controlUnit") or {}).get("accessories") or []:
        yield None, acc
    for room in structure.get("rooms") or []:
        for acc in room.get("accessories") or []:
            yield room, acc


class K102AccessoryEntity(CoordinatorEntity[K102Coordinator]):
    """Entity bound to one accessory (valve, sensor, control unit...)."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: K102Coordinator, mac: str, acc_id: str) -> None:
        super().__init__(coordinator)
        self._mac = mac
        self._acc_id = acc_id
        gw = coordinator.data.get(mac)
        place, acc = None, {}
        for room, a in iter_accessories(gw):
            if a.get("id") == acc_id:
                place, acc = room, a
                break
        place_name = (
            place.get("description")
            if place
            else ((gw or {}).get("gateway") or {}).get("name")
        )
        label = ACCESSORY_LABELS.get(acc.get("type"), acc.get("type", "Accessorio"))
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{mac}_acc_{acc_id}")},
            name=f"{place_name} {label}".strip() if place_name else label,
            manufacturer="Klima102",
            model=acc.get("type"),
        )

    @property
    def accessory(self) -> dict[str, Any] | None:
        for _room, acc in iter_accessories(self.coordinator.data.get(self._mac)):
            if acc.get("id") == self._acc_id:
                return acc
        return None

    @property
    def available(self) -> bool:
        return super().available and self.accessory is not None


class K102GatewayEntity(CoordinatorEntity[K102Coordinator]):
    """Entity bound to a gateway (system-wide settings)."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: K102Coordinator, mac: str) -> None:
        super().__init__(coordinator)
        self._mac = mac
        gateway = coordinator.data[mac]["gateway"]
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, mac)},
            name=gateway.get("name") or "Klima102",
            manufacturer="Klima102",
            model=gateway.get("systemType"),
        )

    @property
    def available(self) -> bool:
        gw = self.coordinator.data.get(self._mac)
        return super().available and bool(gw and gw["status"].get("connected", True))
