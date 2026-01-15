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
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.storage import Store

from .base_entity import STORAGE_VERSION
from .const import (
    CONF_ENTITIES,
    CONF_ENTITY_NAME,
    DEVICE_TYPE_HUMIDIFIER,
    DOMAIN,
    HUMIDIFIER_TYPES,
)
from .types import HumidifierEntityConfig, HumidifierState

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up virtual humidifier entities."""
    device_type: str | None = config_entry.data.get("device_type")

    if device_type != DEVICE_TYPE_HUMIDIFIER:
        return

    device_info: DeviceInfo = hass.data[DOMAIN][config_entry.entry_id]["device_info"]
    entities: list[VirtualHumidifier] = []
    entities_config: list[HumidifierEntityConfig] = config_entry.data.get(CONF_ENTITIES, [])

    for idx, entity_config in enumerate(entities_config):
        entity = VirtualHumidifier(
            hass,
            config_entry.entry_id,
            entity_config,
            idx,
            device_info,
        )
        entities.append(entity)

    async_add_entities(entities)


class VirtualHumidifier(HumidifierEntity):
    """Representation of a virtual humidifier.

    This entity implements state persistence using the same pattern as BaseVirtualEntity.
    """

    _attr_should_poll: bool = True
    _attr_entity_registry_enabled_default: bool = True

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry_id: str,
        entity_config: HumidifierEntityConfig,
        index: int,
        device_info: DeviceInfo,
    ) -> None:
        """Initialize the virtual humidifier."""
        self._hass = hass
        self._config_entry_id = config_entry_id
        self._entity_config = entity_config
        self._index = index

        entity_name: str = entity_config.get(CONF_ENTITY_NAME, f"Humidifier_{index + 1}")
        self._attr_name = entity_name
        self._attr_unique_id = f"{config_entry_id}_humidifier_{index}"

        # Humidifier type
        humidifier_type: str = entity_config.get("humidifier_type", "ultrasonic")
        self._humidifier_type = humidifier_type

        # Set icon based on type
        icon_map: dict[str, str] = {
            "ultrasonic": "mdi:air-humidifier",
            "evaporative": "mdi:air-filter",
            "steam": "mdi:water",
            "impeller": "mdi:fan",
            "warm_mist": "mdi:water-thermometer",
        }
        self._attr_icon = icon_map.get(humidifier_type, "mdi:air-humidifier")

        # Template support
        self._templates: dict[str, Any] = entity_config.get("templates", {})

        # Storage for state persistence
        self._store: Store[HumidifierState] = Store(
            hass, STORAGE_VERSION, f"virtual_devices_humidifier_{config_entry_id}_{index}"
        )

        # Setup features
        self._setup_humidifier_features()

        # Initial state
        self._attr_is_on: bool = False
        self._attr_target_humidity: int = entity_config.get("target_humidity", 60)
        self._attr_current_humidity: int = entity_config.get("current_humidity", 45)
        self._attr_mode: str | None = "Auto"

        # Water tank related
        self._water_level: float = entity_config.get("water_level", 80)
        self._tank_capacity: float = entity_config.get("tank_capacity", 4.0)

        # Maintenance related
        self._filter_life_time: int = entity_config.get("filter_life_time", 2160)
        self._filter_usage_time: float = 0
        self._needs_filter_replacement: bool = False

        # Running statistics
        self._total_water_consumed: float = entity_config.get("total_water_consumed", 100.0)
        self._running_time: float = 0
        self._last_update: datetime | None = datetime.now()

        # Set device info
        self._attr_device_info = device_info

        _LOGGER.info(f"Virtual humidifier '{self._attr_name}' initialized")

    def get_default_state(self) -> HumidifierState:
        """Return the default state for this entity type."""
        return {
            "is_on": False,
            "target_humidity": 60,
            "current_humidity": 45,
            "mode": "Auto",
        }

    def apply_state(self, state: HumidifierState) -> None:
        """Apply loaded state to entity attributes."""
        self._attr_is_on = state.get("is_on", False)
        self._attr_target_humidity = state.get("target_humidity", 60)
        self._attr_mode = state.get("mode", "Auto")

    def get_current_state(self) -> HumidifierState:
        """Get current state for persistence."""
        return {
            "is_on": self._attr_is_on,
            "target_humidity": self._attr_target_humidity,
            "current_humidity": self._attr_current_humidity,
            "mode": self._attr_mode,
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
                _LOGGER.debug(f"Humidifier '{self._attr_name}' state loaded")
        except Exception as ex:
            _LOGGER.error(f"Failed to load state for humidifier '{self._attr_name}': {ex}")
            self.apply_state(self.get_default_state())

    async def async_save_state(self) -> None:
        """Save current state to storage."""
        try:
            data = self.get_current_state()
            await self._store.async_save(data)
            _LOGGER.debug(f"Humidifier '{self._attr_name}' state saved")
        except Exception as ex:
            _LOGGER.error(f"Failed to save state for humidifier '{self._attr_name}': {ex}")

    async def async_added_to_hass(self) -> None:
        """Call when entity is added to hass."""
        await super().async_added_to_hass()
        await self.async_load_state()
        self.async_write_ha_state()
        _LOGGER.info(f"Virtual humidifier '{self._attr_name}' added to Home Assistant")

    def fire_template_event(self, action: str, **kwargs: Any) -> None:
        """Fire a template update event if templates are configured."""
        if self._templates:
            self._hass.bus.async_fire(
                f"{DOMAIN}_humidifier_template_update",
                {
                    "entity_id": self.entity_id,
                    "device_id": self._config_entry_id,
                    "action": action,
                    **kwargs,
                },
            )

    def _setup_humidifier_features(self) -> None:
        """Setup humidifier features based on type."""
        features: HumidifierEntityFeature = HumidifierEntityFeature(0)

        if self._humidifier_type in ["ultrasonic", "impeller", "warm_mist", "steam", "evaporative"]:
            features |= HumidifierEntityFeature.MODES

        self._attr_supported_features = features

        # Set available modes
        mode_map: dict[str, list[str]] = {
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
    def available_modes(self) -> list[str] | None:
        """Return the available modes."""
        return self._attr_available_modes

    @property
    def min_humidity(self) -> int:
        """Return the minimum humidity."""
        min_map: dict[str, int] = {
            "ultrasonic": 30, "impeller": 30, "warm_mist": 30,
            "evaporative": 20, "steam": 40,
        }
        return min_map.get(self._humidifier_type, 30)

    @property
    def max_humidity(self) -> int:
        """Return the maximum humidity."""
        max_map: dict[str, int] = {
            "ultrasonic": 80, "impeller": 80, "warm_mist": 80,
            "evaporative": 70, "steam": 90,
        }
        return max_map.get(self._humidifier_type, 80)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the humidifier on."""
        if self._water_level < 10:
            _LOGGER.warning(f"Humidifier '{self._attr_name}' water level too low")
            return

        self._attr_is_on = True
        self._running_time = 0
        self._last_update = datetime.now()
        await self.async_save_state()
        self.async_write_ha_state()
        _LOGGER.debug(f"Virtual humidifier '{self._attr_name}' turned on")
        self.fire_template_event("turn_on", target_humidity=self._attr_target_humidity, mode=self._attr_mode)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the humidifier off."""
        self._attr_is_on = False
        await self.async_save_state()
        self.async_write_ha_state()
        _LOGGER.debug(f"Virtual humidifier '{self._attr_name}' turned off")
        self.fire_template_event("turn_off")

    async def async_set_humidity(self, humidity: int) -> None:
        """Set the target humidity."""
        if self.min_humidity <= humidity <= self.max_humidity:
            self._attr_target_humidity = humidity
            await self.async_save_state()
            self.async_write_ha_state()
            _LOGGER.debug(f"Humidifier '{self._attr_name}' target humidity set to {humidity}%")
            self.fire_template_event("set_humidity", target_humidity=humidity)

    async def async_set_mode(self, mode: str) -> None:
        """Set the mode of the humidifier."""
        if mode in self._attr_available_modes:
            self._attr_mode = mode
            await self.async_save_state()
            self.async_write_ha_state()
            _LOGGER.debug(f"Humidifier '{self._attr_name}' mode set to {mode}")
            self.fire_template_event("set_mode", mode=mode)

    async def async_update(self) -> None:
        """Update humidifier state."""
        now = datetime.now()

        if self._attr_is_on and self._last_update:
            time_diff = (now - self._last_update).total_seconds()
            self._running_time += time_diff

            # Simulate humidity change
            target_diff = self._attr_target_humidity - self._attr_current_humidity
            if abs(target_diff) > 1:
                rate_map: dict[str, float] = {
                    "ultrasonic": 1.5, "evaporative": 2.0, "steam": 3.0,
                    "impeller": 2.5, "warm_mist": 1.8,
                }
                rate = rate_map.get(self._humidifier_type, 1.5)

                mode_multiplier: dict[str, float] = {"Auto": 1.0, "Low": 0.6, "Medium": 1.0, "High": 1.5}
                rate *= mode_multiplier.get(self._attr_mode or "Auto", 1.0)

                temp_increase = (rate * time_diff / 60) * 0.9
                if target_diff > 0:
                    self._attr_current_humidity = min(
                        self.max_humidity, self._attr_current_humidity + int(temp_increase))
                else:
                    self._attr_current_humidity = max(self.min_humidity,
                                                      self._attr_current_humidity - int(temp_increase * 0.5))

            # Water consumption
            water_rate_map: dict[str, float] = {
                "ultrasonic": 0.2, "evaporative": 0.8, "steam": 0.5,
                "impeller": 0.6, "warm_mist": 0.3,
            }
            water_rate = water_rate_map.get(self._humidifier_type, 0.2)
            self._total_water_consumed += water_rate * time_diff / 3600
            self._water_level = max(0, self._water_level - (water_rate * time_diff / 3600) * 100 / self._tank_capacity)

            # Filter usage
            self._filter_usage_time += time_diff
            if self._filter_usage_time >= self._filter_life_time:
                self._needs_filter_replacement = True
                self._filter_usage_time = 0

        else:
            # Natural humidity change when off
            ambient_humidity = random.randint(30, 70)
            humidity_diff = (ambient_humidity - self._attr_current_humidity) * 0.1
            self._attr_current_humidity = int(self._attr_current_humidity + humidity_diff)

        self._last_update = now
        self.async_write_ha_state()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        attrs: dict[str, Any] = {
            "humidifier_type": HUMIDIFIER_TYPES.get(self._humidifier_type, self._humidifier_type),
            "water_level": f"{self._water_level:.0f}%",
            "tank_capacity": f"{self._tank_capacity}L",
            "filter_life_time": f"{self._filter_life_time}h",
            "filter_usage_time": f"{round(self._filter_usage_time / 3600, 1)}h",
            "needs_filter_replacement": self._needs_filter_replacement,
            "total_water_consumed": f"{round(self._total_water_consumed, 1)}L",
            "running_time": f"{round(self._running_time / 3600, 1)}h",
        }

        if self._humidifier_type == "ultrasonic":
            attrs["mist_output_level"] = "medium"
        elif self._humidifier_type == "steam":
            attrs["steam_output_level"] = "medium"
        elif self._humidifier_type == "warm_mist":
            attrs["temperature"] = "warm"

        return attrs
