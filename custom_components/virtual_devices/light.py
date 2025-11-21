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

        # 设置支持的颜色模式和功能 - HA 2025.3+ 兼容性：只选择一个主要模式
        supported_modes = set()
        supported_features = LightEntityFeature(0)

        if has_rgb:
            supported_modes.add(ColorMode.RGB)
        if has_color_temp:
            supported_modes.add(ColorMode.COLOR_TEMP)
        if has_brightness:
            supported_modes.add(ColorMode.BRIGHTNESS)

        if not supported_modes:
            supported_modes.add(ColorMode.ONOFF)

        # HA 2025.3+ 颜色模式兼容性：只能选择一个主要模式
        if len(supported_modes) > 1:
            if ColorMode.RGB in supported_modes:
                # 如果选择了RGB，只保留RGB模式（RGB包含亮度控制）
                supported_modes = {ColorMode.RGB}
                _LOGGER.info(f"Light '{self._attr_name}': Multiple modes detected, using RGB mode (includes brightness control)")
            elif ColorMode.COLOR_TEMP in supported_modes:
                # 如果选择了色温，只保留色温模式（色温包含亮度控制）
                supported_modes = {ColorMode.COLOR_TEMP}
                _LOGGER.info(f"Light '{self._attr_name}': Multiple modes detected, using COLOR_TEMP mode (includes brightness control)")
            else:
                # 否则只保留亮度模式
                supported_modes = {ColorMode.BRIGHTNESS}
                _LOGGER.info(f"Light '{self._attr_name}': Multiple modes detected, using BRIGHTNESS mode")

        self._attr_color_mode = next(iter(supported_modes)) if supported_modes else ColorMode.ONOFF
        self._attr_supported_color_modes = supported_modes

        if has_effects:
            supported_features |= LightEntityFeature.EFFECT
            self._attr_effect_list = EFFECT_LIST

        # HA 2026.1+ 色温范围要求：使用Kelvin而不是mireds
        if has_color_temp:
            self._attr_min_color_temp_kelvin = 2000  # 暖色最低温度
            self._attr_max_color_temp_kelvin = 6500  # 冷色最高温度

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

    @property
    def is_on(self) -> bool:
        """Return true if light is on."""
        return self._attr_is_on

    @property
    def brightness(self) -> int | None:
        """Return the brightness of the light."""
        if ColorMode.RGB in self._attr_supported_color_modes:
            # RGB模式下，从RGB颜色计算亮度
            return max(self._attr_rgb_color) if self._attr_rgb_color else 255
        elif ColorMode.COLOR_TEMP in self._attr_supported_color_modes:
            # 色温模式下，返回内部亮度值
            return self._attr_brightness
        elif ColorMode.BRIGHTNESS in self._attr_supported_color_modes:
            return self._attr_brightness
        return None

    @property
    def rgb_color(self) -> tuple[int, int, int] | None:
        """Return the rgb color value."""
        if ColorMode.RGB in self._attr_supported_color_modes:
            return self._attr_rgb_color
        return None

    @property
    def color_temp_kelvin(self) -> int | None:
        """Return the color temperature in kelvin."""
        if ColorMode.COLOR_TEMP in self._attr_supported_color_modes:
            return self._attr_color_temp_kelvin
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

        # 修复：处理亮度调整
        if ATTR_BRIGHTNESS in kwargs:
            brightness = kwargs[ATTR_BRIGHTNESS]

            if ColorMode.RGB in self._attr_supported_color_modes:
                # RGB模式下：保持当前颜色比例，调整RGB值来达到目标亮度
                if self._attr_rgb_color:
                    current_brightness = max(self._attr_rgb_color)
                    if current_brightness > 0:
                        # 计算缩放因子
                        scale_factor = brightness / current_brightness
                        # 应用缩放到RGB值
                        self._attr_rgb_color = tuple(
                            max(0, min(255, int(val * scale_factor)))
                            for val in self._attr_rgb_color
                        )
                    else:
                        # 当前亮度为0，使用白色达到目标亮度
                        self._attr_rgb_color = (brightness, brightness, brightness)
                else:
                    self._attr_rgb_color = (brightness, brightness, brightness)
            else:
                # 非RGB模式下直接设置亮度
                self._attr_brightness = brightness

        # 修复：处理RGB颜色
        if ATTR_RGB_COLOR in kwargs:
            rgb = kwargs[ATTR_RGB_COLOR]
            if ColorMode.RGB in self._attr_supported_color_modes:
                # RGB模式下同步更新亮度
                self._attr_rgb_color = rgb
                self._attr_brightness = max(rgb) if rgb else 255

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