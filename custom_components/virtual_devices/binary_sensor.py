"""Platform for virtual binary sensor integration."""
from __future__ import annotations

import logging
import random

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .base_entity import BaseVirtualEntity
from .const import (
    CONF_ENTITIES,
    DEVICE_TYPE_BINARY_SENSOR,
    DOMAIN,
)
from .types import BinarySensorEntityConfig, BinarySensorState

_LOGGER = logging.getLogger(__name__)

# Binary sensor type mapping
BINARY_SENSOR_TYPE_MAP: dict[str, BinarySensorDeviceClass] = {
    "motion": BinarySensorDeviceClass.MOTION,
    "door": BinarySensorDeviceClass.DOOR,
    "window": BinarySensorDeviceClass.WINDOW,
    "smoke": BinarySensorDeviceClass.SMOKE,
    "gas": BinarySensorDeviceClass.GAS,
    "moisture": BinarySensorDeviceClass.MOISTURE,
    "occupancy": BinarySensorDeviceClass.OCCUPANCY,
    "opening": BinarySensorDeviceClass.OPENING,
    "presence": BinarySensorDeviceClass.PRESENCE,
    "problem": BinarySensorDeviceClass.PROBLEM,
    "safety": BinarySensorDeviceClass.SAFETY,
    "sound": BinarySensorDeviceClass.SOUND,
    "vibration": BinarySensorDeviceClass.VIBRATION,
}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up virtual binary sensor entities."""
    device_type: str | None = config_entry.data.get("device_type")

    if device_type != DEVICE_TYPE_BINARY_SENSOR:
        return

    device_info: DeviceInfo = hass.data[DOMAIN][config_entry.entry_id]["device_info"]
    entities: list[VirtualBinarySensor] = []
    entities_config: list[BinarySensorEntityConfig] = config_entry.data.get(CONF_ENTITIES, [])

    for idx, entity_config in enumerate(entities_config):
        entity = VirtualBinarySensor(
            hass,
            config_entry.entry_id,
            entity_config,
            idx,
            device_info,
        )
        entities.append(entity)

    async_add_entities(entities)


class VirtualBinarySensor(BaseVirtualEntity[BinarySensorEntityConfig, BinarySensorState], BinarySensorEntity):
    """Representation of a virtual binary sensor."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry_id: str,
        entity_config: BinarySensorEntityConfig,
        index: int,
        device_info: DeviceInfo,
    ) -> None:
        """Initialize the virtual binary sensor."""
        super().__init__(hass, config_entry_id, entity_config, index, device_info, "binary_sensor")

        # Entity category support
        entity_category: str | None = entity_config.get("entity_category")
        if entity_category:
            category_map: dict[str, EntityCategory] = {
                "config": EntityCategory.CONFIG,
                "diagnostic": EntityCategory.DIAGNOSTIC,
            }
            self._attr_entity_category = category_map.get(entity_category)
        else:
            self._attr_entity_category = EntityCategory.DIAGNOSTIC

        # Set device class
        sensor_type: str = entity_config.get("sensor_type", "motion")
        self._attr_device_class = BINARY_SENSOR_TYPE_MAP.get(
            sensor_type, BinarySensorDeviceClass.MOTION
        )

        # Initial state
        self._attr_is_on: bool = False

    def get_default_state(self) -> BinarySensorState:
        """Return the default state for this binary sensor entity."""
        return BinarySensorState(is_on=False)

    def apply_state(self, state: BinarySensorState) -> None:
        """Apply loaded state to entity attributes."""
        self._attr_is_on = state.get("is_on", False)
        _LOGGER.info("Loaded state for binary sensor '%s': is_on=%s", self._attr_name, self._attr_is_on)

    def get_current_state(self) -> BinarySensorState:
        """Get current state for persistence."""
        return BinarySensorState(is_on=self._attr_is_on)

    async def async_update(self) -> None:
        """Update the binary sensor state."""
        # Randomly generate state changes
        self._attr_is_on = random.choice([True, False])
        await self.async_save_state()
