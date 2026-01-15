"""Platform for virtual air purifier integration."""
from __future__ import annotations

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
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.storage import Store

from .base_entity import STORAGE_VERSION
from .const import (
    CONF_ENTITIES,
    CONF_ENTITY_NAME,
    DEVICE_TYPE_AIR_PURIFIER,
    DOMAIN,
    AIR_PURIFIER_TYPES,
    AQI_LEVELS,
)
from .types import AirPurifierEntityConfig, AirPurifierState

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up virtual air purifier entities."""
    device_type: str | None = config_entry.data.get("device_type")

    if device_type != DEVICE_TYPE_AIR_PURIFIER:
        return

    device_info: DeviceInfo = hass.data[DOMAIN][config_entry.entry_id]["device_info"]
    entities: list[VirtualAirPurifier] = []
    entities_config: list[AirPurifierEntityConfig] = config_entry.data.get(CONF_ENTITIES, [])

    for idx, entity_config in enumerate(entities_config):
        entity = VirtualAirPurifier(
            hass,
            config_entry.entry_id,
            entity_config,
            idx,
            device_info,
        )
        entities.append(entity)

    async_add_entities(entities)


class VirtualAirPurifier(FanEntity):
    """Representation of a virtual air purifier.

    This entity implements state persistence using the same pattern as BaseVirtualEntity.
    """

    _attr_should_poll: bool = True
    _attr_entity_registry_enabled_default: bool = True

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry_id: str,
        entity_config: AirPurifierEntityConfig,
        index: int,
        device_info: DeviceInfo,
    ) -> None:
        """Initialize the virtual air purifier."""
        self._hass = hass
        self._config_entry_id = config_entry_id
        self._entity_config = entity_config
        self._index = index

        entity_name: str = entity_config.get(CONF_ENTITY_NAME, f"Air Purifier_{index + 1}")
        self._attr_name = entity_name
        self._attr_unique_id = f"{config_entry_id}_air_purifier_{index}"
        self._attr_icon = "mdi:air-purifier"

        # Template support
        self._templates: dict[str, Any] = entity_config.get("templates", {})

        # Storage for state persistence
        self._store: Store[AirPurifierState] = Store(
            hass, STORAGE_VERSION, f"virtual_devices_air_purifier_{config_entry_id}_{index}"
        )

        # Purifier type
        purifier_type: str = entity_config.get("purifier_type", "hepa")
        self._purifier_type = purifier_type

        # Set icon based on type
        icon_map: dict[str, str] = {
            "hepa": "mdi:air-filter",
            "activated_carbon": "mdi:air-filter",
            "uv_c": "mdi:lightbulb",
            "ionic": "mdi:creation",
            "ozone": "mdi:weather-tornado",
            "hybrid": "mdi:air-purifier",
        }
        self._attr_icon = icon_map.get(purifier_type, "mdi:air-purifier")

        # Supported features
        self._attr_supported_features: FanEntityFeature = (
            FanEntityFeature.TURN_ON
            | FanEntityFeature.TURN_OFF
            | FanEntityFeature.SET_SPEED
            | FanEntityFeature.OSCILLATE
        )

        # Set device info
        self._attr_device_info = device_info

        # Initial state
        self._attr_is_on: bool = False
        self._attr_percentage: int = entity_config.get("fan_speed", 0)
        self._attr_oscillating: bool = False

        # Setup speed list
        self._setup_purifier_features()

        # Air quality related
        self._pm25: float = entity_config.get("pm25", 35)
        self._pm10: float = entity_config.get("pm10", 50)
        self._co2: float = entity_config.get("co2", 400)
        self._voc: float = entity_config.get("voc", 0.3)
        self._formaldehyde: float = entity_config.get("formaldehyde", 0.05)

        # Filter status
        self._filter_life: float = entity_config.get("filter_life", 80)
        self._filter_usage_hours: float = 0
        self._filter_max_hours: int = 2160

        # Running statistics
        self._total_air_cleaned: float = entity_config.get("total_air_cleaned", 50000)
        self._running_time: float = 0
        self._last_update: datetime | None = None

        # Room volume (m³)
        self._room_volume: float = entity_config.get("room_volume", 50)

        # Cleaning rate (m³/h)
        self._cleaning_rate: float = self._get_cleaning_rate()

        _LOGGER.info(f"Virtual air purifier '{self._attr_name}' initialized")

    def get_default_state(self) -> AirPurifierState:
        """Return the default state for this entity type."""
        return {
            "is_on": False,
            "percentage": 0,
            "preset_mode": None,
            "pm25": 35,
            "aqi": 50,
        }

    def apply_state(self, state: AirPurifierState) -> None:
        """Apply loaded state to entity attributes."""
        self._attr_is_on = state.get("is_on", False)
        self._attr_percentage = state.get("percentage", 0)
        self._attr_oscillating = False

    def get_current_state(self) -> AirPurifierState:
        """Get current state for persistence."""
        return {
            "is_on": self._attr_is_on,
            "percentage": self._attr_percentage,
            "preset_mode": None,
            "pm25": int(self._pm25),
            "aqi": self.calculate_aqi()["aqi"],
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
                _LOGGER.debug(f"Air purifier '{self._attr_name}' state loaded")
        except Exception as ex:
            _LOGGER.error(f"Failed to load state for air purifier '{self._attr_name}': {ex}")
            self.apply_state(self.get_default_state())

    async def async_save_state(self) -> None:
        """Save current state to storage."""
        try:
            data = self.get_current_state()
            await self._store.async_save(data)
            _LOGGER.debug(f"Air purifier '{self._attr_name}' state saved")
        except Exception as ex:
            _LOGGER.error(f"Failed to save state for air purifier '{self._attr_name}': {ex}")

    async def async_added_to_hass(self) -> None:
        """Call when entity is added to hass."""
        await super().async_added_to_hass()
        await self.async_load_state()
        self._last_update = datetime.now()
        self.async_write_ha_state()
        _LOGGER.info(f"Virtual air purifier '{self._attr_name}' added to Home Assistant")

    def fire_template_event(self, action: str, **kwargs: Any) -> None:
        """Fire a template update event if templates are configured."""
        if self._templates:
            self._hass.bus.async_fire(
                f"{DOMAIN}_air_purifier_template_update",
                {
                    "entity_id": self.entity_id,
                    "device_id": self._config_entry_id,
                    "action": action,
                    **kwargs,
                },
            )

    def _setup_purifier_features(self) -> None:
        """Setup air purifier features based on type."""
        speed_map: dict[str, list[int]] = {
            "hepa": [0, 25, 50, 75, 100],
            "activated_carbon": [0, 33, 66, 100],
            "uv_c": [0, 50, 100],
            "ionic": [0, 25, 50, 75, 100],
            "ozone": [0, 50, 100],
            "hybrid": [0, 20, 40, 60, 80, 100],
        }
        self._speed_list: list[int] = speed_map.get(self._purifier_type, [0, 50, 100])

    def _get_cleaning_rate(self) -> float:
        """Get cleaning rate based on purifier type and fan speed."""
        base_rates: dict[str, float] = {
            "hepa": 200, "activated_carbon": 180, "uv_c": 150,
            "ionic": 120, "ozone": 100, "hybrid": 250,
        }
        base_rate = base_rates.get(self._purifier_type, 150)

        if self._attr_percentage > 0:
            return base_rate * (self._attr_percentage / 100)
        return 0

    @property
    def is_on(self) -> bool:
        """Return true if the air purifier is on."""
        return self._attr_is_on

    @property
    def percentage(self) -> int | None:
        """Return the current speed percentage."""
        return self._attr_percentage if self._attr_is_on else 0

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
        if self._filter_life < 10:
            _LOGGER.warning(f"Air purifier '{self._attr_name}' filter needs replacement")
            return

        self._attr_is_on = True
        self._attr_percentage = percentage if percentage is not None else 50
        self._running_time = 0
        self._last_update = datetime.now()
        await self.async_save_state()
        self.async_write_ha_state()
        _LOGGER.debug(f"Virtual air purifier '{self._attr_name}' turned on")
        self.fire_template_event("turn_on", percentage=self._attr_percentage)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the air purifier off."""
        self._attr_is_on = False
        self._attr_percentage = 0
        await self.async_save_state()
        self.async_write_ha_state()
        _LOGGER.debug(f"Virtual air purifier '{self._attr_name}' turned off")
        self.fire_template_event("turn_off")

    async def async_set_percentage(self, percentage: int) -> None:
        """Set the speed percentage of the fan."""
        if self._attr_is_on and percentage > 0:
            closest_speed = min(self._speed_list, key=lambda x: abs(x - percentage))
            self._attr_percentage = closest_speed
            self._cleaning_rate = self._get_cleaning_rate()
            await self.async_save_state()
            self.async_write_ha_state()
            _LOGGER.debug(f"Air purifier '{self._attr_name}' speed set to {closest_speed}%")
            self.fire_template_event("set_speed", percentage=closest_speed)

    async def async_oscillate(self, oscillating: bool) -> None:
        """Set oscillation."""
        self._attr_oscillating = oscillating
        await self.async_save_state()
        self.async_write_ha_state()
        _LOGGER.debug(f"Air purifier '{self._attr_name}' oscillation set to {oscillating}")
        self.fire_template_event("set_oscillate", oscillating=oscillating)

    def calculate_aqi(self) -> dict[str, Any]:
        """Calculate AQI based on current air quality."""
        pm25_aqi = self._calculate_pm25_aqi(self._pm25)

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
            time_diff = time.time() - self._last_update.timestamp()
            self._running_time += time_diff
            self._filter_usage_hours += time_diff / 3600

            # Update filter life
            usage_percentage = (self._filter_usage_hours / self._filter_max_hours) * 100
            self._filter_life = max(0, 100 - usage_percentage)

            # Calculate cleaning effect
            if self._cleaning_rate > 0:
                cleaned_air = self._cleaning_rate * (time_diff / 3600)
                self._total_air_cleaned += cleaned_air

                improvement_factor = cleaned_air / self._room_volume
                self._pm25 = max(0, self._pm25 - improvement_factor * 2)
                self._pm10 = max(0, self._pm10 - improvement_factor * 1.5)
                self._voc = max(0, self._voc - improvement_factor * 0.1)
                self._formaldehyde = max(0, self._formaldehyde - improvement_factor * 0.01)
                self._co2 = max(350, self._co2 - improvement_factor * 10)
        else:
            # Natural air quality degradation
            self._pm25 = min(500, self._pm25 + random.uniform(0.1, 0.5))
            self._pm10 = min(600, self._pm10 + random.uniform(0.1, 0.3))
            self._voc = min(2.0, self._voc + random.uniform(0.001, 0.005))
            self._formaldehyde = min(0.3, self._formaldehyde + random.uniform(0.0001, 0.0005))
            self._co2 = min(2000, self._co2 + random.uniform(1, 5))

        self._last_update = datetime.now()
        self.async_write_ha_state()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        aqi_data = self.calculate_aqi()

        attrs: dict[str, Any] = {
            "purifier_type": AIR_PURIFIER_TYPES.get(self._purifier_type, self._purifier_type),
            "room_volume": f"{self._room_volume:.1f} m³",
            "cleaning_rate": f"{self._cleaning_rate:.0f} m³/h",
            "filter_life": f"{self._filter_life:.1f}%",
            "pm25": f"{self._pm25:.1f} µg/m³",
            "pm10": f"{self._pm10:.1f} µg/m³",
            "co2": f"{self._co2:.0f} ppm",
            "voc": f"{self._voc:.2f} mg/m³",
            "formaldehyde": f"{self._formaldehyde:.3f} mg/m³",
            "aqi": aqi_data["aqi"],
            "aqi_level": aqi_data["level"],
            "aqi_label": aqi_data["label"],
            "total_air_cleaned": f"{round(self._total_air_cleaned):.0f} m³",
            "running_time": f"{round(self._running_time / 3600, 1)} h",
        }

        if self._purifier_type == "uv_c":
            uv_lamp_life = max(0, 100 - self._filter_usage_hours / 21.6)
            attrs["uv_lamp_status"] = self._attr_is_on
            attrs["uv_lamp_life"] = f"{uv_lamp_life:.1f}%"
        elif self._purifier_type == "ionic":
            attrs["ionizer_active"] = self._attr_is_on
        elif self._purifier_type == "ozone":
            attrs["ozone_level"] = "low" if self._attr_percentage <= 50 else "high"

        return attrs
