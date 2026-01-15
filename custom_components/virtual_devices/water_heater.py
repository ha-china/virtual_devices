"""Platform for virtual water heater integration."""
from __future__ import annotations

import logging
import random
import time
from typing import Any

from homeassistant.components.water_heater import (
    WaterHeaterEntity,
    WaterHeaterEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.storage import Store

from .base_entity import STORAGE_VERSION
from .const import (
    CONF_ENTITIES,
    CONF_ENTITY_NAME,
    DEVICE_TYPE_WATER_HEATER,
    DOMAIN,
    WATER_HEATER_TYPES,
)
from .types import WaterHeaterEntityConfig, WaterHeaterState

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up virtual water heater entities."""
    device_type: str | None = config_entry.data.get("device_type")

    if device_type != DEVICE_TYPE_WATER_HEATER:
        return

    device_info: DeviceInfo = hass.data[DOMAIN][config_entry.entry_id]["device_info"]
    entities: list[VirtualWaterHeater] = []
    entities_config: list[WaterHeaterEntityConfig] = config_entry.data.get(CONF_ENTITIES, [])

    for idx, entity_config in enumerate(entities_config):
        entity = VirtualWaterHeater(
            hass,
            config_entry.entry_id,
            entity_config,
            idx,
            device_info,
        )
        entities.append(entity)

    async_add_entities(entities)


class VirtualWaterHeater(WaterHeaterEntity):
    """Representation of a virtual water heater.

    This entity implements state persistence using the same pattern as BaseVirtualEntity.
    """

    _attr_should_poll: bool = True
    _attr_entity_registry_enabled_default: bool = True

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry_id: str,
        entity_config: WaterHeaterEntityConfig,
        index: int,
        device_info: DeviceInfo,
    ) -> None:
        """Initialize the virtual water heater."""
        self._hass = hass
        self._config_entry_id = config_entry_id
        self._entity_config = entity_config
        self._index = index

        entity_name: str = entity_config.get(CONF_ENTITY_NAME, f"water_heater_{index + 1}")
        self._attr_name = entity_name
        self._attr_unique_id = f"{config_entry_id}_water_heater_{index}"
        self._attr_device_info = device_info
        self._attr_icon = "mdi:water-boiler"

        # Template support
        self._templates: dict[str, Any] = entity_config.get("templates", {})

        # Storage for state persistence
        self._store: Store[WaterHeaterState] = Store(
            hass, STORAGE_VERSION, f"virtual_devices_water_heater_{config_entry_id}_{index}"
        )

        # Supported features
        self._attr_supported_features: WaterHeaterEntityFeature = (
            WaterHeaterEntityFeature.TARGET_TEMPERATURE
            | WaterHeaterEntityFeature.OPERATION_MODE
            | WaterHeaterEntityFeature.AWAY_MODE
        )

        # Heater type
        heater_type: str = entity_config.get("heater_type", "electric")
        self._heater_type = heater_type

        # Set icon based on type
        icon_map: dict[str, str] = {
            "electric": "mdi:water-boiler",
            "gas": "mdi:fire",
            "solar": "mdi:solar-power",
            "heat_pump": "mdi:heat-pump",
            "tankless": "mdi:water-boiler-outline",
        }
        self._attr_icon = icon_map.get(heater_type, "mdi:water-boiler")

        # Initial state
        self._attr_current_operation: str | None = "off"
        self._attr_is_away_mode_on: bool = False

        # Temperature settings
        self._attr_current_temperature: float = entity_config.get("current_temperature", 25)
        self._attr_target_temperature: float = entity_config.get("target_temperature", 60)

        # Set temperature range based on heater type
        temp_ranges: dict[str, tuple[int, int]] = {
            "electric": (40, 75),
            "gas": (35, 80),
            "solar": (45, 70),
            "heat_pump": (35, 65),
            "tankless": (35, 60),
        }
        min_temp, max_temp = temp_ranges.get(heater_type, (40, 75))
        self._attr_min_temp: float = min_temp
        self._attr_max_temp: float = max_temp
        self._attr_temperature_unit = UnitOfTemperature.CELSIUS

        # Operation modes
        self._attr_operation_list: list[str] = ["off", "heat", "eco"]

        # Energy consumption
        self._energy_consumed_today: float = entity_config.get("energy_consumed_today", 5.0)
        self._power_consumption: float = 0
        self._total_energy_consumed: float = entity_config.get("total_energy_consumed", 1000.0)

        # Capacity and efficiency
        self._tank_capacity: int = entity_config.get("tank_capacity", 80)
        self._efficiency: float = entity_config.get("efficiency", 0.9)

        # Heating state
        self._is_heating: bool = False
        self._heating_start_time: float | None = None
        self._last_update: float | None = None

        _LOGGER.info(f"Virtual water heater '{self._attr_name}' initialized")

    def get_default_state(self) -> WaterHeaterState:
        """Return the default state for this entity type."""
        return {
            "current_operation": "off",
            "target_temperature": 60.0,
            "current_temperature": 25.0,
        }

    def apply_state(self, state: WaterHeaterState) -> None:
        """Apply loaded state to entity attributes."""
        self._attr_current_operation = state.get("current_operation", "off")
        self._attr_target_temperature = state.get("target_temperature", 60.0)
        self._attr_current_temperature = state.get("current_temperature", 25.0)

    def get_current_state(self) -> WaterHeaterState:
        """Get current state for persistence."""
        return {
            "current_operation": self._attr_current_operation or "off",
            "target_temperature": self._attr_target_temperature,
            "current_temperature": self._attr_current_temperature,
        }

    @property
    def should_expose(self) -> bool:
        """Return if this entity should be exposed to voice assistants."""
        return True

    async def async_load_state(self) -> None:
        """Load saved state from storage."""
        try:
            data = await self._store.async_load()
            if data:
                self.apply_state(data)
                _LOGGER.debug(f"Water heater '{self._attr_name}' state loaded")
        except Exception as ex:
            _LOGGER.error(f"Failed to load state for water heater '{self._attr_name}': {ex}")
            self.apply_state(self.get_default_state())

    async def async_save_state(self) -> None:
        """Save current state to storage."""
        try:
            data = self.get_current_state()
            await self._store.async_save(data)
            _LOGGER.debug(f"Water heater '{self._attr_name}' state saved")
        except Exception as ex:
            _LOGGER.error(f"Failed to save state for water heater '{self._attr_name}': {ex}")

    async def async_added_to_hass(self) -> None:
        """Call when entity is added to hass."""
        await super().async_added_to_hass()
        await self.async_load_state()
        self.async_write_ha_state()
        _LOGGER.info(f"Virtual water heater '{self._attr_name}' added to Home Assistant")

    def fire_template_event(self, action: str, **kwargs: Any) -> None:
        """Fire a template update event if templates are configured."""
        if self._templates:
            self._hass.bus.async_fire(
                f"{DOMAIN}_water_heater_template_update",
                {
                    "entity_id": self.entity_id,
                    "device_id": self._config_entry_id,
                    "action": action,
                    **kwargs,
                },
            )

    @property
    def current_temperature(self) -> float | None:
        """Return the current temperature."""
        return self._attr_current_temperature

    @property
    def target_temperature(self) -> float | None:
        """Return the target temperature."""
        return self._attr_target_temperature

    @property
    def current_operation(self) -> str | None:
        """Return the current operation mode."""
        return self._attr_current_operation

    @property
    def is_away_mode_on(self) -> bool:
        """Return the away mode."""
        return self._attr_is_away_mode_on

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        temperature = kwargs.get("temperature")
        if temperature is None:
            return

        if self._attr_min_temp <= temperature <= self._attr_max_temp:
            self._attr_target_temperature = temperature
            await self.async_save_state()
            self.async_write_ha_state()
            _LOGGER.debug(f"Water heater '{self._attr_name}' target temperature set to {temperature}°C")
            self.fire_template_event("set_temperature", temperature=temperature)

    async def async_set_operation_mode(self, operation_mode: str) -> None:
        """Set new operation mode."""
        self._attr_current_operation = operation_mode
        self._update_heating_state()
        await self.async_save_state()
        self.async_write_ha_state()
        _LOGGER.debug(f"Water heater '{self._attr_name}' operation mode set to {operation_mode}")
        self.fire_template_event("set_operation_mode", operation_mode=operation_mode)

    async def async_turn_away_mode_on(self) -> None:
        """Turn away mode on."""
        self._attr_is_away_mode_on = True
        self.async_write_ha_state()
        _LOGGER.debug(f"Water heater '{self._attr_name}' away mode turned on")
        self.fire_template_event("turn_away_mode_on")

    async def async_turn_away_mode_off(self) -> None:
        """Turn away mode off."""
        self._attr_is_away_mode_on = False
        self.async_write_ha_state()
        _LOGGER.debug(f"Water heater '{self._attr_name}' away mode turned off")
        self.fire_template_event("turn_away_mode_off")

    def _update_heating_state(self) -> None:
        """Update heating state based on operation mode."""
        was_heating = self._is_heating

        if self._attr_current_operation == "heat":
            if self._attr_current_temperature < self._attr_target_temperature - 2:
                if not self._is_heating:
                    self._is_heating = True
                    self._heating_start_time = time.time()
            elif self._attr_current_temperature >= self._attr_target_temperature:
                if self._is_heating:
                    self._is_heating = False
                    self._heating_start_time = None
        else:
            self._is_heating = False
            self._heating_start_time = None

        if was_heating != self._is_heating:
            self._update_power_consumption()

    def _update_power_consumption(self) -> None:
        """Update power consumption based on heating state and heater type."""
        if self._is_heating:
            power_map: dict[str, tuple[float, float]] = {
                "electric": (2000, 3000),
                "gas": (3000, 5000),
                "solar": (1000, 2000),
                "heat_pump": (800, 1500),
                "tankless": (5000, 8000),
            }
            min_power, max_power = power_map.get(self._heater_type, (2000, 3000))
            self._power_consumption = round(random.uniform(min_power, max_power), 0)
        else:
            standby_map: dict[str, tuple[float, float]] = {
                "electric": (5, 15),
                "gas": (10, 30),
                "solar": (2, 5),
                "heat_pump": (5, 20),
                "tankless": (5, 10),
            }
            min_power, max_power = standby_map.get(self._heater_type, (5, 15))
            self._power_consumption = round(random.uniform(min_power, max_power), 0)

    async def async_update(self) -> None:
        """Update water heater state."""
        current_time = time.time()

        # Simulate temperature change
        if self._is_heating and self._attr_current_operation == "heat":
            if self._heating_start_time:
                elapsed = current_time - self._heating_start_time
                heating_rate_map: dict[str, float] = {
                    "electric": 0.5,
                    "gas": 1.2,
                    "solar": 0.3,
                    "heat_pump": 0.4,
                    "tankless": 2.0,
                }
                heating_rate = heating_rate_map.get(self._heater_type, 0.5)
                temp_increase = (heating_rate * elapsed / 60) * self._efficiency
                self._attr_current_temperature = min(
                    self._attr_target_temperature,
                    self._attr_current_temperature + temp_increase
                )
        else:
            # Natural cooling
            if self._attr_current_temperature > 20:
                cooling_rate = 0.1
                time_diff = current_time - (self._last_update or current_time)
                self._attr_current_temperature = max(
                    20,
                    self._attr_current_temperature - (cooling_rate * time_diff / 60)
                )

        # Update energy consumption
        self._last_update = current_time
        if self._power_consumption > 0:
            time_diff = 1.0 / 3600
            energy_increase = (self._power_consumption / 1000) * time_diff
            self._energy_consumed_today += energy_increase
            self._total_energy_consumed += energy_increase

        self._update_heating_state()
        await self.async_save_state()
        self.async_write_ha_state()

        if self._templates:
            self._hass.bus.async_fire(
                f"{DOMAIN}_water_heater_template_update",
                {
                    "entity_id": self.entity_id,
                    "device_id": self._config_entry_id,
                    "current_temperature": self._attr_current_temperature,
                    "target_temperature": self._attr_target_temperature,
                    "operation_mode": self._attr_current_operation,
                    "is_heating": self._is_heating,
                    "power_consumption": self._power_consumption,
                },
            )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        attrs: dict[str, Any] = {
            "heater_type": WATER_HEATER_TYPES.get(self._heater_type, self._heater_type),
            "tank_capacity": f"{self._tank_capacity}L",
            "efficiency": f"{self._efficiency * 100:.0f}%",
            "is_heating": self._is_heating,
            "power_consumption": f"{self._power_consumption:.0f}W",
            "energy_consumed_today": f"{self._energy_consumed_today:.2f}kWh",
            "total_energy_consumed": f"{self._total_energy_consumed:.2f}kWh",
        }

        if self._heating_start_time:
            attrs["heating_duration"] = round(time.time() - self._heating_start_time, 1)

        if self._heater_type == "solar":
            attrs["solar_boost_available"] = random.choice([True, False])
        elif self._heater_type == "gas":
            attrs["pilot_light_on"] = self._is_heating

        return attrs
