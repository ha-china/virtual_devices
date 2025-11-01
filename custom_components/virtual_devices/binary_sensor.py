"""Platform for virtual binary sensor integration."""
from __future__ import annotations

import logging
import random
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_ENTITIES,
    CONF_ENTITY_NAME,
    DEVICE_TYPE_BINARY_SENSOR,
    DOMAIN,
    TEMPLATE_ENABLED_DEVICE_TYPES,
)

_LOGGER = logging.getLogger(__name__)

# 二进制传感器类型映射
BINARY_SENSOR_TYPE_MAP = {
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
    device_type = config_entry.data.get("device_type")

    # 只有二进制传感器类型的设备才设置二进制传感器实体
    if device_type != DEVICE_TYPE_BINARY_SENSOR:
        return

    device_info = hass.data[DOMAIN][config_entry.entry_id]["device_info"]
    entities = []
    entities_config = config_entry.data.get(CONF_ENTITIES, [])

    for idx, entity_config in enumerate(entities_config):
        entity = VirtualBinarySensor(
            config_entry.entry_id,
            entity_config,
            idx,
            device_info,
        )
        entities.append(entity)

    async_add_entities(entities)


class VirtualBinarySensor(BinarySensorEntity):
    """Representation of a virtual binary sensor."""

    def __init__(
        self,
        config_entry_id: str,
        entity_config: dict[str, Any],
        index: int,
        device_info: dict[str, Any],
    ) -> None:
        """Initialize the virtual binary sensor."""
        self._config_entry_id = config_entry_id
        self._entity_config = entity_config
        self._index = index
        self._device_info = device_info

        entity_name = entity_config.get(CONF_ENTITY_NAME, f"Binary Sensor_{index + 1}")
        self._attr_name = entity_name
        self._attr_unique_id = f"{config_entry_id}_binary_sensor_{index}"
        self._attr_device_info = device_info

        # Template support
        self._templates = entity_config.get("templates", {})

        # Entity category支持
        entity_category = entity_config.get("entity_category")
        if entity_category:
            category_map = {
                "config": EntityCategory.CONFIG,
                "diagnostic": EntityCategory.DIAGNOSTIC,
            }
            self._attr_entity_category = category_map.get(entity_category)
        else:
            self._attr_entity_category = EntityCategory.DIAGNOSTIC  # 默认为诊断类别

        # 设置设备类型
        sensor_type = entity_config.get("sensor_type", "motion")
        self._attr_device_class = BINARY_SENSOR_TYPE_MAP.get(
            sensor_type, BinarySensorDeviceClass.MOTION
        )

        # 初始状态
        self._attr_is_on = False

    async def async_update(self) -> None:
        """Update the binary sensor state."""
        # 随机生成状态变化
        self._attr_is_on = random.choice([True, False])
