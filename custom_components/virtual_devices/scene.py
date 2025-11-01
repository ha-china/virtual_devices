"""Platform for virtual scene integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.scene import Scene
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_ENTITIES,
    CONF_ENTITY_NAME,
    DEVICE_TYPE_SCENE,
    DOMAIN,
    TEMPLATE_ENABLED_DEVICE_TYPES,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up virtual scene entities."""
    device_type = config_entry.data.get("device_type")

    # 只有场景类型的设备才设置场景实体
    if device_type != DEVICE_TYPE_SCENE:
        return

    device_info = hass.data[DOMAIN][config_entry.entry_id]["device_info"]
    entities = []
    entities_config = config_entry.data.get(CONF_ENTITIES, [])

    for idx, entity_config in enumerate(entities_config):
        entity = VirtualScene(
            config_entry.entry_id,
            entity_config,
            idx,
            device_info,
        )
        entities.append(entity)

    async_add_entities(entities)


class VirtualScene(Scene):
    """Representation of a virtual scene."""

    def __init__(
        self,
        config_entry_id: str,
        entity_config: dict[str, Any],
        index: int,
        device_info: dict[str, Any],
    ) -> None:
        """Initialize the virtual scene."""
        self._config_entry_id = config_entry_id
        self._entity_config = entity_config
        self._index = index
        self._device_info = device_info

        entity_name = entity_config.get(CONF_ENTITY_NAME, f"scene_{index + 1}")
        self._attr_name = entity_name
        self._attr_unique_id = f"{config_entry_id}_scene_{index}"
        self._attr_device_info = device_info

        # Template support
        self._templates = entity_config.get("templates", {})

    async def async_activate(self, **kwargs: Any) -> None:
        """Activate the scene."""
        _LOGGER.info(f"Virtual scene '{self._attr_name}' activated")
        # 虚拟场景被激活，触发事件供自动化使用
        self.hass.bus.async_fire(
            f"{DOMAIN}_scene_activated",
            {
                "entity_id": self.entity_id,
                "name": self._attr_name,
                "device_id": self._config_entry_id,
            },
        )
