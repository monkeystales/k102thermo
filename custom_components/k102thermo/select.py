"""Select: which kind of manual a temperature change creates."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .coordinator import K102ConfigEntry, K102Coordinator
from .entity import K102RoomEntity

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
