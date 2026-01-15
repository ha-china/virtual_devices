"""Platform for virtual climate integration."""
from __future__ import annotations

import logging
import random
from typing import Any

from homeassistant.components.climate import (
    ClimateEntity, ClimateEntityFeature, HVACAction, HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .base_entity import BaseVirtualEntity
from .const import (
    CONF_ENTITIES, DEFAULT_MAX_TEMP, DEFAULT_MIN_TEMP, DEFAULT_TEMP_STEP,
    DEVICE_TYPE_CLIMATE, DOMAIN,
)
from .types import ClimateEntityConfig, ClimateState

_LOGGER = logging.getLogger(__name__)

# Preset mode temperature mappings
PRESET_TEMPERATURES: dict[str, float] = {"comfort": 24.0, "eco": 26.0, "sleep": 23.0, "boost": 18.0}


async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up virtual climate entities."""
    if config_entry.data.get("device_type") != DEVICE_TYPE_CLIMATE:
        return

    device_info: DeviceInfo = hass.data[DOMAIN][config_entry.entry_id]["device_info"]
    entities: list[VirtualClimate] = []

    for idx, entity_config in enumerate(config_entry.data.get(CONF_ENTITIES, [])):
        try:
            entities.append(VirtualClimate(hass, config_entry.entry_id, entity_config, idx, device_info))
        except Exception as e:
            _LOGGER.error("Failed to create VirtualClimate %d: %s", idx, e)

    if entities:
        async_add_entities(entities)


class VirtualClimate(BaseVirtualEntity[ClimateEntityConfig, ClimateState], ClimateEntity):
    """Representation of a virtual climate device."""

    _attr_temperature_unit: str = UnitOfTemperature.CELSIUS
    _attr_supported_features: ClimateEntityFeature = (
        ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.FAN_MODE
        | ClimateEntityFeature.SWING_MODE | ClimateEntityFeature.PRESET_MODE
        | ClimateEntityFeature.TURN_ON | ClimateEntityFeature.TURN_OFF
    )
    _attr_hvac_modes: list[HVACMode] = [
        HVACMode.OFF, HVACMode.HEAT, HVACMode.COOL, HVACMode.AUTO, HVACMode.DRY, HVACMode.FAN_ONLY,
    ]
    _attr_fan_modes: list[str] = ["auto", "low", "medium", "high", "quiet", "turbo"]
    _attr_swing_modes: list[str] = ["off", "vertical", "horizontal", "all"]
    _attr_preset_modes: list[str] = ["comfort", "eco", "sleep", "boost"]

    def __init__(
        self, hass: HomeAssistant, config_entry_id: str, entity_config: ClimateEntityConfig,
        index: int, device_info: DeviceInfo,
    ) -> None:
        """Initialize the virtual climate."""
        # Set humidity_enabled BEFORE super().__init__() because get_default_state() needs it
        self._humidity_enabled: bool = entity_config.get("enable_humidity_sensor", True)
        self._simulation_enabled: bool = entity_config.get("enable_temperature_simulation", True)

        super().__init__(hass, config_entry_id, entity_config, index, device_info, "climate")
        self._attr_entity_category = None
        # Temperature range from config
        self._attr_min_temp: float = float(entity_config.get("min_temp", DEFAULT_MIN_TEMP))
        self._attr_max_temp: float = float(entity_config.get("max_temp", DEFAULT_MAX_TEMP))
        self._attr_target_temperature_step: float = float(entity_config.get("temp_step", DEFAULT_TEMP_STEP))
        # State attributes - defaults, will be overwritten by async_load_state
        self._attr_hvac_mode: HVACMode = HVACMode.OFF
        self._attr_target_temperature: float = 24.0
        self._attr_current_temperature: float = 22.0
        self._attr_fan_mode: str = "auto"
        self._attr_swing_mode: str = "off"
        self._attr_preset_mode: str | None = None
        self._attr_hvac_action: HVACAction = HVACAction.OFF
        # Humidity and temperature simulation
        self._current_humidity: float = 55.0
        self._target_humidity: float = 50.0
        self._target_reached_threshold: float = 1.0
        self._temperature_change_rate: float = 0.5

    def get_default_state(self) -> ClimateState:
        """Return the default state for this climate entity."""
        state: ClimateState = {
            "hvac_mode": HVACMode.OFF, "target_temperature": 24.0, "current_temperature": 22.0,
            "fan_mode": "auto", "swing_mode": "off", "preset_mode": None, "hvac_action": HVACAction.OFF,
        }
        if self._humidity_enabled:
            state["current_humidity"] = 55.0
            state["target_humidity"] = 50.0
        return state

    def apply_state(self, state: ClimateState) -> None:
        """Apply loaded state to entity attributes."""
        self._attr_hvac_mode = HVACMode(state.get("hvac_mode", HVACMode.OFF))
        self._attr_target_temperature = float(state.get("target_temperature", 24.0))
        self._attr_current_temperature = float(state.get("current_temperature", 22.0))
        self._attr_fan_mode = state.get("fan_mode", "auto")
        self._attr_swing_mode = state.get("swing_mode", "off")
        self._attr_preset_mode = state.get("preset_mode")
        hvac_action_value = state.get("hvac_action", HVACAction.OFF)
        self._attr_hvac_action = HVACAction(hvac_action_value) if isinstance(
            hvac_action_value, str) else hvac_action_value
        if self._humidity_enabled:
            self._current_humidity = float(state.get("current_humidity", 55.0))
            self._target_humidity = float(state.get("target_humidity", 50.0))

    def get_current_state(self) -> ClimateState:
        """Get current state for persistence."""
        state: ClimateState = {
            "hvac_mode": self._attr_hvac_mode, "target_temperature": self._attr_target_temperature,
            "current_temperature": self._attr_current_temperature, "fan_mode": self._attr_fan_mode,
            "swing_mode": self._attr_swing_mode, "preset_mode": self._attr_preset_mode,
            "hvac_action": self._attr_hvac_action,
        }
        if self._humidity_enabled:
            state["current_humidity"] = self._current_humidity
            state["target_humidity"] = self._target_humidity
        return state

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the climate device."""
        if self._attr_hvac_mode == HVACMode.OFF:
            self._attr_hvac_mode = HVACMode.COOL
            self._update_hvac_action()
            self.fire_template_event("turn_on", hvac_mode=self._attr_hvac_mode,
                                     target_temperature=self._attr_target_temperature, current_temperature=self._attr_current_temperature)
            await self.async_save_state()
            self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the climate device."""
        if self._attr_hvac_mode != HVACMode.OFF:
            self._attr_hvac_mode = HVACMode.OFF
            self._attr_hvac_action = HVACAction.OFF
            self.fire_template_event("turn_off", hvac_mode=HVACMode.OFF,
                                     target_temperature=self._attr_target_temperature, current_temperature=self._attr_current_temperature)
            await self.async_save_state()
            self.async_write_ha_state()

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new target hvac mode."""
        self._attr_hvac_mode = hvac_mode
        self._update_hvac_action()
        self.fire_template_event("set_hvac_mode", hvac_mode=hvac_mode,
                                 target_temperature=self._attr_target_temperature, current_temperature=self._attr_current_temperature)
        await self.async_save_state()
        self.async_write_ha_state()

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        temperature: float | None = kwargs.get(ATTR_TEMPERATURE)
        if temperature is not None:
            temperature = max(self._attr_min_temp, min(self._attr_max_temp, temperature))
            self._attr_target_temperature = temperature
            self._update_hvac_action()
            self.fire_template_event("set_temperature", target_temperature=temperature,
                                     current_temperature=self._attr_current_temperature)
            await self.async_save_state()
            self.async_write_ha_state()

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Set new target fan mode."""
        self._attr_fan_mode = fan_mode
        self.fire_template_event("set_fan_mode", fan_mode=fan_mode)
        await self.async_save_state()
        self.async_write_ha_state()

    async def async_set_swing_mode(self, swing_mode: str) -> None:
        """Set new target swing operation."""
        self._attr_swing_mode = swing_mode
        self.fire_template_event("set_swing_mode", swing_mode=swing_mode)
        await self.async_save_state()
        self.async_write_ha_state()

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set new preset mode."""
        self._attr_preset_mode = preset_mode
        if preset_mode in PRESET_TEMPERATURES:
            self._attr_target_temperature = PRESET_TEMPERATURES[preset_mode]
        self._update_hvac_action()
        self.fire_template_event("set_preset_mode", preset_mode=preset_mode,
                                 target_temperature=self._attr_target_temperature)
        await self.async_save_state()
        self.async_write_ha_state()

    def _update_hvac_action(self) -> None:
        """Update HVAC action based on current state."""
        if self._attr_hvac_mode == HVACMode.OFF:
            self._attr_hvac_action = HVACAction.OFF
        elif self._attr_hvac_mode == HVACMode.FAN_ONLY:
            self._attr_hvac_action = HVACAction.FAN
        elif self._attr_hvac_mode == HVACMode.DRY:
            self._attr_hvac_action = HVACAction.DRYING
        else:
            temp_diff = self._attr_target_temperature - self._attr_current_temperature
            if abs(temp_diff) <= self._target_reached_threshold:
                self._attr_hvac_action = HVACAction.IDLE
            elif temp_diff > 0:
                self._attr_hvac_action = HVACAction.HEATING if self._attr_hvac_mode in [
                    HVACMode.HEAT, HVACMode.AUTO] else HVACAction.COOLING
            else:
                self._attr_hvac_action = HVACAction.COOLING if self._attr_hvac_mode in [
                    HVACMode.COOL, HVACMode.AUTO] else HVACAction.HEATING

    async def async_update(self) -> None:
        """Update the climate entity state."""
        if self._simulation_enabled and self._attr_hvac_mode != HVACMode.OFF:
            if self._attr_hvac_action in [HVACAction.HEATING, HVACAction.COOLING]:
                temp_change = self._temperature_change_rate * 0.1
                if self._attr_hvac_action == HVACAction.HEATING:
                    self._attr_current_temperature += temp_change
                else:
                    self._attr_current_temperature -= temp_change
                self._attr_current_temperature = max(self._attr_min_temp, min(
                    self._attr_max_temp, self._attr_current_temperature))
            if self._humidity_enabled:
                self._update_humidity()
            self._update_hvac_action()
            self.async_write_ha_state()

    def _update_humidity(self) -> None:
        """Update humidity based on HVAC mode and temperature."""
        humidity_change = random.uniform(-2, 2)
        if self._attr_hvac_action == HVACAction.COOLING:
            humidity_change -= random.uniform(0.5, 2.0)
        elif self._attr_hvac_action == HVACAction.HEATING:
            humidity_change += random.uniform(0.5, 2.0)
        elif self._attr_hvac_mode == HVACMode.DRY:
            humidity_change -= random.uniform(2.0, 4.0)
        elif self._attr_hvac_mode == HVACMode.FAN_ONLY:
            humidity_change += random.uniform(-0.5, 0.5)
        humidity_change -= (self._attr_current_temperature - 20) * 0.1
        self._current_humidity = max(20.0, min(90.0, self._current_humidity + humidity_change))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        if self._humidity_enabled:
            return {"humidity": round(self._current_humidity, 1), "target_humidity": self._target_humidity}
        return {}
