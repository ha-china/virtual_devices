"""Platform for virtual button integration."""
from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .base_entity import BaseVirtualEntity
from .const import (
    CONF_ENTITIES,
    DEVICE_TYPE_BUTTON,
    DOMAIN,
)
from .types import ButtonEntityConfig, EntityState

_LOGGER = logging.getLogger(__name__)


# Button state is stateless, but we need a TypedDict for the base class
class ButtonState(EntityState):
    """State structure for button entities (stateless)."""
    pass


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up virtual button entities."""
    device_type: str | None = config_entry.data.get("device_type")

    if device_type != DEVICE_TYPE_BUTTON:
        return

    device_info: DeviceInfo = hass.data[DOMAIN][config_entry.entry_id]["device_info"]
    entities: list[VirtualButton] = []
    entities_config: list[ButtonEntityConfig] = config_entry.data.get(CONF_ENTITIES, [])

    for idx, entity_config in enumerate(entities_config):
        entity = VirtualButton(
            hass,
            config_entry.entry_id,
            entity_config,
            idx,
            device_info,
        )
        entities.append(entity)

    async_add_entities(entities)


class VirtualButton(BaseVirtualEntity[ButtonEntityConfig, ButtonState], ButtonEntity):
    """Representation of a virtual button."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry_id: str,
        entity_config: ButtonEntityConfig,
        index: int,
        device_info: DeviceInfo,
    ) -> None:
        """Initialize virtual button."""
        super().__init__(hass, config_entry_id, entity_config, index, device_info, "button")

        # Set button type icon
        button_type: str = entity_config.get("button_type", "generic")
        icon_map: dict[str, str] = {
            "generic": "mdi:gesture-tap-button",
            "restart": "mdi:restart",
            "update": "mdi:update",
            "identify": "mdi:bullseye-arrow",
        }
        self._attr_icon = icon_map.get(button_type, "mdi:gesture-tap-button")

    def get_default_state(self) -> ButtonState:
        """Return the default state for this button entity."""
        # Buttons are stateless
        return ButtonState()

    def apply_state(self, state: ButtonState) -> None:
        """Apply loaded state to entity attributes."""
        # Buttons are stateless, nothing to apply
        pass

    def get_current_state(self) -> ButtonState:
        """Get current state for persistence."""
        # Buttons are stateless
        return ButtonState()

    async def async_press(self) -> None:
        """Handle button press."""
        _LOGGER.info("Virtual button '%s' pressed", self._attr_name)

        # Fire button pressed event for automations
        self._hass.bus.async_fire(
            f"{DOMAIN}_button_pressed",
            {
                "entity_id": self.entity_id,
                "name": self._attr_name,
                "device_id": self._config_entry_id,
            },
        )

        self.fire_template_event("press")
