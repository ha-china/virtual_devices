"""Light platform for virtual devices integration."""
from __future__ import annotations

import logging
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
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.storage import Store

from .const import (
    CONF_BRIGHTNESS,
    CONF_COLOR_TEMP,
    CONF_EFFECT,
    CONF_ENTITIES,
    CONF_ENTITY_NAME,
    CONF_RGB,
    DEVICE_TYPE_LIGHT,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

EFFECT_LIST = ["rainbow", "blink", "breathe", "chase", "steady"]


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up virtual light entities."""
    device_type = config_entry.data.get("device_type")

    # Only create light entities for light device types
    if device_type != DEVICE_TYPE_LIGHT:
        _LOGGER.debug(f"Skipping light setup for device type: {device_type}")
        return

    _LOGGER.info(f"Setting up light entities for device type: {device_type}")

    device_info = hass.data[DOMAIN][config_entry.entry_id]["device_info"]
    entities = []
    entities_config = config_entry.data.get(CONF_ENTITIES, [])

    for idx, entity_config in enumerate(entities_config):
        try:
            entity = VirtualLight(
                hass,
                config_entry.entry_id,
                entity_config,
                idx,
                device_info,
            )
            entities.append(entity)
        except Exception as e:
            _LOGGER.error(f"Failed to create VirtualLight {idx}: {e}")

    if entities:
        async_add_entities(entities)
        _LOGGER.info(f"Added {len(entities)} light entities")


class VirtualLight(LightEntity):
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
        self._config_entry_id = config_entry_id
        self._entity_config = entity_config
        self._index = index
        self._device_info = device_info
        self._hass = hass

        entity_name = entity_config.get(CONF_ENTITY_NAME, f"light_{index + 1}")
        self._attr_name = entity_name
        self._attr_unique_id = f"{config_entry_id}_light_{index}"
        self._attr_device_info = device_info

        # Template support
        self._templates = entity_config.get("templates", {})
        self._attr_entity_category = None  # 灯光是主要控制实体，无类别

        # 存储实体状态
        self._store = Store[dict[str, Any]](hass, 1, f"virtual_devices_light_{config_entry_id}_{index}")

        # 灯光配置
        has_brightness = entity_config.get(CONF_BRIGHTNESS, True)
        has_rgb = entity_config.get(CONF_RGB, False)
        has_color_temp = entity_config.get(CONF_COLOR_TEMP, False)
        has_effects = entity_config.get(CONF_EFFECT, False)

        # 设置支持的颜色模式和功能
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

        # 灯光状态 - 默认值，稍后从存储恢复
        self._attr_is_on = False
        self._attr_brightness = 255 if has_brightness else None
        self._attr_rgb_color = (255, 255, 255) if has_rgb else None
        self._attr_color_temp_kelvin = 3000 if has_color_temp else None
        self._attr_effect = None

        # 功能标志
        self._has_brightness = has_brightness
        self._has_rgb = has_rgb
        self._has_color_temp = has_color_temp
        self._has_effects = has_effects

        # 加载保存的状态
        self._load_state()

    def _load_state(self) -> None:
        """Load saved state from storage."""
        try:
            # 这里简化实现，实际应该异步加载
            self._attr_is_on = False
            if self._has_brightness:
                self._attr_brightness = 255
            if self._has_rgb:
                self._attr_rgb_color = (255, 255, 255)
            if self._has_color_temp:
                self._attr_color_temp_kelvin = 3000
        except Exception as ex:
            _LOGGER.error(f"Failed to load state for light: {ex}")

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the light on."""
        self._attr_is_on = True

        if ATTR_BRIGHTNESS in kwargs and self._has_brightness:
            self._attr_brightness = kwargs[ATTR_BRIGHTNESS]

        if ATTR_RGB_COLOR in kwargs and self._has_rgb:
            self._attr_rgb_color = kwargs[ATTR_RGB_COLOR]

        if ATTR_COLOR_TEMP_KELVIN in kwargs and self._has_color_temp:
            self._attr_color_temp_kelvin = kwargs[ATTR_COLOR_TEMP_KELVIN]

        if ATTR_EFFECT in kwargs and self._has_effects:
            self._attr_effect = kwargs[ATTR_EFFECT]

        await self._save_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the light off."""
        self._attr_is_on = False
        await self._save_state()

    async def _save_state(self) -> None:
        """Save state to storage."""
        try:
            state = {
                "is_on": self._attr_is_on,
            }
            if self._has_brightness:
                state["brightness"] = self._attr_brightness
            if self._has_rgb:
                state["rgb_color"] = self._attr_rgb_color
            if self._has_color_temp:
                state["color_temp_kelvin"] = self._attr_color_temp_kelvin
            if self._has_effects:
                state["effect"] = self._attr_effect

            await self._store.async_save(state)
        except Exception as ex:
            _LOGGER.error(f"Failed to save state for light: {ex}")