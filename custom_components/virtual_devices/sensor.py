"""Platform for virtual sensor integration."""
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
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_ENTITIES,
    CONF_ENTITY_NAME,
    DEVICE_TYPE_SENSOR,
    DOMAIN,
    ENTITY_CATEGORIES,
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
        "device_class": None,  # ILLUMINANCE might not be available in HA 2025.10.0
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
    "signal_strength": {
        "device_class": None,  # SIGNAL_STRENGTH might not be available in HA 2025.10.0
        "unit": "dBm",
        "state_class": SensorStateClass.MEASUREMENT,
        "range": (-120, 0),
        "icon": "mdi:wifi",
    },
    "pm25": {
        "device_class": None,  # PM25 might not be available in HA 2025.10.0
        "unit": "µg/m³",
        "state_class": SensorStateClass.MEASUREMENT,
        "range": (0, 500),
        "icon": "mdi:air-filter",
    },
    "pm10": {
        "device_class": None,  # PM10 might not be available in HA 2025.10.0
        "unit": "µg/m³",
        "state_class": SensorStateClass.MEASUREMENT,
        "range": (0, 600),
        "icon": "mdi:air-filter",
    },
    "co2": {
        "device_class": None,  # HA没有CO2的device_class
        "unit": "ppm",
        "state_class": SensorStateClass.MEASUREMENT,
        "range": (400, 2000),
        "icon": "mdi:molecule-co2",
    },
    "voc": {
        "device_class": None,  # VOC might not be available in HA 2025.10.0
        "unit": "µg/m³",
        "state_class": SensorStateClass.MEASUREMENT,
        "range": (0, 1000),
        "icon": "mdi:chemical-weapon",
    },
    "formaldehyde": {
        "device_class": None,
        "unit": "mg/m³",
        "state_class": SensorStateClass.MEASUREMENT,
        "range": (0, 1),
        "icon": "mdi:chemical-weapon",
    },
    "noise": {
        "device_class": None,
        "unit": "dB",
        "state_class": SensorStateClass.MEASUREMENT,
        "range": (30, 120),
        "icon": "mdi:volume-high",
    },
    "uv_index": {
        "device_class": None,
        "unit": None,
        "state_class": SensorStateClass.MEASUREMENT,
        "range": (0, 15),
        "icon": "mdi:weather-sunny",
    },
    "rainfall": {
        "device_class": None,  # PRECIPITATION might not be available in HA 2025.10.0
        "unit": "mm",
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "range": (0, 1000),
        "icon": "mdi:weather-rainy",
    },
    "wind_speed": {
        "device_class": None,  # WIND_SPEED might not be available in HA 2025.10.0
        "unit": "km/h",
        "state_class": SensorStateClass.MEASUREMENT,
        "range": (0, 200),
        "icon": "mdi:weather-windy",
    },
    "water_quality": {
        "device_class": None,
        "unit": None,
        "state_class": None,
        "range": (0, 100),
        "icon": "mdi:water-check",
    },
    "ph": {
        "device_class": None,
        "unit": "pH",
        "state_class": SensorStateClass.MEASUREMENT,
        "range": (0, 14),
        "icon": "mdi:ph",
    },
}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up virtual sensor entities."""
    device_type = config_entry.data.get("device_type")

    # 只有传感器类型的设备才设置传感器实体
    if device_type != DEVICE_TYPE_SENSOR:
        return

    device_info = hass.data[DOMAIN][config_entry.entry_id]["device_info"]
    entities = []
    entities_config = config_entry.data.get(CONF_ENTITIES, [])

    for idx, entity_config in enumerate(entities_config):
        entity = VirtualSensor(
            config_entry.entry_id,
            entity_config,
            idx,
            device_info,
        )
        entities.append(entity)

    async_add_entities(entities)


class VirtualSensor(SensorEntity):
    """Representation of a virtual sensor."""

    def __init__(
        self,
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

        entity_name = entity_config.get(CONF_ENTITY_NAME, f"sensor_{index + 1}")
        self._attr_name = entity_name
        self._attr_unique_id = f"{config_entry_id}_sensor_{index}"
        self._attr_device_info = device_info

        # 获取传感器类型配置
        sensor_type = entity_config.get("sensor_type", "temperature")
        type_config = SENSOR_TYPE_CONFIG.get(sensor_type, {})

        self._attr_device_class = type_config.get("device_class")
        self._attr_native_unit_of_measurement = type_config.get("unit")
        self._attr_state_class = type_config.get("state_class")
        self._attr_icon = type_config.get("icon")
        self._value_range = type_config.get("range", (0, 100))

        # 设置实体类别
        self._attr_entity_category = ENTITY_CATEGORIES.get(sensor_type)

        # Template support
        self._templates = entity_config.get("templates", {})
        self._template_value = None

        # 特殊传感器类型处理
        self._sensor_type = sensor_type
        self._last_energy_value = 0  # 用于电量传感器累积

        # 生成初始值
        self._attr_native_value = self._generate_value()

    @property
    def native_value(self):
        """Return the native value of the sensor."""
        return self._template_value if self._template_value is not None else self._attr_native_value

    def _generate_value(self) -> float:
        """Generate a realistic value within range for the sensor type."""
        min_val, max_val = self._value_range

        # 根据传感器类型生成更真实的数据
        if self._sensor_type == "temperature":
            # 温度：使用正弦波动，模拟日常温度变化
            import time
            base_temp = (min_val + max_val) / 2
            variation = (max_val - min_val) / 4
            value = base_temp + variation * random.uniform(-1, 1)

        elif self._sensor_type == "humidity":
            # 湿度：通常在40-70%之间
            value = random.uniform(40, 70)

        elif self._sensor_type == "pressure":
            # 气压：通常在标准气压附近
            value = random.uniform(980, 1030)

        elif self._sensor_type == "illuminance":
            # 照度：根据时间模拟光照变化
            import time
            hour = int(time.time() / 3600) % 24
            if 6 <= hour <= 18:  # 白天
                value = random.uniform(100, 10000)
            else:  # 夜晚
                value = random.uniform(0, 100)

        elif self._sensor_type == "battery":
            # 电池：缓慢下降
            if not hasattr(self, '_battery_value'):
                self._battery_value = random.uniform(20, 100)
            self._battery_value = max(0, self._battery_value - random.uniform(0, 0.1))
            value = self._battery_value

        elif self._sensor_type == "signal_strength":
            # 信号强度：通常在-40到-80之间
            value = random.uniform(-80, -40)

        elif self._sensor_type == "energy":
            # 电量：累积值
            if self._last_energy_value > 0:
                increment = random.uniform(0.001, 0.01)
                value = self._last_energy_value + increment
            else:
                value = random.uniform(0, 1)
            self._last_energy_value = value

        elif self._sensor_type == "co2":
            # CO2：通常在400-1000ppm之间
            value = random.uniform(400, 1000)

        elif self._sensor_type == "pm25":
            # PM2.5：根据空气质量生成
            quality = random.choice(['good', 'moderate', 'unhealthy'])
            if quality == 'good':
                value = random.uniform(0, 35)
            elif quality == 'moderate':
                value = random.uniform(35, 75)
            else:
                value = random.uniform(75, 150)

        elif self._sensor_type == "uv_index":
            # 紫外线指数：根据时间模拟
            import time
            hour = int(time.time() / 3600) % 24
            if 11 <= hour <= 16:  # 中午时分
                value = random.uniform(6, 11)
            elif 6 <= hour <= 18:  # 白天其他时间
                value = random.uniform(1, 6)
            else:  # 夜晚
                value = 0

        else:
            # 其他传感器类型：使用随机值
            value = random.uniform(min_val, max_val)

        # 根据传感器类型确定小数位数
        if self._sensor_type in ["temperature", "humidity", "ph"]:
            return round(value, 1)
        elif self._sensor_type in ["battery", "signal_strength", "co2"]:
            return round(value, 0)
        elif self._sensor_type in ["energy", "rainfall"]:
            return round(value, 3)
        else:
            return round(value, 2)

    async def async_update(self) -> None:
        """Update the sensor value."""
        if not self._templates:
            # 如果没有模板配置，则生成随机值
            self._attr_native_value = self._generate_value()

        # 触发模板更新事件（如果有模板配置）
        if self._templates:
            self.hass.bus.async_fire(
                f"{DOMAIN}_sensor_template_update",
                {
                    "entity_id": self.entity_id,
                    "device_id": self._config_entry_id,
                    "sensor_type": self._entity_config.get("sensor_type"),
                    "current_value": self._attr_native_value,
                },
            )

    def set_template_value(self, value: float) -> None:
        """Set sensor value from template."""
        self._template_value = value
        self.async_write_ha_state()
