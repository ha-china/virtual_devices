"""Platform for virtual valve integration."""
from __future__ import annotations

import asyncio
import logging
import random
from typing import Any

from homeassistant.components.valve import (
    ValveEntity,
    ValveEntityFeature,
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
    CONF_TRAVEL_TIME,
    CONF_VALVE_POSITION,
    CONF_VALVE_REPORTS_POSITION,
    DEVICE_TYPE_VALVE,
    DOMAIN,
    VALVE_TYPES,
)
from .types import ValveEntityConfig, ValveState

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up virtual valve entities."""
    device_type: str | None = config_entry.data.get("device_type")

    if device_type != DEVICE_TYPE_VALVE:
        return

    device_info: DeviceInfo = hass.data[DOMAIN][config_entry.entry_id]["device_info"]
    entities: list[VirtualValve] = []
    entities_config: list[ValveEntityConfig] = config_entry.data.get(CONF_ENTITIES, [])

    for idx, entity_config in enumerate(entities_config):
        entity = VirtualValve(
            hass,
            config_entry.entry_id,
            entity_config,
            idx,
            device_info,
        )
        entities.append(entity)

    async_add_entities(entities)


class VirtualValve(ValveEntity):
    """Representation of a virtual valve.

    This entity implements state persistence using the same pattern as BaseVirtualEntity.
    """

    _attr_should_poll: bool = False
    _attr_entity_registry_enabled_default: bool = True

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry_id: str,
        entity_config: ValveEntityConfig,
        index: int,
        device_info: DeviceInfo,
    ) -> None:
        """Initialize the virtual valve."""
        self._hass = hass
        self._config_entry_id = config_entry_id
        self._entity_config = entity_config
        self._index = index

        entity_name: str = entity_config.get(CONF_ENTITY_NAME, f"valve_{index + 1}")
        self._attr_name = entity_name
        self._attr_unique_id = f"{config_entry_id}_valve_{index}"
        self._attr_device_info = device_info

        # Template support
        self._templates: dict[str, Any] = entity_config.get("templates", {})

        # Storage for state persistence
        self._store: Store[ValveState] = Store(
            hass, STORAGE_VERSION, f"virtual_devices_valve_{config_entry_id}_{index}"
        )

        # Travel time settings (seconds)
        self._travel_time: int = entity_config.get(CONF_TRAVEL_TIME, 10)
        self._is_moving: bool = False
        self._start_position: int | None = None
        self._start_time: float | None = None

        # Valve type
        valve_type: str = entity_config.get("valve_type", "water_valve")
        self._valve_type = valve_type

        # Set icon based on type
        icon_map: dict[str, str] = {
            "water_valve": "mdi:valve",
            "gas_valve": "mdi:valve-open",
            "irrigation": "mdi:sprinkler",
            "zone_valve": "mdi:valve-closed",
        }
        self._attr_icon = icon_map.get(valve_type, "mdi:valve")

        # Supported features
        self._attr_supported_features: ValveEntityFeature = (
            ValveEntityFeature.OPEN
            | ValveEntityFeature.CLOSE
            | ValveEntityFeature.SET_POSITION
            | ValveEntityFeature.STOP
        )

        # Reports position
        self._attr_reports_position: bool = entity_config.get(CONF_VALVE_REPORTS_POSITION, True)

        # Initial position
        self._attr_current_position: int = entity_config.get(CONF_VALVE_POSITION, 0)

        # Valve attributes
        self._is_opening: bool = False
        self._is_closing: bool = False
        self._target_position: int = self._attr_current_position

        # Flow related (simulation)
        self._flow_rate: float = 0
        self._total_flow: float = 0
        self._valve_size: int = entity_config.get("valve_size", 25)

        # Pressure related
        self._pressure: float = 0

        _LOGGER.info(f"Virtual valve '{self._attr_name}' initialized")

    def get_default_state(self) -> ValveState:
        """Return the default state for this entity type."""
        return {
            "is_open": False,
            "position": 0,
        }

    def apply_state(self, state: ValveState) -> None:
        """Apply loaded state to entity attributes."""
        self._attr_current_position = state.get("position", 0)
        self._target_position = self._attr_current_position
        self._is_moving = False
        self._is_opening = False
        self._is_closing = False
        self._start_position = None
        self._start_time = None

    def get_current_state(self) -> ValveState:
        """Get current state for persistence."""
        return {
            "is_open": self._attr_current_position > 0,
            "position": self._attr_current_position,
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
                _LOGGER.debug(f"Valve '{self._attr_name}' state loaded - position: {self._attr_current_position}%")
        except Exception as ex:
            _LOGGER.error(f"Failed to load state for valve '{self._attr_name}': {ex}")
            self.apply_state(self.get_default_state())

    async def async_save_state(self) -> None:
        """Save current state to storage."""
        try:
            data = self.get_current_state()
            await self._store.async_save(data)
            _LOGGER.debug(f"Valve '{self._attr_name}' state saved")
        except Exception as ex:
            _LOGGER.error(f"Failed to save state for valve '{self._attr_name}': {ex}")

    async def async_added_to_hass(self) -> None:
        """Call when entity is added to hass."""
        await super().async_added_to_hass()
        await self.async_load_state()
        self.async_write_ha_state()
        _LOGGER.info(f"Virtual valve '{self._attr_name}' added to Home Assistant")

    def fire_template_event(self, action: str, **kwargs: Any) -> None:
        """Fire a template update event if templates are configured."""
        if self._templates:
            self._hass.bus.async_fire(
                f"{DOMAIN}_valve_template_update",
                {
                    "entity_id": self.entity_id,
                    "device_id": self._config_entry_id,
                    "action": action,
                    **kwargs,
                },
            )

    @property
    def current_position(self) -> int:
        """Return current position of valve."""
        return self._attr_current_position

    @property
    def is_closed(self) -> bool:
        """Return true if valve is closed."""
        return self._attr_current_position == 0

    @property
    def is_opening(self) -> bool:
        """Return true if valve is opening."""
        return self._is_opening

    @property
    def is_closing(self) -> bool:
        """Return true if valve is closing."""
        return self._is_closing

    async def async_open_valve(self) -> None:
        """Open the valve."""
        if self._attr_current_position == 100:
            return

        self._is_opening = True
        self._is_closing = False

        try:
            await self._move_to_position(100)
        except Exception as ex:
            _LOGGER.error(f"Failed to open valve: {ex}")
            self._is_opening = False
            self._is_closing = False
            self._is_moving = False
            self.async_write_ha_state()

        _LOGGER.debug(f"Virtual valve '{self._attr_name}' opening")
        self.fire_template_event("open", target_position=100)

    async def async_close_valve(self) -> None:
        """Close the valve."""
        if self._attr_current_position == 0:
            return

        self._is_closing = True
        self._is_opening = False

        try:
            await self._move_to_position(0)
        except Exception as ex:
            _LOGGER.error(f"Failed to close valve: {ex}")
            self._is_opening = False
            self._is_closing = False
            self._is_moving = False
            self.async_write_ha_state()

        _LOGGER.debug(f"Virtual valve '{self._attr_name}' closing")
        self.fire_template_event("close", target_position=0)

    async def async_set_valve_position(self, position: int) -> None:
        """Set the valve to a specific position."""
        if not 0 <= position <= 100:
            _LOGGER.warning(f"Invalid valve position: {position}")
            return

        if position == self._attr_current_position:
            return

        if position > self._attr_current_position:
            self._is_opening = True
            self._is_closing = False
        else:
            self._is_closing = True
            self._is_opening = False

        try:
            await self._move_to_position(position)
        except Exception as ex:
            _LOGGER.error(f"Failed to move valve to position {position}: {ex}")
            self._is_opening = False
            self._is_closing = False
            self._is_moving = False
            self.async_write_ha_state()

        _LOGGER.debug(f"Virtual valve '{self._attr_name}' moving to position {position}%")
        self.fire_template_event("set_position", position=position)

    async def async_stop_valve(self) -> None:
        """Stop the valve."""
        self._is_opening = False
        self._is_closing = False
        self._is_moving = False
        self.async_write_ha_state()
        _LOGGER.debug(f"Virtual valve '{self._attr_name}' stopped")
        self.fire_template_event("stop")

    async def _move_to_position(self, target_position: int) -> None:
        """Move valve to target position with travel time simulation."""
        if target_position == self._attr_current_position:
            return

        self._is_moving = True
        self._target_position = target_position
        self._start_position = self._attr_current_position
        self._start_time = self._hass.loop.time()

        await self._update_position_during_movement()

    async def _update_position_during_movement(self) -> None:
        """Update position during movement based on elapsed time."""
        if not self._is_moving or self._target_position is None or self._start_time is None:
            return

        current_time = self._hass.loop.time()
        elapsed_time = current_time - self._start_time
        travel_time_per_percent = self._travel_time / 100.0

        if self._target_position > self._start_position:
            new_position = min(
                self._target_position,
                self._start_position + int(elapsed_time / travel_time_per_percent)
            )
        else:
            new_position = max(
                self._target_position,
                self._start_position - int(elapsed_time / travel_time_per_percent)
            )

        self._attr_current_position = new_position
        self._update_flow_and_pressure()

        await self.async_save_state()
        self.async_write_ha_state()

        if self._attr_current_position == self._target_position:
            self._is_moving = False
            self._is_opening = False
            self._is_closing = False
            await self.async_save_state()
            self.async_write_ha_state()
        else:
            await asyncio.sleep(0.5)
            await self._update_position_during_movement()

    def _update_flow_and_pressure(self) -> None:
        """Update flow rate and pressure based on position."""
        if self._attr_current_position > 0:
            self._flow_rate = round(self._attr_current_position * 0.1 * (self._valve_size / 25), 2)
            if self._valve_type == "water_valve":
                self._pressure = round(2 + (self._attr_current_position / 100) * 3, 1)
            elif self._valve_type == "gas_valve":
                self._pressure = round(0.5 + (self._attr_current_position / 100) * 2, 1)
        else:
            self._flow_rate = 0
            self._pressure = 0

    async def async_update(self) -> None:
        """Update valve state."""
        if self._is_moving and self._start_time is not None:
            await self._update_position_during_movement()
            return

        if self._flow_rate > 0:
            flow_increment = self._flow_rate / 60
            self._total_flow += flow_increment

        if self._pressure > 0:
            self._pressure += random.uniform(-0.1, 0.1)
            self._pressure = max(0, self._pressure)

        if not self._is_moving:
            self._update_flow_and_pressure()

        self.async_write_ha_state()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        attrs: dict[str, Any] = {
            "valve_type": VALVE_TYPES.get(self._valve_type, self._valve_type),
            "valve_size": f"{self._valve_size}mm",
            "target_position": self._target_position,
            "reports_position": self._attr_reports_position,
        }

        if self._flow_rate > 0:
            attrs["flow_rate"] = f"{self._flow_rate} L/min"

        if self._total_flow > 0:
            attrs["total_flow"] = f"{round(self._total_flow, 2)} L"

        if self._pressure > 0:
            attrs["pressure"] = f"{self._pressure} bar"

        return attrs
