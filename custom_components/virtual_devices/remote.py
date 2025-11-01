"""Virtual Remote platform."""
import logging
from typing import Any, Dict, Optional

from homeassistant.components.remote import RemoteEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up virtual remote platform."""
    devices = config_entry.data.get("devices", [])
    remotes = [device for device in devices if device["type"] == "remote"]
    
    entities = []
    for remote_config in remotes:
        entities.append(VirtualRemote(remote_config))
    
    if entities:
        async_add_entities(entities)


class VirtualRemote(RemoteEntity):
    """Representation of a Virtual Remote device."""

    def __init__(self, config: Dict[str, Any]) -> None:
        """Initialize the virtual remote device."""
        self._config = config
        self._attr_name = config["name"]
        self._attr_unique_id = config["unique_id"]

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the remote on."""
        _LOGGER.info("Remote turned on: %s", self._attr_name)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the remote off."""
        _LOGGER.info("Remote turned off: %s", self._attr_name)

    async def async_send_command(self, command: str, **kwargs: Any) -> None:
        """Send a command."""
        _LOGGER.info("Command sent: %s", command)