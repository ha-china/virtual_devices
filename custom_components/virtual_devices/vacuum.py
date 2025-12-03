"""Platform for virtual vacuum integration."""
from __future__ import annotations

import logging
import random
from datetime import datetime
from typing import Any

from homeassistant.components.vacuum import (
    StateVacuumEntity,
    VacuumEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_ENTITIES,
    CONF_ENTITY_NAME,
    CONF_VACUUM_BATTERY_LEVEL,
    CONF_VACUUM_FAN_SPEED,
    CONF_VACUUM_STATUS,
    DEVICE_TYPE_VACUUM,
    DOMAIN,
    TEMPLATE_ENABLED_DEVICE_TYPES,
    VACUUM_FAN_SPEEDS,
    VACUUM_STATUS_TYPES,
    VACUUM_ROOMS,
    VACUUM_CLEANING_MODES,
)

_LOGGER = logging.getLogger(__name__)

# 扫地机预设区域
PRESET_ROOMS = list(VACUUM_ROOMS.values())

# 清洁模式
CLEANING_MODES = list(VACUUM_CLEANING_MODES.values())


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up virtual vacuum entities."""
    device_type = config_entry.data.get("device_type")

    # 只有扫地机器人类型的设备才设置扫地机器人实体
    if device_type != DEVICE_TYPE_VACUUM:
        return

    device_info = hass.data[DOMAIN][config_entry.entry_id]["device_info"]
    entities = []
    entities_config = config_entry.data.get(CONF_ENTITIES, [])

    for idx, entity_config in enumerate(entities_config):
        entity = VirtualVacuum(
            config_entry.entry_id,
            entity_config,
            idx,
            device_info,
        )
        entities.append(entity)

    async_add_entities(entities)


class VirtualVacuum(StateVacuumEntity):
    """Representation of a virtual vacuum."""

    def __init__(
        self,
        config_entry_id: str,
        entity_config: dict[str, Any],
        index: int,
        device_info: dict[str, Any],
    ) -> None:
        """Initialize the virtual vacuum."""
        self._config_entry_id = config_entry_id
        self._entity_config = entity_config
        self._index = index
        self._device_info = device_info

        entity_name = entity_config.get(CONF_ENTITY_NAME, f"vacuum_{index + 1}")
        self._attr_name = entity_name
        self._attr_unique_id = f"{config_entry_id}_vacuum_{index}"
        self._attr_device_info = device_info
        self._attr_icon = "mdi:robot-vacuum"

        # Template support
        self._templates = entity_config.get("templates", {})

        # 支持的功能 (移除 BATTERY 功能，HA 2026.8+ 将弃用)
        self._attr_supported_features = (
            # TURN_ON和TURN_OFF在HA 2025.10.0中是默认的
            VacuumEntityFeature.START
            | VacuumEntityFeature.STOP
            | VacuumEntityFeature.PAUSE
            | VacuumEntityFeature.RETURN_HOME
            | VacuumEntityFeature.CLEAN_SPOT
            | VacuumEntityFeature.LOCATE
            | VacuumEntityFeature.FAN_SPEED
            | VacuumEntityFeature.SEND_COMMAND
        )

        # 初始化状态 - StateVacuumEntity 使用 state 属性，不是 status
        initial_status = entity_config.get(CONF_VACUUM_STATUS, "docked")
        # 确保状态值符合 Home Assistant 的要求
        valid_states = ["docked", "cleaning", "paused", "returning", "idle", "error"]
        if initial_status not in valid_states:
            initial_status = "docked"
        self._attr_state = initial_status

        # 电池电量 (保留属性但不在功能中声明，避免弃用警告)
        self._battery_level = entity_config.get(CONF_VACUUM_BATTERY_LEVEL, 100)

        # 风扇速度
        fan_speeds = list(VACUUM_FAN_SPEEDS.keys())
        initial_fan_speed = entity_config.get(CONF_VACUUM_FAN_SPEED, "medium")
        self._attr_fan_speed = initial_fan_speed if initial_fan_speed in fan_speeds else fan_speeds[0]
        self._attr_fan_speed_list = fan_speeds

        # 清洁相关状态
        self._cleaning_started_at = None
        self._cleaning_duration = 0
        self._cleaned_area = 0  # 平方米
        self._current_room = None
        self._map_available = True  # 支持地图

        # 错误状态
        self._error_message = None
        
        _LOGGER.info(f"Virtual vacuum '{self._attr_name}' initialized with state: {self._attr_state}")

    @property
    def state(self) -> str:
        """Return the state of the vacuum cleaner."""
        return self._attr_state
    
    async def async_added_to_hass(self) -> None:
        """Called when entity is added to Home Assistant."""
        await super().async_added_to_hass()
        
        # 确保状态正确设置并立即更新
        self.async_write_ha_state()
        
        _LOGGER.info(f"Virtual vacuum '{self._attr_name}' added to Home Assistant with state: {self._attr_state}")

    @property
    def battery_level(self) -> int | None:
        """Return the battery level of the vacuum cleaner."""
        return self._battery_level

    @property
    def fan_speed(self) -> str | None:
        """Return the fan speed of the vacuum cleaner."""
        return self._attr_fan_speed

    @property
    def fan_speed_list(self) -> list[str] | None:
        """Get the list of available fan speed steps of the vacuum cleaner."""
        return self._attr_fan_speed_list

    async def async_start(self) -> None:
        """Start or resume the cleaning task."""
        if self._attr_state in ["docked", "returning", "idle"]:
            self._attr_state = "cleaning"
            self._cleaning_started_at = datetime.now()
            self._cleaned_area = 0
            self._current_room = random.choice(PRESET_ROOMS) if random.random() > 0.3 else None
            self.async_write_ha_state()
            _LOGGER.debug(f"Virtual vacuum '{self._attr_name}' started cleaning")

            # 触发模板更新事件
            if self._templates:
                self.hass.bus.async_fire(
                    f"{DOMAIN}_vacuum_template_update",
                    {
                        "entity_id": self.entity_id,
                        "device_id": self._config_entry_id,
                        "action": "start",
                        "status": self._attr_state,
                        "current_room": self._current_room,
                    },
                )

    async def async_pause(self) -> None:
        """Pause the cleaning task."""
        if self._attr_state == "cleaning":
            self._attr_state = "paused"
            if self._cleaning_started_at:
                self._cleaning_duration += (datetime.now() - self._cleaning_started_at).total_seconds()
                self._cleaning_started_at = None
            self.async_write_ha_state()
            _LOGGER.debug(f"Virtual vacuum '{self._attr_name}' paused cleaning")

            # 触发模板更新事件
            if self._templates:
                self.hass.bus.async_fire(
                    f"{DOMAIN}_vacuum_template_update",
                    {
                        "entity_id": self.entity_id,
                        "device_id": self._config_entry_id,
                        "action": "pause",
                        "status": self._attr_state,
                    },
                )

    async def async_stop(self, **kwargs: Any) -> None:
        """Stop the cleaning task."""
        if self._attr_state in ["cleaning", "paused"]:
            self._attr_state = "idle"
            if self._cleaning_started_at:
                self._cleaning_duration += (datetime.now() - self._cleaning_started_at).total_seconds()
                self._cleaning_started_at = None
            self.async_write_ha_state()
            _LOGGER.debug(f"Virtual vacuum '{self._attr_name}' stopped cleaning")

            # 触发模板更新事件
            if self._templates:
                self.hass.bus.async_fire(
                    f"{DOMAIN}_vacuum_template_update",
                    {
                        "entity_id": self.entity_id,
                        "device_id": self._config_entry_id,
                        "action": "stop",
                        "status": self._attr_state,
                        "cleaned_area": self._cleaned_area,
                        "cleaning_duration": self._cleaning_duration,
                    },
                )

    async def async_return_to_base(self, **kwargs: Any) -> None:
        """Set the vacuum cleaner to return to the dock."""
        if self._attr_state in ["cleaning", "paused"]:
            self._attr_state = "returning"
            if self._cleaning_started_at:
                self._cleaning_duration += (datetime.now() - self._cleaning_started_at).total_seconds()
                self._cleaning_started_at = None
            self.async_write_ha_state()
            _LOGGER.debug(f"Virtual vacuum '{self._attr_name}' returning to base")

            # 触发模板更新事件
            if self._templates:
                self.hass.bus.async_fire(
                    f"{DOMAIN}_vacuum_template_update",
                    {
                        "entity_id": self.entity_id,
                        "device_id": self._config_entry_id,
                        "action": "return_to_base",
                        "status": self._attr_state,
                    },
                )

            # 模拟返回充电座的时间
            self.hass.loop.call_later(30, self._dock_callback)

    async def async_clean_spot(self, **kwargs: Any) -> None:
        """Perform a spot clean-up."""
        self._attr_state = "cleaning"
        self._cleaning_started_at = datetime.now()
        self._current_room = "point_area"
        self._cleaned_area = random.uniform(2, 5)  # 2-5平方米
        self.async_write_ha_state()
        _LOGGER.debug(f"Virtual vacuum '{self._attr_name}' started spot cleaning")

        # 触发模板更新事件
        if self._templates:
            self.hass.bus.async_fire(
                f"{DOMAIN}_vacuum_template_update",
                {
                    "entity_id": self.entity_id,
                    "device_id": self._config_entry_id,
                    "action": "clean_spot",
                    "status": self._attr_state,
                    "cleaned_area": self._cleaned_area,
                },
            )

        # 点点清洁通常时间较短
        self.hass.loop.call_later(60, self._spot_cleaning_complete_callback)

    async def async_locate(self, **kwargs: Any) -> None:
        """Locate the vacuum cleaner."""
        _LOGGER.info(f"Virtual vacuum '{self._attr_name}' location beep")

        # 触发模板更新事件
        if self._templates:
            self.hass.bus.async_fire(
                f"{DOMAIN}_vacuum_template_update",
                {
                    "entity_id": self.entity_id,
                    "device_id": self._config_entry_id,
                    "action": "locate",
                },
            )

    async def async_set_fan_speed(self, fan_speed: str, **kwargs: Any) -> None:
        """Set fan speed of the vacuum."""
        if fan_speed in self._attr_fan_speed_list:
            self._attr_fan_speed = fan_speed
            self.async_write_ha_state()
            _LOGGER.debug(f"Virtual vacuum '{self._attr_name}' fan speed set to {fan_speed}")

            # 触发模板更新事件
            if self._templates:
                self.hass.bus.async_fire(
                    f"{DOMAIN}_vacuum_template_update",
                    {
                        "entity_id": self.entity_id,
                        "device_id": self._config_entry_id,
                        "action": "set_fan_speed",
                        "fan_speed": fan_speed,
                    },
                )

    async def async_send_command(self, command: str, params: dict[str, Any] | None = None, **kwargs: Any) -> None:
        """Send a command to a vacuum cleaner."""
        _LOGGER.debug(f"Virtual vacuum '{self._attr_name}' received command: {command} with params: {params}")

        if command == "clean_room" and params and "room" in params:
            # 清洁指定房间
            self._attr_state = "cleaning"
            self._cleaning_started_at = datetime.now()
            self._current_room = params["room"]
            self._cleaned_area = random.uniform(5, 15)  # 5-15平方米
            self.async_write_ha_state()

            # 触发模板更新事件
            if self._templates:
                self.hass.bus.async_fire(
                    f"{DOMAIN}_vacuum_template_update",
                    {
                        "entity_id": self.entity_id,
                        "device_id": self._config_entry_id,
                        "action": "clean_room",
                        "command": command,
                        "params": params,
                        "current_room": self._current_room,
                    },
                )

        elif command == "set_map":
            # 设置地图
            self._map_available = True
            self.async_write_ha_state()

        elif command == "get_cleaning_history":
            # 获取清洁历史（模拟返回）
            history = {
                "total_cleanings": random.randint(1, 50),
                "total_time": random.randint(100, 1000),
                "total_area": random.randint(100, 1000),
            }

            # 触发模板更新事件
            if self._templates:
                self.hass.bus.async_fire(
                    f"{DOMAIN}_vacuum_template_update",
                    {
                        "entity_id": self.entity_id,
                        "device_id": self._config_entry_id,
                        "action": "send_command",
                        "command": command,
                        "params": params,
                        "result": history,
                    },
                )

    async def async_turn_on(self) -> None:
        """Turn on the vacuum cleaner."""
        if self._attr_state in ["docked", "idle"]:
            self._attr_state = "cleaning"
            self._cleaning_started_at = datetime.now()
            self._current_room = random.choice(PRESET_ROOMS) if random.random() > 0.3 else None
            self.async_write_ha_state()
            _LOGGER.debug(f"Virtual vacuum '{self._attr_name}' turned on")

            # 触发模板更新事件
            if self._templates:
                self.hass.bus.async_fire(
                    f"{DOMAIN}_vacuum_template_update",
                    {
                        "entity_id": self.entity_id,
                        "device_id": self._config_entry_id,
                        "action": "turn_on",
                        "status": self._attr_state,
                        "current_room": self._current_room,
                    },
                )

    async def async_turn_off(self) -> None:
        """Turn off the vacuum cleaner."""
        if self._attr_state != "docked":
            self._attr_state = "returning"
            if self._cleaning_started_at:
                self._cleaning_duration += (datetime.now() - self._cleaning_started_at).total_seconds()
                self._cleaning_started_at = None
            self.async_write_ha_state()
            _LOGGER.debug(f"Virtual vacuum '{self._attr_name}' turning off")

            # 触发模板更新事件
            if self._templates:
                self.hass.bus.async_fire(
                    f"{DOMAIN}_vacuum_template_update",
                    {
                        "entity_id": self.entity_id,
                        "device_id": self._config_entry_id,
                        "action": "turn_off",
                        "status": self._attr_state,
                    },
                )

            # 模拟返回充电座的时间
            self.hass.loop.call_later(30, self._dock_callback)

    async def async_update(self) -> None:
        """Update vacuum state and battery."""
        # 更新电池电量
        if self._attr_state == "cleaning":
            # 清洁时消耗电量
            self._battery_level = max(0, self._battery_level - random.uniform(0.1, 0.3))
        elif self._attr_state == "returning":
            # 返回时也消耗电量
            self._battery_level = max(0, self._battery_level - random.uniform(0.2, 0.4))
        elif self._attr_state == "docked":
            # 充电时增加电量
            self._battery_level = min(100, self._battery_level + random.uniform(0.5, 1.0))

        # 检查低电量自动返回
        if self._attr_state == "cleaning" and self._battery_level < 20:
            await self.async_return_to_base()

        # 更新清洁进度
        if self._attr_state == "cleaning" and self._cleaning_started_at:
            elapsed_time = (datetime.now() - self._cleaning_started_at).total_seconds()

            # 根据风扇速度计算清洁面积
            speed_multiplier = {
                "quiet": 0.8,
                "low": 1.0,
                "medium": 1.2,
                "high": 1.5,
                "turbo": 1.8,
            }.get(self._attr_fan_speed, 1.0)

            self._cleaned_area = min(100, elapsed_time * speed_multiplier * random.uniform(0.1, 0.2))

            # 模拟随机错误（小概率）
            if random.random() < 0.01:  # 1% 概率出现错误
                self._attr_state = "error"
                self._error_message = "virtual_sensor_error"
                self.async_write_ha_state()

        # 返回充电座完成
        if self._attr_state == "returning" and self._battery_level < 30:
            # 模拟到达充电座
            if random.random() < 0.1:  # 10% 概率到达
                self._attr_state = "docked"
                self._current_room = None
                self.async_write_ha_state()

        self.async_write_ha_state()

    def _dock_callback(self) -> None:
        """Callback for when vacuum reaches dock."""
        if self._attr_state == "returning":
            self._attr_state = "docked"
            self._current_room = None
            self.async_write_ha_state()
            _LOGGER.debug(f"Virtual vacuum '{self._attr_name}' reached dock")

            # 触发模板更新事件
            if self._templates:
                self.hass.bus.async_fire(
                    f"{DOMAIN}_vacuum_template_update",
                    {
                        "entity_id": self.entity_id,
                        "device_id": self._config_entry_id,
                        "action": "docked",
                        "status": self._attr_state,
                    },
                )

    def _spot_cleaning_complete_callback(self) -> None:
        """Callback for when spot cleaning is complete."""
        if self._attr_state == "cleaning" and self._current_room == "point_area":
            self._attr_state = "idle"
            self._cleaning_started_at = None
            self._current_room = None
            self.async_write_ha_state()
            _LOGGER.debug(f"Virtual vacuum '{self._attr_name}' completed spot cleaning")

            # 触发模板更新事件
            if self._templates:
                self.hass.bus.async_fire(
                    f"{DOMAIN}_vacuum_template_update",
                    {
                        "entity_id": self.entity_id,
                        "device_id": self._config_entry_id,
                        "action": "spot_cleaning_complete",
                        "status": self._attr_state,
                    },
                )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        attrs = {}

        if self._cleaned_area > 0:
            attrs["cleaned_area"] = round(self._cleaned_area, 1)

        if self._cleaning_duration > 0:
            attrs["cleaning_duration"] = round(self._cleaning_duration, 1)

        if self._current_room:
            attrs["current_room"] = self._current_room

        if self._error_message:
            attrs["error"] = self._error_message

        attrs["map_available"] = self._map_available

        # 添加清洁模式
        attrs["available_cleaning_modes"] = CLEANING_MODES

        # 添加可用房间
        attrs["available_rooms"] = PRESET_ROOMS

        return attrs