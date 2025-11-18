"""Automation scene domain service for buttons, scenes, and media players."""
from __future__ import annotations

import logging
from typing import Any, List

from homeassistant.components.button import ButtonEntity
from homeassistant.components.scene import Scene
from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaType,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .base_service import BaseVirtualEntity, VirtualDeviceService
from .const import (
    CONF_ENTITIES,
    CONF_ENTITY_NAME,
    DEVICE_TYPE_BUTTON,
    DEVICE_TYPE_SCENE,
    DEVICE_TYPE_MEDIA_PLAYER,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class VirtualButton(BaseVirtualEntity, ButtonEntity):
    """Representation of a virtual button."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry_id: str,
        entity_config: dict[str, Any],
        index: int,
        device_info: dict[str, Any],
    ) -> None:
        """Initialize the virtual button."""
        super().__init__(hass, config_entry_id, entity_config, index, device_info, "button")

        # Button specific configuration
        button_type = entity_config.get("button_type", "generic")
        self._button_type = button_type

        # Set icon based on type
        icon_map = {
            "generic": "mdi:gesture-tap-button",
            "power": "mdi:power",
            "reset": "mdi:restart",
            "emergency": "mdi:alarm-light",
            "doorbell": "mdi:doorbell",
        }
        self._attr_icon = icon_map.get(button_type, "mdi:gesture-tap-button")

        # Button action
        self._action = entity_config.get("action", "pressed")

    async def _apply_loaded_state(self) -> None:
        """Apply loaded state to button entity."""
        # Buttons are stateless, no state to load
        pass

    async def _initialize_default_state(self) -> None:
        """Initialize default button state."""
        # Buttons are stateless
        self._state = {}

    async def async_press(self) -> None:
        """Press the button."""
        _LOGGER.info(f"Virtual button '{self._attr_name}' pressed")
        # In a real implementation, this would trigger an action
        # For now, we just log the press
        pass


class VirtualScene(BaseVirtualEntity, Scene):
    """Representation of a virtual scene."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry_id: str,
        entity_config: dict[str, Any],
        index: int,
        device_info: dict[str, Any],
    ) -> None:
        """Initialize the virtual scene."""
        super().__init__(hass, config_entry_id, entity_config, index, device_info, "scene")

        # Scene specific configuration
        scene_type = entity_config.get("scene_type", "generic")
        self._scene_type = scene_type

        # Set icon based on type
        icon_map = {
            "generic": "mdi:palette",
            "movie": "mdi:movie",
            "reading": "mdi:book-open-variant",
            "relax": "mdi:spa",
            "party": "mdi:party-popper",
            "sleep": "mdi:sleep",
            "away": "mdi:home-export-outline",
            "home": "mdi:home-import-outline",
        }
        self._attr_icon = icon_map.get(scene_type, "mdi:palette")

    async def _apply_loaded_state(self) -> None:
        """Apply loaded state to scene entity."""
        # Scenes are stateless, no state to load
        pass

    async def _initialize_default_state(self) -> None:
        """Initialize default scene state."""
        # Scenes are stateless
        self._state = {}

    async def async_activate(self, **kwargs: Any) -> None:
        """Activate the scene."""
        _LOGGER.info(f"Virtual scene '{self._attr_name}' activated")
        # In a real implementation, this would change device states
        # For now, we just log the activation
        pass


class VirtualMediaPlayer(BaseVirtualEntity, MediaPlayerEntity):
    """Representation of a virtual media player."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry_id: str,
        entity_config: dict[str, Any],
        index: int,
        device_info: dict[str, Any],
    ) -> None:
        """Initialize the virtual media player."""
        super().__init__(hass, config_entry_id, entity_config, index, device_info, "media_player")

        # Media player specific configuration
        player_type = entity_config.get("player_type", "speaker")
        self._player_type = player_type

        # Set icon based on type
        icon_map = {
            "speaker": "mdi:speaker",
            "tv": "mdi:television",
            "receiver": "mdi:receiver",
            "chromecast": "mdi:cast",
            "apple_tv": "mdi:apple",
        }
        self._attr_icon = icon_map.get(player_type, "mdi:speaker")

        # Set supported features
        self._attr_supported_features = (
            MediaPlayerEntityFeature.PLAY
            | MediaPlayerEntityFeature.PAUSE
            | MediaPlayerEntityFeature.STOP
            | MediaPlayerEntityFeature.NEXT_TRACK
            | MediaPlayerEntityFeature.PREVIOUS_TRACK
            | MediaPlayerEntityFeature.VOLUME_SET
            | MediaPlayerEntityFeature.VOLUME_STEP
            | MediaPlayerEntityFeature.VOLUME_MUTE
        )

        # Media player specific state
        self._attr_state = "idle"
        self._attr_volume_level = 0.5
        self._attr_is_volume_muted = False
        self._attr_media_title = None
        self._attr_media_artist = None
        self._attr_media_album_name = None
        self._attr_media_duration = None
        self._attr_media_position = None
        self._attr_media_position_updated_at = None
        self._attr_media_content_type = MediaType.MUSIC

    async def _apply_loaded_state(self) -> None:
        """Apply loaded state to media player entity."""
        self._attr_state = self._state.get("state", "idle")
        self._attr_volume_level = self._state.get("volume_level", 0.5)
        self._attr_is_volume_muted = self._state.get("is_volume_muted", False)
        self._attr_media_title = self._state.get("media_title")
        self._attr_media_artist = self._state.get("media_artist")

    async def _initialize_default_state(self) -> None:
        """Initialize default media player state."""
        self._state = {
            "state": "idle",
            "volume_level": 0.5,
            "is_volume_muted": False,
            "media_title": None,
            "media_artist": None,
        }

    async def async_media_play(self) -> None:
        """Play media."""
        self._attr_state = "playing"
        self._state["state"] = "playing"
        await self.async_save_state()

    async def async_media_pause(self) -> None:
        """Pause media."""
        self._attr_state = "paused"
        self._state["state"] = "paused"
        await self.async_save_state()

    async def async_media_stop(self) -> None:
        """Stop media."""
        self._attr_state = "idle"
        self._attr_media_title = None
        self._attr_media_artist = None
        self._state["state"] = "idle"
        self._state["media_title"] = None
        self._state["media_artist"] = None
        await self.async_save_state()

    async def async_media_next_track(self) -> None:
        """Play next track."""
        # Simulate changing to next track
        self._attr_media_title = "Virtual Track 2"
        self._attr_media_artist = "Virtual Artist"
        self._state["media_title"] = "Virtual Track 2"
        self._state["media_artist"] = "Virtual Artist"
        await self.async_save_state()

    async def async_media_previous_track(self) -> None:
        """Play previous track."""
        # Simulate changing to previous track
        self._attr_media_title = "Virtual Track 1"
        self._attr_media_artist = "Virtual Artist"
        self._state["media_title"] = "Virtual Track 1"
        self._state["media_artist"] = "Virtual Artist"
        await self.async_save_state()

    async def async_mute_volume(self, mute: bool) -> None:
        """Mute or unmute volume."""
        self._attr_is_volume_muted = mute
        self._state["is_volume_muted"] = mute
        await self.async_save_state()

    async def async_set_volume_level(self, volume: float) -> None:
        """Set volume level."""
        self._attr_volume_level = volume
        self._state["volume_level"] = volume
        await self.async_save_state()


class AutomationSceneService(VirtualDeviceService):
    """Automation scene domain service."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the automation scene service."""
        super().__init__(hass, "automation_scene")
        self._supported_device_types = [
            DEVICE_TYPE_BUTTON,
            DEVICE_TYPE_SCENE,
            DEVICE_TYPE_MEDIA_PLAYER,
        ]

    async def async_setup_entry(
        self,
        config_entry: ConfigEntry,
        async_add_entities,
    ) -> None:
        """Set up automation scene entities."""
        device_type = config_entry.data.get("device_type")

        if not self.is_device_type_supported(device_type):
            return

        device_info = self._get_device_info(config_entry)
        entities_config = self._get_entities_config(config_entry)
        entities = []

        for idx, entity_config in enumerate(entities_config):
            if device_type == DEVICE_TYPE_BUTTON:
                entity = VirtualButton(self._hass, config_entry.entry_id, entity_config, idx, device_info)
            elif device_type == DEVICE_TYPE_SCENE:
                entity = VirtualScene(self._hass, config_entry.entry_id, entity_config, idx, device_info)
            elif device_type == DEVICE_TYPE_MEDIA_PLAYER:
                entity = VirtualMediaPlayer(self._hass, config_entry.entry_id, entity_config, idx, device_info)
            else:
                continue

            entities.append(entity)

        if entities:
            async_add_entities(entities)
            _LOGGER.info(f"Added {len(entities)} automation scene entities for {device_type}")