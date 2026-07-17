"""Platform for virtual fan integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util.percentage import int_states_in_range

from .base_entity import BaseVirtualEntity
from .const import (
    CONF_ENTITIES,
    DEVICE_TYPE_AIR_PURIFIER,
    DEVICE_TYPE_FAN,
    DOMAIN,
)
from .types import FanEntityConfig, FanState

_LOGGER = logging.getLogger(__name__)

# Speed range for percentage calculation (1-100)
SPEED_RANGE: tuple[int, int] = (1, 100)

# Available preset modes for the fan
PRESET_MODES: list[str] = ["sleep", "nature", "strong"]


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up virtual fan and air purifier entities."""
    device_type: str | None = config_entry.data.get("device_type")

    # Only handle fan and air purifier device types
    if device_type not in (DEVICE_TYPE_FAN, DEVICE_TYPE_AIR_PURIFIER):
        return

    device_info: DeviceInfo = hass.data[DOMAIN][config_entry.entry_id]["device_info"]
    entities: list[VirtualFan] = []
    entities_config: list[FanEntityConfig] = config_entry.data.get(CONF_ENTITIES, [])

    # Create entities based on device type
    if device_type == DEVICE_TYPE_AIR_PURIFIER:
        # Import air_purifier module and create entities
        from .air_purifier import VirtualAirPurifier

        for idx, entity_config in enumerate(entities_config):
            entity = VirtualAirPurifier(
                hass,
                config_entry.entry_id,
                entity_config,
                idx,
                device_info,
            )
            entities.append(entity)
    else:
        # Create regular fan entities
        for idx, entity_config in enumerate(entities_config):
            entity = VirtualFan(
                hass,
                config_entry.entry_id,
                entity_config,
                idx,
                device_info,
            )
            entities.append(entity)

    async_add_entities(entities)


class VirtualFan(BaseVirtualEntity[FanEntityConfig, FanState], FanEntity):
    """Representation of a virtual fan."""

    _attr_supported_features: FanEntityFeature = (
        FanEntityFeature.TURN_ON
        | FanEntityFeature.TURN_OFF
        | FanEntityFeature.SET_SPEED
        | FanEntityFeature.PRESET_MODE
        | FanEntityFeature.OSCILLATE
        | FanEntityFeature.DIRECTION
    )

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry_id: str,
        entity_config: FanEntityConfig,
        index: int,
        device_info: DeviceInfo,
    ) -> None:
        """Initialize the virtual fan."""
        super().__init__(hass, config_entry_id, entity_config, index, device_info, "fan")

        # Fan-specific attributes
        self._attr_preset_modes = PRESET_MODES
        self._attr_speed_count = int_states_in_range(SPEED_RANGE)

        # State attributes - will be populated by async_load_state.
        # HA Core `FanEntity` exposes these via cached_properties that read the
        # matching `_attr_*` fields, so we set those directly and do NOT
        # redefine them as @property overrides.
        self._attr_is_on: bool = False
        self._attr_percentage: int | None = 50
        self._attr_preset_mode: str | None = None
        self._attr_oscillating: bool = False
        self._attr_current_direction: str | None = "forward"

    def get_default_state(self) -> FanState:
        """Return the default state for this fan entity."""
        return {
            "is_on": False,
            "percentage": 50,
            "preset_mode": None,
            "oscillating": False,
            "direction": "forward",
        }

    def apply_state(self, state: FanState) -> None:
        """Apply loaded state to entity attributes."""
        self._attr_is_on = state.get("is_on", False)
        self._attr_percentage = state.get("percentage", 50)
        self._attr_preset_mode = state.get("preset_mode")
        self._attr_oscillating = state.get("oscillating", False)
        self._attr_current_direction = state.get("direction", "forward")
        _LOGGER.debug(
            "Applied state for fan '%s': is_on=%s, percentage=%s, preset_mode=%s",
            self._attr_name, self._attr_is_on, self._attr_percentage, self._attr_preset_mode,
        )

    def get_current_state(self) -> FanState:
        """Get current state for persistence."""
        return {
            "is_on": self._attr_is_on,
            "percentage": self._attr_percentage,
            "preset_mode": self._attr_preset_mode,
            "oscillating": self._attr_oscillating,
            "direction": self._attr_current_direction,
        }

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Turn on the fan."""
        self._attr_is_on = True

        if percentage is not None:
            self._attr_percentage = percentage
            self._attr_preset_mode = None
        elif preset_mode is not None:
            self._attr_preset_mode = preset_mode
            self._attr_percentage = 50

        await self.async_save_state()
        self.async_write_ha_state()
        self.fire_template_event("turn_on", percentage=percentage, preset_mode=preset_mode)
        _LOGGER.debug("Virtual fan '%s' turned on", self._attr_name)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the fan off."""
        self._attr_is_on = False

        await self.async_save_state()
        self.async_write_ha_state()
        self.fire_template_event("turn_off")
        _LOGGER.debug("Virtual fan '%s' turned off", self._attr_name)

    async def async_set_percentage(self, percentage: int) -> None:
        """Set the speed percentage of the fan."""
        # Validate percentage range (0-100)
        original_percentage: int = percentage
        percentage = max(0, min(100, percentage))

        if original_percentage != percentage:
            _LOGGER.warning(
                "Fan percentage %d%% out of range (0-100%%), clamped to %d%%",
                original_percentage, percentage,
            )

        self._attr_percentage = percentage
        self._attr_preset_mode = None
        if percentage == 0:
            self._attr_is_on = False
        else:
            self._attr_is_on = True

        await self.async_save_state()
        self.async_write_ha_state()
        self.fire_template_event("set_percentage", percentage=percentage)
        _LOGGER.debug("Virtual fan '%s' speed set to %d%%", self._attr_name, percentage)

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set the preset mode of the fan."""
        self._attr_preset_mode = preset_mode
        self._attr_is_on = True

        await self.async_save_state()
        self.async_write_ha_state()
        self.fire_template_event("set_preset_mode", preset_mode=preset_mode)
        _LOGGER.debug(
            "Virtual fan '%s' preset mode set to %s", self._attr_name, preset_mode
        )

    async def async_oscillate(self, oscillating: bool) -> None:
        """Set oscillation."""
        self._attr_oscillating = oscillating

        await self.async_save_state()
        self.async_write_ha_state()
        self.fire_template_event("oscillate", oscillating=oscillating)
        _LOGGER.debug(
            "Virtual fan '%s' oscillation set to %s", self._attr_name, oscillating
        )

    async def async_set_direction(self, direction: str) -> None:
        """Set the direction of the fan."""
        self._attr_current_direction = direction

        await self.async_save_state()
        self.async_write_ha_state()
        self.fire_template_event("set_direction", direction=direction)
        _LOGGER.debug("Virtual fan '%s' direction set to %s", self._attr_name, direction)
