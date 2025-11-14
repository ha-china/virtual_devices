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
from homeassistant.helpers.storage import Store

STORAGE_VERSION = 1

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
            hass,
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
        hass: HomeAssistant,
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
        self._hass = hass

        entity_name = entity_config.get(CONF_ENTITY_NAME, f"cover_{index + 1}")
        self._attr_name = entity_name
        self._attr_unique_id = f"{config_entry_id}_cover_{index}"
        self._attr_device_info = device_info

        # Template support
        self._templates = entity_config.get("templates", {})

        # 存储实体状态
        self._store = Store[dict[str, Any]](hass, STORAGE_VERSION, f"virtual_devices_cover_{config_entry_id}_{index}")

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

        # 状态 - 默认值，稍后从存储恢复
        self._position = 0
        self._is_closed = True

    async def async_load_state(self) -> None:
        """Load saved state from storage."""
        try:
            data = await self._store.async_load()
            if data:
                self._position = data.get("position", 0)
                self._is_closed = data.get("is_closed", True)
                _LOGGER.info(f"Cover '{self._attr_name}' state loaded from storage")
        except Exception as ex:
            _LOGGER.error(f"Failed to load state for cover '{self._attr_name}': {ex}")

    async def async_save_state(self) -> None:
        """Save current state to storage."""
        try:
            data = {
                "position": self._position,
                "is_closed": self._is_closed,
            }
            await self._store.async_save(data)
        except Exception as ex:
            _LOGGER.error(f"Failed to save state for cover '{self._attr_name}': {ex}")

    async def async_added_to_hass(self) -> None:
        """Call when entity is added to hass."""
        await super().async_added_to_hass()
        # 加载保存的状态
        await self.async_load_state()

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

        # 保存状态到存储
        await self.async_save_state()

        self.async_write_ha_state()
        _LOGGER.debug(f"Virtual cover '{self._attr_name}' opened")

    async def async_close_cover(self, **kwargs: Any) -> None:
        """Close the cover."""
        self._position = 0
        self._is_closed = True

        # 保存状态到存储
        await self.async_save_state()

        self.async_write_ha_state()
        _LOGGER.debug(f"Virtual cover '{self._attr_name}' closed")

    async def async_stop_cover(self, **kwargs: Any) -> None:
        """Stop the cover."""
        # 修复：保持当前位置状态，只更新HA状态
        current_position = self._position
        self.async_write_ha_state()
        _LOGGER.debug(f"Virtual cover '{self._attr_name}' stopped at position {current_position}")

    async def async_set_cover_position(self, **kwargs: Any) -> None:
        """Move the cover to a specific position."""
        if (position := kwargs.get(ATTR_POSITION)) is not None:
            self._position = position
            self._is_closed = position == 0

            # 保存状态到存储
            await self.async_save_state()

            self.async_write_ha_state()
            _LOGGER.debug(
                f"Virtual cover '{self._attr_name}' position set to {position}"
            )
