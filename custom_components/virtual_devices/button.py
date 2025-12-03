"""Platform for virtual button integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_ENTITIES,
    CONF_ENTITY_NAME,
    DEVICE_TYPE_BUTTON,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up virtual button entities."""
    device_type = config_entry.data.get("device_type")

    device_info = hass.data[DOMAIN][config_entry.entry_id]["device_info"]
    entities = []
    entities_config = config_entry.data.get(CONF_ENTITIES, [])

    # 只有按钮类型的设备才设置按钮实体
    if device_type == DEVICE_TYPE_BUTTON:
        for idx, entity_config in enumerate(entities_config):
            entity = VirtualButton(
                config_entry.entry_id,
                entity_config,
                idx,
                device_info,
            )
            entities.append(entity)

    async_add_entities(entities)


class VirtualButton(ButtonEntity):
    """Representation of a virtual button."""

    def __init__(
        self,
        config_entry_id: str,
        entity_config: dict[str, Any],
        index: int,
        device_info: dict[str, Any],
    ) -> None:
        """Initialize virtual button."""
        self._config_entry_id = config_entry_id
        self._entity_config = entity_config
        self._index = index
        self._device_info = device_info

        entity_name = entity_config.get(CONF_ENTITY_NAME, f"Button {index + 1}")
        self._attr_name = entity_name
        self._attr_unique_id = f"{config_entry_id}_button_{index}"
        self._attr_device_info = device_info

        # Template support
        self._templates = entity_config.get("templates", {})

        # 设置按钮类型图标
        button_type = entity_config.get("button_type", "generic")
        icon_map = {
            "generic": "mdi:gesture-tap-button",
            "restart": "mdi:restart",
            "update": "mdi:update",
            "identify": "mdi:bullseye-arrow",
        }
        self._attr_icon = icon_map.get(button_type, "mdi:gesture-tap-button")

    async def async_press(self) -> None:
        """Handle button press."""
        _LOGGER.info(f"Virtual button '{self._attr_name}' pressed")
        # 虚拟按钮按下，不执行实际操作
        # 可以触发事件供自动化使用
        self.hass.bus.async_fire(
            f"{DOMAIN}_button_pressed",
            {
                "entity_id": self.entity_id,
                "name": self._attr_name,
                "device_id": self._config_entry_id,
            },
        )


