"""Platform for virtual air purifier integration."""
from __future__ import annotations

import asyncio
import logging
import random
from datetime import datetime
from typing import Any

from homeassistant.components.fan import (
    FanEntity,
    FanEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.storage import Store

STORAGE_VERSION = 1

from .const import (
    CONF_ENTITIES,
    CONF_ENTITY_NAME,
    DEVICE_TYPE_AIR_PURIFIER,
    DOMAIN,
    TEMPLATE_ENABLED_DEVICE_TYPES,
    AIR_PURIFIER_TYPES,
    AQI_LEVELS,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up virtual air purifier entities."""
    device_type = config_entry.data.get("device_type")
    _LOGGER.info(f"Setting up air purifier entities for device type: {device_type}")

    # Only air purifier devices set air purifier entities
    if device_type != DEVICE_TYPE_AIR_PURIFIER:
        _LOGGER.debug(f"Device type is {device_type}, not air purifier, skipping setup")
        return

    device_info = hass.data[DOMAIN][config_entry.entry_id]["device_info"]
    entities = []
    entities_config = config_entry.data.get(CONF_ENTITIES, [])
    _LOGGER.info(f"Found {len(entities_config)} air purifier entities to set up")

    for idx, entity_config in enumerate(entities_config):
        _LOGGER.info(f"Creating air purifier entity {idx + 1}: {entity_config}")
        entity = VirtualAirPurifier(
            hass,
            config_entry.entry_id,
            entity_config,
            idx,
            device_info,
        )
        entities.append(entity)
        _LOGGER.info(f"Air purifier entity created: {entity.entity_id}")

    async_add_entities(entities)
    _LOGGER.info(f"Added {len(entities)} air purifier entities to Home Assistant")


class VirtualAirPurifier(FanEntity):
    """Representation of a virtual air purifier."""

    @property
    def icon(self) -> str | None:
        """Return the icon to use in the frontend."""
        return self._attr_icon

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry_id: str,
        entity_config: dict[str, Any],
        index: int,
        device_info: dict[str, Any],
    ) -> None:
        """Initialize the virtual air purifier."""
        self._config_entry_id = config_entry_id
        self._entity_config = entity_config
        self._index = index
        self._device_info = device_info
        self._hass = hass

        entity_name = entity_config.get(CONF_ENTITY_NAME, f"Air Purifier_{index + 1}")
        self._attr_name = entity_name
        self._attr_unique_id = f"{config_entry_id}_air_purifier_{index}"
        self._attr_icon = "mdi:air-purifier"

        # Template support
        self._templates = entity_config.get("templates", {})

        # 存储实体状态
        self._store = Store[dict[str, Any]](hass, STORAGE_VERSION, f"virtual_devices_air_purifier_{config_entry_id}_{index}")

        # Air purifier type - must be set before calling _get_enhanced_device_info()
        purifier_type = entity_config.get("purifier_type", "hepa")
        self._purifier_type = purifier_type

        # 根据类型设置图标和参数
        icon_map = {
            "hepa": "mdi:air-filter",
            "activated_carbon": "mdi:air-filter",
            "uv_c": "mdi:lightbulb",
            "ionic": "mdi:creation",
            "ozone": "mdi:weather-tornado",
            "hybrid": "mdi:air-purifier",
        }
        self._attr_icon = icon_map.get(purifier_type, "mdi:air-purifier")

        # 支持的功能
        self._attr_supported_features = (
            FanEntityFeature.TURN_ON
            | FanEntityFeature.TURN_OFF
            | FanEntityFeature.SET_SPEED
            | FanEntityFeature.OSCILLATE
        )

        # 设置设备信息（必须在所有属性设置后）
        self._attr_device_info = self._get_enhanced_device_info()

        # 初始状态
        self._attr_is_on = False
        self._attr_percentage = entity_config.get("fan_speed", 0)
        self._attr_oscillating = False

        # 根据净化器类型设置速度
        self._setup_purifier_features()

        # 空气质量相关
        self._pm25 = entity_config.get("pm25", 35)  # µg/m³
        self._pm10 = entity_config.get("pm10", 50)  # µg/m³
        self._co2 = entity_config.get("co2", 400)  # ppm
        self._voc = entity_config.get("voc", 0.3)  # mg/m³
        self._formaldehyde = entity_config.get("formaldehyde", 0.05)  # mg/m³

        # 滤网状态
        self._filter_life = entity_config.get("filter_life", 80)  # %
        self._filter_usage_hours = 0
        self._filter_max_hours = 2160  # 90 days

        # 清洁相关
        self._is_cleaning = False
        self._auto_mode = False
        self._sleep_mode = False
        self._child_lock = False

        # 运行统计
        self._total_air_cleaned = entity_config.get("total_air_cleaned", 50000)  # m³
        self._running_time = 0
        self._last_update = None

        # 房间大小 (m³)
        self._room_volume = entity_config.get("room_volume", 50)  # 20m² × 2.5m height

        # 净化速率 (m³/h)
        self._cleaning_rate = self._get_cleaning_rate()

        _LOGGER.info(f"Virtual air purifier '{self._attr_name}' initialized with type '{self._purifier_type}'")
        _LOGGER.info(f"Air purifier device info: {self._attr_device_info}")
        _LOGGER.info(f"Initial attributes - PM2.5: {self._pm25}, PM10: {self._pm10}, Filter Life: {self._filter_life}")

    async def async_load_state(self) -> None:
        """Load saved state from storage."""
        try:
            data = await self._store.async_load()
            if data:
                self._attr_is_on = data.get("is_on", False)
                self._attr_percentage = data.get("percentage", 0)
                self._attr_oscillating = data.get("oscillating", False)
                _LOGGER.info(f"Air purifier '{self._attr_name}' state loaded from storage")
        except Exception as ex:
            _LOGGER.error(f"Failed to load state for air purifier '{self._attr_name}': {ex}")

    async def async_save_state(self) -> None:
        """Save current state to storage."""
        try:
            data = {
                "is_on": self._attr_is_on,
                "percentage": self._attr_percentage,
                "oscillating": self._attr_oscillating,
            }
            await self._store.async_save(data)
        except Exception as ex:
            _LOGGER.error(f"Failed to save state for air purifier '{self._attr_name}': {ex}")

    async def async_added_to_hass(self) -> None:
        """Call when entity is added to hass."""
        await super().async_added_to_hass()
        await self.async_load_state()

        # 确保在添加到 HA 后立即设置初始状态
        self._last_update = datetime.now()

        # 立即触发状态更新，确保属性可见
        self.async_write_ha_state()

        # 等待一小段时间后再次更新，确保所有属性都被正确设置和显示
        async def delayed_update():
            await asyncio.sleep(0.5)
            self.async_write_ha_state()
            _LOGGER.info(f"Air purifier '{self._attr_name}' state updated after adding to HA")

        self.hass.async_create_task(delayed_update())

        attrs = self.extra_state_attributes
        _LOGGER.info(f"Air purifier '{self._attr_name}' added to Home Assistant")
        _LOGGER.info(f"  - State: {self._attr_is_on}, Percentage: {self._attr_percentage}")
        _LOGGER.info(f"  - Attributes count: {len(attrs)}")
        _LOGGER.info(f"  - Sample: PM2.5={attrs.get('pm25', 'N/A')}, Filter Life={attrs.get('filter_life', 'N/A')}, AQI={attrs.get('aqi', 'N/A')}")
        _LOGGER.debug(f"  - All attributes keys: {list(attrs.keys())}")

    def _get_enhanced_device_info(self) -> dict[str, Any]:
        """Get enhanced device information for air purifier."""
        base_info = self._device_info.copy()

        # 只添加有效的设备信息字段
        base_info.update({
            "model": f"Air Purifier-{self._purifier_type.upper()}-{self._index + 1}",
            "manufacturer": "Virtual Devices",
        })

        return base_info

    def _get_filter_type(self) -> str:
        """Get filter type based on purifier type."""
        from .const import AIR_PURIFIER_FILTER_TYPES
        return AIR_PURIFIER_FILTER_TYPES.get(self._purifier_type, "standard")

    def _get_noise_level(self) -> str:
        """Get noise level range based on purifier type and speed."""
        if self._attr_percentage == 0:
            return "silent"
        elif self._attr_percentage <= 25:
            return "25-35dB"
        elif self._attr_percentage <= 50:
            return "35-45dB"
        elif self._attr_percentage <= 75:
            return "45-55dB"
        else:
            return "55-65dB"

    def _get_power_consumption(self) -> str:
        """Get power consumption based on purifier type and speed."""
        base_power = {
            "hepa": 50,
            "activated_carbon": 40,
            "uv_c": 60,
            "ionic": 30,
            "ozone": 35,
            "hybrid": 70,
        }
        base = base_power.get(self._purifier_type, 50)

        if self._attr_percentage == 0:
            return "standby: 2W"
        else:
            actual_power = base * (self._attr_percentage / 100)
            return f"running: {actual_power:.0f}W"

    def _setup_purifier_features(self) -> None:
        """Setup air purifier features based on type."""
        # 根据净化器类型设置速度范围
        speed_map = {
            "hepa": [0, 25, 50, 75, 100],
            "activated_carbon": [0, 33, 66, 100],
            "uv_c": [0, 50, 100],
            "ionic": [0, 25, 50, 75, 100],
            "ozone": [0, 50, 100],
            "hybrid": [0, 20, 40, 60, 80, 100],
        }
        self._speed_list = speed_map.get(self._purifier_type, [0, 50, 100])

    def _get_cleaning_rate(self) -> float:
        """Get cleaning rate based on purifier type and fan speed."""
        base_rates = {
            "hepa": 200,        # 200 m³/h
            "activated_carbon": 180,  # 180 m³/h
            "uv_c": 150,        # 150 m³/h
            "ionic": 120,       # 120 m³/h
            "ozone": 100,       # 100 m³/h
            "hybrid": 250,      # 250 m³/h
        }
        base_rate = base_rates.get(self._purifier_type, 150)

        # 根据当前风扇速度调整
        if self._attr_percentage > 0:
            speed_factor = self._attr_percentage / 100
            return base_rate * speed_factor
        return 0

    @property
    def is_on(self) -> bool:
        """Return true if the air purifier is on."""
        return self._attr_is_on

    @property
    def percentage(self) -> int | None:
        """Return the current speed percentage."""
        if self._attr_is_on:
            return self._attr_percentage
        return 0

    @property
    def current_speed(self) -> str | None:
        """Return the current speed."""
        if not self._attr_is_on or self._attr_percentage == 0:
            return "off"

        if self._attr_percentage <= 25:
            return "low"
        elif self._attr_percentage <= 50:
            return "medium"
        elif self._attr_percentage <= 75:
            return "high"
        else:
            return "turbo"

    @property
    def speed_count(self) -> int:
        """Return the number of speeds the fan supports."""
        return len(self._speed_list)

    @property
    def oscillating(self) -> bool:
        """Return true if the purifier is oscillating."""
        return self._attr_oscillating

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Turn the air purifier on."""
        if not self._attr_is_on:
            self._attr_is_on = True
            self._attr_percentage = percentage if percentage is not None else 50
            self._running_time = 0
            self._last_update = datetime.now()
            await self.async_save_state()

            # 检查滤网寿命
            if self._filter_life < 10:
                _LOGGER.warning(f"Virtual air purifier '{self._attr_name}' filter needs replacement")
                return

            self.async_write_ha_state()
            _LOGGER.debug(f"Virtual air purifier '{self._attr_name}' turned on")

            # 触发模板更新事件
            if self._templates:
                self.hass.bus.async_fire(
                    f"{DOMAIN}_air_purifier_template_update",
                    {
                        "entity_id": self.entity_id,
                        "device_id": self._config_entry_id,
                        "action": "turn_on",
                        "speed": self.current_speed,
                        "percentage": self._attr_percentage,
                    },
                )

    async def async_turn_off(self) -> None:
        """Turn the air purifier off."""
        if self._attr_is_on:
            self._attr_is_on = False
            self._attr_percentage = 0
            await self.async_save_state()
            self.async_write_ha_state()
            _LOGGER.debug(f"Virtual air purifier '{self._attr_name}' turned off")

            # 触发模板更新事件
            if self._templates:
                self.hass.bus.async_fire(
                    f"{DOMAIN}_air_purifier_template_update",
                    {
                        "entity_id": self.entity_id,
                        "device_id": self._config_entry_id,
                        "action": "turn_off",
                    },
                )

    async def async_set_percentage(self, percentage: int) -> None:
        """Set the speed percentage of the fan."""
        if self._attr_is_on and percentage > 0:
            # 找到最接近的支持速度
            closest_speed = min(self._speed_list, key=lambda x: abs(x - percentage))
            self._attr_percentage = closest_speed
            self._cleaning_rate = self._get_cleaning_rate()
            await self.async_save_state()
            self.async_write_ha_state()
            _LOGGER.debug(f"Virtual air purifier '{self._attr_name}' speed set to {percentage}% (actual: {closest_speed}%)")

            # 触发模板更新事件
            if self._templates:
                self.hass.bus.async_fire(
                    f"{DOMAIN}_air_purifier_template_update",
                    {
                        "entity_id": self.entity_id,
                        "device_id": self._config_entry_id,
                        "action": "set_speed",
                        "speed": self.current_speed,
                        "percentage": self._attr_percentage,
                    },
                )

    async def async_oscillate(self, oscillating: bool) -> None:
        """Set oscillation."""
        self._attr_oscillating = oscillating
        await self.async_save_state()
        self.async_write_ha_state()
        _LOGGER.debug(f"Virtual air purifier '{self._attr_name}' oscillation set to {oscillating}")

        # 触发模板更新事件
        if self._templates:
            self.hass.bus.async_fire(
                f"{DOMAIN}_air_purifier_template_update",
                {
                    "entity_id": self.entity_id,
                    "device_id": self._config_entry_id,
                    "action": "set_oscillate",
                    "oscillating": oscillating,
                },
            )

    def calculate_aqi(self) -> dict[str, Any]:
        """Calculate AQI based on current air quality."""
        # 简化的AQI计算，基于PM2.5
        pm25_aqi = self._calculate_pm25_aqi(self._pm25)

        # 确定AQI等级
        aqi_level = "good"
        for level, config in AQI_LEVELS.items():
            if config["min"] <= pm25_aqi <= config["max"]:
                aqi_level = level
                break

        return {
            "aqi": pm25_aqi,
            "level": aqi_level,
            "color": AQI_LEVELS[aqi_level]["color"],
            "label": AQI_LEVELS[aqi_level]["label"],
        }

    def _calculate_pm25_aqi(self, pm25: float) -> int:
        """Calculate AQI from PM2.5 concentration."""
        # 简化的AQI计算公式
        if pm25 <= 35:
            return int((50 / 35) * pm25)
        elif pm25 <= 75:
            return 50 + int((100 / 40) * (pm25 - 35))
        elif pm25 <= 115:
            return 100 + int((50 / 40) * (pm25 - 75))
        elif pm25 <= 150:
            return 150 + int((50 / 35) * (pm25 - 115))
        elif pm25 <= 250:
            return 200 + int((100 / 100) * (pm25 - 150))
        else:
            return 300 + int((200 / 100) * min(pm25 - 250, 100))

    async def async_update(self) -> None:
        """Update air purifier state."""
        import time

        if self._attr_is_on and self._last_update:
            # 计算运行时间
            time_diff = time.time() - self._last_update.timestamp()
            self._running_time += time_diff
            self._filter_usage_hours += time_diff / 3600

            # 更新滤网寿命
            usage_percentage = (self._filter_usage_hours / self._filter_max_hours) * 100
            self._filter_life = max(0, 100 - usage_percentage)

            # 计算净化效果
            if self._cleaning_rate > 0:
                # 简化的净化效果计算
                cleaned_air = self._cleaning_rate * (time_diff / 3600)  # m³
                self._total_air_cleaned += cleaned_air

                # 根据净化效果改善空气质量
                improvement_factor = cleaned_air / self._room_volume
                self._pm25 = max(0, self._pm25 - improvement_factor * 2)
                self._pm10 = max(0, self._pm10 - improvement_factor * 1.5)
                self._voc = max(0, self._voc - improvement_factor * 0.1)
                self._formaldehyde = max(0, self._formaldehyde - improvement_factor * 0.01)
                self._co2 = max(350, self._co2 - improvement_factor * 10)

        else:
            # 自然空气质量恶化
            self._pm25 = min(500, self._pm25 + random.uniform(0.1, 0.5))
            self._pm10 = min(600, self._pm10 + random.uniform(0.1, 0.3))
            self._voc = min(2.0, self._voc + random.uniform(0.001, 0.005))
            self._formaldehyde = min(0.3, self._formaldehyde + random.uniform(0.0001, 0.0005))
            self._co2 = min(2000, self._co2 + random.uniform(1, 5))

        self._last_update = datetime.now()
        self.async_write_ha_state()

        # 触发模板更新事件
        if self._templates:
            aqi_data = self.calculate_aqi()
            self.hass.bus.async_fire(
                f"{DOMAIN}_air_purifier_template_update",
                {
                    "entity_id": self.entity_id,
                    "device_id": self._config_entry_id,
                    "pm25": round(self._pm25, 1),
                    "pm10": round(self._pm10, 1),
                    "co2": round(self._co2, 0),
                    "voc": round(self._voc, 2),
                    "formaldehyde": round(self._formaldehyde, 3),
                    "filter_life": round(self._filter_life, 1),
                    "aqi": aqi_data["aqi"],
                    "aqi_level": aqi_data["level"],
                    "aqi_label": aqi_data["label"],
                    "running_time": self._running_time,
                },
            )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        _LOGGER.debug(f"Generating extra_state_attributes for air purifier '{self._attr_name}'")

        aqi_data = self.calculate_aqi()
        
        # 分离数值和带单位的字符串，以便前端能更好地显示
        attrs = {
            # 基本信息
            "purifier_type": AIR_PURIFIER_TYPES.get(self._purifier_type, self._purifier_type),
            "filter_type": self._get_filter_type(),
            "current_speed": self.current_speed,
            "is_on": self._attr_is_on,
            "oscillating": self._attr_oscillating,
            
            # 数值属性 - 用于图表和统计
            "room_volume_m3": round(self._room_volume, 1),
            "suggested_area_m2": round(self._room_volume / 2.5, 1),
            "cleaning_rate_m3_per_h": round(self._cleaning_rate, 1),
            "filter_life_percent": round(self._filter_life, 1),
            "filter_usage_hours": round(self._filter_usage_hours, 1),
            "pm25_ug_per_m3": round(self._pm25, 1),
            "pm10_ug_per_m3": round(self._pm10, 1),
            "co2_ppm": round(self._co2, 0),
            "voc_mg_per_m3": round(self._voc, 3),
            "formaldehyde_mg_per_m3": round(self._formaldehyde, 3),
            "aqi": aqi_data["aqi"],
            "total_air_cleaned_m3": round(self._total_air_cleaned, 0),
            "running_time_hours": round(self._running_time / 3600, 2),
            "fan_percentage": self._attr_percentage,
            
            # 显示用的带单位字符串
            "room_volume": f"{self._room_volume:.1f} m³",
            "suggested_area": f"{self._room_volume / 2.5:.0f} m²",
            "cleaning_rate": f"{self._cleaning_rate:.0f} m³/h",
            "filter_life": f"{self._filter_life:.1f}%",
            "filter_usage_hours": f"{self._filter_usage_hours:.1f} h",
            "pm25": f"{self._pm25:.1f} µg/m³",
            "pm10": f"{self._pm10:.1f} µg/m³",
            "co2": f"{self._co2:.0f} ppm",
            "voc": f"{self._voc:.2f} mg/m³",
            "formaldehyde": f"{self._formaldehyde:.3f} mg/m³",
            "aqi_level": aqi_data["level"],
            "aqi_label": aqi_data["label"],
            "aqi_color": aqi_data["color"],
            "total_air_cleaned": f"{round(self._total_air_cleaned):.0f} m³",
            "running_time": f"{round(self._running_time / 3600, 1)} h",
            "noise_level": self._get_noise_level(),
            "power_consumption": self._get_power_consumption(),
        }

        # 添加净化器特定属性
        if self._purifier_type == "uv_c":
            uv_lamp_life = max(0, 100 - self._filter_usage_hours / 21.6)
            attrs["uv_lamp_status"] = self._attr_is_on
            attrs["uv_lamp_life_percent"] = round(uv_lamp_life, 1)
            attrs["uv_lamp_life"] = f"{uv_lamp_life:.1f}%"
        elif self._purifier_type == "ionic":
            attrs["ionizer_active"] = self._attr_is_on
        elif self._purifier_type == "ozone":
            attrs["ozone_level"] = "low" if self._attr_percentage <= 50 else "high"

        _LOGGER.debug(f"Air purifier attributes count: {len(attrs)}")
        _LOGGER.debug(f"Air purifier attributes: {attrs}")

        # 确保所有属性都是正确的数据类型
        for key, value in attrs.items():
            if value is None:
                _LOGGER.warning(f"Air purifier attribute '{key}' has None value")

        return attrs