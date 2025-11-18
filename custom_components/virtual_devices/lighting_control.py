"""Lighting control domain service for lights, switches, and covers."""
from __future__ import annotations

import logging
from typing import Any, List

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_EFFECT,
    ATTR_RGB_COLOR,
    ColorMode,
    LightEntity,
    LightEntityFeature,
)
from homeassistant.components.switch import SwitchEntity
from homeassistant.components.cover import (
    ATTR_POSITION,
    CoverEntity,
    CoverEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .base_service import BaseVirtualEntity, VirtualDeviceService
from .const import (
    CONF_BRIGHTNESS,
    CONF_COLOR_TEMP,
    CONF_EFFECT,
    CONF_ENTITIES,
    CONF_ENTITY_NAME,
    CONF_RGB,
    DEVICE_TYPE_LIGHT,
    DEVICE_TYPE_SWITCH,
    DEVICE_TYPE_COVER,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

EFFECT_LIST = ["rainbow", "blink", "breathe", "chase", "steady"]


class VirtualLight(BaseVirtualEntity, LightEntity):
    """Representation of a virtual light."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry_id: str,
        entity_config: dict[str, Any],
        index: int,
        device_info: dict[str, Any],
    ) -> None:
        """Initialize the virtual light."""
        super().__init__(hass, config_entry_id, entity_config, index, device_info, "light")

        # Light specific configuration
        has_brightness = entity_config.get(CONF_BRIGHTNESS, True)
        has_rgb = entity_config.get(CONF_RGB, False)
        has_color_temp = entity_config.get(CONF_COLOR_TEMP, False)
        has_effects = entity_config.get(CONF_EFFECT, False)

        # Set supported color modes and features
        supported_modes = []
        supported_features = LightEntityFeature(0)

        if has_rgb:
            supported_modes.append(ColorMode.RGB)
        if has_color_temp:
            supported_modes.append(ColorMode.COLOR_TEMP)
        if has_brightness:
            supported_modes.append(ColorMode.BRIGHTNESS)

        if not supported_modes:
            supported_modes.append(ColorMode.ONOFF)

        self._attr_color_mode = supported_modes[0] if supported_modes else ColorMode.ONOFF
        self._attr_supported_color_modes = supported_modes

        if has_effects:
            supported_features |= LightEntityFeature.EFFECT
            self._attr_effect_list = EFFECT_LIST

        self._attr_supported_features = supported_features

        # Light specific state
        self._attr_is_on = False
        self._attr_brightness = 255 if has_brightness else None
        self._attr_rgb_color = (255, 255, 255) if has_rgb else None
        self._attr_color_temp_kelvin = 3000 if has_color_temp else None
        self._attr_effect = None

        # Feature flags
        self._has_brightness = has_brightness
        self._has_rgb = has_rgb
        self._has_color_temp = has_color_temp
        self._has_effects = has_effects

    async def _apply_loaded_state(self) -> None:
        """Apply loaded state to light entity."""
        self._attr_is_on = self._state.get("is_on", False)

        if self._has_brightness:
            self._attr_brightness = self._state.get("brightness", 255)

        if self._has_rgb:
            self._attr_rgb_color = tuple(self._state.get("rgb_color", (255, 255, 255)))

        if self._has_color_temp:
            self._attr_color_temp_kelvin = self._state.get("color_temp_kelvin", 3000)

        if self._has_effects:
            self._attr_effect = self._state.get("effect")

    async def _initialize_default_state(self) -> None:
        """Initialize default light state."""
        self._state = {
            "is_on": False,
        }

        if self._has_brightness:
            self._state["brightness"] = 255

        if self._has_rgb:
            self._state["rgb_color"] = (255, 255, 255)

        if self._has_color_temp:
            self._state["color_temp_kelvin"] = 3000

        if self._has_effects:
            self._state["effect"] = None

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the light on."""
        self._attr_is_on = True

        if ATTR_BRIGHTNESS in kwargs and self._has_brightness:
            self._attr_brightness = kwargs[ATTR_BRIGHTNESS]
            self._state["brightness"] = kwargs[ATTR_BRIGHTNESS]

        if ATTR_RGB_COLOR in kwargs and self._has_rgb:
            self._attr_rgb_color = kwargs[ATTR_RGB_COLOR]
            self._state["rgb_color"] = list(kwargs[ATTR_RGB_COLOR])

        if ATTR_COLOR_TEMP_KELVIN in kwargs and self._has_color_temp:
            self._attr_color_temp_kelvin = kwargs[ATTR_COLOR_TEMP_KELVIN]
            self._state["color_temp_kelvin"] = kwargs[ATTR_COLOR_TEMP_KELVIN]

        if ATTR_EFFECT in kwargs and self._has_effects:
            self._attr_effect = kwargs[ATTR_EFFECT]
            self._state["effect"] = kwargs[ATTR_EFFECT]

        self._state["is_on"] = True
        await self.async_save_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the light off."""
        self._attr_is_on = False
        self._state["is_on"] = False
        await self.async_save_state()


class VirtualSwitch(BaseVirtualEntity, SwitchEntity):
    """Representation of a virtual switch."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry_id: str,
        entity_config: dict[str, Any],
        index: int,
        device_info: dict[str, Any],
    ) -> None:
        """Initialize the virtual switch."""
        super().__init__(hass, config_entry_id, entity_config, index, device_info, "switch")

        # Switch specific configuration
        switch_type = entity_config.get("switch_type", "generic")
        self._switch_type = switch_type

        # Set icon based on type
        icon_map = {
            "generic": "mdi:electric-switch",
            "power": "mdi:power",
            "outlet": "mdi:power-socket",
            "relay": "mdi:relay",
        }
        self._attr_icon = icon_map.get(switch_type, "mdi:electric-switch")

        # Switch specific state
        self._attr_is_on = False

    async def _apply_loaded_state(self) -> None:
        """Apply loaded state to switch entity."""
        self._attr_is_on = self._state.get("is_on", False)

    async def _initialize_default_state(self) -> None:
        """Initialize default switch state."""
        self._state = {
            "is_on": False,
        }

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        self._attr_is_on = True
        self._state["is_on"] = True
        await self.async_save_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        self._attr_is_on = False
        self._state["is_on"] = False
        await self.async_save_state()


class VirtualCover(BaseVirtualEntity, CoverEntity):
    """Representation of a virtual cover."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry_id: str,
        entity_config: dict[str, Any],
        index: int,
        device_info: dict[str, Any],
    ) -> None:
        """Initialize the virtual cover."""
        super().__init__(hass, config_entry_id, entity_config, index, device_info, "cover")

        # Cover specific configuration
        cover_type = entity_config.get("cover_type", "curtain")
        self._cover_type = cover_type

        # Set supported features based on type
        if cover_type == "curtain":
            self._attr_supported_features = CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE | CoverEntityFeature.SET_POSITION
            self._attr_icon = "mdi:curtain"
        elif cover_type == "blind":
            self._attr_supported_features = CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE | CoverEntityFeature.SET_POSITION | CoverEntityFeature.OPEN_TILT | CoverEntityFeature.CLOSE_TILT | CoverEntityFeature.SET_TILT_POSITION
            self._attr_icon = "mdi:blinds"
        elif cover_type == "garage":
            self._attr_supported_features = CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE
            self._attr_icon = "mdi:garage"
        else:
            self._attr_supported_features = CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE | CoverEntityFeature.SET_POSITION
            self._attr_icon = "mdi:window-shutter"

        # Cover specific state
        self._attr_is_closed = True
        self._attr_is_opening = False
        self._attr_is_closing = False
        self._attr_current_position = 0  # 0 = closed, 100 = fully open
        self._attr_current_tilt_position = 0  # 0 = horizontal, 100 = vertical

    async def _apply_loaded_state(self) -> None:
        """Apply loaded state to cover entity."""
        self._attr_is_closed = self._state.get("is_closed", True)
        self._attr_current_position = self._state.get("current_position", 0)
        if self._cover_type == "blind":
            self._attr_current_tilt_position = self._state.get("current_tilt_position", 0)

    async def _initialize_default_state(self) -> None:
        """Initialize default cover state."""
        self._state = {
            "is_closed": True,
            "current_position": 0,
        }
        if self._cover_type == "blind":
            self._state["current_tilt_position"] = 0

    async def async_open_cover(self, **kwargs: Any) -> None:
        """Open the cover."""
        self._attr_is_closed = False
        self._attr_current_position = 100
        self._state["is_closed"] = False
        self._state["current_position"] = 100
        await self.async_save_state()

    async def async_close_cover(self, **kwargs: Any) -> None:
        """Close the cover."""
        self._attr_is_closed = True
        self._attr_current_position = 0
        self._state["is_closed"] = True
        self._state["current_position"] = 0
        await self.async_save_state()

    async def async_set_cover_position(self, **kwargs: Any) -> None:
        """Move the cover to a specific position."""
        if ATTR_POSITION in kwargs:
            position = kwargs[ATTR_POSITION]
            self._attr_current_position = position
            self._attr_is_closed = position == 0
            self._state["current_position"] = position
            self._state["is_closed"] = position == 0
            await self.async_save_state()

    async def async_open_cover_tilt(self, **kwargs: Any) -> None:
        """Open the cover tilt."""
        if self._cover_type == "blind":
            self._attr_current_tilt_position = 100
            self._state["current_tilt_position"] = 100
            await self.async_save_state()

    async def async_close_cover_tilt(self, **kwargs: Any) -> None:
        """Close the cover tilt."""
        if self._cover_type == "blind":
            self._attr_current_tilt_position = 0
            self._state["current_tilt_position"] = 0
            await self.async_save_state()

    async def async_set_cover_tilt_position(self, **kwargs: Any) -> None:
        """Move the cover tilt to a specific position."""
        if self._cover_type == "blind" and ATTR_POSITION in kwargs:
            position = kwargs[ATTR_POSITION]
            self._attr_current_tilt_position = position
            self._state["current_tilt_position"] = position
            await self.async_save_state()


class LightingControlService(VirtualDeviceService):
    """Lighting control domain service."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the lighting control service."""
        super().__init__(hass, "lighting_control")
        self._supported_device_types = [
            DEVICE_TYPE_LIGHT,
            DEVICE_TYPE_SWITCH,
            DEVICE_TYPE_COVER,
        ]

    async def async_setup_entry(
        self,
        config_entry: ConfigEntry,
        async_add_entities,
    ) -> None:
        """Set up lighting control entities."""
        device_type = config_entry.data.get("device_type")

        if not self.is_device_type_supported(device_type):
            return

        device_info = self._get_device_info(config_entry)
        entities_config = self._get_entities_config(config_entry)
        entities = []

        for idx, entity_config in enumerate(entities_config):
            if device_type == DEVICE_TYPE_LIGHT:
                entity = VirtualLight(self._hass, config_entry.entry_id, entity_config, idx, device_info)
            elif device_type == DEVICE_TYPE_SWITCH:
                entity = VirtualSwitch(self._hass, config_entry.entry_id, entity_config, idx, device_info)
            elif device_type == DEVICE_TYPE_COVER:
                entity = VirtualCover(self._hass, config_entry.entry_id, entity_config, idx, device_info)
            else:
                continue

            entities.append(entity)

        if entities:
            async_add_entities(entities)
            _LOGGER.info(f"Added {len(entities)} lighting control entities for {device_type}")