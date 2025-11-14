"""Platform for virtual light integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,  # HA 2025.10.0+ 使用这个替代 ATTR_COLOR_TEMP
    ATTR_EFFECT,
    ATTR_RGB_COLOR,
    ColorMode,
    LightEntity,
    LightEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_BRIGHTNESS,
    CONF_COLOR_TEMP,
    CONF_EFFECT,
    CONF_ENTITIES,
    CONF_ENTITY_NAME,
    CONF_RGB,
    DEVICE_TYPE_LIGHT,
    DOMAIN,
    TEMPLATE_ENABLED_DEVICE_TYPES,
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

    # 只有灯光类型的设备才设置灯光实体
    if device_type != DEVICE_TYPE_LIGHT:
        return

    device_info = hass.data[DOMAIN][config_entry.entry_id]["device_info"]
    entities = []
    entities_config = config_entry.data.get(CONF_ENTITIES, [])

    for idx, entity_config in enumerate(entities_config):
        entity = VirtualLight(
            config_entry.entry_id,
            entity_config,
            idx,
            device_info,
        )
        entities.append(entity)

    async_add_entities(entities)


class VirtualLight(LightEntity):
    """Representation of a virtual light."""

    def __init__(
        self,
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

        entity_name = entity_config.get(CONF_ENTITY_NAME, f"light_{index + 1}")
        self._attr_name = entity_name
        self._attr_unique_id = f"{config_entry_id}_light_{index}"
        self._attr_device_info = device_info

        # Template support
        self._templates = entity_config.get("templates", {})
        self._attr_entity_category = None  # 灯光是主要控制实体，无类别

        # 灯光状态
        self._is_on = False
        self._brightness = 255
        self._color_temp_kelvin = 2700  # 使用 kelvin 而不是 mireds
        self._color_temp = 2700  # 色温值，用于 color_temp 属性
        self._rgb_color = (255, 255, 255)
        self._effect = None

        # 根据配置设置支持的功能
        self._setup_features()

    def _setup_features(self) -> None:
        """Setup light features based on configuration."""
        supported_features = LightEntityFeature(0)
        color_modes = set()

        # 基础亮度 - 严格按照用户配置
        if self._entity_config.get(CONF_BRIGHTNESS, False):
            color_modes.add(ColorMode.BRIGHTNESS)

        # 色温
        if self._entity_config.get(CONF_COLOR_TEMP, False):
            color_modes.add(ColorMode.COLOR_TEMP)
            # 使用 kelvin 而不是 mireds (HA 2025.3+)
            self._attr_min_color_temp_kelvin = 2000
            self._attr_max_color_temp_kelvin = 6500

        # RGB颜色
        if self._entity_config.get(CONF_RGB, False):
            color_modes.add(ColorMode.RGB)

        # 灯效
        if self._entity_config.get(CONF_EFFECT, False):
            supported_features |= LightEntityFeature.EFFECT
            self._attr_effect_list = EFFECT_LIST

        # 只有在用户完全没有选择任何功能时，才默认启用亮度
        if not color_modes:
            color_modes.add(ColorMode.BRIGHTNESS)

        # HA 2025.3+ 颜色模式兼容性：只能选择一个主要模式
        if len(color_modes) > 1:
            if ColorMode.RGB in color_modes:
                # 如果选择了RGB，只保留RGB模式
                color_modes = {ColorMode.RGB}
            elif ColorMode.COLOR_TEMP in color_modes:
                # 如果选择了色温，只保留色温模式
                color_modes = {ColorMode.COLOR_TEMP}
            else:
                # 否则只保留亮度模式
                color_modes = {ColorMode.BRIGHTNESS}

        self._attr_supported_color_modes = color_modes
        self._attr_supported_features = supported_features

        # 调试信息
        _LOGGER.debug(f"Light '{self._attr_name}' config: brightness={self._entity_config.get(CONF_BRIGHTNESS)}, "
                     f"color_temp={self._entity_config.get(CONF_COLOR_TEMP)}, rgb={self._entity_config.get(CONF_RGB)}")
        _LOGGER.debug(f"Light '{self._attr_name}' final supported modes: {self._attr_supported_color_modes}")

        # 确保颜色模式正确设置
        if not self._attr_supported_color_modes:
            _LOGGER.warning(f"Light '{self._attr_name}': No color modes configured, defaulting to BRIGHTNESS")
            self._attr_supported_color_modes = {ColorMode.BRIGHTNESS}

    @property
    def is_on(self) -> bool:
        """Return true if light is on."""
        return self._is_on

    @property
    def brightness(self) -> int | None:
        """Return the brightness of the light."""
        if ColorMode.BRIGHTNESS in self._attr_supported_color_modes:
            return self._brightness
        return None

    @property
    def color_temp(self) -> int | None:
        """Return the color temperature in mireds."""
        if ColorMode.COLOR_TEMP in self._attr_supported_color_modes:
            # 将 kelvin 转换为 mireds
            return round(1000000 / self._color_temp_kelvin)
        return None

    @property
    def color_temp_kelvin(self) -> int | None:
        """Return the color temperature in kelvin."""
        if ColorMode.COLOR_TEMP in self._attr_supported_color_modes:
            return self._color_temp_kelvin
        return None

    @property
    def color_mode(self) -> ColorMode:
        """Return the current color mode."""
        # 返回支持的颜色模式中的第一个
        if self._attr_supported_color_modes:
            return next(iter(self._attr_supported_color_modes))
        return ColorMode.BRIGHTNESS  # 默认返回亮度模式

    @property
    def rgb_color(self) -> tuple[int, int, int] | None:
        """Return the rgb color value."""
        if ColorMode.RGB in self._attr_supported_color_modes:
            _LOGGER.debug(f"Returning RGB color: {self._rgb_color} for light '{self._attr_name}'")
            return self._rgb_color
        return None

    @property
    def hs_color(self) -> tuple[float, float] | None:
        """Return the hs color value."""
        if ColorMode.RGB in self._attr_supported_color_modes and self._rgb_color:
            # 简单的RGB到HS转换
            r, g, b = self._rgb_color
            max_val = max(r, g, b)
            min_val = min(r, g, b)
            delta = max_val - min_val

            if delta == 0:
                hue = 0
            elif max_val == r:
                hue = (g - b) / delta % 6
            elif max_val == g:
                hue = (b - r) / delta + 2
            else:
                hue = (r - g) / delta + 4

            hue = round(hue * 60)
            if hue < 0:
                hue += 360

            saturation = 0 if max_val == 0 else round(delta / max_val * 100)
            return (hue, saturation)
        return None

    @property
    def effect(self) -> str | None:
        """Return the current effect."""
        if self._attr_supported_features & LightEntityFeature.EFFECT:
            return self._effect
        return None

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the light on."""
        self._is_on = True

        if ATTR_BRIGHTNESS in kwargs:
            self._brightness = kwargs[ATTR_BRIGHTNESS]

        if ATTR_COLOR_TEMP_KELVIN in kwargs:
            self._color_temp_kelvin = kwargs[ATTR_COLOR_TEMP_KELVIN]

        if ATTR_RGB_COLOR in kwargs:
            self._rgb_color = kwargs[ATTR_RGB_COLOR]

        if ATTR_EFFECT in kwargs:
            self._effect = kwargs[ATTR_EFFECT]

        self.async_write_ha_state()
        _LOGGER.debug(f"Virtual light '{self._attr_name}' turned on")

        # 触发模板更新事件（如果有模板配置）
        if self._templates:
            self.hass.bus.async_fire(
                f"{DOMAIN}_template_update",
                {
                    "entity_id": self.entity_id,
                    "device_id": self._config_entry_id,
                    "state": "on",
                    "attributes": {
                        "brightness": self._brightness,
                        "color_temp": self._color_temp,
                        "rgb_color": self._rgb_color,
                        "effect": self._effect,
                    },
                },
            )

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the light off."""
        self._is_on = False
        self.async_write_ha_state()
        _LOGGER.debug(f"Virtual light '{self._attr_name}' turned off")

        # 触发模板更新事件（如果有模板配置）
        if self._templates:
            self.hass.bus.async_fire(
                f"{DOMAIN}_template_update",
                {
                    "entity_id": self.entity_id,
                    "device_id": self._config_entry_id,
                    "state": "off",
                    "attributes": {},
                },
            )
