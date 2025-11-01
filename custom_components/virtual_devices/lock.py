"""Platform for virtual lock integration."""
from __future__ import annotations

import logging
import random
from typing import Any

from homeassistant.components.lock import LockEntity, LockState
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_ENTITIES,
    CONF_ENTITY_NAME,
    CONF_LOCK_BATTERY_LEVEL,
    CONF_LOCK_STATE,
    DEVICE_TYPE_LOCK,
    DOMAIN,
    LOCK_TYPES,
    TEMPLATE_ENABLED_DEVICE_TYPES,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up virtual lock entities."""
    device_type = config_entry.data.get("device_type")

    # 只有锁类型的设备才设置锁实体
    if device_type != DEVICE_TYPE_LOCK:
        return

    device_info = hass.data[DOMAIN][config_entry.entry_id]["device_info"]
    entities = []
    entities_config = config_entry.data.get(CONF_ENTITIES, [])

    for idx, entity_config in enumerate(entities_config):
        entity = VirtualLock(
            config_entry.entry_id,
            entity_config,
            idx,
            device_info,
        )
        entities.append(entity)

    async_add_entities(entities)


class VirtualLock(LockEntity):
    """Representation of a virtual lock."""

    def __init__(
        self,
        config_entry_id: str,
        entity_config: dict[str, Any],
        index: int,
        device_info: dict[str, Any],
    ) -> None:
        """Initialize the virtual lock."""
        self._config_entry_id = config_entry_id
        self._entity_config = entity_config
        self._index = index
        self._device_info = device_info

        entity_name = entity_config.get(CONF_ENTITY_NAME, f"lock_{index + 1}")
        self._attr_name = entity_name
        self._attr_unique_id = f"{config_entry_id}_lock_{index}"
        self._attr_device_info = device_info

        # Template support
        self._templates = entity_config.get("templates", {})

        # 锁类型
        lock_type = entity_config.get("lock_type", "smart_lock")
        self._lock_type = lock_type

        # 根据类型设置图标
        icon_map = {
            "deadbolt": "mdi:lock",
            "door_lock": "mdi:lock-outline",
            "padlock": "mdi:lock-open-variant",
            "smart_lock": "mdi:lock-smart",
        }
        self._attr_icon = icon_map.get(lock_type, "mdi:lock")

        # 初始化状态
        initial_state = entity_config.get(CONF_LOCK_STATE, "locked")
        self._attr_state = LockState.LOCKED if initial_state == "locked" else LockState.UNLOCKED

        # 电池电量
        self._attr_battery_level = entity_config.get(CONF_LOCK_BATTERY_LEVEL, random.randint(20, 100))

        # 锁的其他属性
        self._is_jammed = False
        self._last_access = None
        self._access_code = entity_config.get("access_code", "1234")
        self._auto_lock_enabled = entity_config.get("auto_lock", True)
        self._auto_lock_delay = entity_config.get("auto_lock_delay", 30)  # 秒

    @property
    def is_locked(self) -> bool:
        """Return true if the lock is locked."""
        return self._attr_state == LockState.LOCKED

    @property
    def is_jammed(self) -> bool:
        """Return true if the lock is jammed."""
        return self._is_jammed

    @property
    def battery_level(self) -> int | None:
        """Return the battery level of the lock."""
        return self._attr_battery_level

    async def async_lock(self, **kwargs: Any) -> None:
        """Lock the lock."""
        if self._is_jammed:
            _LOGGER.warning(f"Virtual lock '{self._attr_name}' is jammed, cannot lock")
            return

        self._attr_state = LockState.LOCKED
        self._last_access = self.hass.util.dt.utcnow()
        self.async_write_ha_state()
        _LOGGER.debug(f"Virtual lock '{self._attr_name}' locked")

        # 触发模板更新事件
        if self._templates:
            self.hass.bus.async_fire(
                f"{DOMAIN}_lock_template_update",
                {
                    "entity_id": self.entity_id,
                    "device_id": self._config_entry_id,
                    "action": "lock",
                    "state": "locked",
                },
            )

        # 触发锁状态变化事件
        self.hass.bus.async_fire(
            f"{DOMAIN}_lock_state_changed",
            {
                "entity_id": self.entity_id,
                "device_id": self._config_entry_id,
                "lock_state": "locked",
                "timestamp": self._last_access.isoformat() if self._last_access else None,
            },
        )

    async def async_unlock(self, **kwargs: Any) -> None:
        """Unlock the lock."""
        if self._is_jammed:
            _LOGGER.warning(f"Virtual lock '{self._attr_name}' is jammed, cannot unlock")
            return

        self._attr_state = LockState.UNLOCKED
        self._last_access = self.hass.util.dt.utcnow()
        self.async_write_ha_state()
        _LOGGER.debug(f"Virtual lock '{self._attr_name}' unlocked")

        # 触发模板更新事件
        if self._templates:
            self.hass.bus.async_fire(
                f"{DOMAIN}_lock_template_update",
                {
                    "entity_id": self.entity_id,
                    "device_id": self._config_entry_id,
                    "action": "unlock",
                    "state": "unlocked",
                },
            )

        # 触发锁状态变化事件
        self.hass.bus.async_fire(
            f"{DOMAIN}_lock_state_changed",
            {
                "entity_id": self.entity_id,
                "device_id": self._config_entry_id,
                "lock_state": "unlocked",
                "timestamp": self._last_access.isoformat() if self._last_access else None,
            },
        )

        # 自动锁定（如果启用）
        if self._auto_lock_enabled:
            self.hass.loop.call_later(self._auto_lock_delay, self._auto_lock_callback)

    async def async_open(self, **kwargs: Any) -> None:
        """Open the lock (unlocked)."""
        await self.async_unlock(**kwargs)

    async def async_update(self) -> None:
        """Update lock state."""
        # 模拟电池消耗
        if self._attr_state == LockState.UNLOCKED:
            self._attr_battery_level = max(0, self._attr_battery_level - random.uniform(0.01, 0.05))
        else:
            self._attr_battery_level = max(0, self._attr_battery_level - random.uniform(0.001, 0.01))

        # 模拟随机卡滞（小概率）
        if random.random() < 0.01:  # 1% 概率卡滞
            self._is_jammed = True
            self.async_write_ha_state()
            _LOGGER.warning(f"Virtual lock '{self._attr_name}' is jammed")
        elif self._is_jammed and random.random() < 0.1:  # 10% 概率恢复
            self._is_jammed = False
            self.async_write_ha_state()
            _LOGGER.info(f"Virtual lock '{self._attr_name}' is no longer jammed")

        self.async_write_ha_state()

    def _auto_lock_callback(self) -> None:
        """Callback for auto-lock functionality."""
        if self._attr_state == LockState.UNLOCKED and self._auto_lock_enabled:
            self.hass.create_task(self.async_lock())
            _LOGGER.debug(f"Virtual lock '{self._attr_name}' auto-locked")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        attrs = {
            "lock_type": LOCK_TYPES.get(self._lock_type, self._lock_type),
            "auto_lock_enabled": self._auto_lock_enabled,
            "auto_lock_delay": self._auto_lock_delay,
            "is_jammed": self._is_jammed,
        }

        if self._last_access:
            attrs["last_access"] = self._last_access.isoformat()

        return attrs