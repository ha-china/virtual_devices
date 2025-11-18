"""Climate control domain service for climate, humidifier, and water heater devices."""
from __future__ import annotations

import logging
import random
from typing import Any, List

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.components.humidifier import (
    HumidifierEntity,
    HumidifierEntityFeature,
)
from homeassistant.components.water_heater import (
    WaterHeaterEntity,
    WaterHeaterEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change

from .base_service import BaseVirtualEntity, VirtualDeviceService
from .const import (
    CONF_ENTITIES,
    CONF_ENTITY_NAME,
    DEFAULT_MAX_TEMP,
    DEFAULT_MIN_TEMP,
    DEFAULT_TEMP_STEP,
    DEVICE_TYPE_CLIMATE,
    DEVICE_TYPE_HUMIDIFIER,
    DEVICE_TYPE_WATER_HEATER,
    DOMAIN,
    HUMIDIFIER_TYPES,
)

_LOGGER = logging.getLogger(__name__)


class VirtualClimate(BaseVirtualEntity, ClimateEntity):
    """Representation of a virtual climate device."""

    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.FAN_MODE
        | ClimateEntityFeature.SWING_MODE
        | ClimateEntityFeature.PRESET_MODE
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
        super().__init__(hass, config_entry_id, entity_config, index, device_info, "climate")

        # Temperature range
        self._attr_min_temp = entity_config.get("min_temp", DEFAULT_MIN_TEMP)
        self._attr_max_temp = entity_config.get("max_temp", DEFAULT_MAX_TEMP)
        self._attr_target_temperature_step = entity_config.get(
            "temp_step", DEFAULT_TEMP_STEP
        )

        # Climate specific state
        self._attr_hvac_mode = HVACMode.OFF
        self._attr_target_temperature = 24
        self._attr_current_temperature = 22
        self._attr_fan_mode = "auto"
        self._attr_swing_mode = "off"
        self._attr_preset_mode = None
        self._attr_hvac_action = HVACAction.OFF

        # Temperature simulation
        self._target_reached_threshold = 1.0
        self._temperature_change_rate = 0.5
        self._simulation_enabled = entity_config.get("enable_temperature_simulation", True)

    async def _apply_loaded_state(self) -> None:
        """Apply loaded state to climate entity."""
        self._attr_hvac_mode = self._state.get("hvac_mode", HVACMode.OFF)
        self._attr_target_temperature = self._state.get("target_temperature", 24)
        self._attr_current_temperature = self._state.get("current_temperature", 22)
        self._attr_fan_mode = self._state.get("fan_mode", "auto")
        self._attr_swing_mode = self._state.get("swing_mode", "off")
        self._attr_preset_mode = self._state.get("preset_mode")
        self._attr_hvac_action = self._state.get("hvac_action", HVACAction.OFF)

    async def _initialize_default_state(self) -> None:
        """Initialize default climate state."""
        self._state = {
            "hvac_mode": HVACMode.OFF,
            "target_temperature": 24,
            "current_temperature": 22,
            "fan_mode": "auto",
            "swing_mode": "off",
            "preset_mode": None,
            "hvac_action": HVACAction.OFF,
        }

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        if (temperature := kwargs.get(ATTR_TEMPERATURE)) is not None:
            self._attr_target_temperature = temperature
            self._state["target_temperature"] = temperature
            await self.async_save_state()

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new target hvac mode."""
        self._attr_hvac_mode = hvac_mode
        self._state["hvac_mode"] = hvac_mode
        if hvac_mode == HVACMode.OFF:
            self._attr_hvac_action = HVACAction.OFF
            self._state["hvac_action"] = HVACAction.OFF
        await self.async_save_state()

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Set new target fan mode."""
        self._attr_fan_mode = fan_mode
        self._state["fan_mode"] = fan_mode
        await self.async_save_state()

    async def async_set_swing_mode(self, swing_mode: str) -> None:
        """Set new target swing mode."""
        self._attr_swing_mode = swing_mode
        self._state["swing_mode"] = swing_mode
        await self.async_save_state()

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set new preset mode."""
        self._attr_preset_mode = preset_mode
        self._state["preset_mode"] = preset_mode
        await self.async_save_state()


class VirtualHumidifier(BaseVirtualEntity, HumidifierEntity):
    """Representation of a virtual humidifier."""

    _attr_supported_features = (
        HumidifierEntityFeature.MODES
        | HumidifierEntityFeature.TARGET_HUMIDITY
    )

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry_id: str,
        entity_config: dict[str, Any],
        index: int,
        device_info: dict[str, Any],
    ) -> None:
        """Initialize the virtual humidifier."""
        super().__init__(hass, config_entry_id, entity_config, index, device_info, "humidifier")

        # Humidifier specific configuration
        humidifier_type = entity_config.get("humidifier_type", "ultrasonic")
        self._humidifier_type = humidifier_type

        # Set icon based on type
        icon_map = {
            "ultrasonic": "mdi:air-humidifier",
            "evaporative": "mdi:water",
            "steam": "mdi:weather-rainy",
        }
        self._attr_icon = icon_map.get(humidifier_type, "mdi:air-humidifier")

        # Available modes
        self._attr_available_modes = ["Auto", "Low", "Medium", "High"]
        self._attr_min_humidity = 20
        self._attr_max_humidity = 80

        # Humidifier specific state
        self._attr_mode = "Auto"
        self._attr_target_humidity = 50
        self._attr_current_humidity = 45
        self._attr_is_on = False

        # Special features
        self._special_features = entity_config.get("special_features", [])
        self._noise_level = entity_config.get("noise_level", "low")
        self._power_state = entity_config.get("power_state", "normal")

    async def _apply_loaded_state(self) -> None:
        """Apply loaded state to humidifier entity."""
        self._attr_mode = self._state.get("mode", "Auto")
        self._attr_target_humidity = self._state.get("target_humidity", 50)
        self._attr_current_humidity = self._state.get("current_humidity", 45)
        self._attr_is_on = self._state.get("is_on", False)

    async def _initialize_default_state(self) -> None:
        """Initialize default humidifier state."""
        self._state = {
            "mode": "Auto",
            "target_humidity": 50,
            "current_humidity": 45,
            "is_on": False,
        }

    async def async_set_humidity(self, humidity: int) -> None:
        """Set new target humidity."""
        self._attr_target_humidity = humidity
        self._state["target_humidity"] = humidity
        await self.async_save_state()

    async def async_set_mode(self, mode: str) -> None:
        """Set new mode."""
        if mode in self._attr_available_modes:
            self._attr_mode = mode
            self._state["mode"] = mode
            await self.async_save_state()

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the device on."""
        self._attr_is_on = True
        self._state["is_on"] = True
        await self.async_save_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the device off."""
        self._attr_is_on = False
        self._state["is_on"] = False
        await self.async_save_state()


class VirtualWaterHeater(BaseVirtualEntity, WaterHeaterEntity):
    """Representation of a virtual water heater."""

    _attr_supported_features = (
        WaterHeaterEntityFeature.TARGET_TEMPERATURE
        | WaterHeaterEntityFeature.OPERATION_MODE
        | WaterHeaterEntityFeature.AWAY_MODE
    )

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry_id: str,
        entity_config: dict[str, Any],
        index: int,
        device_info: dict[str, Any],
    ) -> None:
        """Initialize the virtual water heater."""
        super().__init__(hass, config_entry_id, entity_config, index, device_info, "water_heater")

        # Temperature range
        self._attr_min_temp = 30
        self._attr_max_temp = 70
        self._attr_temperature_unit = UnitOfTemperature.CELSIUS

        # Water heater specific state
        self._attr_operation_list = ["Off", "Eco", "Performance"]
        self._attr_current_operation = "Off"
        self._attr_current_temperature = 40
        self._attr_target_temperature = 50
        self._attr_away_mode = False

    async def _apply_loaded_state(self) -> None:
        """Apply loaded state to water heater entity."""
        self._attr_current_operation = self._state.get("current_operation", "Off")
        self._attr_current_temperature = self._state.get("current_temperature", 40)
        self._attr_target_temperature = self._state.get("target_temperature", 50)
        self._attr_away_mode = self._state.get("away_mode", False)

    async def _initialize_default_state(self) -> None:
        """Initialize default water heater state."""
        self._state = {
            "current_operation": "Off",
            "current_temperature": 40,
            "target_temperature": 50,
            "away_mode": False,
        }

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        if (temperature := kwargs.get("temperature")) is not None:
            self._attr_target_temperature = temperature
            self._state["target_temperature"] = temperature
            await self.async_save_state()

    async def async_set_operation_mode(self, operation_mode: str) -> None:
        """Set new target operation mode."""
        if operation_mode in self._attr_operation_list:
            self._attr_current_operation = operation_mode
            self._state["current_operation"] = operation_mode
            await self.async_save_state()

    async def async_turn_away_mode_on(self) -> None:
        """Turn away mode on."""
        self._attr_away_mode = True
        self._state["away_mode"] = True
        await self.async_save_state()

    async def async_turn_away_mode_off(self) -> None:
        """Turn away mode off."""
        self._attr_away_mode = False
        self._state["away_mode"] = False
        await self.async_save_state()


class ClimateControlService(VirtualDeviceService):
    """Climate control domain service."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the climate control service."""
        super().__init__(hass, "climate_control")
        self._supported_device_types = [
            DEVICE_TYPE_CLIMATE,
            DEVICE_TYPE_HUMIDIFIER,
            DEVICE_TYPE_WATER_HEATER,
        ]

    async def async_setup_entry(
        self,
        config_entry: ConfigEntry,
        async_add_entities,
    ) -> None:
        """Set up climate control entities."""
        device_type = config_entry.data.get("device_type")

        if not self.is_device_type_supported(device_type):
            return

        device_info = self._get_device_info(config_entry)
        entities_config = self._get_entities_config(config_entry)
        entities = []

        for idx, entity_config in enumerate(entities_config):
            if device_type == DEVICE_TYPE_CLIMATE:
                entity = VirtualClimate(self._hass, config_entry.entry_id, entity_config, idx, device_info)
            elif device_type == DEVICE_TYPE_HUMIDIFIER:
                entity = VirtualHumidifier(self._hass, config_entry.entry_id, entity_config, idx, device_info)
            elif device_type == DEVICE_TYPE_WATER_HEATER:
                entity = VirtualWaterHeater(self._hass, config_entry.entry_id, entity_config, idx, device_info)
            else:
                continue

            entities.append(entity)

        if entities:
            async_add_entities(entities)
            _LOGGER.info(f"Added {len(entities)} climate control entities for {device_type}")