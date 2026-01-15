"""Switch platform for virtual devices integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .base_entity import BaseVirtualEntity
from .const import (
    CONF_ENTITIES,
    DEVICE_TYPE_SWITCH,
    DOMAIN,
)
from .types import SwitchEntityConfig, SwitchState

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up virtual switch entities."""
    device_type: str | None = config_entry.data.get("device_type")

    # Only create switch entities for switch device types
    if device_type != DEVICE_TYPE_SWITCH:
        _LOGGER.debug("Skipping switch setup for device type: %s", device_type)
        return

    _LOGGER.info("Setting up switch entities for device type: %s", device_type)

    device_info: DeviceInfo = hass.data[DOMAIN][config_entry.entry_id]["device_info"]
    entities: list[VirtualSwitch] = []
    entities_config: list[SwitchEntityConfig] = config_entry.data.get(CONF_ENTITIES, [])

    for idx, entity_config in enumerate(entities_config):
        try:
            entity = VirtualSwitch(
                hass,
                config_entry.entry_id,
                entity_config,
                idx,
                device_info,
            )
            entities.append(entity)
        except Exception as e:
            _LOGGER.error("Failed to create VirtualSwitch %d: %s", idx, e)

    if entities:
        async_add_entities(entities)
        _LOGGER.info("Added %d switch entities", len(entities))


class VirtualSwitch(BaseVirtualEntity[SwitchEntityConfig, SwitchState], SwitchEntity):
    """Representation of a virtual switch."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry_id: str,
        entity_config: SwitchEntityConfig,
        index: int,
        device_info: DeviceInfo,
    ) -> None:
        """Initialize the virtual switch."""
        super().__init__(hass, config_entry_id, entity_config, index, device_info, "switch")

        self._attr_icon = "mdi:electric-switch"
        self._attr_is_on: bool = False

    def get_default_state(self) -> SwitchState:
        """Return the default state for this switch entity."""
        return {"is_on": False}

    def apply_state(self, state: SwitchState) -> None:
        """Apply loaded state to entity attributes."""
        self._attr_is_on = state.get("is_on", False)
        _LOGGER.debug("Applied state for switch '%s': is_on=%s", self._attr_name, self._attr_is_on)

    def get_current_state(self) -> SwitchState:
        """Get current state for persistence."""
        return {"is_on": self._attr_is_on}

    @property
    def is_on(self) -> bool:
        """Return true if switch is on."""
        return self._attr_is_on

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        self._attr_is_on = True
        self.fire_template_event("turn_on", **kwargs)
        await self.async_save_state()
        self.async_write_ha_state()
        _LOGGER.debug("Virtual switch '%s' turned on", self._attr_name)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        self._attr_is_on = False
        self.fire_template_event("turn_off")
        await self.async_save_state()
        self.async_write_ha_state()
        _LOGGER.debug("Virtual switch '%s' turned off", self._attr_name)
