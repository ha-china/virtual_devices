"""Platform for virtual fan integration."""
from __future__ import annotations

import logging
import math
from typing import Any

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util.percentage import (
    int_states_in_range,
    percentage_to_ranged_value,
    ranged_value_to_percentage,
)

from .const import (
    CONF_ENTITIES,
    CONF_ENTITY_NAME,
    DEVICE_TYPE_AIR_PURIFIER,
    DEVICE_TYPE_FAN,
    DOMAIN,
    TEMPLATE_ENABLED_DEVICE_TYPES,
)

_LOGGER = logging.getLogger(__name__)

SPEED_RANGE = (1, 100)
PRESET_MODES = ["sleep", "nature", "strong"]


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up virtual fan and air purifier entities."""
    device_type = config_entry.data.get("device_type")

    # 只处理风扇和空气净化器类型的设备
    if device_type not in (DEVICE_TYPE_FAN, DEVICE_TYPE_AIR_PURIFIER):
        return

    device_info = hass.data[DOMAIN][config_entry.entry_id]["device_info"]
    entities = []
    entities_config = config_entry.data.get(CONF_ENTITIES, [])

    # 根据设备类型创建相应的实体
    if device_type == DEVICE_TYPE_AIR_PURIFIER:
        # 导入 air_purifier 模块并创建实体
        from .air_purifier import VirtualAirPurifier
        
        for idx, entity_config in enumerate(entities_config):
            entity = VirtualAirPurifier(
                config_entry.entry_id,
                entity_config,
                idx,
                device_info,
            )
            entities.append(entity)
    else:
        # 创建普通风扇实体
        for idx, entity_config in enumerate(entities_config):
            entity = VirtualFan(
                config_entry.entry_id,
                entity_config,
                idx,
                device_info,
            )
            entities.append(entity)

    async_add_entities(entities)


class VirtualFan(FanEntity):
    """Representation of a virtual fan."""

    _attr_supported_features = (
        # TURN_ON和TURN_OFF在HA 2025.10.0中是默认的
        FanEntityFeature.SET_SPEED
        | FanEntityFeature.PRESET_MODE
        | FanEntityFeature.OSCILLATE
        | FanEntityFeature.DIRECTION
    )

    def __init__(
        self,
        config_entry_id: str,
        entity_config: dict[str, Any],
        index: int,
        device_info: dict[str, Any],
    ) -> None:
        """Initialize the virtual fan."""
        self._config_entry_id = config_entry_id
        self._entity_config = entity_config
        self._index = index
        self._device_info = device_info

        entity_name = entity_config.get(CONF_ENTITY_NAME, f"fan_{index + 1}")
        self._attr_name = entity_name
        self._attr_unique_id = f"{config_entry_id}_fan_{index}"
        self._attr_device_info = device_info
        self._attr_preset_modes = PRESET_MODES

        # Template support
        self._templates = entity_config.get("templates", {})

        # 状态
        self._is_on = False
        self._percentage = 50
        self._preset_mode = None
        self._oscillating = False
        self._direction = "forward"

        self._attr_speed_count = int_states_in_range(SPEED_RANGE)

    @property
    def is_on(self) -> bool:
        """Return true if the fan is on."""
        return self._is_on

    @property
    def percentage(self) -> int | None:
        """Return the current speed percentage."""
        if self._is_on:
            return self._percentage
        return 0

    @property
    def preset_mode(self) -> str | None:
        """Return the current preset mode."""
        return self._preset_mode

    @property
    def oscillating(self) -> bool:
        """Return whether or not the fan is oscillating."""
        return self._oscillating

    @property
    def current_direction(self) -> str:
        """Return the current direction of the fan."""
        return self._direction

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Turn on the fan."""
        self._is_on = True

        if percentage is not None:
            self._percentage = percentage
            self._preset_mode = None
        elif preset_mode is not None:
            self._preset_mode = preset_mode
            self._percentage = 50

        self.async_write_ha_state()
        _LOGGER.debug(f"Virtual fan '{self._attr_name}' turned on")

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the fan off."""
        self._is_on = False
        self.async_write_ha_state()
        _LOGGER.debug(f"Virtual fan '{self._attr_name}' turned off")

    async def async_set_percentage(self, percentage: int) -> None:
        """Set the speed percentage of the fan."""
        self._percentage = percentage
        self._preset_mode = None
        if percentage == 0:
            self._is_on = False
        else:
            self._is_on = True
        self.async_write_ha_state()
        _LOGGER.debug(f"Virtual fan '{self._attr_name}' speed set to {percentage}%")

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set the preset mode of the fan."""
        self._preset_mode = preset_mode
        self._is_on = True
        self.async_write_ha_state()
        _LOGGER.debug(
            f"Virtual fan '{self._attr_name}' preset mode set to {preset_mode}"
        )

    async def async_oscillate(self, oscillating: bool) -> None:
        """Set oscillation."""
        self._oscillating = oscillating
        self.async_write_ha_state()
        _LOGGER.debug(
            f"Virtual fan '{self._attr_name}' oscillation set to {oscillating}"
        )

    async def async_set_direction(self, direction: str) -> None:
        """Set the direction of the fan."""
        self._direction = direction
        self.async_write_ha_state()
        _LOGGER.debug(f"Virtual fan '{self._attr_name}' direction set to {direction}")
