"""Base entity class for all virtual device entities.

This module provides a unified base class with generic type parameters
for configuration and state, implementing common functionality like
state persistence, attribute initialization, and template support.
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.storage import Store

from .const import CONF_ENTITY_NAME, DOMAIN
from .types import EntityConfigBase, EntityState, TemplateDict

_LOGGER = logging.getLogger(__name__)

# Storage version for state persistence - increment for migrations
STORAGE_VERSION = 1

# Type variables for generic configuration and state types
TConfig = TypeVar("TConfig", bound=EntityConfigBase)
TState = TypeVar("TState", bound=EntityState)


class BaseVirtualEntity(Entity, ABC, Generic[TConfig, TState]):
    """Base class for all virtual device entities.

    This class provides common functionality for virtual device entities:
    - State persistence (load/save to storage)
    - Common attribute initialization (name, unique_id, device_info)
    - Template support for automation integration
    - Event firing for template updates

    Subclasses must implement:
    - get_default_state(): Return default state for the entity type
    - apply_state(state): Apply loaded state to entity attributes
    - get_current_state(): Get current state for persistence

    Type Parameters:
        TConfig: The TypedDict type for entity configuration
        TState: The TypedDict type for entity state
    """

    _attr_should_poll: bool = False
    _attr_entity_registry_enabled_default: bool = True

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry_id: str,
        entity_config: TConfig,
        index: int,
        device_info: DeviceInfo,
        domain: str,
    ) -> None:
        """Initialize the base virtual entity.

        Args:
            hass: Home Assistant instance
            config_entry_id: The config entry ID for this device
            entity_config: Entity-specific configuration dictionary
            index: Index of this entity within the device (0-based)
            device_info: Device registry information
            domain: The entity domain (e.g., "light", "switch")
        """
        self._hass = hass
        self._config_entry_id = config_entry_id
        self._entity_config = entity_config
        self._index = index
        self._domain = domain

        # Set common entity attributes from config
        entity_name = entity_config.get(CONF_ENTITY_NAME, f"{domain}_{index + 1}")
        self._attr_name = entity_name
        self._attr_unique_id = f"{config_entry_id}_{domain}_{index}"
        self._attr_device_info = device_info

        # Template support - extract templates from config
        self._templates: TemplateDict = entity_config.get("templates", {})

        # Storage setup with versioned key for future migrations
        self._store: Store[TState] = Store(
            hass,
            STORAGE_VERSION,
            f"virtual_devices_{domain}_{config_entry_id}_{index}"
        )

        # Initialize state - will be populated by async_load_state
        self._state: TState = self.get_default_state()

    @abstractmethod
    def get_default_state(self) -> TState:
        """Return the default state for this entity type.

        This method is called when no saved state exists or when
        state loading fails. Subclasses must implement this to
        provide appropriate default values for their state type.

        Returns:
            A TypedDict containing default state values
        """
        ...

    @abstractmethod
    def apply_state(self, state: TState) -> None:
        """Apply loaded state to entity attributes.

        This method is called after state is loaded from storage.
        Subclasses must implement this to update their internal
        attributes based on the loaded state.

        Args:
            state: The state dictionary loaded from storage
        """
        ...

    @abstractmethod
    def get_current_state(self) -> TState:
        """Get current state for persistence.

        This method is called when saving state to storage.
        Subclasses must implement this to return a dictionary
        containing all state that should be persisted.

        Returns:
            A TypedDict containing current state values
        """
        ...

    async def async_added_to_hass(self) -> None:
        """Run when entity is added to Home Assistant.

        This method loads saved state from storage and applies it
        to the entity. If no saved state exists or loading fails,
        default state is used instead.
        """
        await super().async_added_to_hass()
        await self.async_load_state()

    async def async_load_state(self) -> None:
        """Load entity state from storage.

        Attempts to load previously saved state. If successful,
        applies the state to entity attributes. If loading fails
        or no state exists, initializes with default values.
        """
        try:
            data = await self._store.async_load()
            if data is not None:
                self._state = data
                self.apply_state(data)
                _LOGGER.debug(
                    "Loaded state for %s: %s",
                    self.entity_id or self._attr_unique_id,
                    data
                )
            else:
                self._state = self.get_default_state()
                self.apply_state(self._state)
                _LOGGER.debug(
                    "Initialized default state for %s",
                    self.entity_id or self._attr_unique_id
                )
        except Exception as ex:
            _LOGGER.error(
                "Error loading state for %s: %s",
                self.entity_id or self._attr_unique_id,
                ex
            )
            # Fall back to default state on error
            self._state = self.get_default_state()
            self.apply_state(self._state)

    async def async_save_state(self) -> None:
        """Save entity state to storage.

        Gets the current state from the entity and persists it
        to storage. Errors are logged but not raised to avoid
        disrupting entity operation.
        """
        try:
            self._state = self.get_current_state()
            await self._store.async_save(self._state)
            _LOGGER.debug(
                "Saved state for %s: %s",
                self.entity_id or self._attr_unique_id,
                self._state
            )
        except Exception as ex:
            _LOGGER.error(
                "Error saving state for %s: %s",
                self.entity_id or self._attr_unique_id,
                ex
            )

    @property
    def should_expose(self) -> bool:
        """Return if this entity should be exposed to voice assistants.

        Returns:
            True to expose entity to voice assistants
        """
        return True

    def fire_template_event(self, action: str, **kwargs: Any) -> None:
        """Fire a template update event if templates are configured.

        This method fires an event on the Home Assistant event bus
        that can be used by automations to react to entity changes.
        The event is only fired if the entity has templates configured.

        Args:
            action: The action that triggered the event (e.g., "turn_on")
            **kwargs: Additional data to include in the event
        """
        if self._templates:
            event_type = f"{DOMAIN}_{self._domain}_template_update"
            event_data = {
                "entity_id": self.entity_id,
                "device_id": self._config_entry_id,
                "action": action,
                **kwargs,
            }
            self._hass.bus.async_fire(event_type, event_data)
            _LOGGER.debug(
                "Fired template event %s: %s",
                event_type,
                event_data
            )
