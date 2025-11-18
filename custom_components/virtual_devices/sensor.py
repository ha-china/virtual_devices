"""Sensor platform for virtual devices integration."""
from __future__ import annotations

import logging
import random
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfPressure,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_ENTITIES,
    CONF_ENTITY_NAME,
    DEVICE_TYPE_SENSOR,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

# 传感器类型配置
SENSOR_TYPE_CONFIG = {
    "temperature": {
        "device_class": SensorDeviceClass.TEMPERATURE,
        "unit": UnitOfTemperature.CELSIUS,
        "state_class": SensorStateClass.MEASUREMENT,
        "range": (-30, 50),
        "icon": "mdi:thermometer",
    },
    "humidity": {
        "device_class": SensorDeviceClass.HUMIDITY,
        "unit": PERCENTAGE,
        "state_class": SensorStateClass.MEASUREMENT,
        "range": (0, 100),
        "icon": "mdi:water-percent",
    },
    "pressure": {
        "device_class": SensorDeviceClass.PRESSURE,
        "unit": UnitOfPressure.HPA,
        "state_class": SensorStateClass.MEASUREMENT,
        "range": (950, 1050),
        "icon": "mdi:gauge",
    },
    "illuminance": {
        "device_class": None,
        "unit": "lx",
        "state_class": SensorStateClass.MEASUREMENT,
        "range": (0, 100000),
        "icon": "mdi:brightness-6",
    },
    "power": {
        "device_class": SensorDeviceClass.POWER,
        "unit": UnitOfPower.WATT,
        "state_class": SensorStateClass.MEASUREMENT,
        "range": (0, 5000),
        "icon": "mdi:flash",
    },
    "energy": {
        "device_class": SensorDeviceClass.ENERGY,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "range": (0, 10000),
        "icon": "mdi:lightning-bolt",
    },
    "voltage": {
        "device_class": SensorDeviceClass.VOLTAGE,
        "unit": UnitOfElectricPotential.VOLT,
        "state_class": SensorStateClass.MEASUREMENT,
        "range": (0, 500),
        "icon": "mdi:lightning-bolt-outline",
    },
    "current": {
        "device_class": SensorDeviceClass.CURRENT,
        "unit": UnitOfElectricCurrent.AMPERE,
        "state_class": SensorStateClass.MEASUREMENT,
        "range": (0, 50),
        "icon": "mdi:current-ac",
    },
    "battery": {
        "device_class": SensorDeviceClass.BATTERY,
        "unit": PERCENTAGE,
        "state_class": SensorStateClass.MEASUREMENT,
        "range": (0, 100),
        "icon": "mdi:battery",
    },
}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up virtual sensor entities using unified service."""
    from .unified_service import UnifiedServiceManager

    manager = UnifiedServiceManager(hass)
    await manager.setup_platform("sensor", config_entry, async_add_entities)


class VirtualSensor(SensorEntity):
    """Representation of a virtual sensor."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry_id: str,
        entity_config: dict[str, Any],
        index: int,
        device_info: dict[str, Any],
    ) -> None:
        """Initialize the virtual sensor."""
        self._config_entry_id = config_entry_id
        self._entity_config = entity_config
        self._index = index
        self._device_info = device_info
        self._hass = hass

        entity_name = entity_config.get(CONF_ENTITY_NAME, f"sensor_{index + 1}")
        self._attr_name = entity_name
        self._attr_unique_id = f"{config_entry_id}_sensor_{index}"
        self._attr_device_info = device_info

        # 传感器特定配置
        sensor_type = entity_config.get("sensor_type", "temperature")
        self._sensor_type = sensor_type

        # 获取传感器类型配置
        type_config = SENSOR_TYPE_CONFIG.get(sensor_type, {})

        # 设置传感器属性
        self._attr_device_class = type_config.get("device_class")
        self._attr_native_unit_of_measurement = type_config.get("unit")
        self._attr_state_class = type_config.get("state_class")
        self._attr_icon = type_config.get("icon", "mdi:eye")

        # 传感器状态
        self._attr_native_value = self._generate_initial_value(type_config)

        # 模拟设置
        self._simulation_enabled = entity_config.get("enable_simulation", True)
        self._update_frequency = entity_config.get("update_frequency", 30)  # 秒

    def _generate_initial_value(self, type_config: dict[str, Any]) -> Any:
        """根据传感器类型生成初始值。"""
        if self._sensor_type == "temperature":
            return round(random.uniform(18, 25), 1)
        elif self._sensor_type == "humidity":
            return round(random.uniform(30, 70), 1)
        elif self._sensor_type == "pressure":
            return round(random.uniform(980, 1020), 1)
        elif self._sensor_type == "illuminance":
            return round(random.uniform(100, 1000), 1)
        elif self._sensor_type in ["power", "voltage", "current"]:
            range_vals = type_config.get("range", (0, 100))
            return round(random.uniform(range_vals[0], range_vals[1]), 1)
        elif self._sensor_type == "battery":
            return random.randint(20, 100)
        else:
            return 0

    async def async_update(self) -> None:
        """Update sensor value if simulation is enabled."""
        if self._simulation_enabled:
            # 模拟传感器数值变化
            if self._sensor_type == "temperature":
                self._attr_native_value = round(random.uniform(18, 28), 1)
            elif self._sensor_type == "humidity":
                self._attr_native_value = round(random.uniform(30, 80), 1)
            elif self._sensor_type == "pressure":
                self._attr_native_value = round(random.uniform(980, 1030), 1)
            elif self._sensor_type == "battery":
                # 电池电量变化较慢
                current = self._attr_native_value if isinstance(self._attr_native_value, (int, float)) else 50
                change = random.uniform(-5, 5)
                new_value = max(0, min(100, current + change))
                self._attr_native_value = round(new_value)
            elif self._sensor_type == "illuminance":
                self._attr_native_value = round(random.uniform(0, 5000), 1)
            else:
                # 其他传感器类型
                type_config = SENSOR_TYPE_CONFIG.get(self._sensor_type, {})
                range_vals = type_config.get("range", (0, 100))
                self._attr_native_value = round(random.uniform(range_vals[0], range_vals[1]), 1)