"""Platform for virtual climate integration."""
from __future__ import annotations

import logging
import random
from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change
from homeassistant.helpers.storage import Store

STORAGE_VERSION = 1

from .const import (
    CONF_ENTITIES,
    CONF_ENTITY_NAME,
    DEFAULT_MAX_TEMP,
    DEFAULT_MIN_TEMP,
    DEFAULT_TEMP_STEP,
    DEVICE_TYPE_CLIMATE,
    DOMAIN,
    TEMPLATE_ENABLED_DEVICE_TYPES,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up virtual climate entities."""
    device_type = config_entry.data.get("device_type")

    # 只有空调类型的设备才设置空调实体
    if device_type != DEVICE_TYPE_CLIMATE:
        return

    device_info = hass.data[DOMAIN][config_entry.entry_id]["device_info"]
    entities = []
    entities_config = config_entry.data.get(CONF_ENTITIES, [])

    for idx, entity_config in enumerate(entities_config):
        entity = VirtualClimate(
            hass,
            config_entry.entry_id,
            entity_config,
            idx,
            device_info,
        )
        entities.append(entity)

    async_add_entities(entities)


class VirtualClimate(ClimateEntity):
    """Representation of a virtual climate device."""

    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.FAN_MODE
        | ClimateEntityFeature.SWING_MODE
        | ClimateEntityFeature.PRESET_MODE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
    )
    _attr_hvac_modes = [
        HVACMode.OFF,
        HVACMode.HEAT,
        HVACMode.COOL,
        HVACMode.AUTO,
        HVACMode.DRY,
        HVACMode.FAN_ONLY,
    ]
    _attr_fan_modes = ["auto", "low", "medium", "high", "quiet", "turbo"]
    _attr_swing_modes = ["off", "vertical", "horizontal", "all"]
    _attr_preset_modes = ["comfort", "eco", "sleep", "boost"]

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry_id: str,
        entity_config: dict[str, Any],
        index: int,
        device_info: dict[str, Any],
    ) -> None:
        """Initialize the virtual climate."""
        self._config_entry_id = config_entry_id
        self._entity_config = entity_config
        self._index = index
        self._device_info = device_info
        self._hass = hass

        entity_name = entity_config.get(CONF_ENTITY_NAME, f"Climate_{index + 1}")
        self._attr_name = entity_name
        self._attr_unique_id = f"{config_entry_id}_climate_{index}"
        self._attr_device_info = device_info

        # Template support
        self._templates = entity_config.get("templates", {})

        # 存储实体状态
        self._store = Store[dict[str, Any]](hass, STORAGE_VERSION, f"virtual_devices_climate_{config_entry_id}_{index}")

        # 温度范围
        self._attr_min_temp = entity_config.get("min_temp", DEFAULT_MIN_TEMP)
        self._attr_max_temp = entity_config.get("max_temp", DEFAULT_MAX_TEMP)
        self._attr_target_temperature_step = entity_config.get(
            "temp_step", DEFAULT_TEMP_STEP
        )

        # 状态 - 默认值，稍后从存储恢复
        self._attr_hvac_mode = HVACMode.OFF
        self._attr_target_temperature = 24
        self._attr_current_temperature = 22
        self._attr_fan_mode = "auto"
        self._attr_swing_mode = "off"
        self._attr_preset_mode = None
        self._attr_hvac_action = HVACAction.OFF

        # 湿度模拟相关
        self._current_humidity = 55  # 当前湿度 (%)
        self._target_humidity = 50     # 目标湿度 (%)
        self._humidity_enabled = entity_config.get("enable_humidity_sensor", True)

        # 温度模拟相关
        self._target_reached_threshold = 1.0  # 目标温度达到阈值
        self._temperature_change_rate = 0.5    # 温度变化速率
        self._simulation_enabled = entity_config.get("enable_temperature_simulation", True)

        # 设置默认暴露给语音助手
        self._attr_entity_registry_enabled_default = True
        self._attr_should_poll = False
        self._attr_entity_category = None

    @property
    def should_expose(self) -> bool:
        """Return if this entity should be exposed to voice assistants."""
        return True

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the virtual climate device."""
        self._attr_is_on = True
        # 默认设置为制冷模式
        self._attr_hvac_mode = "cool"
        self.async_write_ha_state()
        _LOGGER.info(f"Virtual climate '{self._attr_name}' turned on")

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the virtual climate device."""
        self._attr_is_on = False
        self._attr_hvac_mode = HVACMode.OFF
        self.async_write_ha_state()
        _LOGGER.info(f"Virtual climate '{self._attr_name}' turned off")

    async def async_added_to_hass(self) -> None:
        """Call when entity is added to hass."""
        await super().async_added_to_hass()
        # 加载保存的状态
        await self.async_load_state()

    async def async_load_state(self) -> None:
        """Load saved state from storage."""
        try:
            data = await self._store.async_load()
            if data:
                self._attr_hvac_mode = data.get("hvac_mode", HVACMode.OFF)
                self._attr_target_temperature = data.get("target_temperature", 24)
                self._attr_current_temperature = data.get("current_temperature", 22)
                self._attr_fan_mode = data.get("fan_mode", "auto")
                self._attr_swing_mode = data.get("swing_mode", "off")
                self._attr_preset_mode = data.get("preset_mode")
                self._attr_hvac_action = data.get("hvac_action", HVACAction.OFF)
                self._current_humidity = data.get("current_humidity", 55)
                self._target_humidity = data.get("target_humidity", 50)
                _LOGGER.info(f"Climate '{self._attr_name}' state loaded from storage")
        except Exception as ex:
            _LOGGER.error(f"Failed to load state for climate '{self._attr_name}': {ex}")

    async def async_save_state(self) -> None:
        """Save current state to storage."""
        try:
            data = {
                "hvac_mode": self._attr_hvac_mode,
                "target_temperature": self._attr_target_temperature,
                "current_temperature": self._attr_current_temperature,
                "fan_mode": self._attr_fan_mode,
                "swing_mode": self._attr_swing_mode,
                "preset_mode": self._attr_preset_mode,
                "hvac_action": self._attr_hvac_action,
                "current_humidity": self._current_humidity,
                "target_humidity": self._target_humidity,
            }
            await self._store.async_save(data)
        except Exception as ex:
            _LOGGER.error(f"Failed to save state for climate '{self._attr_name}': {ex}")

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the climate device."""
        # 如果当前是关闭状态，设置为制冷模式（可以根据需要改为AUTO模式）
        if self._attr_hvac_mode == HVACMode.OFF:
            self._attr_hvac_mode = HVACMode.COOL
            self._update_hvac_action()

            # 保存状态到存储
            await self.async_save_state()

            self.async_write_ha_state()
            _LOGGER.debug(f"Virtual climate '{self._attr_name}' turned on")

            # 触发模板更新事件
            if self._templates:
                self.hass.bus.async_fire(
                    f"{DOMAIN}_climate_template_update",
                    {
                        "entity_id": self.entity_id,
                        "device_id": self._config_entry_id,
                        "hvac_mode": self._attr_hvac_mode,
                        "target_temperature": self._attr_target_temperature,
                        "current_temperature": self._attr_current_temperature,
                    },
                )

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the climate device."""
        if self._attr_hvac_mode != HVACMode.OFF:
            self._attr_hvac_mode = HVACMode.OFF
            self._attr_hvac_action = HVACAction.OFF

            # 保存状态到存储
            await self.async_save_state()

            self.async_write_ha_state()
            _LOGGER.debug(f"Virtual climate '{self._attr_name}' turned off")

            # 触发模板更新事件
            if self._templates:
                self.hass.bus.async_fire(
                    f"{DOMAIN}_climate_template_update",
                    {
                        "entity_id": self.entity_id,
                        "device_id": self._config_entry_id,
                        "hvac_mode": HVACMode.OFF,
                        "target_temperature": self._attr_target_temperature,
                        "current_temperature": self._attr_current_temperature,
                    },
                )

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new target hvac mode."""
        self._attr_hvac_mode = hvac_mode
        self._update_hvac_action()

        # 保存状态到存储
        await self.async_save_state()

        self.async_write_ha_state()
        _LOGGER.debug(f"Virtual climate '{self._attr_name}' mode set to {hvac_mode}")

        # 触发模板更新事件
        if self._templates:
            self.hass.bus.async_fire(
                f"{DOMAIN}_climate_template_update",
                {
                    "entity_id": self.entity_id,
                    "device_id": self._config_entry_id,
                    "hvac_mode": hvac_mode,
                    "target_temperature": self._attr_target_temperature,
                    "current_temperature": self._attr_current_temperature,
                },
            )

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        if (temperature := kwargs.get(ATTR_TEMPERATURE)) is not None:
            # 修复：添加温度范围验证
            original_temp = temperature
            temperature = max(self._attr_min_temp, min(self._attr_max_temp, temperature))

            if original_temp != temperature:
                _LOGGER.warning(
                    f"Temperature {original_temp}°C out of range ({self._attr_min_temp}-{self._attr_max_temp}°C), "
                    f"clamped to {temperature}°C"
                )

            self._attr_target_temperature = temperature
            self._update_hvac_action()

            # 保存状态到存储
            await self.async_save_state()

            self.async_write_ha_state()
            _LOGGER.debug(
                f"Virtual climate '{self._attr_name}' temperature set to {temperature}"
            )

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Set new target fan mode."""
        self._attr_fan_mode = fan_mode

        # 保存状态到存储
        await self.async_save_state()

        self.async_write_ha_state()
        _LOGGER.debug(f"Virtual climate '{self._attr_name}' fan mode set to {fan_mode}")

    async def async_set_swing_mode(self, swing_mode: str) -> None:
        """Set new target swing operation."""
        self._attr_swing_mode = swing_mode

        # 保存状态到存储
        await self.async_save_state()

        self.async_write_ha_state()
        _LOGGER.debug(
            f"Virtual climate '{self._attr_name}' swing mode set to {swing_mode}"
        )

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set new preset mode."""
        self._attr_preset_mode = preset_mode
        # 根据预设模式调整目标温度
        if preset_mode == "comfort":
            self._attr_target_temperature = 24
        elif preset_mode == "eco":
            self._attr_target_temperature = 26
        elif preset_mode == "sleep":
            self._attr_target_temperature = 23
        elif preset_mode == "boost":
            self._attr_target_temperature = 18

        self._update_hvac_action()

        # 保存状态到存储
        await self.async_save_state()

        self.async_write_ha_state()
        _LOGGER.debug(f"Virtual climate '{self._attr_name}' preset mode set to {preset_mode}")

    def _update_hvac_action(self) -> None:
        """Update HVAC action based on current state."""
        if self._attr_hvac_mode == HVACMode.OFF:
            self._attr_hvac_action = HVACAction.OFF
        elif self._attr_hvac_mode == HVACMode.FAN_ONLY:
            self._attr_hvac_action = HVACAction.FAN
        elif self._attr_hvac_mode == HVACMode.DRY:
            self._attr_hvac_action = HVACAction.DRYING
        else:
            # Heating or cooling based on temperature difference
            temp_diff = self._attr_target_temperature - self._attr_current_temperature
            if abs(temp_diff) <= self._target_reached_threshold:
                self._attr_hvac_action = HVACAction.IDLE
            elif temp_diff > 0:
                if self._attr_hvac_mode in [HVACMode.HEAT, HVACMode.AUTO]:
                    self._attr_hvac_action = HVACAction.HEATING
                else:
                    self._attr_hvac_action = HVACAction.COOLING
            else:
                if self._attr_hvac_mode in [HVACMode.COOL, HVACMode.AUTO]:
                    self._attr_hvac_action = HVACAction.COOLING
                else:
                    self._attr_hvac_action = HVACAction.HEATING

    async def async_update(self) -> None:
        """Update the climate entity state."""
        if self._simulation_enabled and self._attr_hvac_mode != HVACMode.OFF:
            # 模拟温度变化
            if self._attr_hvac_action in [HVACAction.HEATING, HVACAction.COOLING]:
                temp_change = self._temperature_change_rate * 0.1  # 每次更新的温度变化
                if self._attr_hvac_action == HVACAction.HEATING:
                    self._attr_current_temperature += temp_change
                elif self._attr_hvac_action == HVACAction.COOLING:
                    self._attr_current_temperature -= temp_change

                # 确保温度在合理范围内
                self._attr_current_temperature = max(self._attr_min_temp, min(self._attr_max_temp, self._attr_current_temperature))

            # 模拟湿度变化
            if self._humidity_enabled:
                self._update_humidity()

            # 检查是否达到目标温度
            self._update_hvac_action()
            self.async_write_ha_state()

    def _update_humidity(self) -> None:
        """Update humidity based on HVAC mode and temperature."""
        # 基础随机变化
        humidity_change = random.uniform(-2, 2)

        # 根据空调模式调整湿度
        if self._attr_hvac_action in [HVACAction.COOLING]:
            # 制冷模式：除湿效果，湿度下降
            humidity_change -= random.uniform(0.5, 2.0)
        elif self._attr_hvac_action == HVACAction.HEATING:
            # 制热模式：蒸发增加湿度，湿度上升
            humidity_change += random.uniform(0.5, 2.0)
        elif self._attr_hvac_mode == HVACMode.DRY:
            # 除湿模式：湿度下降
            humidity_change -= random.uniform(2.0, 4.0)
        elif self._attr_hvac_mode == HVACMode.FAN:
            # 仅送风模式：轻微影响
            humidity_change += random.uniform(-0.5, 0.5)

        # 温度对湿度的影响（温度高时湿度相对较低）
        temp_effect = (self._attr_current_temperature - 20) * 0.1
        humidity_change -= temp_effect

        # 应用湿度变化
        self._current_humidity += humidity_change
        self._current_humidity = max(20, min(90, self._current_humidity))  # 限制在20-90%之间

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        if self._humidity_enabled:
            return {
                "humidity": round(self._current_humidity, 1),
                "target_humidity": self._target_humidity,
            }
        return {}
