"""Platform for virtual cover integration."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from homeassistant.components.cover import (
    ATTR_POSITION,
    CoverDeviceClass,
    CoverEntity,
    CoverEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
import homeassistant.config_entries as config_entries
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.storage import Store

from .const import (
    CONF_ENTITIES,
    CONF_ENTITY_NAME,
    CONF_TRAVEL_TIME,
    DEVICE_TYPE_COVER,
    DOMAIN,
    TEMPLATE_ENABLED_DEVICE_TYPES,
)

_LOGGER = logging.getLogger(__name__)

STORAGE_VERSION = 1


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

        # 运行时间设置（秒）
        self._travel_time = entity_config.get(CONF_TRAVEL_TIME, 15)  # 默认15秒完成全行程
        self._is_moving = False  # 是否正在移动
        self._target_position = None  # 目标位置
        self._start_position = None  # 开始位置
        self._start_time = None  # 开始移动的时间

        # 状态 - 默认值，稍后从存储恢复
        self._position = 0
        self._is_closed = True

        # 设置默认暴露给语音助手
        self._attr_entity_registry_enabled_default = True
        self._attr_should_poll = False
        self._attr_entity_category = None

    @property
    def should_expose(self) -> bool:
        """Return if this entity should be exposed to voice assistants."""
        return True

    async def async_load_state(self) -> None:
        """Load saved state from storage."""
        try:
            data = await self._store.async_load()
            if data:
                self._position = data.get("position", 0)
                self._is_closed = data.get("is_closed", True)
                # 重置移动状态，避免重启后卡在移动中
                self._is_moving = False
                self._target_position = None
                self._start_position = None
                self._start_time = None
                _LOGGER.info(f"Cover '{self._attr_name}' state loaded from storage")
        except Exception as ex:
            _LOGGER.error(f"Failed to load state for cover '{self._attr_name}': {ex}")

    async def async_save_state(self) -> None:
        """Save current state to storage."""
        try:
            data = {
                "position": self._position,
                "is_closed": self._is_closed,
                "is_moving": self._is_moving,
                "target_position": self._target_position,
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

    @property
    def is_opening(self) -> bool:
        """Return if the cover is opening."""
        return self._is_moving and self._target_position and self._target_position > self._position

    @property
    def is_closing(self) -> bool:
        """Return if the cover is closing."""
        return self._is_moving and self._target_position and self._target_position < self._position

    async def async_open_cover(self, **kwargs: Any) -> None:
        """Open the cover."""
        await self._move_to_position(100)

    async def async_close_cover(self, **kwargs: Any) -> None:
        """Close the cover."""
        await self._move_to_position(0)

    async def _move_to_position(self, target_position: int) -> None:
        """Move cover to target position with travel time simulation."""
        if target_position == self._position:
            return

        self._is_moving = True
        self._target_position = target_position
        self._start_position = self._position
        self._start_time = self._hass.loop.time()

        _LOGGER.debug(f"Cover '{self._attr_name}' moving from {self._position}% to {target_position}% (travel time: {self._travel_time}s)")

        # 开始移动，定期更新位置
        await self._update_position_during_movement()

    async def _update_position_during_movement(self) -> None:
        """Update position during movement based on elapsed time."""
        if not self._is_moving or self._target_position is None:
            return

        current_time = self._hass.loop.time()
        elapsed_time = current_time - self._start_time

        # 计算应该移动的距离
        total_distance = abs(self._target_position - self._start_position)
        travel_time_per_percent = self._travel_time / 100.0  # 每个百分比需要的秒数

        # 计算当前位置
        if self._target_position > self._start_position:
            # 正在开启
            new_position = min(
                self._target_position,
                self._start_position + int(elapsed_time / travel_time_per_percent)
            )
        else:
            # 正在关闭
            new_position = max(
                self._target_position,
                self._start_position - int(elapsed_time / travel_time_per_percent)
            )

        self._position = new_position
        self._is_closed = (self._position == 0)

        # 保存状态并更新HA
        await self.async_save_state()
        self.async_write_ha_state()

        # 检查是否到达目标位置
        if self._position == self._target_position:
            self._is_moving = False
            self._target_position = None
            action = "opened" if self._position == 100 else "closed" if self._position == 0 else f"moved to {self._position}%"
            _LOGGER.debug(f"Virtual cover '{self._attr_name}' {action}")
        else:
            # 继续移动，0.5秒后再次检查
            await asyncio.sleep(0.5)
            await self._update_position_during_movement()

    async def async_stop_cover(self, **kwargs: Any) -> None:
        """Stop the cover."""
        if self._is_moving:
            self._is_moving = False
            self._target_position = None
            await self.async_save_state()
            _LOGGER.debug(f"Virtual cover '{self._attr_name}' stopped at position {self._position}%")

        self.async_write_ha_state()

    async def async_set_cover_position(self, **kwargs: Any) -> None:
        """Move the cover to a specific position."""
        if (position := kwargs.get(ATTR_POSITION)) is not None:
            await self._move_to_position(position)
            _LOGGER.debug(
                f"Virtual cover '{self._attr_name}' moving to position {position}%"
            )
