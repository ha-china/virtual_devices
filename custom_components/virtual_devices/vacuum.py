"""Platform for virtual vacuum integration."""
from __future__ import annotations

import logging
import random
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.components.vacuum import (
    StateVacuumEntity,
    VacuumEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .base_entity import BaseVirtualEntity
from .const import (
    CONF_ENTITIES,
    CONF_VACUUM_FAN_SPEED,
    CONF_VACUUM_STATUS,
    DEVICE_TYPE_VACUUM,
    DOMAIN,
    VACUUM_FAN_SPEEDS,
    VACUUM_ROOMS,
    VACUUM_CLEANING_MODES,
)
from .types import VacuumEntityConfig, VacuumState

_LOGGER = logging.getLogger(__name__)

# Preset rooms for vacuum
PRESET_ROOMS: list[str] = list(VACUUM_ROOMS.values())

# Cleaning modes
CLEANING_MODES: list[str] = list(VACUUM_CLEANING_MODES.values())

# Valid vacuum states
VALID_STATES: list[str] = ["docked", "cleaning", "paused", "returning", "idle", "error"]


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up virtual vacuum entities."""
    device_type: str | None = config_entry.data.get("device_type")

    if device_type != DEVICE_TYPE_VACUUM:
        return

    device_info: DeviceInfo = hass.data[DOMAIN][config_entry.entry_id]["device_info"]
    entities: list[StateVacuumEntity | SensorEntity] = []
    entities_config: list[VacuumEntityConfig] = config_entry.data.get(CONF_ENTITIES, [])

    for idx, entity_config in enumerate(entities_config):
        vacuum = VirtualVacuum(
            hass,
            config_entry.entry_id,
            entity_config,
            idx,
            device_info,
        )
        entities.append(vacuum)

        # Create linked battery sensor
        battery_sensor = VirtualVacuumBatterySensor(
            hass,
            config_entry.entry_id,
            entity_config,
            idx,
            device_info,
            vacuum,
        )
        entities.append(battery_sensor)

    async_add_entities(entities)


class VirtualVacuum(BaseVirtualEntity[VacuumEntityConfig, VacuumState], StateVacuumEntity):
    """Representation of a virtual vacuum."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry_id: str,
        entity_config: VacuumEntityConfig,
        index: int,
        device_info: DeviceInfo,
    ) -> None:
        """Initialize the virtual vacuum."""
        super().__init__(hass, config_entry_id, entity_config, index, device_info, "vacuum")

        self._attr_icon = "mdi:robot-vacuum"

        # Supported features
        self._attr_supported_features = (
            VacuumEntityFeature.START
            | VacuumEntityFeature.STOP
            | VacuumEntityFeature.PAUSE
            | VacuumEntityFeature.RETURN_HOME
            | VacuumEntityFeature.CLEAN_SPOT
            | VacuumEntityFeature.LOCATE
            | VacuumEntityFeature.FAN_SPEED
            | VacuumEntityFeature.SEND_COMMAND
        )

        # Initialize state
        initial_status: str = entity_config.get(CONF_VACUUM_STATUS, "docked")
        if initial_status not in VALID_STATES:
            initial_status = "docked"
        self._attr_state: str = initial_status

        # Battery level (internal tracking, exposed via battery sensor)
        self._battery_level: int = 100

        # Fan speed
        fan_speeds: list[str] = list(VACUUM_FAN_SPEEDS.keys())
        initial_fan_speed: str = entity_config.get(CONF_VACUUM_FAN_SPEED, "medium")
        self._attr_fan_speed: str = initial_fan_speed if initial_fan_speed in fan_speeds else fan_speeds[0]
        self._attr_fan_speed_list: list[str] = fan_speeds

        # Cleaning related state
        self._cleaning_started_at: datetime | None = None
        self._cleaning_duration: float = 0
        self._cleaned_area: float = 0
        self._current_room: str | None = None
        self._map_available: bool = True

        # Error state
        self._error_message: str | None = None

        _LOGGER.info("Virtual vacuum '%s' initialized with state: %s", self._attr_name, self._attr_state)

    def get_default_state(self) -> VacuumState:
        """Return the default state for this vacuum entity."""
        return VacuumState(
            state="docked",
            fan_speed="medium",
            cleaned_area=0,
            cleaning_duration=0,
            current_room=None,
        )

    def apply_state(self, state: VacuumState) -> None:
        """Apply loaded state to entity attributes."""
        self._attr_state = state.get("state", "docked")
        self._attr_fan_speed = state.get("fan_speed", "medium")
        self._cleaned_area = state.get("cleaned_area", 0)
        self._cleaning_duration = state.get("cleaning_duration", 0)
        self._current_room = state.get("current_room")
        _LOGGER.info("Loaded state for vacuum '%s': state=%s", self._attr_name, self._attr_state)

    def get_current_state(self) -> VacuumState:
        """Get current state for persistence."""
        return VacuumState(
            state=self._attr_state,
            fan_speed=self._attr_fan_speed,
            cleaned_area=self._cleaned_area,
            cleaning_duration=self._cleaning_duration,
            current_room=self._current_room,
        )

    async def async_added_to_hass(self) -> None:
        """Run when entity is added to Home Assistant."""
        await super().async_added_to_hass()
        self.async_write_ha_state()
        _LOGGER.info("Virtual vacuum '%s' added to Home Assistant with state: %s", self._attr_name, self._attr_state)

    @property
    def state(self) -> str:
        """Return the state of the vacuum cleaner."""
        return self._attr_state

    @property
    def battery_level_internal(self) -> int:
        """Return the battery level for internal use by battery sensor."""
        return self._battery_level

    @property
    def fan_speed(self) -> str | None:
        """Return the fan speed of the vacuum cleaner."""
        return self._attr_fan_speed

    @property
    def fan_speed_list(self) -> list[str] | None:
        """Get the list of available fan speed steps of the vacuum cleaner."""
        return self._attr_fan_speed_list

    async def async_start(self) -> None:
        """Start or resume the cleaning task."""
        if self._attr_state in ["docked", "returning", "idle"]:
            self._attr_state = "cleaning"
            self._cleaning_started_at = datetime.now()
            self._cleaned_area = 0
            self._current_room = random.choice(PRESET_ROOMS) if random.random() > 0.3 else None
            await self.async_save_state()
            self.async_write_ha_state()
            _LOGGER.debug("Virtual vacuum '%s' started cleaning", self._attr_name)

            self.fire_template_event(
                "start",
                status=self._attr_state,
                current_room=self._current_room,
            )

    async def async_pause(self) -> None:
        """Pause the cleaning task."""
        if self._attr_state == "cleaning":
            self._attr_state = "paused"
            if self._cleaning_started_at:
                self._cleaning_duration += (datetime.now() - self._cleaning_started_at).total_seconds()
                self._cleaning_started_at = None
            await self.async_save_state()
            self.async_write_ha_state()
            _LOGGER.debug("Virtual vacuum '%s' paused cleaning", self._attr_name)

            self.fire_template_event("pause", status=self._attr_state)

    async def async_stop(self, **kwargs: Any) -> None:
        """Stop the cleaning task."""
        if self._attr_state in ["cleaning", "paused"]:
            self._attr_state = "idle"
            if self._cleaning_started_at:
                self._cleaning_duration += (datetime.now() - self._cleaning_started_at).total_seconds()
                self._cleaning_started_at = None
            await self.async_save_state()
            self.async_write_ha_state()
            _LOGGER.debug("Virtual vacuum '%s' stopped cleaning", self._attr_name)

            self.fire_template_event(
                "stop",
                status=self._attr_state,
                cleaned_area=self._cleaned_area,
                cleaning_duration=self._cleaning_duration,
            )

    async def async_return_to_base(self, **kwargs: Any) -> None:
        """Set the vacuum cleaner to return to the dock."""
        if self._attr_state in ["cleaning", "paused"]:
            self._attr_state = "returning"
            if self._cleaning_started_at:
                self._cleaning_duration += (datetime.now() - self._cleaning_started_at).total_seconds()
                self._cleaning_started_at = None
            await self.async_save_state()
            self.async_write_ha_state()
            _LOGGER.debug("Virtual vacuum '%s' returning to base", self._attr_name)

            self.fire_template_event("return_to_base", status=self._attr_state)

            # Simulate return to dock time
            self._hass.loop.call_later(30, self._dock_callback)

    async def async_clean_spot(self, **kwargs: Any) -> None:
        """Perform a spot clean-up."""
        self._attr_state = "cleaning"
        self._cleaning_started_at = datetime.now()
        self._current_room = "point_area"
        self._cleaned_area = random.uniform(2, 5)
        await self.async_save_state()
        self.async_write_ha_state()
        _LOGGER.debug("Virtual vacuum '%s' started spot cleaning", self._attr_name)

        self.fire_template_event(
            "clean_spot",
            status=self._attr_state,
            cleaned_area=self._cleaned_area,
        )

        # Spot cleaning is usually shorter
        self._hass.loop.call_later(60, self._spot_cleaning_complete_callback)

    async def async_locate(self, **kwargs: Any) -> None:
        """Locate the vacuum cleaner."""
        _LOGGER.info("Virtual vacuum '%s' location beep", self._attr_name)
        self.fire_template_event("locate")

    async def async_set_fan_speed(self, fan_speed: str, **kwargs: Any) -> None:
        """Set fan speed of the vacuum."""
        if fan_speed in self._attr_fan_speed_list:
            self._attr_fan_speed = fan_speed
            await self.async_save_state()
            self.async_write_ha_state()
            _LOGGER.debug("Virtual vacuum '%s' fan speed set to %s", self._attr_name, fan_speed)

            self.fire_template_event("set_fan_speed", fan_speed=fan_speed)

    async def async_send_command(
        self,
        command: str,
        params: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """Send a command to a vacuum cleaner."""
        _LOGGER.debug("Virtual vacuum '%s' received command: %s with params: %s", self._attr_name, command, params)

        if command == "clean_room" and params and "room" in params:
            self._attr_state = "cleaning"
            self._cleaning_started_at = datetime.now()
            self._current_room = params["room"]
            self._cleaned_area = random.uniform(5, 15)
            await self.async_save_state()
            self.async_write_ha_state()

            self.fire_template_event(
                "clean_room",
                command=command,
                params=params,
                current_room=self._current_room,
            )

        elif command == "set_map":
            self._map_available = True
            self.async_write_ha_state()

        elif command == "get_cleaning_history":
            history = {
                "total_cleanings": random.randint(1, 50),
                "total_time": random.randint(100, 1000),
                "total_area": random.randint(100, 1000),
            }

            self.fire_template_event(
                "send_command",
                command=command,
                params=params,
                result=history,
            )

    async def async_turn_on(self) -> None:
        """Turn on the vacuum cleaner."""
        if self._attr_state in ["docked", "idle"]:
            self._attr_state = "cleaning"
            self._cleaning_started_at = datetime.now()
            self._current_room = random.choice(PRESET_ROOMS) if random.random() > 0.3 else None
            await self.async_save_state()
            self.async_write_ha_state()
            _LOGGER.debug("Virtual vacuum '%s' turned on", self._attr_name)

            self.fire_template_event(
                "turn_on",
                status=self._attr_state,
                current_room=self._current_room,
            )

    async def async_turn_off(self) -> None:
        """Turn off the vacuum cleaner."""
        if self._attr_state != "docked":
            self._attr_state = "returning"
            if self._cleaning_started_at:
                self._cleaning_duration += (datetime.now() - self._cleaning_started_at).total_seconds()
                self._cleaning_started_at = None
            await self.async_save_state()
            self.async_write_ha_state()
            _LOGGER.debug("Virtual vacuum '%s' turning off", self._attr_name)

            self.fire_template_event("turn_off", status=self._attr_state)

            # Simulate return to dock time
            self._hass.loop.call_later(30, self._dock_callback)

    async def async_update(self) -> None:
        """Update vacuum state and battery."""
        # Update battery level
        if self._attr_state == "cleaning":
            self._battery_level = max(0, self._battery_level - random.uniform(0.1, 0.3))
        elif self._attr_state == "returning":
            self._battery_level = max(0, self._battery_level - random.uniform(0.2, 0.4))
        elif self._attr_state == "docked":
            self._battery_level = min(100, self._battery_level + random.uniform(0.5, 1.0))

        # Check low battery auto return
        if self._attr_state == "cleaning" and self._battery_level < 20:
            await self.async_return_to_base()

        # Update cleaning progress
        if self._attr_state == "cleaning" and self._cleaning_started_at:
            elapsed_time = (datetime.now() - self._cleaning_started_at).total_seconds()

            speed_multiplier = {
                "quiet": 0.8,
                "low": 1.0,
                "medium": 1.2,
                "high": 1.5,
                "turbo": 1.8,
            }.get(self._attr_fan_speed, 1.0)

            self._cleaned_area = min(100, elapsed_time * speed_multiplier * random.uniform(0.1, 0.2))

            # Simulate random error (small probability)
            if random.random() < 0.01:
                self._attr_state = "error"
                self._error_message = "virtual_sensor_error"
                self.async_write_ha_state()

        # Return to dock completion
        if self._attr_state == "returning" and self._battery_level < 30:
            if random.random() < 0.1:
                self._attr_state = "docked"
                self._current_room = None
                self.async_write_ha_state()

        self.async_write_ha_state()

    def _dock_callback(self) -> None:
        """Callback for when vacuum reaches dock."""
        if self._attr_state == "returning":
            self._attr_state = "docked"
            self._current_room = None
            self.async_write_ha_state()
            _LOGGER.debug("Virtual vacuum '%s' reached dock", self._attr_name)

            self.fire_template_event("docked", status=self._attr_state)

    def _spot_cleaning_complete_callback(self) -> None:
        """Callback for when spot cleaning is complete."""
        if self._attr_state == "cleaning" and self._current_room == "point_area":
            self._attr_state = "idle"
            self._cleaning_started_at = None
            self._current_room = None
            self.async_write_ha_state()
            _LOGGER.debug("Virtual vacuum '%s' completed spot cleaning", self._attr_name)

            self.fire_template_event("spot_cleaning_complete", status=self._attr_state)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        attrs: dict[str, Any] = {}

        if self._cleaned_area > 0:
            attrs["cleaned_area"] = round(self._cleaned_area, 1)

        if self._cleaning_duration > 0:
            attrs["cleaning_duration"] = round(self._cleaning_duration, 1)

        if self._current_room:
            attrs["current_room"] = self._current_room

        if self._error_message:
            attrs["error"] = self._error_message

        attrs["map_available"] = self._map_available
        attrs["available_cleaning_modes"] = CLEANING_MODES
        attrs["available_rooms"] = PRESET_ROOMS

        return attrs


class VirtualVacuumBatterySensor(SensorEntity):
    """Battery sensor for virtual vacuum."""

    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = "diagnostic"
    _attr_should_poll = True

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry_id: str,
        entity_config: VacuumEntityConfig,
        index: int,
        device_info: DeviceInfo,
        vacuum: VirtualVacuum,
    ) -> None:
        """Initialize the battery sensor."""
        self._hass = hass
        self._vacuum = vacuum
        entity_name = entity_config.get("entity_name", f"vacuum_{index + 1}")
        self._attr_name = f"{entity_name} Battery"
        self._attr_unique_id = f"{config_entry_id}_vacuum_{index}_battery"
        self._attr_device_info = device_info

    @property
    def native_value(self) -> int:
        """Return the battery level."""
        return self._vacuum.battery_level_internal

    async def async_update(self) -> None:
        """Update the sensor state."""
        # Battery level is updated by the vacuum entity, we just read it
        pass
