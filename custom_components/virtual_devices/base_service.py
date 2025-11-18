"""Base service class for all virtual device entities."""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.storage import Store

from .const import DOMAIN, CONF_ENTITY_NAME

_LOGGER = logging.getLogger(__name__)

# Storage version for all entities
STORAGE_VERSION = 1


class BaseVirtualEntity(Entity, ABC):
    """Base class for all virtual device entities."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry_id: str,
        entity_config: dict[str, Any],
        index: int,
        device_info: dict[str, Any],
        domain: str,
    ) -> None:
        """Initialize the base virtual entity."""
        self._config_entry_id = config_entry_id
        self._entity_config = entity_config
        self._index = index
        self._device_info = device_info
        self._hass = hass
        self._domain = domain

        # Basic entity attributes
        entity_name = entity_config.get(CONF_ENTITY_NAME, f"{domain}_{index + 1}")
        self._attr_name = entity_name
        self._attr_unique_id = f"{config_entry_id}_{domain}_{index}"
        self._attr_device_info = device_info

        # Template support
        self._templates = entity_config.get("templates", {})

        # Storage setup
        self._store = Store[dict[str, Any]](
            hass,
            STORAGE_VERSION,
            f"virtual_devices_{domain}_{config_entry_id}_{index}"
        )

        # Initialize state
        self._state = {}

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        await super().async_added_to_hass()
        await self.async_load_state()

    async def async_will_remove_from_hass(self) -> None:
        """Run when entity will be removed from hass."""
        await self.async_save_state()
        await super().async_will_remove_from_hass()

    async def async_load_state(self) -> None:
        """Load entity state from storage."""
        try:
            if (data := await self._store.async_load()) is not None:
                self._state = data
                await self._apply_loaded_state()
                _LOGGER.debug(f"Loaded state for {self.entity_id}")
            else:
                await self._initialize_default_state()
                _LOGGER.debug(f"Initialized default state for {self.entity_id}")
        except Exception as ex:
            _LOGGER.error(f"Error loading state for {self.entity_id}: {ex}")
            await self._initialize_default_state()

    async def async_save_state(self) -> None:
        """Save entity state to storage."""
        try:
            await self._store.async_save(self._state)
            _LOGGER.debug(f"Saved state for {self.entity_id}")
        except Exception as ex:
            _LOGGER.error(f"Error saving state for {self.entity_id}: {ex}")

    @abstractmethod
    async def _apply_loaded_state(self) -> None:
        """Apply loaded state to entity attributes."""
        pass

    @abstractmethod
    async def _initialize_default_state(self) -> None:
        """Initialize default state when no saved state exists."""
        pass

    def _get_template_value(self, key: str, default: Any = None) -> Any:
        """Get value from templates configuration."""
        return self._templates.get(key, default)


class VirtualDeviceService(ABC):
    """Base class for virtual device services managing multiple entities."""

    def __init__(self, hass: HomeAssistant, domain: str) -> None:
        """Initialize the virtual device service."""
        self._hass = hass
        self._domain = domain
        self._supported_device_types = []

    @property
    def supported_device_types(self) -> List[str]:
        """Get list of supported device types."""
        return self._supported_device_types

    @abstractmethod
    async def async_setup_entry(
        self,
        config_entry: ConfigEntry,
        async_add_entities,
    ) -> None:
        """Set up entities for this service."""
        pass

    def is_device_type_supported(self, device_type: str) -> bool:
        """Check if device type is supported by this service."""
        return device_type in self._supported_device_types

    def _get_device_info(self, config_entry: ConfigEntry) -> DeviceInfo:
        """Get device info for entities."""
        return self._hass.data[DOMAIN][config_entry.entry_id]["device_info"]

    def _get_entities_config(self, config_entry: ConfigEntry) -> List[dict[str, Any]]:
        """Get entities configuration."""
        return config_entry.data.get("entities", [])