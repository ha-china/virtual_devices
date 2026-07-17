"""Platform for virtual remote integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.remote import RemoteEntity, RemoteEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .base_entity import BaseVirtualEntity
from .const import (
    CONF_ENTITIES,
    CONF_REMOTE_ACTIVITY,
    CONF_REMOTE_COMMANDS,
    DEVICE_TYPE_REMOTE,
    DOMAIN,
)
from .types import RemoteEntityConfig, RemoteState

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up virtual remote entities."""
    device_type: str | None = config_entry.data.get("device_type")
    if device_type != DEVICE_TYPE_REMOTE:
        return

    device_info: DeviceInfo = hass.data[DOMAIN][config_entry.entry_id]["device_info"]
    entities: list[VirtualRemote] = []
    entities_config: list[RemoteEntityConfig] = config_entry.data.get(CONF_ENTITIES, [])

    for idx, entity_config in enumerate(entities_config):
        entities.append(VirtualRemote(hass, config_entry.entry_id, entity_config, idx, device_info))

    async_add_entities(entities)


class VirtualRemote(BaseVirtualEntity[RemoteEntityConfig, RemoteState], RemoteEntity):
    """Representation of a virtual remote."""

    # NOTE: HA Core routes `remote.learn_command` / `remote.delete_command`
    # services only when `LEARN_COMMAND` / `DELETE_COMMAND` features are
    # declared, and they call `async_learn_command` / `async_delete_command`.
    # We do not implement either (this is a virtual remote), so omit both
    # features to avoid NotImplementedError when the services are invoked.
    _attr_supported_features = RemoteEntityFeature.ACTIVITY

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry_id: str,
        entity_config: RemoteEntityConfig,
        index: int,
        device_info: DeviceInfo,
    ) -> None:
        super().__init__(hass, config_entry_id, entity_config, index, device_info, "remote")
        self._attr_icon = "mdi:remote"
        self._attr_is_on: bool = False
        self._attr_current_activity: str | None = entity_config.get(CONF_REMOTE_ACTIVITY, "tv")
        commands = entity_config.get(CONF_REMOTE_COMMANDS, ["power", "volume_up", "volume_down", "mute"])
        if isinstance(commands, str):
            commands = [item.strip() for item in commands.split(",") if item.strip()]
        self._commands = commands or ["power"]
        self._last_command: str | None = None
        self._attr_activity_list = ["tv", "movie", "music", "game"]

    def get_default_state(self) -> RemoteState:
        return {"is_on": False, "current_activity": "tv", "last_command": None}

    def apply_state(self, state: RemoteState) -> None:
        self._attr_is_on = state.get("is_on", False)
        self._attr_current_activity = state.get("current_activity", "tv")
        self._last_command = state.get("last_command")

    def get_current_state(self) -> RemoteState:
        return {
            "is_on": self._attr_is_on,
            "current_activity": self._attr_current_activity,
            "last_command": self._last_command,
        }

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"available_commands": self._commands, "last_command": self._last_command}

    async def async_turn_on(self, activity: str | None = None, **kwargs: Any) -> None:
        self._attr_is_on = True
        if activity is not None:
            self._attr_current_activity = activity
        await self.async_save_state()
        self.async_write_ha_state()
        self.fire_template_event("turn_on", activity=self._attr_current_activity)

    async def async_turn_off(self, **kwargs: Any) -> None:
        self._attr_is_on = False
        await self.async_save_state()
        self.async_write_ha_state()
        self.fire_template_event("turn_off")

    async def async_send_command(self, command: list[str] | str, **kwargs: Any) -> None:
        if isinstance(command, list):
            self._last_command = command[-1] if command else None
        else:
            self._last_command = command
        self._attr_is_on = True
        await self.async_save_state()
        self.async_write_ha_state()
        self.fire_template_event("send_command", command=self._last_command)
