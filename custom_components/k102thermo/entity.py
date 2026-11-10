"""Base entity."""

from __future__ import annotations

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
