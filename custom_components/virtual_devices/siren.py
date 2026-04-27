"""Platform for virtual siren integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.siren import SirenEntity, SirenEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .base_entity import BaseVirtualEntity
from .const import (
    CONF_ENTITIES,
    CONF_SIREN_DURATION,
    CONF_SIREN_TONE,
    CONF_SIREN_VOLUME,
    DEVICE_TYPE_SIREN,
    DOMAIN,
    SIREN_TONES,
)
from .types import SirenEntityConfig, SirenState

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up virtual siren entities."""
    device_type: str | None = config_entry.data.get("device_type")
    if device_type != DEVICE_TYPE_SIREN:
        return

    device_info: DeviceInfo = hass.data[DOMAIN][config_entry.entry_id]["device_info"]
    entities: list[VirtualSiren] = []
    entities_config: list[SirenEntityConfig] = config_entry.data.get(CONF_ENTITIES, [])

    for idx, entity_config in enumerate(entities_config):
        entities.append(
            VirtualSiren(hass, config_entry.entry_id, entity_config, idx, device_info)
        )

    async_add_entities(entities)


class VirtualSiren(BaseVirtualEntity[SirenEntityConfig, SirenState], SirenEntity):
    """Representation of a virtual siren."""

    _attr_supported_features = (
        SirenEntityFeature.TONES
        | SirenEntityFeature.DURATION
        | SirenEntityFeature.VOLUME_SET
        | SirenEntityFeature.TURN_ON
        | SirenEntityFeature.TURN_OFF
    )

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry_id: str,
        entity_config: SirenEntityConfig,
        index: int,
        device_info: DeviceInfo,
    ) -> None:
        super().__init__(hass, config_entry_id, entity_config, index, device_info, "siren")
        self._attr_icon = "mdi:bullhorn"
        self._attr_available_tones = list(SIREN_TONES.keys())
        self._is_on = False
        self._tone = entity_config.get(CONF_SIREN_TONE, "alarm")
        self._duration = int(entity_config.get(CONF_SIREN_DURATION, 30))
        self._volume_level = float(entity_config.get(CONF_SIREN_VOLUME, 1.0))

    def get_default_state(self) -> SirenState:
        return {
            "is_on": False,
            "tone": "alarm",
            "duration": 30,
            "volume_level": 1.0,
        }

    def apply_state(self, state: SirenState) -> None:
        self._is_on = state.get("is_on", False)
        self._tone = state.get("tone", "alarm")
        self._duration = state.get("duration", 30)
        self._volume_level = state.get("volume_level", 1.0)

    def get_current_state(self) -> SirenState:
        return {
            "is_on": self._is_on,
            "tone": self._tone,
            "duration": self._duration,
            "volume_level": self._volume_level,
        }

    @property
    def is_on(self) -> bool:
        return self._is_on

    @property
    def tone(self) -> str | int | None:
        return self._tone

    @property
    def available_tones(self) -> list[str] | dict[str, str] | None:
        return self._attr_available_tones

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "tone": self._tone,
            "duration": self._duration,
            "volume_level": self._volume_level,
        }

    async def async_turn_on(self, **kwargs: Any) -> None:
        self._is_on = True
        self._tone = kwargs.get("tone", self._tone)
        self._duration = int(kwargs.get("duration", self._duration))
        self._volume_level = float(kwargs.get("volume_level", self._volume_level))
        await self.async_save_state()
        self.async_write_ha_state()
        self.fire_template_event(
            "turn_on",
            tone=self._tone,
            duration=self._duration,
            volume_level=self._volume_level,
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        self._is_on = False
        await self.async_save_state()
        self.async_write_ha_state()
        self.fire_template_event("turn_off")

