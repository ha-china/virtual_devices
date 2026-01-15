"""Platform for virtual cover integration."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from homeassistant.components.cover import (
    ATTR_POSITION,
    CoverDeviceClass,
    CoverEntity,
    CoverEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .base_entity import BaseVirtualEntity
from .const import (
    CONF_ENTITIES,
    CONF_TRAVEL_TIME,
    DEVICE_TYPE_COVER,
    DOMAIN,
)
from .types import CoverEntityConfig, CoverState

_LOGGER = logging.getLogger(__name__)

# Device class mapping for cover types
COVER_TYPE_DEVICE_CLASS_MAP: dict[str, CoverDeviceClass] = {
    "blind": CoverDeviceClass.BLIND,
    "curtain": CoverDeviceClass.CURTAIN,
    "damper": CoverDeviceClass.DAMPER,
    "door": CoverDeviceClass.DOOR,
    "garage": CoverDeviceClass.GARAGE,
    "shade": CoverDeviceClass.SHADE,
    "shutter": CoverDeviceClass.SHUTTER,
    "window": CoverDeviceClass.WINDOW,
}

# Default travel time in seconds for full cover movement
DEFAULT_TRAVEL_TIME = 15


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up virtual cover entities."""
    device_type: str | None = config_entry.data.get("device_type")

    # Only create cover entities for cover device types
    if device_type != DEVICE_TYPE_COVER:
        _LOGGER.debug("Skipping cover setup for device type: %s", device_type)
        return

    _LOGGER.info("Setting up cover entities for device type: %s", device_type)

    device_info: DeviceInfo = hass.data[DOMAIN][config_entry.entry_id]["device_info"]
    entities: list[VirtualCover] = []
    entities_config: list[CoverEntityConfig] = config_entry.data.get(CONF_ENTITIES, [])

    for idx, entity_config in enumerate(entities_config):
        try:
            entity = VirtualCover(
                hass,
                config_entry.entry_id,
                entity_config,
                idx,
                device_info,
            )
            entities.append(entity)
        except Exception as e:
            _LOGGER.error("Failed to create VirtualCover %d: %s", idx, e)

    if entities:
        async_add_entities(entities)
        _LOGGER.info("Added %d cover entities", len(entities))


class VirtualCover(BaseVirtualEntity[CoverEntityConfig, CoverState], CoverEntity):
    """Representation of a virtual cover with travel time simulation."""

    _attr_supported_features: CoverEntityFeature = (
        CoverEntityFeature.OPEN
        | CoverEntityFeature.CLOSE
        | CoverEntityFeature.STOP
        | CoverEntityFeature.SET_POSITION
    )

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry_id: str,
        entity_config: CoverEntityConfig,
        index: int,
        device_info: DeviceInfo,
    ) -> None:
        """Initialize the virtual cover."""
        super().__init__(hass, config_entry_id, entity_config, index, device_info, "cover")

        # Set device class based on cover type
        cover_type: str = entity_config.get("cover_type", "curtain")
        self._attr_device_class = COVER_TYPE_DEVICE_CLASS_MAP.get(
            cover_type, CoverDeviceClass.CURTAIN
        )

        # Travel time configuration (seconds for full movement)
        self._travel_time: int = entity_config.get(CONF_TRAVEL_TIME, DEFAULT_TRAVEL_TIME)

        # Movement tracking state (not persisted)
        self._is_moving: bool = False
        self._target_position: int | None = None
        self._start_position: int | None = None
        self._start_time: float | None = None

        # Cover position state (persisted)
        self._position: int = 0
        self._is_closed: bool = True

        # Entity category (None = primary entity)
        self._attr_entity_category = None

    def get_default_state(self) -> CoverState:
        """Return the default state for this cover entity."""
        return {
            "position": 0,
            "is_closed": True,
            "is_moving": False,
            "target_position": None,
        }

    def apply_state(self, state: CoverState) -> None:
        """Apply loaded state to entity attributes."""
        self._position = state.get("position", 0)
        self._is_closed = state.get("is_closed", True)
        # Reset movement state on load to avoid stuck states after restart
        self._is_moving = False
        self._target_position = None
        self._start_position = None
        self._start_time = None
        _LOGGER.debug(
            "Applied state for cover '%s': position=%d, is_closed=%s",
            self._attr_name, self._position, self._is_closed,
        )

    def get_current_state(self) -> CoverState:
        """Get current state for persistence."""
        return {
            "position": self._position,
            "is_closed": self._is_closed,
            "is_moving": self._is_moving,
            "target_position": self._target_position,
        }

    @property
    def current_cover_position(self) -> int:
        """Return current position of cover (0-100)."""
        return self._position

    @property
    def is_closed(self) -> bool:
        """Return if the cover is closed."""
        return self._is_closed

    @property
    def is_opening(self) -> bool:
        """Return if the cover is opening."""
        return (
            self._is_moving
            and self._target_position is not None
            and self._target_position > self._position
        )

    @property
    def is_closing(self) -> bool:
        """Return if the cover is closing."""
        return (
            self._is_moving
            and self._target_position is not None
            and self._target_position < self._position
        )

    async def async_open_cover(self, **kwargs: Any) -> None:
        """Open the cover fully."""
        await self._move_to_position(100)
        self.fire_template_event("open_cover", **kwargs)

    async def async_close_cover(self, **kwargs: Any) -> None:
        """Close the cover fully."""
        await self._move_to_position(0)
        self.fire_template_event("close_cover", **kwargs)

    async def async_stop_cover(self, **kwargs: Any) -> None:
        """Stop the cover movement."""
        if self._is_moving:
            self._is_moving = False
            self._target_position = None
            self._start_position = None
            self._start_time = None
            await self.async_save_state()
            _LOGGER.debug(
                "Virtual cover '%s' stopped at position %d%%",
                self._attr_name,
                self._position,
            )
        self.fire_template_event("stop_cover", **kwargs)
        self.async_write_ha_state()

    async def async_set_cover_position(self, **kwargs: Any) -> None:
        """Move the cover to a specific position."""
        position: int | None = kwargs.get(ATTR_POSITION)
        if position is not None:
            await self._move_to_position(position)
            self.fire_template_event("set_cover_position", position=position, **kwargs)
            _LOGGER.debug(
                "Virtual cover '%s' moving to position %d%%",
                self._attr_name,
                position,
            )

    async def _move_to_position(self, target_position: int) -> None:
        """Move cover to target position with travel time simulation."""
        if target_position == self._position:
            return

        self._is_moving = True
        self._target_position = target_position
        self._start_position = self._position
        self._start_time = self._hass.loop.time()

        _LOGGER.debug(
            "Cover '%s' moving from %d%% to %d%% (travel time: %ds)",
            self._attr_name, self._position, target_position, self._travel_time,
        )

        await self._update_position_during_movement()

    async def _update_position_during_movement(self) -> None:
        """Update position during movement based on elapsed time."""
        if (
            not self._is_moving
            or self._target_position is None
            or self._start_position is None
            or self._start_time is None
        ):
            return

        current_time: float = self._hass.loop.time()
        elapsed_time: float = current_time - self._start_time

        # Calculate position based on elapsed time
        travel_time_per_percent: float = self._travel_time / 100.0

        if self._target_position > self._start_position:
            # Opening
            new_position = min(
                self._target_position,
                self._start_position + int(elapsed_time / travel_time_per_percent),
            )
        else:
            # Closing
            new_position = max(
                self._target_position,
                self._start_position - int(elapsed_time / travel_time_per_percent),
            )

        self._position = new_position
        self._is_closed = self._position == 0

        # Save state and update Home Assistant
        await self.async_save_state()
        self.async_write_ha_state()

        # Check if target reached
        if self._position == self._target_position:
            self._is_moving = False
            self._target_position = None
            self._start_position = None
            self._start_time = None

            action = (
                "opened"
                if self._position == 100
                else "closed"
                if self._position == 0
                else f"moved to {self._position}%"
            )
            _LOGGER.debug("Virtual cover '%s' %s", self._attr_name, action)
        else:
            # Continue movement, check again after 0.5 seconds
            await asyncio.sleep(0.5)
            await self._update_position_during_movement()
