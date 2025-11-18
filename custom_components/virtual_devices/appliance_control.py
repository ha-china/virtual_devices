"""Appliance control domain service for fans, air purifiers, and vacuums."""
from __future__ import annotations

import logging
from typing import Any, List

from homeassistant.components.fan import (
    FanEntity,
    FanEntityFeature,
)
from homeassistant.components.air_purifier import (
    AirPurifierEntity,
    AirPurifierEntityFeature,
)
from homeassistant.components.vacuum import (
    VacuumEntity,
    VacuumEntityFeature,
    VacuumState,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .base_service import BaseVirtualEntity, VirtualDeviceService
from .const import (
    CONF_ENTITIES,
    CONF_ENTITY_NAME,
    DEVICE_TYPE_FAN,
    DEVICE_TYPE_AIR_PURIFIER,
    DEVICE_TYPE_VACUUM,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class VirtualFan(BaseVirtualEntity, FanEntity):
    """Representation of a virtual fan."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry_id: str,
        entity_config: dict[str, Any],
        index: int,
        device_info: dict[str, Any],
    ) -> None:
        """Initialize the virtual fan."""
        super().__init__(hass, config_entry_id, entity_config, index, device_info, "fan")

        # Fan specific configuration
        fan_type = entity_config.get("fan_type", "ceiling")
        self._fan_type = fan_type

        # Set icon based on type
        icon_map = {
            "ceiling": "mdi:fan",
            "table": "mdi:fan-chevron-down",
            "tower": "mdi:fan-auto",
            "exhaust": "mdi:fan-removed",
        }
        self._attr_icon = icon_map.get(fan_type, "mdi:fan")

        # Set supported features
        self._attr_supported_features = FanEntityFeature.SET_SPEED
        if entity_config.get("has_oscillate", False):
            self._attr_supported_features |= FanEntityFeature.OSCILLATE
        if entity_config.get("has_direction", False):
            self._attr_supported_features |= FanEntityFeature.DIRECTION

        # Fan specific state
        self._attr_is_on = False
        self._attr_percentage = 0
        self._attr_oscillating = False
        self._attr_current_direction = "forward"

        # Speed settings
        self._attr_speed_count = 3

    async def _apply_loaded_state(self) -> None:
        """Apply loaded state to fan entity."""
        self._attr_is_on = self._state.get("is_on", False)
        self._attr_percentage = self._state.get("percentage", 0)
        self._attr_oscillating = self._state.get("oscillating", False)
        self._attr_current_direction = self._state.get("current_direction", "forward")

    async def _initialize_default_state(self) -> None:
        """Initialize default fan state."""
        self._state = {
            "is_on": False,
            "percentage": 0,
            "oscillating": False,
            "current_direction": "forward",
        }

    async def async_turn_on(self, percentage: int | None = None, **kwargs: Any) -> None:
        """Turn the fan on."""
        self._attr_is_on = True
        self._attr_percentage = percentage if percentage is not None else 33
        self._state["is_on"] = True
        self._state["percentage"] = self._attr_percentage
        await self.async_save_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the fan off."""
        self._attr_is_on = False
        self._attr_percentage = 0
        self._state["is_on"] = False
        self._state["percentage"] = 0
        await self.async_save_state()

    async def async_set_percentage(self, percentage: int) -> None:
        """Set the speed percentage of the fan."""
        if percentage == 0:
            await self.async_turn_off()
        else:
            self._attr_is_on = True
            self._attr_percentage = percentage
            self._state["is_on"] = True
            self._state["percentage"] = percentage
            await self.async_save_state()

    async def async_oscillate(self, oscillating: bool) -> None:
        """Set oscillation."""
        self._attr_oscillating = oscillating
        self._state["oscillating"] = oscillating
        await self.async_save_state()

    async def async_set_direction(self, direction: str) -> None:
        """Set direction."""
        self._attr_current_direction = direction
        self._state["current_direction"] = direction
        await self.async_save_state()


class VirtualAirPurifier(BaseVirtualEntity, AirPurifierEntity):
    """Representation of a virtual air purifier."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry_id: str,
        entity_config: dict[str, Any],
        index: int,
        device_info: dict[str, Any],
    ) -> None:
        """Initialize the virtual air purifier."""
        super().__init__(hass, config_entry_id, entity_config, index, device_info, "air_purifier")

        # Air purifier specific configuration
        purifier_type = entity_config.get("purifier_type", "hepa")
        self._purifier_type = purifier_type

        # Set icon based on type
        icon_map = {
            "hepa": "mdi:air-filter",
            "carbon": "mdi:air-purifier",
            "uv": "mdi:sun-wireless",
            "ionic": "mdi:ionizer",
        }
        self._attr_icon = icon_map.get(purifier_type, "mdi:air-filter")

        # Set supported features
        self._attr_supported_features = (
            AirPurifierEntityFeature.MODES
            | AirPurifierEntityFeature.TARGET_HUMIDITY
        )

        # Air purifier specific state
        self._attr_is_on = False
        self._attr_mode = "Auto"
        self._attr_available_modes = ["Off", "Auto", "Low", "Medium", "High", "Turbo"]

    async def _apply_loaded_state(self) -> None:
        """Apply loaded state to air purifier entity."""
        self._attr_is_on = self._state.get("is_on", False)
        self._attr_mode = self._state.get("mode", "Auto")

    async def _initialize_default_state(self) -> None:
        """Initialize default air purifier state."""
        self._state = {
            "is_on": False,
            "mode": "Auto",
        }

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the air purifier on."""
        self._attr_is_on = True
        if self._attr_mode == "Off":
            self._attr_mode = "Auto"
        self._state["is_on"] = True
        self._state["mode"] = self._attr_mode
        await self.async_save_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the air purifier off."""
        self._attr_is_on = False
        self._state["is_on"] = False
        await self.async_save_state()

    async def async_set_mode(self, mode: str) -> None:
        """Set new mode."""
        if mode in self._attr_available_modes:
            self._attr_mode = mode
            self._attr_is_on = mode != "Off"
            self._state["mode"] = mode
            self._state["is_on"] = self._attr_is_on
            await self.async_save_state()


class VirtualVacuum(BaseVirtualEntity, VacuumEntity):
    """Representation of a virtual vacuum."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry_id: str,
        entity_config: dict[str, Any],
        index: int,
        device_info: dict[str, Any],
    ) -> None:
        """Initialize the virtual vacuum."""
        super().__init__(hass, config_entry_id, entity_config, index, device_info, "vacuum")

        # Vacuum specific configuration
        vacuum_type = entity_config.get("vacuum_type", "robot")
        self._vacuum_type = vacuum_type

        # Set icon based on type
        icon_map = {
            "robot": "mdi:robot-vacuum",
            "upright": "mdi:vacuum",
            "handheld": "mdi:hand-saw",
        }
        self._attr_icon = icon_map.get(vacuum_type, "mdi:robot-vacuum")

        # Set supported features
        self._attr_supported_features = (
            VacuumEntityFeature.START
            | VacuumEntityFeature.PAUSE
            | VacuumEntityFeature.RETURN_HOME
            | VacuumEntityFeature.STOP
            | VacuumEntityFeature.STATUS
            | VacuumEntityFeature.SEND_COMMAND
        )

        # Vacuum specific state
        self._attr_status = VacuumState.DOCKED
        self._attr_battery_level = 100

    async def _apply_loaded_state(self) -> None:
        """Apply loaded state to vacuum entity."""
        self._attr_status = self._state.get("status", VacuumState.DOCKED)
        self._attr_battery_level = self._state.get("battery_level", 100)

    async def _initialize_default_state(self) -> None:
        """Initialize default vacuum state."""
        self._state = {
            "status": VacuumState.DOCKED,
            "battery_level": 100,
        }

    async def async_start(self) -> None:
        """Start the vacuum."""
        self._attr_status = VacuumState.CLEANING
        self._state["status"] = VacuumState.CLEANING
        await self.async_save_state()

    async def async_pause(self) -> None:
        """Pause the vacuum."""
        self._attr_status = VacuumState.PAUSED
        self._state["status"] = VacuumState.PAUSED
        await self.async_save_state()

    async def async_return_to_base(self, **kwargs: Any) -> None:
        """Return vacuum to base."""
        self._attr_status = VacuumState.RETURNING
        self._state["status"] = VacuumState.RETURNING
        await self.async_save_state()

    async def async_stop(self, **kwargs: Any) -> None:
        """Stop the vacuum."""
        self._attr_status = VacuumState.DOCKED
        self._state["status"] = VacuumState.DOCKED
        await self.async_save_state()


class ApplianceControlService(VirtualDeviceService):
    """Appliance control domain service."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the appliance control service."""
        super().__init__(hass, "appliance_control")
        self._supported_device_types = [
            DEVICE_TYPE_FAN,
            DEVICE_TYPE_AIR_PURIFIER,
            DEVICE_TYPE_VACUUM,
        ]

    async def async_setup_entry(
        self,
        config_entry: ConfigEntry,
        async_add_entities,
    ) -> None:
        """Set up appliance control entities."""
        device_type = config_entry.data.get("device_type")

        if not self.is_device_type_supported(device_type):
            return

        device_info = self._get_device_info(config_entry)
        entities_config = self._get_entities_config(config_entry)
        entities = []

        for idx, entity_config in enumerate(entities_config):
            if device_type == DEVICE_TYPE_FAN:
                entity = VirtualFan(self._hass, config_entry.entry_id, entity_config, idx, device_info)
            elif device_type == DEVICE_TYPE_AIR_PURIFIER:
                entity = VirtualAirPurifier(self._hass, config_entry.entry_id, entity_config, idx, device_info)
            elif device_type == DEVICE_TYPE_VACUUM:
                entity = VirtualVacuum(self._hass, config_entry.entry_id, entity_config, idx, device_info)
            else:
                continue

            entities.append(entity)

        if entities:
            async_add_entities(entities)
            _LOGGER.info(f"Added {len(entities)} appliance control entities for {device_type}")