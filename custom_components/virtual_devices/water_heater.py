"""Platform for virtual water heater integration."""
from __future__ import annotations

import logging
import random
from typing import Any

from homeassistant.components.water_heater import (
    WaterHeaterEntity,
    WaterHeaterEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_TEMPERATURE,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_ENTITIES,
    CONF_ENTITY_NAME,
    DEVICE_TYPE_WATER_HEATER,
    DOMAIN,
    TEMPLATE_ENABLED_DEVICE_TYPES,
    WATER_HEATER_TYPES,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up virtual water heater entities."""
    device_type = config_entry.data.get("device_type")

    # 只有热水器类型的设备才设置热水器实体
    if device_type != DEVICE_TYPE_WATER_HEATER:
        return

    device_info = hass.data[DOMAIN][config_entry.entry_id]["device_info"]
    entities = []
    entities_config = config_entry.data.get(CONF_ENTITIES, [])

    for idx, entity_config in enumerate(entities_config):
        entity = VirtualWaterHeater(
            config_entry.entry_id,
            entity_config,
            idx,
            device_info,
        )
        entities.append(entity)

    async_add_entities(entities)


class VirtualWaterHeater(WaterHeaterEntity):
    """Representation of a virtual water heater."""

    def __init__(
        self,
        config_entry_id: str,
        entity_config: dict[str, Any],
        index: int,
        device_info: dict[str, Any],
    ) -> None:
        """Initialize the virtual water heater."""
        self._config_entry_id = config_entry_id
        self._entity_config = entity_config
        self._index = index
        self._device_info = device_info

        entity_name = entity_config.get(CONF_ENTITY_NAME, f"water_heater_{index + 1}")
        self._attr_name = entity_name
        self._attr_unique_id = f"{config_entry_id}_water_heater_{index}"
        self._attr_device_info = device_info
        self._attr_icon = "mdi:water-boiler"

        # Template support
        self._templates = entity_config.get("templates", {})

        # 支持的功能
        self._attr_supported_features = (
            WaterHeaterEntityFeature.TARGET_TEMPERATURE
            | WaterHeaterEntityFeature.OPERATION_MODE
            | WaterHeaterEntityFeature.AWAY_MODE
        )

        # 热水器类型
        heater_type = entity_config.get("heater_type", "electric")
        self._heater_type = heater_type

        # 根据类型设置图标和参数
        icon_map = {
            "electric": "mdi:water-boiler",
            "gas": "mdi:fire",
            "solar": "mdi:solar-power",
            "heat_pump": "mdi:heat-pump",
            "tankless": "mdi:water-boiler-outline",
        }
        self._attr_icon = icon_map.get(heater_type, "mdi:water-boiler")

        # 初始状态
        self._attr_operation_mode = "off"
        self._attr_away_mode = False

        # 温度设置
        self._attr_current_temperature = entity_config.get("current_temperature", 25)
        self._attr_target_temperature = entity_config.get("target_temperature", 60)

        # 根据热水器类型设置合理的温度范围
        if heater_type == "electric":
            self._attr_min_temp = 40
            self._attr_max_temp = 75
        elif heater_type == "gas":
            self._attr_min_temp = 35
            self._attr_max_temp = 80
        elif heater_type == "solar":
            self._attr_min_temp = 45
            self._attr_max_temp = 70
        elif heater_type == "heat_pump":
            self._attr_min_temp = 35
            self._attr_max_temp = 65
        else:  # tankless
            self._attr_min_temp = 35
            self._attr_max_temp = 60

        self._attr_temperature_unit = UnitOfTemperature.CELSIUS

        # 能耗相关
        self._attr_current_operation = None
        self._attr_energy_consumed_today = entity_config.get("energy_consumed_today", 5.0)  # kWh
        self._attr_power_consumption = 0  # W
        self._attr_total_energy_consumed = entity_config.get("total_energy_consumed", 1000.0)  # kWh

        # 容量和效率
        self._tank_capacity = entity_config.get("tank_capacity", 80)  # 升
        self._efficiency = entity_config.get("efficiency", 0.9)  # 90%效率

        # 加热状态
        self._is_heating = False
        self._heating_start_time = None
        self._last_update = None

    @property
    def current_temperature(self) -> float | None:
        """Return the current temperature."""
        return self._attr_current_temperature

    @property
    def target_temperature(self) -> float | None:
        """Return the target temperature."""
        return self._attr_target_temperature

    @property
    def min_temp(self) -> float:
        """Return the minimum temperature."""
        return self._attr_min_temp

    @property
    def max_temp(self) -> float:
        """Return the maximum temperature."""
        return self._attr_max_temp

    @property
    def operation_mode(self) -> str | None:
        """Return the current operation mode."""
        return self._attr_operation_mode

    @property
    def away_mode(self) -> bool:
        """Return the away mode."""
        return self._attr_away_mode

    @property
    def current_operation(self) -> str | None:
        """Return the current operation."""
        return self._attr_current_operation

    @property
    def energy_consumed_today(self) -> float | None:
        """Return the energy consumed today in kWh."""
        return self._attr_energy_consumed_today

    @property
    def power_consumption(self) -> float | None:
        """Return the current power consumption in W."""
        return self._attr_power_consumption

    @property
    def total_energy_consumed(self) -> float | None:
        """Return the total energy consumed in kWh."""
        return self._attr_total_energy_consumed

    async def async_set_temperature(self, **kwargs) -> None:
        """Set new target temperature."""
        temperature = kwargs.get("temperature")
        if temperature is None:
            return

        if self._attr_min_temp <= temperature <= self._attr_max_temp:
            self._attr_target_temperature = temperature
            self.async_write_ha_state()
            _LOGGER.debug(f"Virtual water heater '{self._attr_name}' target temperature set to {temperature}°C")

            # 触发模板更新事件
            if self._templates:
                self.hass.bus.async_fire(
                    f"{DOMAIN}_water_heater_template_update",
                    {
                        "entity_id": self.entity_id,
                        "device_id": self._config_entry_id,
                        "action": "set_temperature",
                        "temperature": temperature,
                    },
                )

    async def async_set_operation_mode(self, operation_mode: str) -> None:
        """Set new operation mode."""
        self._attr_operation_mode = operation_mode
        self._update_heating_state()
        self.async_write_ha_state()
        _LOGGER.debug(f"Virtual water heater '{self._attr_name}' operation mode set to {operation_mode}")

        # 触发模板更新事件
        if self._templates:
            self.hass.bus.async_fire(
                f"{DOMAIN}_water_heater_template_update",
                {
                    "entity_id": self.entity_id,
                    "device_id": self._config_entry_id,
                    "action": "set_operation_mode",
                    "operation_mode": operation_mode,
                },
            )

    async def async_turn_away_mode_on(self) -> None:
        """Turn away mode on."""
        self._attr_away_mode = True
        self.async_write_ha_state()
        _LOGGER.debug(f"Virtual water heater '{self._attr_name}' away mode turned on")

        # 触发模板更新事件
        if self._templates:
            self.hass.bus.async_fire(
                f"{DOMAIN}_water_heater_template_update",
                {
                    "entity_id": self.entity_id,
                    "device_id": self._config_entry_id,
                    "action": "turn_away_mode_on",
                },
            )

    async def async_turn_away_mode_off(self) -> None:
        """Turn away mode off."""
        self._attr_away_mode = False
        self.async_write_ha_state()
        _LOGGER.debug(f"Virtual water heater '{self._attr_name}' away mode turned off")

        # 触发模板更新事件
        if self._templates:
            self.hass.bus.async_fire(
                f"{DOMAIN}_water_heater_template_update",
                {
                    "entity_id": self.entity_id,
                    "device_id": self._config_entry_id,
                    "action": "turn_away_mode_off",
                },
            )

    def _update_heating_state(self) -> None:
        """Update heating state based on operation mode."""
        import time

        was_heating = self._is_heating

        if self._attr_operation_mode == "heat":
            # 检查是否需要加热
            if self._attr_current_temperature < self._attr_target_temperature - 2:  # 2度容差
                if not self._is_heating:
                    self._is_heating = True
                    self._heating_start_time = time.time()
                    self._attr_current_operation = "heating"
            elif self._attr_current_temperature >= self._attr_target_temperature:
                if self._is_heating:
                    self._is_heating = False
                    self._heating_start_time = None
                    self._attr_current_operation = "idle"
            else:
                self._attr_current_operation = "maintaining"
        else:
            # 非加热模式
            self._is_heating = False
            self._heating_start_time = None
            self._attr_current_operation = "idle"

        # 如果加热状态改变，更新功率
        if was_heating != self._is_heating:
            self._update_power_consumption()

    def _update_power_consumption(self) -> None:
        """Update power consumption based on heating state and heater type."""
        if self._is_heating:
            # 根据热水器类型设置功率
            power_map = {
                "electric": random.uniform(2000, 3000),  # 2-3kW
                "gas": random.uniform(3000, 5000),        # 3-5kW
                "solar": random.uniform(1000, 2000),     # 1-2kW
                "heat_pump": random.uniform(800, 1500),   # 0.8-1.5kW
                "tankless": random.uniform(5000, 8000),  # 5-8kW
            }
            self._attr_power_consumption = round(power_map.get(self._heater_type, 2000), 0)
        else:
            # 待机功率
            standby_power_map = {
                "electric": random.uniform(5, 15),      # 5-15W
                "gas": random.uniform(10, 30),          # 10-30W
                "solar": random.uniform(2, 5),           # 2-5W
                "heat_pump": random.uniform(5, 20),        # 5-20W
                "tankless": random.uniform(5, 10),        # 5-10W
            }
            self._attr_power_consumption = round(standby_power_map.get(self._heater_type, 10), 0)

    async def async_update(self) -> None:
        """Update water heater state."""
        import time

        # 模拟温度变化
        if self._is_heating and self._attr_operation_mode == "heat":
            if self._heating_start_time:
                elapsed = time.time() - self._heating_start_time
                # 根据热水器类型计算加热速度
                heating_rate_map = {
                    "electric": 0.5,    # 0.5°C/分钟
                    "gas": 1.2,          # 1.2°C/分钟
                    "solar": 0.3,        # 0.3°C/分钟
                    "heat_pump": 0.4,    # 0.4°C/分钟
                    "tankless": 2.0,     # 2.0°C/分钟
                }
                heating_rate = heating_rate_map.get(self._heater_type, 0.5)

                temp_increase = (heating_rate * elapsed / 60) * self._efficiency
                self._attr_current_temperature = min(
                    self._attr_target_temperature,
                    self._attr_current_temperature + temp_increase
                )
        else:
            # 自然冷却
            if self._attr_current_temperature > 20:  # 室温基准
                cooling_rate = 0.1  # 0.1°C/分钟
                time_diff = time.time() - (self._last_update or time.time())
                self._attr_current_temperature = max(
                    20,
                    self._attr_current_temperature - (cooling_rate * time_diff / 60)
                )

        # 更新能耗
        self._last_update = time.time()
        if self._attr_power_consumption > 0:
            # 计算本次更新的能耗 (kWh)
            time_diff = 1.0 / 3600  # 假设每秒更新一次
            energy_increase = (self._attr_power_consumption / 1000) * time_diff

            self._attr_energy_consumed_today += energy_increase
            self._attr_total_energy_consumed += energy_increase

        # 更新加热状态
        self._update_heating_state()

        self.async_write_ha_state()

        # 触发模板更新事件
        if self._templates:
            self.hass.bus.async_fire(
                f"{DOMAIN}_water_heater_template_update",
                {
                    "entity_id": self.entity_id,
                    "device_id": self._config_entry_id,
                    "current_temperature": self._attr_current_temperature,
                    "target_temperature": self._attr_target_temperature,
                    "operation_mode": self._attr_operation_mode,
                    "is_heating": self._is_heating,
                    "power_consumption": self._attr_power_consumption,
                },
            )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        attrs = {
            "heater_type": WATER_HEATER_TYPES.get(self._heater_type, self._heater_type),
            "tank_capacity": f"{self._tank_capacity}L",
            "efficiency": f"{self._efficiency * 100:.0f}%",
            "is_heating": self._is_heating,
        }

        if self._heating_start_time:
            import time
            attrs["heating_duration"] = round(time.time() - self._heating_start_time, 1)

        # 添加热水器特定属性
        if self._heater_type == "solar":
            attrs["solar_boost_available"] = random.choice([True, False])
        elif self._heater_type == "gas":
            attrs["pilot_light_on"] = self._is_heating

        return attrs