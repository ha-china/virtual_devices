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


def _color_temp_kelvin_to_rgb(color_temp_kelvin: int) -> tuple[int, int, int]:
    """
    Convert color temperature in Kelvin to RGB color.

    Approximation algorithm based on Tanner Helland's work:
    https://tannerhelland.com/2012/09/18/convert-temperature-rgb-algorithm-code.html
    """
    # Clamp temperature to valid range
    temp = max(1000, min(40000, color_temp_kelvin)) / 100

    # Calculate red
    if temp <= 66:
        red = 255
    else:
        red = max(0, min(255, int(329.698727446 * ((temp - 60) ** -0.1332047592))))

    # Calculate green
    if temp <= 66:
        green = max(0, min(255, int(99.4708025861 * math.log(temp) - 161.1195681661)))
    else:
        green = max(0, min(255, int(288.1221695283 * ((temp - 60) ** -0.0755148492))))

    # Calculate blue
    if temp >= 66:
        blue = 255
    elif temp <= 19:
        blue = 0
    else:
        blue = max(0, min(255, int(138.5177312231 * math.log(temp - 10) - 305.0447927307)))

    return (red, green, blue)


def _rgb_to_color_temp_kelvin(rgb: tuple[int, int, int]) -> int | None:
    """
    Convert RGB color to approximate color temperature in Kelvin.
    This is an approximation and may not be exact.
    """
    r, g, b = rgb

    # Normalize RGB values
    r_n = r / 255.0
    g_n = g / 255.0
    b_n = b / 255.0

    # Check for grayscale colors (approximate)
    if abs(r_n - g_n) < 0.1 and abs(g_n - b_n) < 0.1:
        # Grayscale - estimate based on brightness
        brightness = (r_n + g_n + b_n) / 3
        if brightness > 0.8:
            return 6500  # Cool white
        elif brightness > 0.5:
            return 4000  # Neutral white
        else:
            return 2700  # Warm white

    # Simple approximation based on color ratios
    if r_n > g_n and g_n > b_n:
        # Reddish colors - warm temperature
        return int(2000 + (g_n / r_n) * 2000)
    elif b_n > r_n and b_n > g_n:
        # Bluish colors - cool temperature
        return int(5000 + (b_n - g_n) * 5000)
    elif g_n > r_n and g_n > b_n:
        # Greenish colors - around neutral
        return int(4000 + (g_n - r_n) * 1000)
    else:
        # Mixed colors - estimate based on warm/cool balance
        warmth = r_n / (r_n + b_n) if (r_n + b_n) > 0 else 0.5
        return int(2700 + warmth * 3800)


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

        # 设置支持的颜色模式和功能 - 使用正确的LightEntityFeature属性
        supported_modes = set()
        supported_features = LightEntityFeature(0)

        if has_rgb:
            supported_modes.add(ColorMode.RGB)
            # 使用正确的属性名
            if hasattr(LightEntityFeature, 'SUPPORT_COLOR'):
                supported_features |= LightEntityFeature.SUPPORT_COLOR

        if has_color_temp:
            supported_modes.add(ColorMode.COLOR_TEMP)
            # 使用正确的属性名
            if hasattr(LightEntityFeature, 'SUPPORT_COLOR_TEMP'):
                supported_features |= LightEntityFeature.SUPPORT_COLOR_TEMP

        if has_brightness:
            supported_modes.add(ColorMode.BRIGHTNESS)
            # 使用正确的属性名
            if hasattr(LightEntityFeature, 'SUPPORT_BRIGHTNESS'):
                supported_features |= LightEntityFeature.SUPPORT_BRIGHTNESS

        if has_effects:
            supported_features |= LightEntityFeature.EFFECT

        if not supported_modes:
            supported_modes.add(ColorMode.ONOFF)

        # HA 2025.8+ 支持多种颜色模式并存，智能组合模式
        if len(supported_modes) > 1:
            # 支持更复杂的颜色模式组合
            if ColorMode.RGB in supported_modes and ColorMode.COLOR_TEMP in supported_modes:
                # RGB + 色温模式
                supported_modes = {ColorMode.RGB, ColorMode.COLOR_TEMP}
                _LOGGER.info(f"Light '{self._attr_name}': RGB + Color temp mode supported")
            elif ColorMode.RGB in supported_modes and ColorMode.BRIGHTNESS in supported_modes:
                # RGB + 亮度模式
                supported_modes = {ColorMode.RGB, ColorMode.BRIGHTNESS}
                _LOGGER.info(f"Light '{self._attr_name}': RGB + Brightness mode supported")
            else:
                # 保持所有支持的模式
                _LOGGER.info(f"Light '{self._attr_name}': Multiple modes supported: {supported_modes}")

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

        # 设置默认暴露给语音助手
        self._attr_entity_registry_enabled_default = True
        self._attr_should_poll = False
        self._attr_entity_category = None

    def _color_temp_kelvin_to_rgb(self, color_temp_kelvin: int) -> tuple[int, int, int]:
        """Convert color temperature in Kelvin to RGB color."""
        return _color_temp_kelvin_to_rgb(color_temp_kelvin)

    def _rgb_to_color_temp_kelvin(self, rgb: tuple[int, int, int]) -> int | None:
        """Convert RGB color to approximate color temperature in Kelvin."""
        return _rgb_to_color_temp_kelvin(rgb)

    @property
    def should_expose(self) -> bool:
        """Return if this entity should be exposed to voice assistants."""
        return True

    async def async_added_to_hass(self) -> None:
        """Call when entity is added to hass."""
        await super().async_added_to_hass()

        # 加载保存的状态并更新HA状态
        await self._load_state()
        self.async_write_ha_state()

    async def _load_state(self) -> None:
        """Load saved state from storage."""
        try:
            # 从存储中加载状态
            data = await self._store.async_load()
            if data:
                self._attr_is_on = data.get("is_on", False)
                if self._has_brightness:
                    self._attr_brightness = data.get("brightness", 255)
                if self._has_rgb:
                    self._attr_rgb_color = tuple(data.get("rgb_color", (255, 255, 255)))
                if self._has_color_temp:
                    self._attr_color_temp_kelvin = data.get("color_temp_kelvin", 3000)
                if self._has_effects:
                    self._attr_effect = data.get("effect", None)

                _LOGGER.info(f"Loaded state for light '{self._attr_name}': is_on={self._attr_is_on}")
            else:
                # 使用默认状态
                self._attr_is_on = False
                if self._has_brightness:
                    self._attr_brightness = 255
                if self._has_rgb:
                    self._attr_rgb_color = (255, 255, 255)
                if self._has_color_temp:
                    self._attr_color_temp_kelvin = 3000
        except Exception as ex:
            _LOGGER.error(f"Failed to load state for light: {ex}")
            # 出错时使用默认状态
            self._attr_is_on = False
            if self._has_brightness:
                self._attr_brightness = 255
            if self._has_rgb:
                self._attr_rgb_color = (255, 255, 255)
            if self._has_color_temp:
                self._attr_color_temp_kelvin = 3000

    @property
    def is_on(self) -> bool:
        """Return true if light is on."""
        return self._attr_is_on

    @property
    def brightness(self) -> int | None:
        """Return the brightness of the light."""
        if self._attr_color_mode == ColorMode.RGB and self._attr_rgb_color:
            # RGB模式下，使用标准亮度公式计算亮度
            r, g, b = self._attr_rgb_color
            # 使用ITU-R BT.709亮度公式：0.2126*R + 0.7152*G + 0.0722*B
            brightness = int(0.2126 * r + 0.7152 * g + 0.0722 * b)
            return max(1, min(255, brightness))  # 确保在有效范围内
        elif ColorMode.COLOR_TEMP in self._attr_supported_color_modes:
            # 色温模式下，返回内部亮度值
            return self._attr_brightness
        elif ColorMode.BRIGHTNESS in self._attr_supported_color_modes:
            return self._attr_brightness
        return None

    @property
    def rgb_color(self) -> tuple[int, int, int] | None:
        """Return the rgb color value."""
        if self._attr_color_mode == ColorMode.RGB:
            return self._attr_rgb_color
        elif self._attr_color_mode == ColorMode.COLOR_TEMP and self._has_color_temp:
            # 色温模式下，将色温转换为RGB值
            return self._color_temp_kelvin_to_rgb(self._attr_color_temp_kelvin or 3000)
        return None

    @property
    def color_temp_kelvin(self) -> int | None:
        """Return the color temperature in kelvin."""
        if self._attr_color_mode == ColorMode.COLOR_TEMP:
            return self._attr_color_temp_kelvin
        elif self._attr_color_mode == ColorMode.RGB and self._attr_rgb_color:
            # RGB模式下，尝试将RGB转换为色温
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

        # 处理RGB颜色设置
        if ATTR_RGB_COLOR in kwargs:
            rgb = kwargs[ATTR_RGB_COLOR]
            if self._has_rgb and rgb:
                self._attr_rgb_color = rgb
                # 设置RGB颜色时，自动切换到RGB模式
                if ColorMode.RGB in self._attr_supported_color_modes:
                    self._attr_color_mode = ColorMode.RGB
                # 根据新RGB颜色计算亮度
                r, g, b = rgb
                calculated_brightness = int(0.2126 * r + 0.7152 * g + 0.0722 * b)
                self._attr_brightness = max(1, min(255, calculated_brightness))

        # 处理色温设置
        if ATTR_COLOR_TEMP_KELVIN in kwargs and self._has_color_temp:
            color_temp = kwargs[ATTR_COLOR_TEMP_KELVIN]
            self._attr_color_temp_kelvin = color_temp
            # 设置色温时，自动切换到色温模式
            if ColorMode.COLOR_TEMP in self._attr_supported_color_modes:
                self._attr_color_mode = ColorMode.COLOR_TEMP
                # 将色温转换为RGB以保持一致性
                self._attr_rgb_color = self._color_temp_kelvin_to_rgb(color_temp)

        # 处理亮度设置
        if ATTR_BRIGHTNESS in kwargs:
            brightness = kwargs[ATTR_BRIGHTNESS]

            if self._attr_color_mode == ColorMode.RGB and self._attr_rgb_color:
                # RGB模式下：保持当前颜色比例，调整RGB值来达到目标亮度
                r, g, b = self._attr_rgb_color
                current_brightness = int(0.2126 * r + 0.7152 * g + 0.0722 * b)
                if current_brightness > 0:
                    scale_factor = brightness / current_brightness
                    self._attr_rgb_color = tuple(
                        max(0, min(255, int(val * scale_factor)))
                        for val in self._attr_rgb_color
                    )
                else:
                    # 当前亮度为0，使用白色达到目标亮度
                    self._attr_rgb_color = (brightness, brightness, brightness)
            else:
                # 非RGB模式下直接设置亮度
                self._attr_brightness = brightness

        # 处理效果设置
        if ATTR_EFFECT in kwargs and self._has_effects:
            self._attr_effect = kwargs[ATTR_EFFECT]

        await self._save_state()
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the light off."""
        self._attr_is_on = False
        await self._save_state()
        self.async_write_ha_state()

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