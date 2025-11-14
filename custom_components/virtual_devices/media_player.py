"""Platform for virtual media player integration."""
from __future__ import annotations

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
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.storage import Store

STORAGE_VERSION = 1

from .const import (
    CONF_ENTITIES,
    CONF_ENTITY_NAME,
    CONF_MEDIA_CONTENT_TYPE,
    CONF_MEDIA_DURATION,
    CONF_MEDIA_POSITION,
    CONF_MEDIA_REPEAT,
    CONF_MEDIA_SHUFFLE,
    CONF_MEDIA_SOURCE_LIST,
    CONF_MEDIA_SUPPORTS_SEEK,
    CONF_MEDIA_VOLUME_LEVEL,
    CONF_MEDIA_VOLUME_MUTED,
    DEVICE_TYPE_MEDIA_PLAYER,
    DOMAIN,
    MEDIA_PLAYER_TYPES,
    TEMPLATE_ENABLED_DEVICE_TYPES,
)

_LOGGER = logging.getLogger(__name__)

# 默认媒体源列表
DEFAULT_MEDIA_SOURCES = [
    "local_music",
    "online_radio",
    "podcast",
    "bluetooth_audio",
    "usb_storage",
    "internet_radio",
    "streaming_service",
    "dlna_device",
]

# 默认播放列表
DEFAULT_PLAYLIST = [
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
    device_type = config_entry.data.get("device_type")

    # 只有媒体播放器类型的设备才设置媒体播放器实体
    if device_type != DEVICE_TYPE_MEDIA_PLAYER:
        return

    device_info = hass.data[DOMAIN][config_entry.entry_id]["device_info"]
    entities = []
    entities_config = config_entry.data.get(CONF_ENTITIES, [])

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
        self._config_entry_id = config_entry_id
        self._entity_config = entity_config
        self._index = index
        self._device_info = device_info
        self._hass = hass

        entity_name = entity_config.get(CONF_ENTITY_NAME, f"media_player_{index + 1}")
        self._attr_name = entity_name
        self._attr_unique_id = f"{config_entry_id}_media_player_{index}"
        self._attr_device_info = device_info

        # Template support
        self._templates = entity_config.get("templates", {})

        # 存储实体状态
        self._store = Store[dict[str, Any]](hass, STORAGE_VERSION, f"virtual_devices_media_player_{config_entry_id}_{index}")

        # 媒体播放器类型
        media_player_type = entity_config.get("media_player_type", "speaker")
        self._media_player_type = media_player_type

        # 根据类型设置图标
        icon_map = {
            "tv": "mdi:television",
            "speaker": "mdi:speaker",
            "receiver": "mdi:audio-video-receiver",
            "streaming": "mdi:cast",
            "game_console": "mdi:gamepad-variant",
            "computer": "mdi:laptop",
        }
        self._attr_icon = icon_map.get(media_player_type, "mdi:speaker")

        # 支持的功能
        self._setup_features()

        # 初始化状态 - 使用 MediaPlayerState 枚举
        self._attr_state = MediaPlayerState.OFF
        self._attr_media_content_type = MediaType.MUSIC
        self._attr_media_title = None
        self._attr_media_artist = None
        self._attr_media_album_name = None
        self._attr_media_duration = entity_config.get(CONF_MEDIA_DURATION, 240)  # 默认4分钟
        self._attr_media_position = entity_config.get(CONF_MEDIA_POSITION, 0)
        self._attr_media_position_updated_at = None
        # 修复：使用正确的属性名 volume_level 而不是 media_volume_level
        self._attr_volume_level = entity_config.get(CONF_MEDIA_VOLUME_LEVEL, 0.5)
        self._attr_volume_muted = entity_config.get(CONF_MEDIA_VOLUME_MUTED, False)
        self._attr_media_repeat = "off"
        self._attr_media_shuffle = False

        # 媒体源列表
        media_sources = entity_config.get(CONF_MEDIA_SOURCE_LIST, DEFAULT_MEDIA_SOURCES)
        self._attr_source_list = media_sources if isinstance(media_sources, list) else DEFAULT_MEDIA_SOURCES
        self._attr_source = self._attr_source_list[0] if self._attr_source_list else None

        # 播放列表
        self._playlist = DEFAULT_PLAYLIST[:]
        self._current_track_index = 0
        
        _LOGGER.info(f"Virtual media player '{self._attr_name}' initialized with state: {self._attr_state}")

    async def async_load_state(self) -> None:
        """Load saved state from storage."""
        try:
            data = await self._store.async_load()
            if data:
                self._attr_state = MediaPlayerState(data.get("state", "off"))
                self._attr_volume_level = data.get("volume_level", 0.5)
                self._attr_volume_muted = data.get("volume_muted", False)
                self._attr_source = data.get("source", self._attr_source_list[0] if self._attr_source_list else None)
                self._attr_media_repeat = data.get("media_repeat", "off")
                self._attr_media_shuffle = data.get("media_shuffle", False)
                _LOGGER.info(f"Media player '{self._attr_name}' state loaded from storage")
        except Exception as ex:
            _LOGGER.error(f"Failed to load state for media player '{self._attr_name}': {ex}")

    async def async_save_state(self) -> None:
        """Save current state to storage."""
        try:
            data = {
                "state": self._attr_state.value if hasattr(self._attr_state, 'value') else str(self._attr_state),
                "volume_level": self._attr_volume_level,
                "volume_muted": self._attr_volume_muted,
                "source": self._attr_source,
                "media_repeat": self._attr_media_repeat,
                "media_shuffle": self._attr_media_shuffle,
            }
            await self._store.async_save(data)
        except Exception as ex:
            _LOGGER.error(f"Failed to save state for media player '{self._attr_name}': {ex}")

    async def async_added_to_hass(self) -> None:
        """Call when entity is added to hass."""
        await super().async_added_to_hass()
        await self.async_load_state()

        # 确保状态正确设置并立即更新
        self.async_write_ha_state()

        _LOGGER.info(f"Virtual media player '{self._attr_name}' added to Home Assistant with state: {self._attr_state}, volume: {self._attr_volume_level}, source: {self._attr_source}")

    def _setup_features(self) -> None:
        """Setup supported features based on media player type."""
        features = (
            # TURN_ON和TURN_OFF在HA 2025.10.0中是默认的
            MediaPlayerEntityFeature.VOLUME_SET
            | MediaPlayerEntityFeature.VOLUME_MUTE
            | MediaPlayerEntityFeature.VOLUME_STEP
            | MediaPlayerEntityFeature.SELECT_SOURCE
        )

        # 根据类型添加特定功能
        if self._media_player_type in ["tv", "streaming", "receiver"]:
            features |= (
                MediaPlayerEntityFeature.PLAY_MEDIA
                | MediaPlayerEntityFeature.PLAY
                | MediaPlayerEntityFeature.PAUSE
                | MediaPlayerEntityFeature.STOP
                | MediaPlayerEntityFeature.NEXT_TRACK
                | MediaPlayerEntityFeature.PREVIOUS_TRACK
            )

        if self._media_player_type in ["speaker", "receiver", "computer"]:
            features |= (
                MediaPlayerEntityFeature.PLAY
                | MediaPlayerEntityFeature.PAUSE
                | MediaPlayerEntityFeature.STOP
                | MediaPlayerEntityFeature.NEXT_TRACK
                | MediaPlayerEntityFeature.PREVIOUS_TRACK
                | MediaPlayerEntityFeature.SHUFFLE_SET
                | MediaPlayerEntityFeature.REPEAT_SET
            )

        # 支持搜索功能的设备
        if self._entity_config.get(CONF_MEDIA_SUPPORTS_SEEK, False):
            features |= MediaPlayerEntityFeature.SEEK

        self._attr_supported_features = features

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
    def media_position_updated_at(self) -> str | None:
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

        # 触发模板更新事件
        if self._templates:
            self.hass.bus.async_fire(
                f"{DOMAIN}_media_player_template_update",
                {
                    "entity_id": self.entity_id,
                    "device_id": self._config_entry_id,
                    "state": "on",
                    "action": "turn_on",
                },
            )

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

        # 触发模板更新事件
        if self._templates:
            self.hass.bus.async_fire(
                f"{DOMAIN}_media_player_template_update",
                {
                    "entity_id": self.entity_id,
                    "device_id": self._config_entry_id,
                    "state": "off",
                    "action": "turn_off",
                },
            )

    async def async_media_play(self) -> None:
        """Play media."""
        if not self._attr_media_title:
            # 如果没有正在播放的媒体，选择第一首
            self._select_next_track()

        self._attr_state = MediaPlayerState.PLAYING
        self._attr_media_position_updated_at = datetime.now()
        await self.async_save_state()
        self.async_write_ha_state()
        _LOGGER.debug(f"Virtual media player '{self._attr_name}' playing")

        # 触发模板更新事件
        if self._templates:
            self.hass.bus.async_fire(
                f"{DOMAIN}_media_player_template_update",
                {
                    "entity_id": self.entity_id,
                    "device_id": self._config_entry_id,
                    "state": "playing",
                    "action": "play",
                    "media_title": self._attr_media_title,
                },
            )

    async def async_media_pause(self) -> None:
        """Pause media."""
        self._attr_state = MediaPlayerState.PAUSED
        await self.async_save_state()
        self.async_write_ha_state()
        _LOGGER.debug(f"Virtual media player '{self._attr_name}' paused")

        # 触发模板更新事件
        if self._templates:
            self.hass.bus.async_fire(
                f"{DOMAIN}_media_player_template_update",
                {
                    "entity_id": self.entity_id,
                    "device_id": self._config_entry_id,
                    "state": "paused",
                    "action": "pause",
                },
            )

    async def async_media_stop(self) -> None:
        """Stop media."""
        self._attr_state = MediaPlayerState.IDLE
        self._attr_media_position = 0
        self._attr_media_position_updated_at = None
        await self.async_save_state()
        self.async_write_ha_state()
        _LOGGER.debug(f"Virtual media player '{self._attr_name}' stopped")

        # 触发模板更新事件
        if self._templates:
            self.hass.bus.async_fire(
                f"{DOMAIN}_media_player_template_update",
                {
                    "entity_id": self.entity_id,
                    "device_id": self._config_entry_id,
                    "state": "idle",
                    "action": "stop",
                },
            )

    async def async_media_next_track(self) -> None:
        """Send next track command."""
        self._select_next_track()
        if self._attr_state == MediaPlayerState.PLAYING:
            self._attr_media_position = 0
            self._attr_media_position_updated_at = datetime.now()
        self.async_write_ha_state()
        _LOGGER.debug(f"Virtual media player '{self._attr_name}' next track")

        # 触发模板更新事件
        if self._templates:
            self.hass.bus.async_fire(
                f"{DOMAIN}_media_player_template_update",
                {
                    "entity_id": self.entity_id,
                    "device_id": self._config_entry_id,
                    "action": "next_track",
                    "media_title": self._attr_media_title,
                },
            )

    async def async_media_previous_track(self) -> None:
        """Send previous track command."""
        self._select_previous_track()
        if self._attr_state == MediaPlayerState.PLAYING:
            self._attr_media_position = 0
            self._attr_media_position_updated_at = datetime.now()
        self.async_write_ha_state()
        _LOGGER.debug(f"Virtual media player '{self._attr_name}' previous track")

        # 触发模板更新事件
        if self._templates:
            self.hass.bus.async_fire(
                f"{DOMAIN}_media_player_template_update",
                {
                    "entity_id": self.entity_id,
                    "device_id": self._config_entry_id,
                    "action": "previous_track",
                    "media_title": self._attr_media_title,
                },
            )

    async def async_media_seek(self, position: float) -> None:
        """Send seek command."""
        self._attr_media_position = int(position)
        self._attr_media_position_updated_at = datetime.now()
        self.async_write_ha_state()
        _LOGGER.debug(f"Virtual media player '{self._attr_name}' seek to {position}s")

        # 触发模板更新事件
        if self._templates:
            self.hass.bus.async_fire(
                f"{DOMAIN}_media_player_template_update",
                {
                    "entity_id": self.entity_id,
                    "device_id": self._config_entry_id,
                    "action": "seek",
                    "position": position,
                },
            )

    async def async_play_media(self, media_type: str, media_id: str, **kwargs: Any) -> None:
        """Play a piece of media."""
        # 设置媒体信息
        self._attr_media_content_type = media_type
        self._attr_media_title = media_id
        self._attr_media_artist = "virtual_artist"
        self._attr_media_album_name = "virtual_album"
        self._attr_media_duration = random.randint(180, 300)  # 3-5分钟
        self._attr_media_position = 0
        self._attr_media_position_updated_at = datetime.now()
        self._attr_state = MediaPlayerState.PLAYING

        self.async_write_ha_state()
        _LOGGER.debug(f"Virtual media player '{self._attr_name}' playing media: {media_id}")

        # 触发模板更新事件
        if self._templates:
            self.hass.bus.async_fire(
                f"{DOMAIN}_media_player_template_update",
                {
                    "entity_id": self.entity_id,
                    "device_id": self._config_entry_id,
                    "action": "play_media",
                    "media_type": media_type,
                    "media_id": media_id,
                    "media_title": self._attr_media_title,
                },
            )

    async def async_select_source(self, source: str) -> None:
        """Select input source."""
        if source in self._attr_source_list:
            self._attr_source = source
            await self.async_save_state()
            self.async_write_ha_state()
            _LOGGER.debug(f"Virtual media player '{self._attr_name}' source changed to {source}")

            # 触发模板更新事件
            if self._templates:
                self.hass.bus.async_fire(
                    f"{DOMAIN}_media_player_template_update",
                    {
                        "entity_id": self.entity_id,
                        "device_id": self._config_entry_id,
                        "action": "select_source",
                        "source": source,
                    },
                )

    async def async_set_volume_level(self, volume: float) -> None:
        """Set volume level, range 0..1."""
        # 修复：添加音量范围验证 (0.0-1.0)
        original_volume = volume
        volume = max(0.0, min(1.0, volume))

        if abs(original_volume - volume) > 0.001:  # 浮点数精度比较
            _LOGGER.warning(
                f"Volume {original_volume} out of range (0.0-1.0), "
                f"clamped to {volume}"
            )

        self._attr_volume_level = volume

        # 修复：可选的静音逻辑 - 仅在音量>0且当前静音时取消静音
        if volume > 0 and self._attr_volume_muted:
            self._attr_volume_muted = False

        await self.async_save_state()
        self.async_write_ha_state()
        _LOGGER.debug(f"Virtual media player '{self._attr_name}' volume set to {volume}")

        # 触发模板更新事件
        if self._templates:
            self.hass.bus.async_fire(
                f"{DOMAIN}_media_player_template_update",
                {
                    "entity_id": self.entity_id,
                    "device_id": self._config_entry_id,
                    "action": "set_volume_level",
                    "volume": volume,
                },
            )

    async def async_mute_volume(self, mute: bool) -> None:
        """Mute (true) or unmute (false) media player."""
        self._attr_volume_muted = mute
        await self.async_save_state()
        self.async_write_ha_state()
        _LOGGER.debug(f"Virtual media player '{self._attr_name}' muted: {mute}")

        # 触发模板更新事件
        if self._templates:
            self.hass.bus.async_fire(
                f"{DOMAIN}_media_player_template_update",
                {
                    "entity_id": self.entity_id,
                    "device_id": self._config_entry_id,
                    "action": "mute_volume",
                    "mute": mute,
                },
            )

    async def async_set_repeat(self, repeat: str) -> None:
        """Set repeat mode."""
        self._attr_media_repeat = repeat
        await self.async_save_state()
        self.async_write_ha_state()
        _LOGGER.debug(f"Virtual media player '{self._attr_name}' repeat set to {repeat}")

        # 触发模板更新事件
        if self._templates:
            self.hass.bus.async_fire(
                f"{DOMAIN}_media_player_template_update",
                {
                    "entity_id": self.entity_id,
                    "device_id": self._config_entry_id,
                    "action": "set_repeat",
                    "repeat": repeat,
                },
            )

    async def async_set_shuffle(self, shuffle: bool) -> None:
        """Enable/disable shuffle mode."""
        self._attr_media_shuffle = shuffle
        if shuffle:
            random.shuffle(self._playlist)
        await self.async_save_state()
        self.async_write_ha_state()
        _LOGGER.debug(f"Virtual media player '{self._attr_name}' shuffle set to {shuffle}")

        # 触发模板更新事件
        if self._templates:
            self.hass.bus.async_fire(
                f"{DOMAIN}_media_player_template_update",
                {
                    "entity_id": self.entity_id,
                    "device_id": self._config_entry_id,
                    "action": "set_shuffle",
                    "shuffle": shuffle,
                },
            )

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
            self._attr_media_duration = random.randint(180, 300)  # 3-5分钟
            self._attr_media_position = 0

    async def async_update(self) -> None:
        """Update media player position."""
        if self._attr_state == MediaPlayerState.PLAYING and self._attr_media_position_updated_at:
            # 更新播放位置
            time_diff = (datetime.now() - self._attr_media_position_updated_at).total_seconds()
            new_position = self._attr_media_position + time_diff

            # 检查是否播放完成
            if new_position >= self._attr_media_duration:
                if self._attr_media_repeat == "one":
                    # 重复当前歌曲
                    self._attr_media_position = 0
                elif self._attr_media_repeat == "all" or not self._attr_media_repeat:
                    # 下一首
                    self._select_next_track()
                    if self._attr_state == MediaPlayerState.PLAYING:
                        self._attr_media_position = 0
                self._attr_media_position_updated_at = datetime.now()
            else:
                self._attr_media_position = int(new_position)

            self.async_write_ha_state()