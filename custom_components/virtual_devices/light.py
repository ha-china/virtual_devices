"""Light platform for virtual devices integration."""
from __future__ import annotations

import logging
import math
from typing import Any

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_EFFECT,
    ATTR_RGB_COLOR,
    ColorMode,
    LightEntity,
    LightEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .base_entity import BaseVirtualEntity
from .const import (
    CONF_BRIGHTNESS,
    CONF_COLOR_TEMP,
    CONF_EFFECT,
    CONF_ENTITIES,
    CONF_RGB,
    DEVICE_TYPE_LIGHT,
    DOMAIN,
)
from .types import LightEntityConfig, LightState, RGBColor

_LOGGER = logging.getLogger(__name__)

EFFECT_LIST: list[str] = ["rainbow", "blink", "breathe", "chase", "steady"]
DEFAULT_BRIGHTNESS: int = 255
DEFAULT_RGB_COLOR: RGBColor = (255, 255, 255)
DEFAULT_COLOR_TEMP_KELVIN: int = 3000


def _color_temp_kelvin_to_rgb(color_temp_kelvin: int) -> RGBColor:
    """Convert color temperature in Kelvin to RGB color."""
    temp = max(1000, min(40000, color_temp_kelvin)) / 100

    if temp <= 66:
        red = 255
    else:
        red = max(0, min(255, int(329.698727446 * ((temp - 60) ** -0.1332047592))))

    if temp <= 66:
        green = max(0, min(255, int(99.4708025861 * math.log(temp) - 161.1195681661)))
    else:
        green = max(0, min(255, int(288.1221695283 * ((temp - 60) ** -0.0755148492))))

    if temp >= 66:
        blue = 255
    elif temp <= 19:
        blue = 0
    else:
        blue = max(0, min(255, int(138.5177312231 * math.log(temp - 10) - 305.0447927307)))

    return (red, green, blue)


def _rgb_to_color_temp_kelvin(rgb: RGBColor) -> int:
    """Convert RGB color to approximate color temperature in Kelvin."""
    r, g, b = rgb
    r_n, g_n, b_n = r / 255.0, g / 255.0, b / 255.0

    if abs(r_n - g_n) < 0.1 and abs(g_n - b_n) < 0.1:
        brightness = (r_n + g_n + b_n) / 3
        if brightness > 0.8:
            return 6500
        elif brightness > 0.5:
            return 4000
        else:
            return 2700

    if r_n > g_n and g_n > b_n:
        return int(2000 + (g_n / r_n) * 2000)
    elif b_n > r_n and b_n > g_n:
        return int(5000 + (b_n - g_n) * 5000)
    elif g_n > r_n and g_n > b_n:
        return int(4000 + (g_n - r_n) * 1000)
    else:
        warmth = r_n / (r_n + b_n) if (r_n + b_n) > 0 else 0.5
        return int(2700 + warmth * 3800)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up virtual light entities."""
    device_type: str | None = config_entry.data.get("device_type")

    if device_type != DEVICE_TYPE_LIGHT:
        _LOGGER.debug("Skipping light setup for device type: %s", device_type)
        return

    _LOGGER.info("Setting up light entities for device type: %s", device_type)

    device_info: DeviceInfo = hass.data[DOMAIN][config_entry.entry_id]["device_info"]
    entities: list[VirtualLight] = []
    entities_config: list[LightEntityConfig] = config_entry.data.get(CONF_ENTITIES, [])

    for idx, entity_config in enumerate(entities_config):
        try:
            entity = VirtualLight(hass, config_entry.entry_id, entity_config, idx, device_info)
            entities.append(entity)
        except Exception as e:
            _LOGGER.error("Failed to create VirtualLight %d: %s", idx, e)

    if entities:
        async_add_entities(entities)
        _LOGGER.info("Added %d light entities", len(entities))


class VirtualLight(BaseVirtualEntity[LightEntityConfig, LightState], LightEntity):
    """Representation of a virtual light."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry_id: str,
        entity_config: LightEntityConfig,
        index: int,
        device_info: DeviceInfo,
    ) -> None:
        """Initialize the virtual light."""
        # Set feature flags BEFORE super().__init__() because get_default_state() needs them
        self._has_brightness: bool = entity_config.get(CONF_BRIGHTNESS, True)
        self._has_rgb: bool = entity_config.get(CONF_RGB, False)
        self._has_color_temp: bool = entity_config.get(CONF_COLOR_TEMP, False)
        self._has_effects: bool = entity_config.get(CONF_EFFECT, False)

        super().__init__(hass, config_entry_id, entity_config, index, device_info, "light")

        self._attr_entity_category = None

        # Set up supported color modes
        # Note: ColorMode.BRIGHTNESS cannot be combined with RGB or COLOR_TEMP
        # RGB and COLOR_TEMP already include brightness control
        supported_modes: set[ColorMode] = set()
        supported_features = LightEntityFeature(0)

        if self._has_effects:
            supported_features |= LightEntityFeature.EFFECT
            self._attr_effect_list = EFFECT_LIST

        # Determine color modes - RGB and COLOR_TEMP take precedence over BRIGHTNESS
        if self._has_rgb and self._has_color_temp:
            # Both RGB and color temp supported
            supported_modes = {ColorMode.RGB, ColorMode.COLOR_TEMP}
        elif self._has_rgb:
            # RGB only (includes brightness)
            supported_modes = {ColorMode.RGB}
        elif self._has_color_temp:
            # Color temp only (includes brightness)
            supported_modes = {ColorMode.COLOR_TEMP}
        elif self._has_brightness:
            # Brightness only
            supported_modes = {ColorMode.BRIGHTNESS}
        else:
            # On/off only
            supported_modes = {ColorMode.ONOFF}

        self._attr_color_mode: ColorMode = next(iter(supported_modes)) if supported_modes else ColorMode.ONOFF
        self._attr_supported_color_modes: set[ColorMode] = supported_modes
        self._attr_supported_features: LightEntityFeature = supported_features

        if self._has_color_temp:
            self._attr_min_color_temp_kelvin: int = 2000
            self._attr_max_color_temp_kelvin: int = 6500

        # Initialize state attributes
        self._attr_is_on: bool = False
        self._attr_brightness: int | None = DEFAULT_BRIGHTNESS if self._has_brightness else None
        self._attr_rgb_color: RGBColor | None = DEFAULT_RGB_COLOR if self._has_rgb else None
        self._attr_color_temp_kelvin: int | None = DEFAULT_COLOR_TEMP_KELVIN if self._has_color_temp else None
        self._attr_effect: str | None = None

    def get_default_state(self) -> LightState:
        """Return the default state for this light entity."""
        state: LightState = {"is_on": False}
        if self._has_brightness:
            state["brightness"] = DEFAULT_BRIGHTNESS
        if self._has_rgb:
            state["rgb_color"] = DEFAULT_RGB_COLOR
        if self._has_color_temp:
            state["color_temp_kelvin"] = DEFAULT_COLOR_TEMP_KELVIN
        if self._has_effects:
            state["effect"] = None
        return state

    def apply_state(self, state: LightState) -> None:
        """Apply loaded state to entity attributes."""
        self._attr_is_on = state.get("is_on", False)
        if self._has_brightness:
            self._attr_brightness = state.get("brightness", DEFAULT_BRIGHTNESS)
        if self._has_rgb:
            rgb_value = state.get("rgb_color", DEFAULT_RGB_COLOR)
            self._attr_rgb_color = tuple(rgb_value) if rgb_value else DEFAULT_RGB_COLOR
        if self._has_color_temp:
            self._attr_color_temp_kelvin = state.get("color_temp_kelvin", DEFAULT_COLOR_TEMP_KELVIN)
        if self._has_effects:
            self._attr_effect = state.get("effect")
        _LOGGER.info("Loaded state for light '%s': is_on=%s", self._attr_name, self._attr_is_on)

    def get_current_state(self) -> LightState:
        """Get current state for persistence."""
        state: LightState = {"is_on": self._attr_is_on}
        if self._has_brightness:
            state["brightness"] = self._attr_brightness
        if self._has_rgb:
            state["rgb_color"] = self._attr_rgb_color
        if self._has_color_temp:
            state["color_temp_kelvin"] = self._attr_color_temp_kelvin
        if self._has_effects:
            state["effect"] = self._attr_effect
        return state

    async def async_added_to_hass(self) -> None:
        """Run when entity is added to Home Assistant."""
        await super().async_added_to_hass()
        self.async_write_ha_state()

    def _color_temp_kelvin_to_rgb(self, color_temp_kelvin: int) -> RGBColor:
        """Convert color temperature in Kelvin to RGB color."""
        return _color_temp_kelvin_to_rgb(color_temp_kelvin)

    def _rgb_to_color_temp_kelvin(self, rgb: RGBColor) -> int:
        """Convert RGB color to approximate color temperature in Kelvin."""
        return _rgb_to_color_temp_kelvin(rgb)

    @property
    def is_on(self) -> bool:
        """Return true if light is on."""
        return self._attr_is_on

    @property
    def brightness(self) -> int | None:
        """Return the brightness of the light."""
        if self._attr_color_mode == ColorMode.RGB and self._attr_rgb_color:
            r, g, b = self._attr_rgb_color
            brightness = int(0.2126 * r + 0.7152 * g + 0.0722 * b)
            return max(1, min(255, brightness))
        elif ColorMode.COLOR_TEMP in self._attr_supported_color_modes:
            return self._attr_brightness
        elif ColorMode.BRIGHTNESS in self._attr_supported_color_modes:
            return self._attr_brightness
        return None

    @property
    def rgb_color(self) -> RGBColor | None:
        """Return the RGB color value."""
        if self._attr_color_mode == ColorMode.RGB:
            return self._attr_rgb_color
        elif self._attr_color_mode == ColorMode.COLOR_TEMP and self._has_color_temp:
            return self._color_temp_kelvin_to_rgb(self._attr_color_temp_kelvin or DEFAULT_COLOR_TEMP_KELVIN)
        return None

    @property
    def color_temp_kelvin(self) -> int | None:
        """Return the color temperature in Kelvin."""
        if self._attr_color_mode == ColorMode.COLOR_TEMP:
            return self._attr_color_temp_kelvin
        elif self._attr_color_mode == ColorMode.RGB and self._attr_rgb_color:
            return self._rgb_to_color_temp_kelvin(self._attr_rgb_color)
        return None

    @property
    def effect(self) -> str | None:
        """Return the current effect."""
        if self._attr_supported_features & LightEntityFeature.EFFECT:
            return self._attr_effect
        return None

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the light on."""
        self._attr_is_on = True

        if ATTR_RGB_COLOR in kwargs:
            rgb: RGBColor | None = kwargs[ATTR_RGB_COLOR]
            if self._has_rgb and rgb:
                self._attr_rgb_color = rgb
                if ColorMode.RGB in self._attr_supported_color_modes:
                    self._attr_color_mode = ColorMode.RGB
                r, g, b = rgb
                self._attr_brightness = max(1, min(255, int(0.2126 * r + 0.7152 * g + 0.0722 * b)))

        if ATTR_COLOR_TEMP_KELVIN in kwargs and self._has_color_temp:
            color_temp: int = kwargs[ATTR_COLOR_TEMP_KELVIN]
            self._attr_color_temp_kelvin = color_temp
            if ColorMode.COLOR_TEMP in self._attr_supported_color_modes:
                self._attr_color_mode = ColorMode.COLOR_TEMP
                self._attr_rgb_color = self._color_temp_kelvin_to_rgb(color_temp)

        if ATTR_BRIGHTNESS in kwargs:
            brightness: int = kwargs[ATTR_BRIGHTNESS]
            if self._attr_color_mode == ColorMode.RGB and self._attr_rgb_color:
                r, g, b = self._attr_rgb_color
                current_brightness = int(0.2126 * r + 0.7152 * g + 0.0722 * b)
                if current_brightness > 0:
                    scale = brightness / current_brightness
                    self._attr_rgb_color = (
                        max(0, min(255, int(r * scale))),
                        max(0, min(255, int(g * scale))),
                        max(0, min(255, int(b * scale))),
                    )
                else:
                    self._attr_rgb_color = (brightness, brightness, brightness)
            else:
                self._attr_brightness = brightness

        if ATTR_EFFECT in kwargs and self._has_effects:
            self._attr_effect = kwargs[ATTR_EFFECT]

        self.fire_template_event("turn_on", **kwargs)
        await self.async_save_state()
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the light off."""
        self._attr_is_on = False
        self.fire_template_event("turn_off")
        await self.async_save_state()
        self.async_write_ha_state()
