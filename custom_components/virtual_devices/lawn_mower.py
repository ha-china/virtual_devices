"""Platform for virtual lawn mower integration."""
from __future__ import annotations

import logging
import random

from homeassistant.components.lawn_mower import LawnMowerActivity, LawnMowerEntity
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .base_entity import BaseVirtualEntity
from .const import (
    CONF_ENTITIES,
    CONF_MOWER_CUTTING_HEIGHT,
    CONF_MOWER_ZONE,
    DEVICE_TYPE_LAWN_MOWER,
    DOMAIN,
)
from .types import LawnMowerEntityConfig, LawnMowerState

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up virtual lawn mower entities."""
    device_type: str | None = config_entry.data.get("device_type")
    if device_type != DEVICE_TYPE_LAWN_MOWER:
        return

    device_info: DeviceInfo = hass.data[DOMAIN][config_entry.entry_id]["device_info"]
    entities: list[LawnMowerEntity | SensorEntity] = []
    entities_config: list[LawnMowerEntityConfig] = config_entry.data.get(CONF_ENTITIES, [])

    for idx, entity_config in enumerate(entities_config):
        mower = VirtualLawnMower(hass, config_entry.entry_id, entity_config, idx, device_info)
        entities.append(mower)
        entities.append(VirtualLawnMowerBatterySensor(config_entry.entry_id, idx, device_info, mower, entity_config))

    async_add_entities(entities)


class VirtualLawnMower(BaseVirtualEntity[LawnMowerEntityConfig, LawnMowerState], LawnMowerEntity):
    """Representation of a virtual lawn mower."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry_id: str,
        entity_config: LawnMowerEntityConfig,
        index: int,
        device_info: DeviceInfo,
    ) -> None:
        super().__init__(hass, config_entry_id, entity_config, index, device_info, "lawn_mower")
        self._attr_icon = "mdi:robot-mower"
        self._activity = LawnMowerActivity.DOCKED
        self._battery_level = 100
        self._current_zone = entity_config.get(CONF_MOWER_ZONE, "full_lawn")
        self._cutting_height = int(entity_config.get(CONF_MOWER_CUTTING_HEIGHT, 45))

    def get_default_state(self) -> LawnMowerState:
        return {
            "state": "docked",
            "battery_level": 100,
            "current_zone": "full_lawn",
            "cutting_height": 45,
        }

    def apply_state(self, state: LawnMowerState) -> None:
        self._activity = LawnMowerActivity(state.get("state", "docked"))
        self._battery_level = state.get("battery_level", 100)
        self._current_zone = state.get("current_zone", "full_lawn")
        self._cutting_height = state.get("cutting_height", 45)

    def get_current_state(self) -> LawnMowerState:
        return {
            "state": self._activity.value,
            "battery_level": self._battery_level,
            "current_zone": self._current_zone,
            "cutting_height": self._cutting_height,
        }

    @property
    def activity(self) -> LawnMowerActivity | None:
        return self._activity

    @property
    def battery_level_internal(self) -> int:
        return self._battery_level

    @property
    def extra_state_attributes(self) -> dict[str, int | str]:
        return {"current_zone": self._current_zone, "cutting_height": self._cutting_height}

    async def async_start_mowing(self) -> None:
        self._activity = LawnMowerActivity.MOWING
        await self.async_save_state()
        self.async_write_ha_state()

    async def async_pause(self) -> None:
        self._activity = LawnMowerActivity.PAUSED
        await self.async_save_state()
        self.async_write_ha_state()

    async def async_dock(self) -> None:
        self._activity = LawnMowerActivity.RETURNING
        await self.async_save_state()
        self.async_write_ha_state()

    async def async_update(self) -> None:
        if self._activity == LawnMowerActivity.MOWING:
            self._battery_level = max(0, self._battery_level - random.randint(1, 3))
        elif self._activity in (LawnMowerActivity.DOCKED, LawnMowerActivity.RETURNING):
            self._battery_level = min(100, self._battery_level + 1)
        if self._activity == LawnMowerActivity.RETURNING and self._battery_level > 10:
            self._activity = LawnMowerActivity.DOCKED
        await self.async_save_state()
        self.async_write_ha_state()


class VirtualLawnMowerBatterySensor(SensorEntity):
    """Battery sensor for virtual lawn mower."""

    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_should_poll = True

    def __init__(
        self,
        config_entry_id: str,
        index: int,
        device_info: DeviceInfo,
        mower: VirtualLawnMower,
        entity_config: LawnMowerEntityConfig,
    ) -> None:
        entity_name = entity_config.get("entity_name", f"lawn_mower_{index + 1}")
        self._mower = mower
        self._attr_name = f"{entity_name} Battery"
        self._attr_unique_id = f"{config_entry_id}_lawn_mower_{index}_battery"
        self._attr_device_info = device_info

    @property
    def native_value(self) -> int:
        return self._mower.battery_level_internal
