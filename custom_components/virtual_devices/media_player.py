"""Platform for virtual media player integration."""
from __future__ import annotations

import asyncio
import logging
import random
from datetime import datetime
from typing import Any

from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
    MediaType,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.storage import Store

from .base_entity import STORAGE_VERSION
from .const import (
    CONF_ENTITIES,
    CONF_ENTITY_NAME,
    CONF_MEDIA_DURATION,
    CONF_MEDIA_POSITION,
    CONF_MEDIA_SOURCE_LIST,
    CONF_MEDIA_SUPPORTS_SEEK,
    CONF_MEDIA_VOLUME_LEVEL,
    CONF_MEDIA_VOLUME_MUTED,
    DEVICE_TYPE_MEDIA_PLAYER,
    DOMAIN,
)
from .types import MediaPlayerEntityConfig, MediaPlayerState as MediaPlayerStateType

_LOGGER = logging.getLogger(__name__)

# Default media sources
DEFAULT_MEDIA_SOURCES: list[str] = [
    "local_music",
    "online_radio",
    "podcast",
    "bluetooth_audio",
    "usb_storage",
    "internet_radio",
    "streaming_service",
    "dlna_device",
]

# Default playlist
DEFAULT_PLAYLIST: list[str] = [
    "virtual_song_1",
    "virtual_song_2",
    "virtual_song_3",
    "virtual_song_4",
    "virtual_song_5",
]


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up virtual media player entities."""
    device_type: str | None = config_entry.data.get("device_type")

    if device_type != DEVICE_TYPE_MEDIA_PLAYER:
        return

    device_info: DeviceInfo = hass.data[DOMAIN][config_entry.entry_id]["device_info"]
    entities: list[VirtualMediaPlayer] = []
    entities_config: list[MediaPlayerEntityConfig] = config_entry.data.get(CONF_ENTITIES, [])

    for idx, entity_config in enumerate(entities_config):
        entity = VirtualMediaPlayer(
            hass,
            config_entry.entry_id,
            entity_config,
            idx,
            device_info,
        )
        entities.append(entity)

    async_add_entities(entities)


class VirtualMediaPlayer(MediaPlayerEntity):
    """Representation of a virtual media player.

    This entity inherits from MediaPlayerEntity and implements state persistence
    using the same pattern as BaseVirtualEntity, but cannot directly inherit from
    it due to MediaPlayerEntity's specific requirements.
    """

    _attr_should_poll: bool = False
    _attr_entity_registry_enabled_default: bool = True

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry_id: str,
        entity_config: MediaPlayerEntityConfig,
        index: int,
        device_info: DeviceInfo,
    ) -> None:
        """Initialize the virtual media player."""
        self._hass = hass
        self._config_entry_id = config_entry_id
        self._entity_config = entity_config
        self._index = index

        entity_name: str = entity_config.get(CONF_ENTITY_NAME, f"Media Player {index + 1}")
        self._attr_name = entity_name
        self._attr_unique_id = f"{config_entry_id}_media_player_{index}"
        self._attr_device_info = device_info

        # Template support
        self._templates: dict[str, Any] = entity_config.get("templates", {})

        # Storage for state persistence
        self._store: Store[MediaPlayerStateType] = Store(
            hass, STORAGE_VERSION, f"virtual_devices_media_player_{config_entry_id}_{index}"
        )

        # Media player type
        media_player_type: str = entity_config.get("media_player_type", "speaker")
        self._media_player_type = media_player_type

        # Set icon based on type
        icon_map: dict[str, str] = {
            "tv": "mdi:television",
            "speaker": "mdi:speaker",
            "receiver": "mdi:audio-video-receiver",
            "streaming": "mdi:cast",
            "game_console": "mdi:gamepad-variant",
            "computer": "mdi:laptop",
        }
        self._attr_icon = icon_map.get(media_player_type, "mdi:speaker")

        # Setup supported features
        self._setup_features()

        # Initialize state with MediaPlayerState enum
        self._attr_state: MediaPlayerState = MediaPlayerState.IDLE
        self._attr_media_content_type: str | None = MediaType.MUSIC
        self._attr_media_title: str | None = "Virtual Song"
        self._attr_media_artist: str | None = "Virtual Artist"
        self._attr_media_album_name: str | None = "Virtual Album"
        self._attr_media_duration: int = entity_config.get(CONF_MEDIA_DURATION, 240)
        self._attr_media_position: int = entity_config.get(CONF_MEDIA_POSITION, 0)
        self._attr_media_position_updated_at: datetime | None = datetime.now()
        self._attr_volume_level: float = entity_config.get(CONF_MEDIA_VOLUME_LEVEL, 0.5)
        self._attr_volume_muted: bool = entity_config.get(CONF_MEDIA_VOLUME_MUTED, False)
        self._attr_media_repeat: str = "off"
        self._attr_media_shuffle: bool = False

        # Media source list
        media_sources: list[str] = entity_config.get(CONF_MEDIA_SOURCE_LIST, DEFAULT_MEDIA_SOURCES)
        self._attr_source_list: list[str] = media_sources if isinstance(media_sources, list) else DEFAULT_MEDIA_SOURCES
        self._attr_source: str | None = self._attr_source_list[0] if self._attr_source_list else None

        # Playlist
        self._playlist: list[str] = DEFAULT_PLAYLIST[:]
        self._current_track_index: int = 0

        # Assumed state for UI
        self._attr_assumed_state: bool = True

        _LOGGER.info(f"Virtual media player '{self._attr_name}' initialized with state: {self._attr_state}")

    def get_default_state(self) -> MediaPlayerStateType:
        """Return the default state for this entity type."""
        return {
            "state": MediaPlayerState.IDLE.value,
            "volume_level": 0.5,
            "is_volume_muted": False,
            "source": self._attr_source_list[0] if self._attr_source_list else None,
            "media_repeat": "off",
            "media_shuffle": False,
        }

    def apply_state(self, state: MediaPlayerStateType) -> None:
        """Apply loaded state to entity attributes."""
        state_value = state.get("state", "idle")
        try:
            self._attr_state = MediaPlayerState(state_value)
        except ValueError:
            self._attr_state = MediaPlayerState.IDLE
        self._attr_volume_level = state.get("volume_level", 0.5)
        self._attr_volume_muted = state.get("is_volume_muted", False)
        self._attr_source = state.get("source", self._attr_source_list[0] if self._attr_source_list else None)
        self._attr_media_repeat = state.get("media_repeat", "off")
        self._attr_media_shuffle = state.get("media_shuffle", False)

    def get_current_state(self) -> MediaPlayerStateType:
        """Get current state for persistence."""
        return {
            "state": self._attr_state.value if hasattr(self._attr_state, 'value') else str(self._attr_state),
            "volume_level": self._attr_volume_level,
            "is_volume_muted": self._attr_volume_muted,
            "source": self._attr_source,
            "media_repeat": self._attr_media_repeat,
            "media_shuffle": self._attr_media_shuffle,
        }

    @property
    def should_expose(self) -> bool:
        """Return if this entity should be exposed to voice assistants."""
        return True

    async def async_load_state(self) -> None:
        """Load saved state from storage."""
        try:
            data = await self._store.async_load()
            if data:
                self.apply_state(data)
                _LOGGER.debug(f"Media player '{self._attr_name}' state loaded from storage")
        except Exception as ex:
            _LOGGER.error(f"Failed to load state for media player '{self._attr_name}': {ex}")
            self.apply_state(self.get_default_state())

    async def async_save_state(self) -> None:
        """Save current state to storage."""
        try:
            data = self.get_current_state()
            await self._store.async_save(data)
            _LOGGER.debug(f"Media player '{self._attr_name}' state saved to storage")
        except Exception as ex:
            _LOGGER.error(f"Failed to save state for media player '{self._attr_name}': {ex}")

    async def async_added_to_hass(self) -> None:
        """Call when entity is added to hass."""
        await super().async_added_to_hass()
        await self.async_load_state()
        self.async_write_ha_state()
        _LOGGER.info(
            f"Virtual media player '{self._attr_name}' added to Home Assistant "
            f"with state: {self._attr_state}, volume: {self._attr_volume_level}, source: {self._attr_source}"
        )

    def _setup_features(self) -> None:
        """Setup supported features based on media player type."""
        features: MediaPlayerEntityFeature = (
            MediaPlayerEntityFeature.PLAY
            | MediaPlayerEntityFeature.PAUSE
            | MediaPlayerEntityFeature.STOP
            | MediaPlayerEntityFeature.NEXT_TRACK
            | MediaPlayerEntityFeature.PREVIOUS_TRACK
            | MediaPlayerEntityFeature.VOLUME_SET
            | MediaPlayerEntityFeature.VOLUME_MUTE
            | MediaPlayerEntityFeature.VOLUME_STEP
            | MediaPlayerEntityFeature.SHUFFLE_SET
            | MediaPlayerEntityFeature.REPEAT_SET
            | MediaPlayerEntityFeature.SELECT_SOURCE
            | MediaPlayerEntityFeature.PLAY_MEDIA
            | MediaPlayerEntityFeature.TURN_ON
            | MediaPlayerEntityFeature.TURN_OFF
        )

        if self._entity_config.get(CONF_MEDIA_SUPPORTS_SEEK, False):
            features |= MediaPlayerEntityFeature.SEEK

        self._attr_supported_features = features

    def fire_template_event(self, action: str, **kwargs: Any) -> None:
        """Fire a template update event if templates are configured."""
        if self._templates:
            self._hass.bus.async_fire(
                f"{DOMAIN}_media_player_template_update",
                {
                    "entity_id": self.entity_id,
                    "device_id": self._config_entry_id,
                    "action": action,
                    **kwargs,
                },
            )

    @property
    def state(self) -> MediaPlayerState:
        """Return the state of the media player."""
        return self._attr_state

    @property
    def volume_level(self) -> float | None:
        """Return the volume level of the media player (0..1)."""
        return self._attr_volume_level

    @property
    def source(self) -> str | None:
        """Return the current input source."""
        return self._attr_source

    @property
    def source_list(self) -> list[str] | None:
        """List of available input sources."""
        return self._attr_source_list

    @property
    def is_volume_muted(self) -> bool:
        """Return true if the media player is muted."""
        return self._attr_volume_muted

    @property
    def media_content_type(self) -> str | None:
        """Return the content type of current playing media."""
        return self._attr_media_content_type

    @property
    def media_title(self) -> str | None:
        """Return the title of current playing media."""
        return self._attr_media_title

    @property
    def media_artist(self) -> str | None:
        """Return the artist of current playing media."""
        return self._attr_media_artist

    @property
    def media_album_name(self) -> str | None:
        """Return the album name of current playing media."""
        return self._attr_media_album_name

    @property
    def media_duration(self) -> int | None:
        """Return the duration of current playing media in seconds."""
        return self._attr_media_duration

    @property
    def media_position(self) -> int | None:
        """Return the position of current playing media in seconds."""
        return self._attr_media_position

    @property
    def media_position_updated_at(self) -> datetime | None:
        """Return when the position was last updated."""
        return self._attr_media_position_updated_at

    @property
    def media_repeat(self) -> str | None:
        """Return current repeat mode."""
        return self._attr_media_repeat

    @property
    def media_shuffle(self) -> bool:
        """Return if shuffle is enabled."""
        return self._attr_media_shuffle

    @property
    def media_image_url(self) -> str | None:
        """Return the image URL of current playing media."""
        if self._attr_media_title:
            return f"https://picsum.photos/seed/{self._attr_media_title}/400/400.jpg"
        return None

    @property
    def media_image_remotely_accessible(self) -> bool:
        """Return if the image is accessible outside the home network."""
        return True

    async def async_turn_on(self) -> None:
        """Turn on the media player."""
        self._attr_state = MediaPlayerState.IDLE
        await self.async_save_state()
        self.async_write_ha_state()
        _LOGGER.debug(f"Virtual media player '{self._attr_name}' turned on")
        self.fire_template_event("turn_on", state="on")

    async def async_turn_off(self) -> None:
        """Turn off the media player."""
        self._attr_state = MediaPlayerState.OFF
        self._attr_media_title = None
        self._attr_media_artist = None
        self._attr_media_album_name = None
        self._attr_media_position = 0
        self._attr_media_position_updated_at = None
        await self.async_save_state()
        self.async_write_ha_state()
        _LOGGER.debug(f"Virtual media player '{self._attr_name}' turned off")
        self.fire_template_event("turn_off", state="off")

    async def async_media_play(self) -> None:
        """Play media."""
        if not self._attr_media_title:
            self._select_next_track()

        self._attr_state = MediaPlayerState.PLAYING
        self._attr_media_position_updated_at = datetime.now()
        await self.async_save_state()
        self.async_write_ha_state()
        _LOGGER.debug(f"Virtual media player '{self._attr_name}' playing")
        self.fire_template_event("play", state="playing", media_title=self._attr_media_title)

    async def async_media_pause(self) -> None:
        """Pause media."""
        self._attr_state = MediaPlayerState.PAUSED
        await self.async_save_state()
        self.async_write_ha_state()
        _LOGGER.debug(f"Virtual media player '{self._attr_name}' paused")
        self.fire_template_event("pause", state="paused")

    async def async_media_stop(self) -> None:
        """Stop media."""
        self._attr_state = MediaPlayerState.IDLE
        self._attr_media_position = 0
        self._attr_media_position_updated_at = None
        await self.async_save_state()
        self.async_write_ha_state()
        _LOGGER.debug(f"Virtual media player '{self._attr_name}' stopped")
        self.fire_template_event("stop", state="idle")

    async def async_media_next_track(self) -> None:
        """Send next track command."""
        self._select_next_track()
        if self._attr_state == MediaPlayerState.PLAYING:
            self._attr_media_position = 0
            self._attr_media_position_updated_at = datetime.now()
        self.async_write_ha_state()
        _LOGGER.debug(f"Virtual media player '{self._attr_name}' next track")
        self.fire_template_event("next_track", media_title=self._attr_media_title)

    async def async_media_previous_track(self) -> None:
        """Send previous track command."""
        self._select_previous_track()
        if self._attr_state == MediaPlayerState.PLAYING:
            self._attr_media_position = 0
            self._attr_media_position_updated_at = datetime.now()
        self.async_write_ha_state()
        _LOGGER.debug(f"Virtual media player '{self._attr_name}' previous track")
        self.fire_template_event("previous_track", media_title=self._attr_media_title)

    async def async_media_seek(self, position: float) -> None:
        """Send seek command."""
        self._attr_media_position = int(position)
        self._attr_media_position_updated_at = datetime.now()
        self.async_write_ha_state()
        _LOGGER.debug(f"Virtual media player '{self._attr_name}' seek to {position}s")
        self.fire_template_event("seek", position=position)

    async def async_play_media(self, media_type: str, media_id: str, **kwargs: Any) -> None:
        """Play a piece of media."""
        self._attr_media_content_type = media_type
        self._attr_media_title = media_id
        self._attr_media_artist = "virtual_artist"
        self._attr_media_album_name = "virtual_album"
        self._attr_media_duration = random.randint(180, 300)
        self._attr_media_position = 0
        self._attr_media_position_updated_at = datetime.now()
        self._attr_state = MediaPlayerState.PLAYING

        self.async_write_ha_state()
        _LOGGER.debug(f"Virtual media player '{self._attr_name}' playing media: {media_id}")
        self.fire_template_event(
            "play_media",
            media_type=media_type,
            media_id=media_id,
            media_title=self._attr_media_title,
        )

    async def async_select_source(self, source: str) -> None:
        """Select input source."""
        if source in self._attr_source_list:
            self._attr_source = source
            await self.async_save_state()
            self.async_write_ha_state()
            _LOGGER.debug(f"Virtual media player '{self._attr_name}' source changed to {source}")
            self.fire_template_event("select_source", source=source)

    async def async_set_volume_level(self, volume: float) -> None:
        """Set volume level, range 0..1."""
        original_volume = volume
        volume = max(0.0, min(1.0, volume))

        if abs(original_volume - volume) > 0.001:
            _LOGGER.warning(
                f"Volume {original_volume} out of range (0.0-1.0), clamped to {volume}"
            )

        self._attr_volume_level = volume

        if volume > 0 and self._attr_volume_muted:
            self._attr_volume_muted = False

        await self.async_save_state()
        self.async_write_ha_state()
        _LOGGER.debug(f"Virtual media player '{self._attr_name}' volume set to {volume}")
        self.fire_template_event("set_volume_level", volume=volume)

    async def async_mute_volume(self, mute: bool) -> None:
        """Mute (true) or unmute (false) media player."""
        self._attr_volume_muted = mute
        await self.async_save_state()
        self.async_write_ha_state()
        _LOGGER.debug(f"Virtual media player '{self._attr_name}' muted: {mute}")
        self.fire_template_event("mute_volume", mute=mute)

    async def async_set_repeat(self, repeat: str) -> None:
        """Set repeat mode."""
        valid_repeat_modes: list[str] = ["off", "one", "all"]
        if repeat not in valid_repeat_modes:
            _LOGGER.warning(f"Invalid repeat mode: {repeat}. Valid modes: {valid_repeat_modes}")
            return

        self._attr_media_repeat = repeat

        if self._attr_state == MediaPlayerState.PLAYING and self._playlist:
            self._select_current_track()

        await self.async_save_state()
        self.async_write_ha_state()

        await asyncio.sleep(0.1)
        self.async_write_ha_state()

        _LOGGER.info(f"Virtual media player '{self._attr_name}' repeat set to {self._attr_media_repeat}")
        self.fire_template_event("set_repeat", repeat=self._attr_media_repeat)

    async def async_set_shuffle(self, shuffle: bool) -> None:
        """Enable/disable shuffle mode."""
        old_shuffle = self._attr_media_shuffle
        self._attr_media_shuffle = shuffle

        if shuffle and not old_shuffle and self._playlist:
            random.shuffle(self._playlist)
            self._current_track_index = 0
            if self._attr_state == MediaPlayerState.PLAYING:
                self._select_current_track()
        elif not shuffle and old_shuffle and self._playlist:
            self._current_track_index = 0
            if self._attr_state == MediaPlayerState.PLAYING:
                self._select_current_track()

        await self.async_save_state()
        self.async_write_ha_state()

        await asyncio.sleep(0.1)
        self.async_write_ha_state()

        _LOGGER.info(f"Virtual media player '{self._attr_name}' shuffle set to {shuffle}")
        self.fire_template_event("set_shuffle", shuffle=shuffle)

    def _select_next_track(self) -> None:
        """Select the next track."""
        if not self._playlist:
            return
        self._current_track_index = (self._current_track_index + 1) % len(self._playlist)
        self._select_current_track()

    def _select_previous_track(self) -> None:
        """Select the previous track."""
        if not self._playlist:
            return
        self._current_track_index = (self._current_track_index - 1) % len(self._playlist)
        self._select_current_track()

    def _select_current_track(self) -> None:
        """Select the current track."""
        if self._playlist:
            track_name = self._playlist[self._current_track_index]
            self._attr_media_title = track_name
            self._attr_media_artist = f"virtual_artist_{self._current_track_index + 1}"
            self._attr_media_album_name = "virtual_album_collection"
            self._attr_media_duration = random.randint(180, 300)
            self._attr_media_position = 0

    async def async_update(self) -> None:
        """Update media player position."""
        if self._attr_state == MediaPlayerState.PLAYING and self._attr_media_position_updated_at:
            time_diff = (datetime.now() - self._attr_media_position_updated_at).total_seconds()
            new_position = self._attr_media_position + time_diff

            if new_position >= self._attr_media_duration:
                if self._attr_media_repeat == "one":
                    self._attr_media_position = 0
                elif self._attr_media_repeat == "all" or not self._attr_media_repeat:
                    self._select_next_track()
                    if self._attr_state == MediaPlayerState.PLAYING:
                        self._attr_media_position = 0
                self._attr_media_position_updated_at = datetime.now()
            else:
                self._attr_media_position = int(new_position)

            self.async_write_ha_state()
