"""Security access domain service for locks and cameras."""
from __future__ import annotations

import logging
from typing import Any, List

from homeassistant.components.lock import LockEntity
from homeassistant.components.camera import Camera
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .base_service import BaseVirtualEntity, VirtualDeviceService
from .const import (
    CONF_ENTITIES,
    CONF_ENTITY_NAME,
    DEVICE_TYPE_LOCK,
    DEVICE_TYPE_CAMERA,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class VirtualLock(BaseVirtualEntity, LockEntity):
    """Representation of a virtual lock."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry_id: str,
        entity_config: dict[str, Any],
        index: int,
        device_info: dict[str, Any],
    ) -> None:
        """Initialize the virtual lock."""
        super().__init__(hass, config_entry_id, entity_config, index, device_info, "lock")

        # Lock specific configuration
        lock_type = entity_config.get("lock_type", "deadbolt")
        self._lock_type = lock_type

        # Set icon based on type
        icon_map = {
            "deadbolt": "mdi:lock",
            "door": "mdi:door-closed-lock",
            "gate": "mdi:gate",
            "garage": "mdi:garage-lock",
        }
        self._attr_icon = icon_map.get(lock_type, "mdi:lock")

        # Lock specific state
        self._attr_is_locked = True

    async def _apply_loaded_state(self) -> None:
        """Apply loaded state to lock entity."""
        self._attr_is_locked = self._state.get("is_locked", True)

    async def _initialize_default_state(self) -> None:
        """Initialize default lock state."""
        self._state = {
            "is_locked": True,
        }

    async def async_lock(self, **kwargs: Any) -> None:
        """Lock the lock."""
        self._attr_is_locked = True
        self._state["is_locked"] = True
        await self.async_save_state()

    async def async_unlock(self, **kwargs: Any) -> None:
        """Unlock the lock."""
        self._attr_is_locked = False
        self._state["is_locked"] = False
        await self.async_save_state()


class VirtualCamera(BaseVirtualEntity, Camera):
    """Representation of a virtual camera."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry_id: str,
        entity_config: dict[str, Any],
        index: int,
        device_info: dict[str, Any],
    ) -> None:
        """Initialize the virtual camera."""
        super().__init__(hass, config_entry_id, entity_config, index, device_info, "camera")

        # Camera specific configuration
        camera_type = entity_config.get("camera_type", "indoor")
        self._camera_type = camera_type

        # Set icon based on type
        icon_map = {
            "indoor": "mdi:camera",
            "outdoor": "mdi:camera-wireless",
            "doorbell": "mdi:doorbell-video",
            "baby": "mdi:baby-carriage",
        }
        self._attr_icon = icon_map.get(camera_type, "mdi:camera")

        # Camera specific state
        self._attr_is_recording = False
        self._attr_motion_detection_enabled = True

    async def _apply_loaded_state(self) -> None:
        """Apply loaded state to camera entity."""
        self._attr_is_recording = self._state.get("is_recording", False)
        self._attr_motion_detection_enabled = self._state.get("motion_detection_enabled", True)

    async def _initialize_default_state(self) -> None:
        """Initialize default camera state."""
        self._state = {
            "is_recording": False,
            "motion_detection_enabled": True,
        }

    async def async_camera_image(
        self, width: int | None = None, height: int | None = None
    ) -> bytes:
        """Return bytes of camera image."""
        # Return a simple placeholder image
        return b""

    @property
    def brand(self) -> str | None:
        """Return the camera brand."""
        return "Virtual"

    @property
    def model(self) -> str | None:
        """Return the camera model."""
        return f"Virtual Camera ({self._camera_type})"


class SecurityAccessService(VirtualDeviceService):
    """Security access domain service."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the security access service."""
        super().__init__(hass, "security_access")
        self._supported_device_types = [
            DEVICE_TYPE_LOCK,
            DEVICE_TYPE_CAMERA,
        ]

    async def async_setup_entry(
        self,
        config_entry: ConfigEntry,
        async_add_entities,
    ) -> None:
        """Set up security access entities."""
        device_type = config_entry.data.get("device_type")

        if not self.is_device_type_supported(device_type):
            return

        device_info = self._get_device_info(config_entry)
        entities_config = self._get_entities_config(config_entry)
        entities = []

        for idx, entity_config in enumerate(entities_config):
            if device_type == DEVICE_TYPE_LOCK:
                entity = VirtualLock(self._hass, config_entry.entry_id, entity_config, idx, device_info)
            elif device_type == DEVICE_TYPE_CAMERA:
                entity = VirtualCamera(self._hass, config_entry.entry_id, entity_config, idx, device_info)
            else:
                continue

            entities.append(entity)

        if entities:
            async_add_entities(entities)
            _LOGGER.info(f"Added {len(entities)} security access entities for {device_type}")