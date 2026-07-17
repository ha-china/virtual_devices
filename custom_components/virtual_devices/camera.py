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
    DEVICE_TYPE_DOORBELL,
    DOMAIN,
)
from .appliance import get_appliance_bundles
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

    if device_type not in (DEVICE_TYPE_CAMERA, DEVICE_TYPE_DOORBELL):
        return

    device_info: DeviceInfo = hass.data[DOMAIN][config_entry.entry_id]["device_info"]
    entities: list[VirtualCamera] = []
    entities_config: list[CameraEntityConfig] = config_entry.data.get(CONF_ENTITIES, [])

    if device_type == DEVICE_TYPE_DOORBELL and not entities_config:
        for bundle in get_appliance_bundles(hass, config_entry.entry_id):
            entities_config.append({
                CONF_ENTITY_NAME: f"{bundle.base_name} Camera",
                "camera_type": "doorbell",
                "motion_detection": True,
                "recording": False,
                "night_vision": True,
            })

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

        # Animation state for the simulated video feed.
        # `_current_frame` is the latest rendered JPEG, refreshed by
        # `async_update` at ~2 fps. `async_camera_image` returns it directly
        # so the HA frontend sees an animated feed without external ffmpeg.
        self._current_frame: bytes | None = None
        self._last_frame_time: float = 0.0
        self._frame_tick: int = 0
        # Simulated actors (people / cars) wandering in the scene.
        # Each entry: {x, y, vx, vy, kind, size}
        self._actors: list[dict[str, Any]] = []
        self._init_actors()

        # Night vision
        self._night_vision_enabled: bool = entity_config.get("night_vision", True)
        self._ir_illumination_enabled: bool = False

        # Audio features
        self._audio_enabled: bool = entity_config.get("audio", False)
        self._two_way_audio: bool = entity_config.get("two_way_audio", False)

        # Camera parameters. HA Core `Camera.model` cached_property reads
        # `self._attr_model` (NOT `_attr_model_name`).
        self._attr_brand: str = "VirtualCam"
        self._attr_model: str = f"VC-{camera_type.upper()}-{index + 1:03d}"

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

    def _init_actors(self) -> None:
        """Initialize simulated moving objects (people / cars) for the feed.

        The scene is drawn on a 640x480 canvas regardless of the reported
        `_resolution` (which only affects the advertised stream resolution);
        the rendered JPEG is scaled up if the caller requests larger frames.
        """
        w, h = 640, 480
        rng = random.Random(hash(self._attr_unique_id or "") & 0xFFFFFFFF)
        # 1-2 walking people + occasionally 1 car for outdoor/doorbell/ptz
        actor_count = 1 if self._camera_type == "baby_monitor" else 2
        self._actors = []
        for _ in range(actor_count):
            self._actors.append({
                "x": rng.uniform(60, w - 60),
                "y": rng.uniform(h * 0.5, h - 80),
                "vx": rng.choice([-1, 1]) * rng.uniform(0.5, 1.8),
                "vy": rng.uniform(-0.3, 0.3),
                "kind": "person",
                "size": rng.randint(18, 26),
                "color": (rng.randint(40, 200), rng.randint(40, 200), rng.randint(40, 200)),
            })
        if self._camera_type in ("outdoor", "doorbell", "ptz"):
            self._actors.append({
                "x": rng.choice([20, w - 20]),
                "y": h - 50,
                "vx": (1 if rng.random() > 0.5 else -1) * rng.uniform(2.0, 3.5),
                "vy": 0.0,
                "kind": "car",
                "size": 40,
                "color": (rng.randint(40, 200), rng.randint(40, 200), rng.randint(40, 200)),
            })

    def _advance_actors(self) -> None:
        """Advance the simulated actors by one frame (bounce off edges)."""
        w, h = 640, 480
        for actor in self._actors:
            actor["x"] += actor["vx"]
            actor["y"] += actor["vy"]
            # Vertical jitter
            actor["vy"] += random.uniform(-0.05, 0.05)
            actor["vy"] = max(-0.6, min(0.6, actor["vy"]))
            size = actor["size"]
            # Bounce horizontally -> reverse direction so the actor stays on screen
            if actor["x"] < size:
                actor["x"] = size
                actor["vx"] = abs(actor["vx"])
            elif actor["x"] > w - size:
                actor["x"] = w - size
                actor["vx"] = -abs(actor["vx"])
            if actor["y"] < h * 0.45:
                actor["y"] = h * 0.45
                actor["vy"] = abs(actor["vy"])
            elif actor["y"] > h - size:
                actor["y"] = h - size
                actor["vy"] = -abs(actor["vy"])

    async def async_camera_image(
        self, width: int | None = None, height: int | None = None
    ) -> bytes | None:
        """Return bytes of camera image.

        Returns the latest cached animated frame if available; otherwise
        renders a fresh frame on demand. The cache is refreshed by
        `async_update` at ~2 fps so the HA frontend sees a moving feed.
        """
        # Minimal valid JPEG fallback (1x1 pixel) used if PIL is unavailable
        # or rendering fails.
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

        # If a caller asks for a specific size, render on demand (snapshot path).
        # Otherwise return the cached animated frame.
        if width is None and height is None and self._current_frame:
            return self._current_frame

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
        """Generate a virtual camera image with animated moving actors.

        The scene is always drawn on a 640x480 canvas (kept small for low CPU
        overhead) and then resized to the caller-requested dimensions. Moving
        actors (people / cars) are drawn at their current positions, which are
        advanced by `_advance_actors` once per frame tick.
        """
        import time

        canvas_w, canvas_h = 640, 480
        image = Image.new("RGB", (canvas_w, canvas_h), color=(0, 0, 0))
        draw = ImageDraw.Draw(image)

        # Background: day/night + camera type
        current_hour = int(time.strftime("%H"))
        is_night = not (6 <= current_hour <= 18)
        if is_night and self._night_vision_enabled:
            sky_color = (0, 30, 0)
            ground_color = (0, 50, 0)
        elif self._camera_type == "outdoor":
            sky_color = (135, 206, 235) if not is_night else (20, 30, 60)
            ground_color = (60, 110, 60) if not is_night else (20, 35, 25)
        else:
            sky_color = (240, 240, 240) if not is_night else (30, 30, 50)
            ground_color = (180, 180, 170) if not is_night else (35, 35, 45)

        # Sky / ceiling
        draw.rectangle([0, 0, canvas_w, canvas_h * 2 // 3], fill=sky_color)
        # Ground / floor
        draw.rectangle([0, canvas_h * 2 // 3, canvas_w, canvas_h], fill=ground_color)
        # Horizon line
        draw.line([(0, canvas_h * 2 // 3), (canvas_w, canvas_h * 2 // 3)],
                  fill=(80, 80, 80), width=1)

        try:
            font = ImageFont.load_default()
        except BaseException:
            font = None

        # Draw moving actors (people / cars)
        for actor in self._actors:
            x = int(actor["x"])
            y = int(actor["y"])
            size = int(actor["size"])
            color = actor["color"]
            # Motion blur trail
            trail_dx = -int(actor["vx"] * 4)
            draw.line([(x + trail_dx, y), (x, y)], fill=color, width=max(2, size // 6))
            if actor["kind"] == "person":
                # Head
                draw.ellipse([x - size // 3, y - size, x + size // 3, y - size // 2],
                             fill=color)
                # Body (trapezoid via rectangle)
                body_top_y = y - size // 2
                draw.rectangle([x - size // 2, body_top_y, x + size // 2, y + size // 2],
                               fill=color)
                # Legs (walking alternation based on tick)
                leg_swing = (self._frame_tick // 6) % 2 == 0
                leg_off = size // 4 if leg_swing else -size // 4
                draw.line([(x, y + size // 2), (x - size // 3 + leg_off, y + size)],
                          fill=color, width=max(2, size // 5))
                draw.line([(x, y + size // 2), (x + size // 3 - leg_off, y + size)],
                          fill=color, width=max(2, size // 5))
            else:  # car
                # Body
                draw.rectangle([x - size, y - size // 2, x + size, y + size // 4],
                               fill=color)
                # Wheels
                wheel_color = (20, 20, 20)
                wheel_r = size // 4
                draw.ellipse([x - size + wheel_r, y + size // 4 - wheel_r,
                              x - size + 3 * wheel_r, y + size // 4 + wheel_r],
                             fill=wheel_color)
                draw.ellipse([x + size - 3 * wheel_r, y + size // 4 - wheel_r,
                              x + size - wheel_r, y + size // 4 + wheel_r],
                             fill=wheel_color)
                # Windows
                win_color = (120, 180, 220) if not is_night else (40, 60, 80)
                direction = 1 if actor["vx"] >= 0 else -1
                draw.polygon([
                    (x + direction * size // 4, y - size // 3),
                    (x + direction * size, y - size // 3),
                    (x + direction * size * 3 // 4, y - size // 2 + 2),
                    (x + direction * size // 2, y - size // 2 + 2),
                ], fill=win_color)

        # Center crosshair
        center_x, center_y = canvas_w // 2, canvas_h // 2
        cross_color = (255, 0, 0) if self._motion_detected else (0, 255, 0)
        draw.line([(center_x - 20, center_y), (center_x + 20, center_y)],
                  fill=cross_color, width=2)
        draw.line([(center_x, center_y - 20), (center_x, center_y + 20)],
                  fill=cross_color, width=2)

        # Scanning line (animated, moves top to bottom)
        scan_y = (self._frame_tick * 8) % canvas_h
        scan_color = (0, 255, 255, 80) if not is_night else (180, 255, 180, 80)
        try:
            # `draw.line` ignores alpha; emulate via thin translucent overlay
            draw.line([(0, scan_y), (canvas_w, scan_y)], fill=(0, 255, 255), width=2)
        except Exception:
            pass

        # HUD: title + timestamp + status
        title_text = f"Virtual Camera - {self._camera_type.upper()}"
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        if font:
            draw.text((20, 20), title_text, fill=(255, 255, 255), font=font)
            draw.text((20, canvas_h - 30), timestamp, fill=(255, 255, 255), font=font)
        status_lines = [
            f"Status: {'Recording' if self._attr_is_recording else 'Idle'}",
            f"Motion: {'ON' if self._attr_motion_detection_enabled else 'OFF'}"
            + (f" [DETECTED]" if self._motion_detected else ""),
            f"Night Vision: {'ON' if self._ir_illumination_enabled else 'OFF'}",
        ]
        status_y = 50
        for line in status_lines:
            if font:
                draw.text((20, status_y), line, fill=(255, 255, 255), font=font)
            status_y += 20

        # Recording indicator (blinking red dot, top-right)
        if self._attr_is_recording and (self._frame_tick // 15) % 2 == 0:
            draw.ellipse([canvas_w - 40, 20, canvas_w - 20, 40], fill=(255, 0, 0))
            if font:
                draw.text((canvas_w - 60, 45), "REC", fill=(255, 0, 0), font=font)

        # Sparse noise (camera sensor simulation)
        noise_count = 60 if not is_night else 120
        for _ in range(noise_count):
            x = random.randint(0, canvas_w - 1)
            y = random.randint(0, canvas_h - 1)
            if is_night:
                noise_color = (random.randint(0, 80), random.randint(80, 160), random.randint(0, 80))
            else:
                noise_color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
            draw.point((x, y), fill=noise_color)

        # Scale to the caller-requested size, if any
        out_w, out_h = canvas_w, canvas_h
        if width and height and (width != canvas_w or height != canvas_h):
            try:
                image = image.resize((width, height))
                out_w, out_h = width, height
            except Exception as e:
                _LOGGER.debug(f"Camera '{self._attr_name}' resize failed: {e}")

        img_bytes = io.BytesIO()
        image.save(img_bytes, format="JPEG", quality=85)
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
        """Update camera state and refresh the animated frame cache.

        HA polls cameras every ~30s by default; the cached frame is also
        refreshed on demand when the frontend requests a snapshot. To keep the
        feed visibly animated we additionally schedule a ~2 fps self-refresh
        via `hass.loop.call_later` once the entity is streaming.
        """
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

        # Refresh animated frame (throttled to ~2 fps = every 0.5s)
        now = time.time()
        if PIL_AVAILABLE and now - self._last_frame_time >= 0.5:
            self._last_frame_time = now
            self._frame_tick += 1
            self._advance_actors()
            try:
                frame = await self.hass.async_add_executor_job(self._generate_image)
                if frame:
                    self._current_frame = frame
                    # Push the new frame to subscribers so the HA frontend
                    # video element refreshes immediately.
                    self.async_write_ha_state()
            except Exception as e:
                _LOGGER.error(f"Error generating animated frame for '{self._attr_name}': {e}")

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
