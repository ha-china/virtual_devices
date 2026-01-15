"""Platform for virtual camera integration."""
from __future__ import annotations

import logging
import random
from typing import Any

from homeassistant.components.camera import (
    Camera,
    CameraEntityFeature,
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
    CONF_CAMERA_MOTION_DETECTION,
    CONF_CAMERA_RECORDING,
    DEVICE_TYPE_CAMERA,
    DOMAIN,
)
from .types import CameraEntityConfig, CameraState

_LOGGER = logging.getLogger(__name__)

try:
    import io
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    _LOGGER.warning("PIL (Pillow) not available, camera images will not be generated")


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up virtual camera entities."""
    device_type: str | None = config_entry.data.get("device_type")

    if device_type != DEVICE_TYPE_CAMERA:
        return

    device_info: DeviceInfo = hass.data[DOMAIN][config_entry.entry_id]["device_info"]
    entities: list[VirtualCamera] = []
    entities_config: list[CameraEntityConfig] = config_entry.data.get(CONF_ENTITIES, [])

    for idx, entity_config in enumerate(entities_config):
        entity = VirtualCamera(
            hass,
            config_entry.entry_id,
            entity_config,
            idx,
            device_info,
        )
        entities.append(entity)

    async_add_entities(entities)


class VirtualCamera(Camera):
    """Representation of a virtual camera.

    This entity implements state persistence using the same pattern as BaseVirtualEntity.
    """

    _attr_should_poll: bool = True
    _attr_entity_registry_enabled_default: bool = True

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry_id: str,
        entity_config: CameraEntityConfig,
        index: int,
        device_info: DeviceInfo,
    ) -> None:
        """Initialize the virtual camera."""
        super().__init__()

        self._hass = hass
        self._config_entry_id = config_entry_id
        self._entity_config = entity_config
        self._index = index

        entity_name: str = entity_config.get(CONF_ENTITY_NAME, f"Camera_{index + 1}")
        self._attr_name = entity_name
        self._attr_unique_id = f"{config_entry_id}_camera_{index}"
        self._attr_available = True

        # Template support
        self._templates: dict[str, Any] = entity_config.get("templates", {})

        # Storage for state persistence
        self._store: Store[CameraState] = Store(
            hass, STORAGE_VERSION, f"virtual_devices_camera_{config_entry_id}_{index}"
        )

        # Camera type
        camera_type: str = entity_config.get("camera_type", "indoor")
        self._camera_type = camera_type

        # Set icon based on type
        icon_map: dict[str, str] = {
            "indoor": "mdi:camera",
            "outdoor": "mdi:camera-outline",
            "doorbell": "mdi:doorbell-video",
            "ptz": "mdi:camera-iris",
            "baby_monitor": "mdi:baby-carriage",
        }
        self._attr_icon = icon_map.get(camera_type, "mdi:camera")

        # Setup supported features
        self._setup_features()

        # Initialize state
        self._attr_is_recording: bool = entity_config.get(CONF_CAMERA_RECORDING, False)
        self._attr_motion_detection_enabled: bool = entity_config.get(CONF_CAMERA_MOTION_DETECTION, True)
        self._attr_is_streaming: bool = False

        # Resolution settings
        resolutions: dict[str, tuple[int, int]] = {
            "indoor": (1920, 1080),
            "outdoor": (2560, 1440),
            "doorbell": (1920, 1080),
            "ptz": (3840, 2160),
            "baby_monitor": (1280, 720),
        }
        self._resolution: tuple[int, int] = resolutions.get(camera_type, (1920, 1080))

        # PTZ control (only PTZ type supports)
        self._ptz_enabled: bool = camera_type == "ptz"
        self._pan: int = 0
        self._tilt: int = 0
        self._zoom: float = 1.0

        # Motion detection
        self._motion_detected: bool = False
        self._last_motion_time: float | None = None

        # Night vision
        self._night_vision_enabled: bool = entity_config.get("night_vision", True)
        self._ir_illumination_enabled: bool = False

        # Audio features
        self._audio_enabled: bool = entity_config.get("audio", False)
        self._two_way_audio: bool = entity_config.get("two_way_audio", False)

        # Camera parameters
        self._attr_brand: str = "VirtualCam"
        self._attr_model_name: str = f"VC-{camera_type.upper()}-{index + 1:03d}"

        # Set device info
        self._attr_device_info = device_info

        _LOGGER.info(f"Virtual camera '{self._attr_name}' initialized (type: {camera_type})")

    def get_default_state(self) -> CameraState:
        """Return the default state for this entity type."""
        return {
            "is_recording": False,
            "is_streaming": False,
            "motion_detection_enabled": True,
        }

    def apply_state(self, state: CameraState) -> None:
        """Apply loaded state to entity attributes."""
        self._attr_is_recording = state.get("is_recording", False)
        self._attr_motion_detection_enabled = state.get("motion_detection_enabled", True)
        self._attr_is_streaming = state.get("is_streaming", False)

    def get_current_state(self) -> CameraState:
        """Get current state for persistence."""
        return {
            "is_recording": self._attr_is_recording,
            "is_streaming": self._attr_is_streaming,
            "motion_detection_enabled": self._attr_motion_detection_enabled,
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
                _LOGGER.debug(f"Camera '{self._attr_name}' state loaded from storage")
        except Exception as ex:
            _LOGGER.error(f"Failed to load state for camera '{self._attr_name}': {ex}")
            self.apply_state(self.get_default_state())

    async def async_save_state(self) -> None:
        """Save current state to storage."""
        try:
            data = self.get_current_state()
            await self._store.async_save(data)
            _LOGGER.debug(f"Camera '{self._attr_name}' state saved to storage")
        except Exception as ex:
            _LOGGER.error(f"Failed to save state for camera '{self._attr_name}': {ex}")

    async def async_added_to_hass(self) -> None:
        """Call when entity is added to hass."""
        await super().async_added_to_hass()
        await self.async_load_state()
        self._attr_available = True
        self.async_write_ha_state()
        _LOGGER.info(f"Virtual camera '{self._attr_name}' added to Home Assistant")

    def fire_template_event(self, action: str, **kwargs: Any) -> None:
        """Fire a template update event if templates are configured."""
        if self._templates:
            self._hass.bus.async_fire(
                f"{DOMAIN}_camera_template_update",
                {
                    "entity_id": self.entity_id,
                    "device_id": self._config_entry_id,
                    "action": action,
                    **kwargs,
                },
            )

    def _setup_features(self) -> None:
        """Setup supported features based on camera type."""
        features: CameraEntityFeature = CameraEntityFeature(0)
        features |= CameraEntityFeature.ON_OFF

        if self._camera_type in ["indoor", "outdoor", "ptz"]:
            features |= CameraEntityFeature.STREAM

        self._attr_supported_features = features

    @property
    def is_recording(self) -> bool:
        """Return true if the camera is recording."""
        return self._attr_is_recording

    @property
    def motion_detection_enabled(self) -> bool:
        """Return the camera motion detection status."""
        return self._attr_motion_detection_enabled

    @property
    def brand(self) -> str | None:
        """Return the camera brand."""
        return self._attr_brand

    @property
    def model(self) -> str | None:
        """Return the camera model."""
        return self._attr_model_name

    async def async_camera_image(
        self, width: int | None = None, height: int | None = None
    ) -> bytes | None:
        """Return bytes of camera image."""
        # Minimal valid JPEG fallback
        minimal_jpeg: bytes = (
            b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00'
            b'\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t'
            b'\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a'
            b'\x1f\x1e\x1d\x1a\x1c\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9=82<.342'
            b'\xff\xc0\x00\x11\x08\x00\x01\x00\x01\x01\x01\x11\x00\x02\x11\x01'
            b'\x03\x11\x01\xff\xc4\x00\x14\x00\x01\x00\x00\x00\x00\x00\x00\x00'
            b'\x00\x00\x00\x00\x00\x00\x00\x00\x08\xff\xc4\x00\x14\x10\x01\x00'
            b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
            b'\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xaa\xff\xd9'
        )

        if not PIL_AVAILABLE:
            return minimal_jpeg

        try:
            image_bytes = await self.hass.async_add_executor_job(
                self._generate_image, width, height
            )
            if image_bytes and len(image_bytes) > 0:
                return image_bytes
            return minimal_jpeg
        except Exception as e:
            _LOGGER.error(f"Error generating camera image: {e}")
            return minimal_jpeg

    def _generate_image(self, width: int | None = None, height: int | None = None) -> bytes:
        """Generate a virtual camera image."""
        import time

        img_width, img_height = self._resolution
        if width and height:
            img_width, img_height = width, height

        image = Image.new("RGB", (img_width, img_height), color=(0, 0, 0))
        draw = ImageDraw.Draw(image)

        # Generate background color based on time and camera type
        current_hour = int(time.strftime("%H"))
        if 6 <= current_hour <= 18:
            bg_color = (135, 206, 235) if self._camera_type == "outdoor" else (240, 240, 240)
        else:
            bg_color = (0, 50, 0) if self._night_vision_enabled else (20, 20, 40)

        draw.rectangle([0, 0, img_width, img_height], fill=bg_color)

        try:
            font = ImageFont.load_default()
        except BaseException:
            font = None

        # Draw title
        title_text = f"Virtual Camera - {self._camera_type.upper()}"
        if font:
            draw.text((20, 20), title_text, fill=(255, 255, 255), font=font)

        # Draw timestamp
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        if font:
            draw.text((20, img_height - 60), timestamp, fill=(255, 255, 255), font=font)

        # Draw status info
        status_y = 60
        status_lines = [
            f"Status: {'Recording' if self._attr_is_recording else 'Idle'}",
            f"Motion Detection: {'ON' if self._attr_motion_detection_enabled else 'OFF'}",
            f"Resolution: {img_width}x{img_height}",
        ]

        for line in status_lines:
            if font:
                draw.text((20, status_y), line, fill=(255, 255, 255), font=font)
            status_y += 25

        # Draw grid
        grid_color = (100, 100, 100)
        for x in range(0, img_width, 50):
            draw.line([(x, 0), (x, img_height)], fill=grid_color, width=1)
        for y in range(0, img_height, 50):
            draw.line([(0, y), (img_width, y)], fill=grid_color, width=1)

        # Draw center crosshair
        center_x, center_y = img_width // 2, img_height // 2
        cross_color = (255, 0, 0) if self._motion_detected else (0, 255, 0)
        draw.line([(center_x - 20, center_y), (center_x + 20, center_y)], fill=cross_color, width=2)
        draw.line([(center_x, center_y - 20), (center_x, center_y + 20)], fill=cross_color, width=2)

        # Add noise
        for _ in range(100):
            x = random.randint(0, img_width - 1)
            y = random.randint(0, img_height - 1)
            noise_color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
            draw.point((x, y), fill=noise_color)

        img_bytes = io.BytesIO()
        image.save(img_bytes, format="JPEG")
        return img_bytes.getvalue()

    async def async_enable_motion_detection(self) -> None:
        """Enable motion detection."""
        self._attr_motion_detection_enabled = True
        await self.async_save_state()
        self.async_write_ha_state()
        _LOGGER.debug(f"Virtual camera '{self._attr_name}' motion detection enabled")
        self.fire_template_event("enable_motion_detection")

    async def async_disable_motion_detection(self) -> None:
        """Disable motion detection."""
        self._attr_motion_detection_enabled = False
        self._motion_detected = False
        await self.async_save_state()
        self.async_write_ha_state()
        _LOGGER.debug(f"Virtual camera '{self._attr_name}' motion detection disabled")
        self.fire_template_event("disable_motion_detection")

    async def async_turn_on(self) -> None:
        """Turn on camera."""
        self._attr_is_streaming = True
        await self.async_save_state()
        self.async_write_ha_state()
        _LOGGER.debug(f"Virtual camera '{self._attr_name}' turned on")
        self.fire_template_event("turn_on")

    async def async_turn_off(self) -> None:
        """Turn off camera."""
        self._attr_is_streaming = False
        self._attr_is_recording = False
        await self.async_save_state()
        self.async_write_ha_state()
        _LOGGER.debug(f"Virtual camera '{self._attr_name}' turned off")
        self.fire_template_event("turn_off")

    async def async_update(self) -> None:
        """Update camera state."""
        import time

        # Simulate motion detection
        if self._attr_motion_detection_enabled and self._attr_is_streaming:
            if random.random() < 0.05:
                self._motion_detected = True
                self._last_motion_time = time.time()
                self._hass.bus.async_fire(
                    f"{DOMAIN}_camera_motion_detected",
                    {
                        "entity_id": self.entity_id,
                        "device_id": self._config_entry_id,
                        "timestamp": self._last_motion_time,
                    },
                )
            elif self._motion_detected and self._last_motion_time:
                if (time.time() - self._last_motion_time) > 5:
                    self._motion_detected = False

        # Auto night vision
        current_hour = int(time.strftime("%H"))
        night_vision_should_be_on = current_hour < 6 or current_hour > 18
        if self._night_vision_enabled and night_vision_should_be_on != self._ir_illumination_enabled:
            self._ir_illumination_enabled = night_vision_should_be_on

        self.async_write_ha_state()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        from .const import CAMERA_TYPES

        attrs: dict[str, Any] = {
            "camera_type": CAMERA_TYPES.get(self._camera_type, self._camera_type),
            "resolution": f"{self._resolution[0]}x{self._resolution[1]}",
            "night_vision_enabled": self._night_vision_enabled,
            "ir_illumination_enabled": self._ir_illumination_enabled,
            "motion_detected": self._motion_detected,
            "is_streaming": self._attr_is_streaming,
            "audio_enabled": self._audio_enabled,
            "two_way_audio": self._two_way_audio,
            "is_recording": self._attr_is_recording,
        }

        if self._ptz_enabled:
            attrs.update({
                "ptz_enabled": True,
                "pan": f"{self._pan}°",
                "tilt": f"{self._tilt}°",
                "zoom": f"{self._zoom:.1f}x",
            })

        if self._last_motion_time:
            attrs["last_motion_time"] = f"{self._last_motion_time}"

        return attrs
