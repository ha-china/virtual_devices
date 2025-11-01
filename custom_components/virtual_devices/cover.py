"""Platform for virtual cover integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.cover import (
    ATTR_POSITION,
    CoverDeviceClass,
    CoverEntity,
    CoverEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_ENTITIES,
    CONF_ENTITY_NAME,
    DEVICE_TYPE_COVER,
    DOMAIN,
    TEMPLATE_ENABLED_DEVICE_TYPES,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up virtual cover entities."""
    device_type = config_entry.data.get("device_type")

    # 只有窗帘类型的设备才设置窗帘实体
    if device_type != DEVICE_TYPE_COVER:
        return

    device_info = hass.data[DOMAIN][config_entry.entry_id]["device_info"]
    entities = []
    entities_config = config_entry.data.get(CONF_ENTITIES, [])

    for idx, entity_config in enumerate(entities_config):
        entity = VirtualCover(
            config_entry.entry_id,
            entity_config,
            idx,
            device_info,
        )
        entities.append(entity)

    async_add_entities(entities)


class VirtualCover(CoverEntity):
    """Representation of a virtual cover."""

    _attr_supported_features = (
        CoverEntityFeature.OPEN
        | CoverEntityFeature.CLOSE
        | CoverEntityFeature.STOP
        | CoverEntityFeature.SET_POSITION
    )

    def __init__(
        self,
        config_entry_id: str,
        entity_config: dict[str, Any],
        index: int,
        device_info: dict[str, Any],
    ) -> None:
        """Initialize the virtual cover."""
        self._config_entry_id = config_entry_id
        self._entity_config = entity_config
        self._index = index
        self._device_info = device_info

        entity_name = entity_config.get(CONF_ENTITY_NAME, f"cover_{index + 1}")
        self._attr_name = entity_name
        self._attr_unique_id = f"{config_entry_id}_cover_{index}"
        self._attr_device_info = device_info

        # Template support
        self._templates = entity_config.get("templates", {})

        # 设置设备类型
        cover_type = entity_config.get("cover_type", "curtain")
        device_class_map = {
            "blind": CoverDeviceClass.BLIND,
            "curtain": CoverDeviceClass.CURTAIN,
            "damper": CoverDeviceClass.DAMPER,
            "door": CoverDeviceClass.DOOR,
            "garage": CoverDeviceClass.GARAGE,
            "shade": CoverDeviceClass.SHADE,
            "shutter": CoverDeviceClass.SHUTTER,
            "window": CoverDeviceClass.WINDOW,
        }
        self._attr_device_class = device_class_map.get(
            cover_type, CoverDeviceClass.CURTAIN
        )

        # 状态
        self._position = 0
        self._is_closed = True

    @property
    def current_cover_position(self) -> int:
        """Return current position of cover."""
        return self._position

    @property
    def is_closed(self) -> bool:
        """Return if the cover is closed."""
        return self._is_closed

    async def async_open_cover(self, **kwargs: Any) -> None:
        """Open the cover."""
        self._position = 100
        self._is_closed = False
        self.async_write_ha_state()
        _LOGGER.debug(f"Virtual cover '{self._attr_name}' opened")

    async def async_close_cover(self, **kwargs: Any) -> None:
        """Close the cover."""
        self._position = 0
        self._is_closed = True
        self.async_write_ha_state()
        _LOGGER.debug(f"Virtual cover '{self._attr_name}' closed")

    async def async_stop_cover(self, **kwargs: Any) -> None:
        """Stop the cover."""
        self.async_write_ha_state()
        _LOGGER.debug(f"Virtual cover '{self._attr_name}' stopped")

    async def async_set_cover_position(self, **kwargs: Any) -> None:
        """Move the cover to a specific position."""
        if (position := kwargs.get(ATTR_POSITION)) is not None:
            self._position = position
            self._is_closed = position == 0
            self.async_write_ha_state()
            _LOGGER.debug(
                f"Virtual cover '{self._attr_name}' position set to {position}"
            )
