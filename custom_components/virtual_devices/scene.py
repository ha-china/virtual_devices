"""Platform for virtual scene integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.scene import Scene
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .base_entity import BaseVirtualEntity
from .const import (
    CONF_ENTITIES,
    DEVICE_TYPE_SCENE,
    DOMAIN,
)
from .types import SceneEntityConfig, EntityState

_LOGGER = logging.getLogger(__name__)


# Scene state is stateless, but we need a TypedDict for the base class
class SceneState(EntityState):
    """State structure for scene entities (stateless)."""
    pass


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up virtual scene entities."""
    device_type: str | None = config_entry.data.get("device_type")

    if device_type != DEVICE_TYPE_SCENE:
        return

    device_info: DeviceInfo = hass.data[DOMAIN][config_entry.entry_id]["device_info"]
    entities: list[VirtualScene] = []
    entities_config: list[SceneEntityConfig] = config_entry.data.get(CONF_ENTITIES, [])

    for idx, entity_config in enumerate(entities_config):
        entity = VirtualScene(
            hass,
            config_entry.entry_id,
            entity_config,
            idx,
            device_info,
        )
        entities.append(entity)

    async_add_entities(entities)


class VirtualScene(BaseVirtualEntity[SceneEntityConfig, SceneState], Scene):
    """Representation of a virtual scene."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry_id: str,
        entity_config: SceneEntityConfig,
        index: int,
        device_info: DeviceInfo,
    ) -> None:
        """Initialize the virtual scene."""
        super().__init__(hass, config_entry_id, entity_config, index, device_info, "scene")

    def get_default_state(self) -> SceneState:
        """Return the default state for this scene entity."""
        # Scenes are stateless
        return SceneState()

    def apply_state(self, state: SceneState) -> None:
        """Apply loaded state to entity attributes."""
        # Scenes are stateless, nothing to apply
        pass

    def get_current_state(self) -> SceneState:
        """Get current state for persistence."""
        # Scenes are stateless
        return SceneState()

    async def async_activate(self, **kwargs: Any) -> None:
        """Activate the scene."""
        _LOGGER.info("Virtual scene '%s' activated", self._attr_name)

        # Fire scene activated event for automations
        self._hass.bus.async_fire(
            f"{DOMAIN}_scene_activated",
            {
                "entity_id": self.entity_id,
                "name": self._attr_name,
                "device_id": self._config_entry_id,
            },
        )

        self.fire_template_event("activate")
