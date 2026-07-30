"""Event platform for virtual devices."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from homeassistant.components.event import EventEntity, EventDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DEVICE_TYPE_DOORBELL, DOMAIN
from .appliance import get_appliance_bundles

_LOGGER = logging.getLogger(__name__)

EVENT_TYPES = ["ring", "motion", "button_press"]


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    device_type = config_entry.data.get("device_type")
    if device_type != DEVICE_TYPE_DOORBELL:
        return
    device_info = hass.data[DOMAIN][config_entry.entry_id]["device_info"]
    entities = []
    for index, bundle in enumerate(get_appliance_bundles(hass, config_entry.entry_id)):
        entities.append(VirtualDoorbellEvent(config_entry.entry_id, bundle.base_name, index, device_info, bundle.manager))
    async_add_entities(entities)


class VirtualDoorbellEvent(EventEntity):
    """Event entity for doorbell rings and motion detection."""

    _attr_should_poll = True
    _attr_device_class = EventDeviceClass.DOORBELL

    def __init__(
        self,
        config_entry_id: str,
        base_name: str,
        index: int,
        device_info: DeviceInfo,
        manager: Any,
    ) -> None:
        self._manager = manager
        self._attr_name = f"{base_name} Events"
        self._attr_unique_id = f"{config_entry_id}_doorbell_{index}_events"
        self._attr_device_info = device_info
        self._attr_event_types = EVENT_TYPES
        self._last_event_type = None

    async def async_update(self) -> None:
        await self._manager.async_refresh()
        state = self._manager.state
        if state.get("last_ring") and self._last_event_type != "ring":
            self._last_event_type = "ring"
            self._trigger_event("ring", {"timestamp": state["last_ring"]})
            self.async_write_ha_state()
        elif state.get("motion_detected") and self._last_event_type != "motion":
            self._last_event_type = "motion"
            self._trigger_event("motion", {"timestamp": datetime.now().isoformat()})
            self.async_write_ha_state()