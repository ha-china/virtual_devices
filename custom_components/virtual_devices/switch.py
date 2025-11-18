"""Switch platform for virtual devices integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_ENTITIES,
    CONF_ENTITY_NAME,
    DEVICE_TYPE_SWITCH,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up virtual switch entities."""
    device_type = config_entry.data.get("device_type")

    # Only create switch entities for switch device types
    if device_type != DEVICE_TYPE_SWITCH:
        _LOGGER.debug(f"Skipping switch setup for device type: {device_type}")
        return

    _LOGGER.info(f"Setting up switch entities for device type: {device_type}")

    device_info = hass.data[DOMAIN][config_entry.entry_id]["device_info"]
    entities = []
    entities_config = config_entry.data.get(CONF_ENTITIES, [])

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
            _LOGGER.error(f"Failed to create VirtualSwitch {idx}: {e}")

    if entities:
        async_add_entities(entities)
        _LOGGER.info(f"Added {len(entities)} switch entities")


class VirtualSwitch(SwitchEntity):
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
        self._config_entry_id = config_entry_id
        self._entity_config = entity_config
        self._index = index
        self._device_info = device_info
        self._hass = hass
        self._is_on = False

        entity_name = entity_config.get(CONF_ENTITY_NAME, f"switch_{index + 1}")
        self._attr_name = entity_name
        self._attr_unique_id = f"{config_entry_id}_switch_{index}"
        self._attr_device_info = device_info
        self._attr_icon = "mdi:electric-switch"

        # Template support
        self._templates = entity_config.get("templates", {})

    @property
    def is_on(self) -> bool:
        """Return true if switch is on."""
        return self._is_on

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        self._is_on = True
        self.async_write_ha_state()
        _LOGGER.debug(f"Virtual switch '{self._attr_name}' turned on")

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        self._is_on = False
        self.async_write_ha_state()
        _LOGGER.debug(f"Virtual switch '{self._attr_name}' turned off")