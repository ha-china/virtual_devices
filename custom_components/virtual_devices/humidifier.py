"""Platform for virtual humidifier integration."""
from __future__ import annotations

import logging
import random
from datetime import datetime
from typing import Any

from homeassistant.components.humidifier import (
    HumidifierEntity,
    HumidifierEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
# ATTR_HUMIDITY 不存在，移除此导入
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.storage import Store

STORAGE_VERSION = 1

from .const import (
    CONF_ENTITIES,
    CONF_ENTITY_NAME,
    DEVICE_TYPE_HUMIDIFIER,
    DOMAIN,
    TEMPLATE_ENABLED_DEVICE_TYPES,
    HUMIDIFIER_TYPES,
    NOISE_LEVELS,
    POWER_STATES,
    HUMIDIFIER_SPECIAL_FEATURES,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up virtual humidifier entities."""
    device_type = config_entry.data.get("device_type")

    _LOGGER.info(f"Setting up humidifier for device type: {device_type}")

    # 只有加湿器类型的设备才设置加湿器实体
    if device_type != DEVICE_TYPE_HUMIDIFIER:
        _LOGGER.info(f"Skipping humidifier setup - device type is {device_type}, not {DEVICE_TYPE_HUMIDIFIER}")
        return

    device_info = hass.data[DOMAIN][config_entry.entry_id]["device_info"]
    entities = []
    entities_config = config_entry.data.get(CONF_ENTITIES, [])
    _LOGGER.info(f"Found {len(entities_config)} humidifier entities to create")

    for idx, entity_config in enumerate(entities_config):
        entity_name = entity_config.get(CONF_ENTITY_NAME, f"Humidifier_{idx + 1}")
        _LOGGER.info(f"Creating humidifier entity {idx + 1}: {entity_name}")

        entity = VirtualHumidifier(
            hass,
            config_entry.entry_id,
            entity_config,
            idx,
            device_info,
        )
        entities.append(entity)

    _LOGGER.info(f"Adding {len(entities)} humidifier entities to Home Assistant")
    async_add_entities(entities)


class VirtualHumidifier(HumidifierEntity):
    """Representation of a virtual humidifier."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry_id: str,
        entity_config: dict[str, Any],
        index: int,
        device_info: dict[str, Any],
    ) -> None:
        """Initialize the virtual humidifier."""
        self._config_entry_id = config_entry_id
        self._entity_config = entity_config
        self._index = index
        self._device_info = device_info
        self._hass = hass

        entity_name = entity_config.get(CONF_ENTITY_NAME, f"Humidifier_{index + 1}")
        self._attr_name = entity_name
        self._attr_unique_id = f"{config_entry_id}_humidifier_{index}"

        # 加湿器类型 - 必须在调用 _get_enhanced_device_info() 之前设置
        humidifier_type = entity_config.get("humidifier_type", "ultrasonic")
        self._humidifier_type = humidifier_type

        # 根据类型设置图标
        icon_map = {
            "ultrasonic": "mdi:air-humidifier",
            "evaporative": "mdi:air-filter",
            "steam": "mdi:water",
            "impeller": "mdi:fan",
            "warm_mist": "mdi:water-thermometer",
        }
        self._attr_icon = icon_map.get(humidifier_type, "mdi:air-humidifier")

        # Template support
        self._templates = entity_config.get("templates", {})

        # 存储实体状态
        self._store = Store[dict[str, Any]](hass, STORAGE_VERSION, f"virtual_devices_humidifier_{config_entry_id}_{index}")

        # 支持的功能
        self._attr_supported_features = HumidifierEntityFeature(0)

        # 初始状态
        self._attr_is_on = False
        self._attr_target_humidity = entity_config.get("target_humidity", 60)
        self._attr_current_humidity = entity_config.get("current_humidity", 45)
        self._attr_mode = "Auto"

        # 根据加湿器类型设置参数
        self._setup_humidifier_features()

        # 水箱相关
        self._water_level = entity_config.get("water_level", 80)  # %
        self._tank_capacity = entity_config.get("tank_capacity", 4.0)  # 升

        # 维护相关
        self._filter_life_time = entity_config.get("filter_life_time", 2160)  # 小时 (90天)
        self._filter_usage_time = 0
        self._needs_filter_replacement = False

        # 运行统计
        self._total_water_consumed = entity_config.get("total_water_consumed", 100.0)  # 升
        self._running_time = 0
        self._last_update = datetime.now()

        # 设置设备信息（必须在所有属性设置后）
        self._attr_device_info = self._get_enhanced_device_info()

        _LOGGER.info(f"Virtual humidifier '{self._attr_name}' initialized with type '{self._humidifier_type}'")
        _LOGGER.info(f"Humidifier device info: {self._attr_device_info}")

    async def async_load_state(self) -> None:
        """Load saved state from storage."""
        try:
            data = await self._store.async_load()
            if data:
                self._attr_is_on = data.get("is_on", False)
                self._attr_target_humidity = data.get("target_humidity", 60)
                self._attr_mode = data.get("mode", "Auto")
                self._water_level = data.get("water_level", 80)
                _LOGGER.info(f"Humidifier '{self._attr_name}' state loaded from storage")
        except Exception as ex:
            _LOGGER.error(f"Failed to load state for humidifier '{self._attr_name}': {ex}")

    async def async_save_state(self) -> None:
        """Save current state to storage."""
        try:
            data = {
                "is_on": self._attr_is_on,
                "target_humidity": self._attr_target_humidity,
                "mode": self._attr_mode,
                "water_level": self._water_level,
            }
            await self._store.async_save(data)
        except Exception as ex:
            _LOGGER.error(f"Failed to save state for humidifier '{self._attr_name}': {ex}")

    async def async_added_to_hass(self) -> None:
        """Call when entity is added to hass."""
        await super().async_added_to_hass()
        await self.async_load_state()

    def _get_enhanced_device_info(self) -> dict[str, Any]:
        """Get enhanced device information for humidifier."""
        base_info = self._device_info.copy()

        # 只添加有效的设备信息字段
        base_info.update({
            "model": f"Humidifier-{self._humidifier_type.title()}-{self._index + 1}",
            "manufacturer": "Virtual Devices",
        })

        return base_info

    def _get_coverage_area(self) -> str:
        """Get coverage area based on tank capacity and humidifier type."""
        area_map = {
            "ultrasonic": self._tank_capacity * 10,  # 10m² per liter
            "evaporative": self._tank_capacity * 8,   # 8m² per liter
            "steam": self._tank_capacity * 12,         # 12m² per liter
            "impeller": self._tank_capacity * 9,       # 9m² per liter
            "warm_mist": self._tank_capacity * 7,      # 7m² per liter
        }
        area = area_map.get(self._humidifier_type, self._tank_capacity * 10)
        return f"{area:.0f}"

    def _get_humidification_rate(self) -> str:
        """Get humidification rate based on humidifier type."""
        rate_map = {
            "ultrasonic": "300mL/h",
            "evaporative": "250mL/h",
            "steam": "400mL/h",
            "impeller": "350mL/h",
            "warm_mist": "280mL/h",
        }
        return rate_map.get(self._humidifier_type, "300mL/h")

    def _get_noise_level(self) -> str:
        """Get noise level based on humidifier type and mode."""
        if not self._attr_is_on:
            return "silent"

        base_noise = {
            "ultrasonic": "25-35dB",
            "evaporative": "30-40dB",
            "steam": "35-45dB",
            "impeller": "32-42dB",
            "warm_mist": "28-38dB",
        }

        if self._attr_mode == "Low":
            return f"low {base_noise.get(self._humidifier_type, '25-35dB').split('-')[0]}"
        elif self._attr_mode == "High":
            return f"high {base_noise.get(self._humidifier_type, '25-35dB').split('-')[1]}"
        else:
            return base_noise.get(self._humidifier_type, "25-35dB")

    def _get_power_consumption(self) -> str:
        """Get power consumption based on humidifier type and mode."""
        base_power = {
            "ultrasonic": 25,
            "evaporative": 40,
            "steam": 120,
            "impeller": 35,
            "warm_mist": 80,
        }
        base = base_power.get(self._humidifier_type, 25)

        if not self._attr_is_on:
            return "standby: 1W"
        else:
            mode_multiplier = {
                "Auto": 1.0,
                "Low": 0.7,
                "Medium": 1.0,
                "High": 1.3,
            }
            actual_power = base * mode_multiplier.get(self._attr_mode, 1.0)
            return f"running: {actual_power:.0f}W"

    def _get_special_features(self) -> str:
        """Get special features based on humidifier type."""
        features = []

        if self._humidifier_type == "ultrasonic":
            features.extend(HUMIDIFIER_SPECIAL_FEATURES["ultrasonic"])
        elif self._humidifier_type == "evaporative":
            features.extend(HUMIDIFIER_SPECIAL_FEATURES["evaporative"])
        elif self._humidifier_type == "steam":
            features.extend(HUMIDIFIER_SPECIAL_FEATURES["steam"])
        elif self._humidifier_type == "impeller":
            features.extend(HUMIDIFIER_SPECIAL_FEATURES["impeller"])
        elif self._humidifier_type == "warm_mist":
            features.extend(HUMIDIFIER_SPECIAL_FEATURES["warm_mist"])

        # 添加通用功能
        features.extend(HUMIDIFIER_SPECIAL_FEATURES["common"])

        return ", ".join(features)

    def _setup_humidifier_features(self) -> None:
        """Setup humidifier features based on type."""
        features = HumidifierEntityFeature(0)

        # 基础开关功能在HA 2025.10.0中是默认的，不需要明确声明

        # 根据类型添加特定功能
        if self._humidifier_type in ["ultrasonic", "impeller", "warm_mist"]:
            features |= HumidifierEntityFeature.MODES

        if self._humidifier_type == "steam":
            features |= HumidifierEntityFeature.MODES
            features |= HumidifierEntityFeature.TARGET_HUMIDITY

        if self._humidifier_type in ["evaporative", "impeller"]:
            features |= HumidifierEntityFeature.TARGET_HUMIDITY

        self._attr_supported_features = features

        # 设置支持的模式
        mode_map = {
            "ultrasonic": ["Auto", "Low", "Medium", "High"],
            "evaporative": ["Auto", "Low", "Medium", "High"],
            "steam": ["Auto", "Low", "High"],
            "impeller": ["Auto", "Low", "Medium", "High"],
            "warm_mist": ["Auto", "Low", "High"],
        }
        self._attr_available_modes = mode_map.get(self._humidifier_type, ["Auto"])

    @property
    def is_on(self) -> bool:
        """Return true if the humidifier is on."""
        return self._attr_is_on

    @property
    def current_humidity(self) -> int | None:
        """Return the current humidity."""
        return self._attr_current_humidity

    @property
    def target_humidity(self) -> int | None:
        """Return the humidity we try to reach."""
        return self._attr_target_humidity

    @property
    def mode(self) -> str | None:
        """Return the current mode."""
        return self._attr_mode

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return True

    @property
    def available_modes(self) -> list[str] | None:
        """Return the available modes."""
        return self._attr_available_modes

    @property
    def min_humidity(self) -> int | None:
        """Return the minimum humidity."""
        if self._humidifier_type in ["ultrasonic", "impeller", "warm_mist"]:
            return 30
        elif self._humidifier_type == "evaporative":
            return 20
        elif self._humidifier_type == "steam":
            return 40
        return 30

    @property
    def max_humidity(self) -> int | None:
        """Return the maximum humidity."""
        if self._humidifier_type in ["ultrasonic", "impeller", "warm_mist"]:
            return 80
        elif self._humidifier_type == "evaporative":
            return 70
        elif self._humidifier_type == "steam":
            return 90
        return 80

    async def async_turn_on(self) -> None:
        """Turn the humidifier on."""
        if not self._attr_is_on:
            self._attr_is_on = True
            self._running_time = 0
            self._last_update = datetime.now()
            await self.async_save_state()

            # 检查水位
            if self._water_level < 10:
                _LOGGER.warning(f"Virtual humidifier '{self._attr_name}' water level too low")
                return

            self.async_write_ha_state()
            _LOGGER.debug(f"Virtual humidifier '{self._attr_name}' turned on")

            # 触发模板更新事件
            if self._templates:
                self.hass.bus.async_fire(
                    f"{DOMAIN}_humidifier_template_update",
                    {
                        "entity_id": self.entity_id,
                        "device_id": self._config_entry_id,
                        "action": "turn_on",
                        "target_humidity": self._attr_target_humidity,
                        "mode": self._attr_mode,
                    },
                )

    async def async_turn_off(self) -> None:
        """Turn the humidifier off."""
        if self._attr_is_on:
            self._attr_is_on = False
            await self.async_save_state()
            self.async_write_ha_state()
            _LOGGER.debug(f"Virtual humidifier '{self._attr_name}' turned off")

            # 触发模板更新事件
            if self._templates:
                self.hass.bus.async_fire(
                    f"{DOMAIN}_humidifier_template_update",
                    {
                        "entity_id": self.entity_id,
                        "device_id": self._config_entry_id,
                        "action": "turn_off",
                    },
                )

    async def async_set_humidity(self, humidity: int) -> None:
        """Set the target humidity."""
        if self.min_humidity <= humidity <= self.max_humidity:
            self._attr_target_humidity = humidity
            await self.async_save_state()
            self.async_write_ha_state()
            _LOGGER.debug(f"Virtual humidifier '{self._attr_name}' target humidity set to {humidity}%")

            # 触发模板更新事件
            if self._templates:
                self.hass.bus.async_fire(
                    f"{DOMAIN}_humidifier_template_update",
                    {
                        "entity_id": self.entity_id,
                        "device_id": self._config_entry_id,
                        "action": "set_humidity",
                        "target_humidity": humidity,
                    },
                )

    async def async_set_mode(self, mode: str) -> None:
        """Set the mode of the humidifier."""
        if mode in self._attr_available_modes:
            self._attr_mode = mode
            await self.async_save_state()
            self.async_write_ha_state()
            _LOGGER.debug(f"Virtual humidifier '{self._attr_name}' mode set to {mode}")

            # 根据模式调整目标湿度
            if mode == "Low":
                self._attr_target_humidity = min(self.max_humidity, 50)
            elif mode == "High":
                self._attr_target_humidity = max(self.min_humidity, 70)
            else:  # Auto
                self._attr_target_humidity = 60

            # 触发模板更新事件
            if self._templates:
                self.hass.bus.async_fire(
                    f"{DOMAIN}_humidifier_template_update",
                    {
                        "entity_id": self.entity_id,
                        "device_id": self._config_entry_id,
                        "action": "set_mode",
                        "mode": mode,
                        "target_humidity": self._attr_target_humidity,
                    },
                )

    async def async_update(self) -> None:
        """Update humidifier state."""
        from datetime import datetime

        now = datetime.now()

        if self._attr_is_on and self._last_update:
            # 计算运行时间（秒）
            time_diff = (now - self._last_update).total_seconds()
            self._running_time += time_diff

            # 模拟湿度变化
            target_diff = self._attr_target_humidity - self._attr_current_humidity
            if abs(target_diff) > 1:
                # 根据加湿器类型设置加湿速率
                rate_map = {
                    "ultrasonic": 1.5,     # 1.5%/分钟
                    "evaporative": 2.0,   # 2.0%/分钟
                    "steam": 3.0,         # 3.0%/分钟
                    "impeller": 2.5,       # 2.5%/分钟
                    "warm_mist": 1.8,      # 1.8%/分钟
                }
                rate = rate_map.get(self._humidifier_type, 1.5)

                # 根据模式调整速率
                mode_multiplier = {
                    "Auto": 1.0,
                    "Low": 0.6,
                    "Medium": 1.0,
                    "High": 1.5,
                }
                rate *= mode_multiplier.get(self._attr_mode, 1.0)

                # 计算湿度变化
                temp_increase = (rate * time_diff / 60) * 0.9  # 90%效率
                self._attr_current_humidity = min(
                    self.max_humidity,
                    max(self.min_humidity,
                    self._attr_current_humidity + temp_increase if target_diff > 0 else -temp_increase * 0.5
                    )
                )

            # 消耗水量
            water_consumption_rate = {
                "ultrasonic": 0.2,    # 0.2L/小时
                "evaporative": 0.8,    # 0.8L/小时
                "steam": 0.5,         # 0.5L/小时
                "impeller": 0.6,       # 0.6L/小时
                "warm_mist": 0.3,      # 0.3L/小时
            }
            water_rate = water_consumption_rate.get(self._humidifier_type, 0.2)
            self._total_water_consumed += water_rate * time_diff / 3600
            self._water_level = max(0, self._water_level - (water_rate * time_diff / 3600) * 100 / self._tank_capacity)

            # 滤网使用寿命
            self._filter_usage_time += time_diff
            if self._filter_usage_time >= self._filter_life_time:
                self._needs_filter_replacement = True
                self._filter_usage_time = 0  # 重置计时器

        # 自然湿度变化（关闭时）
        if not self._attr_is_on:
            ambient_humidity = random.randint(30, 70)
            # 缓慢向环境湿度靠拢
            self._attr_current_humidity += (ambient_humidity - self._attr_current_humidity) * 0.1

        self._last_update = now
        self.async_write_ha_state()

        # 触发模板更新事件
        if self._templates:
            self.hass.bus.async_fire(
                f"{DOMAIN}_humidifier_template_update",
                {
                    "entity_id": self.entity_id,
                    "device_id": self._config_entry_id,
                    "current_humidity": self._attr_current_humidity,
                    "target_humidity": self._attr_target_humidity,
                    "water_level": self._water_level,
                    "running_time": self._running_time,
                },
            )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        _LOGGER.debug(f"Generating extra_state_attributes for humidifier '{self._attr_name}'")

        attrs = {
            "humidifier_type": HUMIDIFIER_TYPES.get(self._humidifier_type, self._humidifier_type),
            "water_level": f"{self._water_level}%",
            "tank_capacity": f"{self._tank_capacity}L",
            "coverage_area": f"{self._get_coverage_area()}m²",
            "humidification_rate": self._get_humidification_rate(),
            "filter_life_time": f"{self._filter_life_time}h",
            "filter_usage_time": f"{round(self._filter_usage_time, 1)}h",
            "needs_filter_replacement": self._needs_filter_replacement,
            "total_water_consumed": f"{round(self._total_water_consumed, 1)}L",
            "running_time": f"{round(self._running_time, 1)}h",
            "noise_level": self._get_noise_level(),
            "power_consumption": self._get_power_consumption(),
            "special_features": self._get_special_features(),
            "current_humidity": f"{self._attr_current_humidity}%",
            "target_humidity": f"{self._attr_target_humidity}%",
            "mode": self._attr_mode,
            "is_on": self._attr_is_on,
        }

        # 添加加湿器特定属性
        if self._humidifier_type == "ultrasonic":
            attrs["mist_output_level"] = "medium"
        elif self._humidifier_type == "steam":
            attrs["steam_output_level"] = "medium"
        elif self._humidifier_type == "warm_mist":
            attrs["temperature"] = "warm"

        _LOGGER.debug(f"Humidifier attributes: {attrs}")
        return attrs