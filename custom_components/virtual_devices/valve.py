"""Platform for virtual valve integration."""
from __future__ import annotations

import asyncio
import logging
import random
from typing import Any

from homeassistant.components.valve import (
    ValveEntity,
    ValveEntityFeature,
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
    CONF_VALVE_POSITION,
    CONF_VALVE_REPORTS_POSITION,
    DEVICE_TYPE_VALVE,
    DOMAIN,
    TEMPLATE_ENABLED_DEVICE_TYPES,
    VALVE_TYPES,
)

STORAGE_VERSION = 1

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up virtual valve entities."""
    device_type = config_entry.data.get("device_type")

    # 只有水阀类型的设备才设置水阀实体
    if device_type != DEVICE_TYPE_VALVE:
        return

    device_info = hass.data[DOMAIN][config_entry.entry_id]["device_info"]
    entities = []
    entities_config = config_entry.data.get(CONF_ENTITIES, [])

    for idx, entity_config in enumerate(entities_config):
        entity = VirtualValve(
            hass,
            config_entry.entry_id,
            entity_config,
            idx,
            device_info,
        )
        entities.append(entity)

    async_add_entities(entities)

    # 为每个实体添加初始化回调
    for entity in entities:
        # 延迟初始化状态，确保 hass 已经设置
        hass.async_create_task(
            entity._async_initialize_state()
        )


class VirtualValve(ValveEntity):
    """Representation of a virtual valve."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry_id: str,
        entity_config: dict[str, Any],
        index: int,
        device_info: dict[str, Any],
    ) -> None:
        """Initialize the virtual valve."""
        self._config_entry_id = config_entry_id
        self._entity_config = entity_config
        self._index = index
        self._device_info = device_info
        self._hass = hass

        entity_name = entity_config.get(CONF_ENTITY_NAME, f"valve_{index + 1}")
        self._attr_name = entity_name
        self._attr_unique_id = f"{config_entry_id}_valve_{index}"
        self._attr_device_info = device_info

        # Template support
        self._templates = entity_config.get("templates", {})

        # 存储实体状态
        self._store = Store[dict[str, Any]](hass, STORAGE_VERSION, f"virtual_devices_valve_{config_entry_id}_{index}")

        # 运行时间设置（秒）
        self._travel_time = entity_config.get(CONF_TRAVEL_TIME, 10)  # 默认10秒完成全行程
        self._is_moving = False  # 是否正在移动
        self._start_position = None  # 开始位置
        self._start_time = None  # 开始移动的时间

        # 水阀类型
        valve_type = entity_config.get("valve_type", "water_valve")
        self._valve_type = valve_type

        # 根据类型设置图标
        icon_map = {
            "water_valve": "mdi:valve",
            "gas_valve": "mdi:valve-open",
            "irrigation": "mdi:sprinkler",
            "zone_valve": "mdi:valve-closed",
        }
        self._attr_icon = icon_map.get(valve_type, "mdi:valve")

        # 支持的功能
        self._attr_supported_features = (
            ValveEntityFeature.OPEN
            | ValveEntityFeature.CLOSE
            | ValveEntityFeature.SET_POSITION
            | ValveEntityFeature.STOP
        )

        # 是否报告位置
        self._attr_reports_position = entity_config.get(CONF_VALVE_REPORTS_POSITION, True)

        # 初始位置
        self._attr_current_position = entity_config.get(CONF_VALVE_POSITION, 0)

        # 水阀属性
        self._is_opening = False
        self._is_closing = False
        self._target_position = self._attr_current_position

        # 流量相关（模拟）
        self._flow_rate = 0  # L/min
        self._total_flow = 0  # L
        self._valve_size = entity_config.get("valve_size", 25)  # mm

        # 水压相关
        self._pressure = 0  # bar

        # 注意：不能在这里调用 async_write_ha_state()，因为 hass 还没有设置

    async def _async_initialize_state(self) -> None:
        """Initialize state after entity is added to hass."""
        if self.hass is not None:
            # 先加载保存的状态
            await self.async_load_state()
            # 然后写入状态
            self.async_write_ha_state()

    async def async_load_state(self) -> None:
        """Load saved state from storage."""
        try:
            data = await self._store.async_load()
            if data:
                self._attr_current_position = data.get("current_position", 0)
                self._target_position = data.get("target_position", self._attr_current_position)
                # 重置移动状态，避免重启后卡在移动中
                self._is_moving = False
                self._is_opening = False
                self._is_closing = False
                self._start_position = None
                self._start_time = None
                _LOGGER.info(f"Valve '{self._attr_name}' state loaded from storage - position: {self._attr_current_position}%")
        except Exception as ex:
            _LOGGER.error(f"Failed to load state for valve '{self._attr_name}': {ex}")

    async def async_save_state(self) -> None:
        """Save current state to storage."""
        try:
            data = {
                "current_position": self._attr_current_position,
                "is_moving": self._is_moving,
                "target_position": self._target_position,
            }
            await self._store.async_save(data)
        except Exception as ex:
            _LOGGER.error(f"Failed to save state for valve '{self._attr_name}': {ex}")

    async def async_added_to_hass(self) -> None:
        """Call when entity is added to hass."""
        await super().async_added_to_hass()
        # 加载保存的状态
        await self.async_load_state()
        # 监听配置更新
        self.async_on_remove(
            self.hass.config_entries.async_get_entry(self._config_entry_id).add_update_listener(
                self._async_config_updated
            )
        )

    async def _async_config_updated(
        self, config_entry: ConfigEntry
    ) -> None:
        """Handle configuration update."""
        # 重新加载配置
        new_entities = config_entry.data.get(CONF_ENTITIES, [])
        if self._index < len(new_entities):
            new_config = new_entities[self._index]
            # 更新本地配置
            self._travel_time = new_config.get(CONF_TRAVEL_TIME, self._travel_time)

            # 保存新状态
            await self.async_save_state()
            self.async_write_ha_state()

            _LOGGER.info(f"Valve '{self._attr_name}' configuration updated: travel_time={self._travel_time}s")

    @property
    def current_position(self) -> int:
        """Return current position of valve."""
        return self._attr_current_position

    @property
    def status(self) -> str:
        """Return the status of the valve."""
        if self._is_opening:
            return "opening"
        elif self._is_closing:
            return "closing"
        elif self._attr_current_position == 0:
            return "closed"
        elif self._attr_current_position == 100:
            return "open"
        else:
            return "normal"

    @property
    def is_closed(self) -> bool:
        """Return true if valve is closed."""
        return self._attr_current_position == 0

    @property
    def is_opening(self) -> bool:
        """Return true if valve is opening."""
        return self._is_opening

    @property
    def is_closing(self) -> bool:
        """Return true if valve is closing."""
        return self._is_closing

    async def async_open_valve(self) -> None:
        """Open the valve."""
        if self._attr_current_position == 100:
            _LOGGER.debug(f"Virtual valve '{self._attr_name}' is already fully open")
            return

        self._is_opening = True
        self._is_closing = False
        await self._move_to_position(100)

        _LOGGER.debug(f"Virtual valve '{self._attr_name}' opening")

        # 触发模板更新事件
        if self._templates:
            self.hass.bus.async_fire(
                f"{DOMAIN}_valve_template_update",
                {
                    "entity_id": self.entity_id,
                    "device_id": self._config_entry_id,
                    "action": "open",
                    "target_position": 100,
                },
            )

    async def async_close_valve(self) -> None:
        """Close the valve."""
        if self._attr_current_position == 0:
            _LOGGER.debug(f"Virtual valve '{self._attr_name}' is already fully closed")
            return

        self._is_closing = True
        self._is_opening = False
        await self._move_to_position(0)

        _LOGGER.debug(f"Virtual valve '{self._attr_name}' closing")

        # 触发模板更新事件
        if self._templates:
            self.hass.bus.async_fire(
                f"{DOMAIN}_valve_template_update",
                {
                    "entity_id": self.entity_id,
                    "device_id": self._config_entry_id,
                    "action": "close",
                    "target_position": 0,
                },
            )

    def _position_update_callback(self) -> None:
        """Callback for position update animation."""
        if self._is_opening:
            self._attr_current_position = self._target_position
            self._is_opening = False
        elif self._is_closing:
            self._attr_current_position = self._target_position
            self._is_closing = False

        # 更新流量
        if self._attr_current_position > 0:
            # 根据阀门开度计算流量
            self._flow_rate = round(self._attr_current_position * 0.1 * (self._valve_size / 25), 2)
            # 根据阀门类型设置压力
            if self._valve_type == "water_valve":
                self._pressure = round(2 + (self._attr_current_position / 100) * 3, 1)
            elif self._valve_type == "gas_valve":
                self._pressure = round(0.5 + (self._attr_current_position / 100) * 2, 1)
        else:
            self._flow_rate = 0
            self._pressure = 0

        self.async_write_ha_state()
        _LOGGER.debug(f"Virtual valve '{self._attr_name}' position updated to {self._attr_current_position}%")

    async def async_set_valve_position(self, position: int) -> None:
        """Set the valve to a specific position."""
        if not 0 <= position <= 100:
            _LOGGER.warning(f"Invalid valve position: {position}. Must be between 0 and 100")
            return

        if position == self._attr_current_position:
            _LOGGER.debug(f"Virtual valve '{self._attr_name}' is already at position {position}")
            return

        # 确定操作方向
        if position > self._attr_current_position:
            self._is_opening = True
            self._is_closing = False
        elif position < self._attr_current_position:
            self._is_closing = True
            self._is_opening = False

        await self._move_to_position(position)

        _LOGGER.debug(f"Virtual valve '{self._attr_name}' moving to position {position}%")

        # 触发模板更新事件
        if self._templates:
            self.hass.bus.async_fire(
                f"{DOMAIN}_valve_template_update",
                {
                    "entity_id": self.entity_id,
                    "device_id": self._config_entry_id,
                    "action": "set_position",
                    "position": position,
                },
            )

    async def async_stop_valve(self) -> None:
        """Stop the valve."""
        self._is_opening = False
        self._is_closing = False
        self.async_write_ha_state()
        _LOGGER.debug(f"Virtual valve '{self._attr_name}' stopped")

        # 触发模板更新事件
        if self._templates:
            self.hass.bus.async_fire(
                f"{DOMAIN}_valve_template_update",
                {
                    "entity_id": self.entity_id,
                    "device_id": self._config_entry_id,
                    "action": "stop",
                },
            )

    async def async_update(self) -> None:
        """Update valve state."""
        # 如果正在移动，继续更新位置
        if self._is_moving and self._start_time is not None:
            await self._update_position_during_movement()
            return

        # 累计流量（如果有流量）
        if self._flow_rate > 0:
            # 假设每秒更新一次，流量转换为升
            flow_increment = self._flow_rate / 60
            self._total_flow += flow_increment

        # 模拟压力波动
        if self._pressure > 0:
            self._pressure += random.uniform(-0.1, 0.1)
            self._pressure = max(0, self._pressure)

        # 只在没有主动移动时更新流量和压力
        if not self._is_moving:
            # 更新流量和压力
            if self._attr_current_position > 0:
                self._flow_rate = round(self._attr_current_position * 0.1 * (self._valve_size / 25), 2)
                if self._valve_type == "water_valve":
                    self._pressure = round(2 + (self._attr_current_position / 100) * 3, 1)
                elif self._valve_type == "gas_valve":
                    self._pressure = round(0.5 + (self._attr_current_position / 100) * 2, 1)
            else:
                self._flow_rate = 0
                self._pressure = 0

        self.async_write_ha_state()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        attrs = {
            "valve_type": VALVE_TYPES.get(self._valve_type, self._valve_type),
            "valve_size": f"{self._valve_size}mm",
            "target_position": self._target_position,
            "reports_position": self._attr_reports_position,
        }

        if self._flow_rate > 0:
            attrs["flow_rate"] = f"{self._flow_rate} L/min"

        if self._total_flow > 0:
            attrs["total_flow"] = f"{round(self._total_flow, 2)} L"

        if self._pressure > 0:
            attrs["pressure"] = f"{self._pressure} bar"

        return attrs

    async def _move_to_position(self, target_position: int) -> None:
        """Move valve to target position with travel time simulation."""
        if target_position == self._attr_current_position:
            return

        self._is_moving = True
        self._target_position = target_position
        self._start_position = self._attr_current_position
        self._start_time = self._hass.loop.time()

        _LOGGER.debug(f"Valve '{self._attr_name}' moving from {self._attr_current_position}% to {target_position}% (travel time: {self._travel_time}s)")

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

        self._attr_current_position = new_position

        # 更新流量和压力
        if self._attr_current_position > 0:
            self._flow_rate = round(self._attr_current_position * 0.1 * (self._valve_size / 25), 2)
            if self._valve_type == "water_valve":
                self._pressure = round(2 + (self._attr_current_position / 100) * 3, 1)
            elif self._valve_type == "gas_valve":
                self._pressure = round(0.5 + (self._attr_current_position / 100) * 2, 1)
        else:
            self._flow_rate = 0
            self._pressure = 0

        # 保存状态并更新HA
        await self.async_save_state()
        self.async_write_ha_state()

        # 检查是否到达目标位置
        if self._attr_current_position == self._target_position:
            self._is_moving = False
            self._is_opening = False
            self._is_closing = False

            # 保存最终状态
            await self.async_save_state()
            self.async_write_ha_state()

            action = "opened" if self._attr_current_position == 100 else "closed" if self._attr_current_position == 0 else f"moved to {self._attr_current_position}%"
            _LOGGER.debug(f"Virtual valve '{self._attr_name}' {action}")
        else:
            # 继续移动，0.5秒后再次检查
            await asyncio.sleep(0.5)
            await self._update_position_during_movement()