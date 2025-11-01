"""Platform for virtual valve integration."""
from __future__ import annotations

import logging
import random
from typing import Any

from homeassistant.components.valve import (
    ValveEntity,
    ValveEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_ENTITIES,
    CONF_ENTITY_NAME,
    CONF_VALVE_POSITION,
    CONF_VALVE_REPORTS_POSITION,
    DEVICE_TYPE_VALVE,
    DOMAIN,
    TEMPLATE_ENABLED_DEVICE_TYPES,
    VALVE_TYPES,
)

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

        entity_name = entity_config.get(CONF_ENTITY_NAME, f"valve_{index + 1}")
        self._attr_name = entity_name
        self._attr_unique_id = f"{config_entry_id}_valve_{index}"
        self._attr_device_info = device_info

        # Template support
        self._templates = entity_config.get("templates", {})

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
            self.async_write_ha_state()

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

        self._target_position = 100
        self._is_opening = True
        self._is_closing = False

        # 如果支持位置报告，模拟渐变过程
        if self._attr_reports_position:
            self.hass.loop.call_later(2, self._position_update_callback)
        else:
            self._attr_current_position = 100
            self.async_write_ha_state()

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

        self._target_position = 0
        self._is_closing = True
        self._is_opening = False

        # 如果支持位置报告，模拟渐变过程
        if self._attr_reports_position:
            self.hass.loop.call_later(2, self._position_update_callback)
        else:
            self._attr_current_position = 0
            self.async_write_ha_state()

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

        self._target_position = position

        # 确定操作方向
        if position > self._attr_current_position:
            self._is_opening = True
            self._is_closing = False
        elif position < self._attr_current_position:
            self._is_closing = True
            self._is_opening = False

        # 如果支持位置报告，模拟渐变过程
        if self._attr_reports_position:
            self.hass.loop.call_later(2, self._position_update_callback)
        else:
            self._attr_current_position = position
            self.async_write_ha_state()

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
        # 累计流量（如果有流量）
        if self._flow_rate > 0:
            # 假设每秒更新一次，流量转换为升
            flow_increment = self._flow_rate / 60
            self._total_flow += flow_increment

        # 模拟压力波动
        if self._pressure > 0:
            self._pressure += random.uniform(-0.1, 0.1)
            self._pressure = max(0, self._pressure)

        # 确保状态正确更新
        if self._is_opening or self._is_closing:
            # 如果正在开启或关闭，继续模拟过程
            if self._is_opening:
                self._attr_current_position = min(self._target_position, self._attr_current_position + 5)
                if self._attr_current_position >= self._target_position:
                    self._is_opening = False
            elif self._is_closing:
                self._attr_current_position = max(self._target_position, self._attr_current_position - 5)
                if self._attr_current_position <= self._target_position:
                    self._is_closing = False

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