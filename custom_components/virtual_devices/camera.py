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
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.storage import Store

STORAGE_VERSION = 1

from .const import (
    CONF_ENTITIES,
    CONF_ENTITY_NAME,
    CONF_CAMERA_MOTION_DETECTION,
    CONF_CAMERA_RECORDING,
    CONF_CAMERA_STREAM_SOURCE,
    DEVICE_TYPE_CAMERA,
    DOMAIN,
    TEMPLATE_ENABLED_DEVICE_TYPES,
)

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
    device_type = config_entry.data.get("device_type")

    # 只有摄像头类型的设备才设置摄像头实体
    if device_type != DEVICE_TYPE_CAMERA:
        return

    device_info = hass.data[DOMAIN][config_entry.entry_id]["device_info"]
    entities = []
    entities_config = config_entry.data.get(CONF_ENTITIES, [])

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
        # 必须先调用父类初始化
        super().__init__()

        self._config_entry_id = config_entry_id
        self._entity_config = entity_config
        self._index = index
        self._device_info = device_info
        self._hass = hass

        entity_name = entity_config.get(CONF_ENTITY_NAME, f"Camera_{index + 1}")
        self._attr_name = entity_name
        self._attr_unique_id = f"{config_entry_id}_camera_{index}"

        # 设置实体为可用
        self._attr_available = True

        # Template support
        self._templates = entity_config.get("templates", {})

        # 存储实体状态
        self._store = Store[dict[str, Any]](hass, STORAGE_VERSION, f"virtual_devices_camera_{config_entry_id}_{index}")

        # 摄像头类型 - 必须在调用_get_enhanced_device_info()之前设置
        camera_type = entity_config.get("camera_type", "indoor")
        self._camera_type = camera_type

        # 根据类型设置图标
        icon_map = {
            "indoor": "mdi:camera",
            "outdoor": "mdi:camera-outline",
            "doorbell": "mdi:doorbell-video",
            "ptz": "mdi:camera-iris",
            "baby_monitor": "mdi:baby-carriage",
        }
        self._attr_icon = icon_map.get(camera_type, "mdi:camera")

        # 支持的功能
        self._setup_features()

        # 初始化状态
        self._attr_is_recording = entity_config.get(CONF_CAMERA_RECORDING, False)
        self._attr_motion_detection_enabled = entity_config.get(CONF_CAMERA_MOTION_DETECTION, True)
        self._attr_is_streaming = False

        # 分辨率设置 - 必须在调用 _get_enhanced_device_info() 之前设置
        resolutions = {
            "indoor": (1920, 1080),
            "outdoor": (2560, 1440),
            "doorbell": (1920, 1080),
            "ptz": (3840, 2160),
            "baby_monitor": (1280, 720),
        }
        self._resolution = resolutions.get(camera_type, (1920, 1080))

        # PTZ控制（仅PTZ类型支持）
        self._ptz_enabled = camera_type == "ptz"
        self._pan = 0
        self._tilt = 0
        self._zoom = 1.0

        # 运动检测
        self._motion_detected = False
        self._last_motion_time = None

        # 夜视功能
        self._night_vision_enabled = entity_config.get("night_vision", True)
        self._ir_illumination_enabled = False

        # 音频功能
        self._audio_enabled = entity_config.get("audio", False)
        self._two_way_audio = entity_config.get("two_way_audio", False)

        # 摄像头参数
        self._attr_brand = "VirtualCam"
        self._attr_model_name = f"VC-{camera_type.upper()}-{index + 1:03d}"

        # 设置默认暴露给语音助手
        self._attr_entity_registry_enabled_default = True

    @property
    def should_expose(self) -> bool:
        """Return if this entity should be exposed to voice assistants."""
        return True
        self._attr_frontend_stream_type = "hls" if entity_config.get(CONF_CAMERA_STREAM_SOURCE) else None

        # 设置WebRTC提供者（必需属性）
        self._webrtc_provider = None

        # 设置设备信息（必须在所有属性设置后）
        self._attr_device_info = self._get_enhanced_device_info()
        
        _LOGGER.info(f"Virtual camera '{self._attr_name}' initialized (type: {camera_type}, available: {self._attr_available})")

    async def async_load_state(self) -> None:
        """Load saved state from storage."""
        try:
            data = await self._store.async_load()
            if data:
                self._attr_is_recording = data.get("is_recording", False)
                self._attr_motion_detection_enabled = data.get("motion_detection_enabled", True)
                self._attr_is_streaming = data.get("is_streaming", False)
                _LOGGER.info(f"Camera '{self._attr_name}' state loaded from storage")
        except Exception as ex:
            _LOGGER.error(f"Failed to load state for camera '{self._attr_name}': {ex}")

    async def async_save_state(self) -> None:
        """Save current state to storage."""
        try:
            data = {
                "is_recording": self._attr_is_recording,
                "motion_detection_enabled": self._attr_motion_detection_enabled,
                "is_streaming": self._attr_is_streaming,
            }
            await self._store.async_save(data)
        except Exception as ex:
            _LOGGER.error(f"Failed to save state for camera '{self._attr_name}': {ex}")

    async def async_added_to_hass(self) -> None:
        """Call when entity is added to hass."""
        await super().async_added_to_hass()
        await self.async_load_state()

        # 确保实体可用并立即更新状态
        self._attr_available = True
        self.async_write_ha_state()

        _LOGGER.info(f"Virtual camera '{self._attr_name}' added to Home Assistant and marked as available")

    def _get_enhanced_device_info(self) -> dict[str, Any]:
        """Get enhanced device information for camera."""
        from .const import CAMERA_TYPES

        base_info = self._device_info.copy()

        # 只添加有效的设备信息字段
        base_info.update({
            "model": self._attr_model_name,
            "manufacturer": self._attr_brand,
        })

        return base_info

    def _get_lens_type(self) -> str:
        """Get lens type based on camera type."""
        from .const import CAMERA_LENS_TYPES
        return CAMERA_LENS_TYPES.get(self._camera_type, "standard")

    def _get_night_vision_info(self) -> str:
        """Get night vision information."""
        if self._night_vision_enabled:
            return "infrared_night_vision_10m"
        else:
            return "no_night_vision"

    def _get_field_of_view(self) -> str:
        """Get field of view based on camera type."""
        fov_map = {
            "indoor": "110°",
            "outdoor": "85°",
            "doorbell": "180°",
            "ptz": "35°-130°",
            "baby_monitor": "95°",
        }
        return fov_map.get(self._camera_type, "90°")

    def _get_recording_format(self) -> str:
        """Get recording format based on camera type."""
        if self._camera_type in ["ptz", "outdoor"]:
            return "H.265"
        else:
            return "H.264"

    def _get_connectivity_info(self) -> str:
        """Get connectivity information."""
        connectivity = ["wi_fi"]
        if self._camera_type == "outdoor":
            connectivity.append("ethernet")
        if self._ptz_enabled:
            connectivity.append("ptz_control")
        return ", ".join(connectivity)

    def _get_storage_type(self) -> str:
        """Get storage type based on camera type."""
        from .const import CAMERA_STORAGE_TYPES
        return CAMERA_STORAGE_TYPES.get(self._camera_type, "local_storage")

    def _setup_features(self) -> None:
        """Setup supported features based on camera type."""
        features = CameraEntityFeature(0)

        # 基础功能
        features |= CameraEntityFeature.ON_OFF

        # 根据摄像头类型添加功能
        if self._camera_type in ["indoor", "outdoor", "ptz"]:
            features |= CameraEntityFeature.STREAM
            # CameraEntityFeature.MOTION_DETECT 不存在，移除此功能

        if self._camera_type == "ptz":
            # CameraEntityFeature.PAN, TILT, ZOOM 可能不存在，移除这些功能
            pass

        if self._entity_config.get("recording", False):
            # CameraEntityFeature.RECORDING 不存在，移除此功能
            pass

        if self._camera_type == "doorbell":
            # CameraEntityFeature.TALK 不存在，移除此功能
            pass

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
        if not PIL_AVAILABLE:
            # 如果PIL不可用，返回最小的有效JPEG图像（1x1像素的黑色图像）
            # 这是一个有效的JPEG图像，确保实体可用
            return b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9=82<.342\xff\xc0\x00\x11\x08\x00\x01\x00\x01\x01\x01\x11\x00\x02\x11\x01\x03\x11\x01\xff\xc4\x00\x14\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x08\xff\xc4\x00\x14\x10\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xaa\xff\xd9'

        try:
            image_bytes = await self.hass.async_add_executor_job(
                self._generate_image, width, height
            )
            # 确保返回有效的图像数据
            if image_bytes and len(image_bytes) > 0:
                return image_bytes
            else:
                _LOGGER.warning(f"Generated empty image for camera '{self._attr_name}', using fallback")
                # 返回最小有效JPEG
                return b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9=82<.342\xff\xc0\x00\x11\x08\x00\x01\x00\x01\x01\x01\x11\x00\x02\x11\x01\x03\x11\x01\xff\xc4\x00\x14\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x08\xff\xc4\x00\x14\x10\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xaa\xff\xd9'
        except Exception as e:
            _LOGGER.error(f"Error generating camera image: {e}")
            # 即使出错也返回最小有效JPEG，确保实体可用
            return b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9=82<.342\xff\xc0\x00\x11\x08\x00\x01\x00\x01\x01\x01\x11\x00\x02\x11\x01\x03\x11\x01\xff\xc4\x00\x14\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x08\xff\xc4\x00\x14\x10\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xaa\xff\xd9'

    def _generate_image(self, width: int | None = None, height: int | None = None) -> bytes:
        """Generate a virtual camera image."""
        if not PIL_AVAILABLE:
            # 返回最小的有效JPEG图像（1x1像素）
            return b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9=82<.342\xff\xc0\x00\x11\x08\x00\x01\x00\x01\x01\x01\x11\x00\x02\x11\x01\x03\x11\x01\xff\xc4\x00\x14\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x08\xff\xc4\x00\x14\x10\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xaa\xff\xd9'

        # 设置图像尺寸
        img_width, img_height = self._resolution
        if width and height:
            img_width, img_height = width, height

        # 创建基础图像
        image = Image.new("RGB", (img_width, img_height), color=(0, 0, 0))
        draw = ImageDraw.Draw(image)

        # 生成背景色（基于时间和摄像头类型）
        import time
        current_hour = int(time.strftime("%H"))

        if 6 <= current_hour <= 18:  # 白天
            if self._camera_type == "outdoor":
                bg_color = (135, 206, 235)  # 天蓝色
            else:
                bg_color = (240, 240, 240)  # 浅灰色
        else:  # 夜晚
            if self._night_vision_enabled:
                bg_color = (0, 50, 0)  # 深绿色（夜视）
            else:
                bg_color = (20, 20, 40)  # 深蓝色

        # 绘制背景
        draw.rectangle([0, 0, img_width, img_height], fill=bg_color)

        # 绘制摄像头信息
        try:
            # 尝试使用默认字体
            font = ImageFont.load_default()
        except:
            font = None

        # 绘制标题
        title_text = f"Virtual Camera - {self._camera_type.upper()}"
        title_position = (20, 20)
        if font:
            draw.text(title_position, title_text, fill=(255, 255, 255), font=font)

        # 绘制时间戳
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        timestamp_position = (20, img_height - 60)
        if font:
            draw.text(timestamp_position, timestamp, fill=(255, 255, 255), font=font)

        # 绘制状态信息
        status_y = 60
        status_lines = [
            f"Status: {'Recording' if self._attr_is_recording else 'Idle'}",
            f"Motion Detection: {'ON' if self._attr_motion_detection_enabled else 'OFF'}",
            f"Resolution: {img_width}x{img_height}",
            f"Night Vision: {'ON' if self._night_vision_enabled else 'OFF'}",
        ]

        if self._ptz_enabled:
            status_lines.extend([
                f"Pan: {self._pan}°",
                f"Tilt: {self._tilt}°",
                f"Zoom: {self._zoom:.1f}x",
            ])

        if self._motion_detected:
            status_lines.append("⚠ MOTION DETECTED")

        for line in status_lines:
            if font:
                draw.text((20, status_y), line, fill=(255, 255, 255), font=font)
            status_y += 25

        # 绘制模拟视频网格
        grid_color = (100, 100, 100)
        # 垂直线
        for x in range(0, img_width, 50):
            draw.line([(x, 0), (x, img_height)], fill=grid_color, width=1)
        # 水平线
        for y in range(0, img_height, 50):
            draw.line([(0, y), (img_width, y)], fill=grid_color, width=1)

        # 绘制中心十字线（瞄准线）
        center_x, center_y = img_width // 2, img_height // 2
        cross_color = (255, 0, 0) if self._motion_detected else (0, 255, 0)
        draw.line([(center_x - 20, center_y), (center_x + 20, center_y)], fill=cross_color, width=2)
        draw.line([(center_x, center_y - 20), (center_x, center_y + 20)], fill=cross_color, width=2)

        # Add some random "noise" to simulate real camera
        for _ in range(100):
            x = random.randint(0, img_width - 1)
            y = random.randint(0, img_height - 1)
            noise_color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
            draw.point((x, y), fill=noise_color)

        # 转换为字节
        img_bytes = io.BytesIO()
        image.save(img_bytes, format="JPEG")
        image_data = img_bytes.getvalue()
        
        # 确保返回的数据不为空
        if not image_data or len(image_data) == 0:
            _LOGGER.warning(f"Generated empty image for camera '{self._attr_name}', using fallback")
            # 返回最小有效JPEG
            return b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9=82<.342\xff\xc0\x00\x11\x08\x00\x01\x00\x01\x01\x01\x11\x00\x02\x11\x01\x03\x11\x01\xff\xc4\x00\x14\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x08\xff\xc4\x00\x14\x10\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xaa\xff\xd9'
        
        return image_data

    async def async_enable_motion_detection(self) -> None:
        """Enable motion detection."""
        self._attr_motion_detection_enabled = True
        await self.async_save_state()
        self.async_write_ha_state()
        _LOGGER.debug(f"Virtual camera '{self._attr_name}' motion detection enabled")

        # 触发模板更新事件
        if self._templates:
            self.hass.bus.async_fire(
                f"{DOMAIN}_camera_template_update",
                {
                    "entity_id": self.entity_id,
                    "device_id": self._config_entry_id,
                    "action": "enable_motion_detection",
                },
            )

    async def async_disable_motion_detection(self) -> None:
        """Disable motion detection."""
        self._attr_motion_detection_enabled = False
        self._motion_detected = False
        await self.async_save_state()
        self.async_write_ha_state()
        _LOGGER.debug(f"Virtual camera '{self._attr_name}' motion detection disabled")

        # 触发模板更新事件
        if self._templates:
            self.hass.bus.async_fire(
                f"{DOMAIN}_camera_template_update",
                {
                    "entity_id": self.entity_id,
                    "device_id": self._config_entry_id,
                    "action": "disable_motion_detection",
                },
            )

    async def async_turn_on(self) -> None:
        """Turn on camera."""
        self._attr_is_streaming = True
        await self.async_save_state()
        self.async_write_ha_state()
        _LOGGER.debug(f"Virtual camera '{self._attr_name}' turned on")

        # 触发模板更新事件
        if self._templates:
            self.hass.bus.async_fire(
                f"{DOMAIN}_camera_template_update",
                {
                    "entity_id": self.entity_id,
                    "device_id": self._config_entry_id,
                    "action": "turn_on",
                },
            )

    async def async_turn_off(self) -> None:
        """Turn off camera."""
        self._attr_is_streaming = False
        self._attr_is_recording = False
        await self.async_save_state()
        self.async_write_ha_state()
        _LOGGER.debug(f"Virtual camera '{self._attr_name}' turned off")

        # 触发模板更新事件
        if self._templates:
            self.hass.bus.async_fire(
                f"{DOMAIN}_camera_template_update",
                {
                    "entity_id": self.entity_id,
                    "device_id": self._config_entry_id,
                    "action": "turn_off",
                },
            )

    async def async_enable_recording(self) -> None:
        """Enable recording."""
        self._attr_is_recording = True
        await self.async_save_state()
        self.async_write_ha_state()
        _LOGGER.debug(f"Virtual camera '{self._attr_name}' recording started")

        # 触发模板更新事件
        if self._templates:
            self.hass.bus.async_fire(
                f"{DOMAIN}_camera_template_update",
                {
                    "entity_id": self.entity_id,
                    "device_id": self._config_entry_id,
                    "action": "start_recording",
                },
            )

    async def async_disable_recording(self) -> None:
        """Disable recording."""
        self._attr_is_recording = False
        await self.async_save_state()
        self.async_write_ha_state()
        _LOGGER.debug(f"Virtual camera '{self._attr_name}' recording stopped")

        # 触发模板更新事件
        if self._templates:
            self.hass.bus.async_fire(
                f"{DOMAIN}_camera_template_update",
                {
                    "entity_id": self.entity_id,
                    "device_id": self._config_entry_id,
                    "action": "stop_recording",
                },
            )

    async def async_ptz_pan(self, tilt: float) -> None:
        """Pan the camera."""
        if self._ptz_enabled:
            self._pan = max(-180, min(180, self._pan + tilt))
            self.async_write_ha_state()
            _LOGGER.debug(f"Virtual camera '{self._attr_name}' panned to {self._pan}°")

            # 触发模板更新事件
            if self._templates:
                self.hass.bus.async_fire(
                    f"{DOMAIN}_camera_template_update",
                    {
                        "entity_id": self.entity_id,
                        "device_id": self._config_entry_id,
                        "action": "ptz_pan",
                        "pan": self._pan,
                    },
                )

    async def async_ptz_tilt(self, pan: float) -> None:
        """Tilt the camera."""
        if self._ptz_enabled:
            self._tilt = max(-90, min(90, self._tilt + pan))
            self.async_write_ha_state()
            _LOGGER.debug(f"Virtual camera '{self._attr_name}' tilted to {self._tilt}°")

            # 触发模板更新事件
            if self._templates:
                self.hass.bus.async_fire(
                    f"{DOMAIN}_camera_template_update",
                    {
                        "entity_id": self.entity_id,
                        "device_id": self._config_entry_id,
                        "action": "ptz_tilt",
                        "tilt": self._tilt,
                    },
                )

    async def async_ptz_zoom(self, zoom: float) -> None:
        """Zoom the camera."""
        if self._ptz_enabled:
            self._zoom = max(1.0, min(10.0, zoom))
            self.async_write_ha_state()
            _LOGGER.debug(f"Virtual camera '{self._attr_name}' zoomed to {self._zoom}x")

            # 触发模板更新事件
            if self._templates:
                self.hass.bus.async_fire(
                    f"{DOMAIN}_camera_template_update",
                    {
                        "entity_id": self.entity_id,
                        "device_id": self._config_entry_id,
                        "action": "ptz_zoom",
                        "zoom": self._zoom,
                    },
                )

    async def async_update(self) -> None:
        """Update camera state."""
        import time

        # 模拟运动检测
        if self._attr_motion_detection_enabled and self._attr_is_streaming:
            # 随机检测到运动（小概率）
            if random.random() < 0.05:  # 5% 概率检测到运动
                self._motion_detected = True
                self._last_motion_time = time.time()

                # 触发运动检测事件
                self.hass.bus.async_fire(
                    f"{DOMAIN}_camera_motion_detected",
                    {
                        "entity_id": self.entity_id,
                        "device_id": self._config_entry_id,
                        "timestamp": self._last_motion_time,
                    },
                )
            else:
                # 运动状态在5秒后自动清除
                if self._motion_detected and self._last_motion_time and (time.time() - self._last_motion_time) > 5:
                    self._motion_detected = False

        # 夜视功能自动切换
        current_hour = int(time.strftime("%H"))
        night_vision_should_be_on = current_hour < 6 or current_hour > 18
        if self._night_vision_enabled and night_vision_should_be_on != self._ir_illumination_enabled:
            self._ir_illumination_enabled = night_vision_should_be_on

        self.async_write_ha_state()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        from .const import CAMERA_TYPES

        attrs = {
            "camera_type": CAMERA_TYPES.get(self._camera_type, self._camera_type),
            "resolution": f"{self._resolution[0]}x{self._resolution[1]}",
            "lens_type": self._get_lens_type(),
            "night_vision_enabled": self._night_vision_enabled,
            "ir_illumination_enabled": self._ir_illumination_enabled,
            "night_vision_capability": self._get_night_vision_info(),
            "field_of_view": self._get_field_of_view(),
            "motion_detected": self._motion_detected,
            "is_streaming": self._attr_is_streaming,
            "audio_enabled": self._audio_enabled,
            "two_way_audio": self._two_way_audio,
            "is_recording": self._attr_is_recording,
            "recording_format": self._get_recording_format(),
            "connectivity": self._get_connectivity_info(),
            "storage_type": self._get_storage_type(),
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