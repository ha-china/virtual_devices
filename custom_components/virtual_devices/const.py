"""Constants for the Virtual Devices Multi integration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from homeassistant.const import EntityCategory

DOMAIN = "virtual_devices"
MANUFACTURER = "Home Assistant China (unofficial)"
MODEL = "Virtual Device"

# 配置键名
CONF_DEVICE_NAME = "device_name"
CONF_DEVICE_TYPE = "device_type"
CONF_ENTITY_COUNT = "entity_count"
CONF_ENTITIES = "entities"
CONF_ENTITY_NAME = "entity_name"
CONF_ENTITY_TYPE = "entity_type"
CONF_ENTITY_ID_SUFFIX = "entity_id_suffix"
CONF_LAUNDRY_MODE = "laundry_mode"
CONF_CYCLE_DURATION_MINUTES = "cycle_duration_minutes"
CONF_SUPPORTS_PAUSE = "supports_pause"
CONF_SIREN_TONE = "siren_tone"
CONF_SIREN_DURATION = "siren_duration"
CONF_SIREN_VOLUME = "siren_volume"
CONF_ALARM_CODE = "alarm_code"
CONF_ALARM_TRIGGER_TIME = "alarm_trigger_time"
CONF_SUPPORTS_ARM_NIGHT = "supports_arm_night"
CONF_SUPPORTS_ARM_VACATION = "supports_arm_vacation"
CONF_REMOTE_ACTIVITY = "remote_activity"
CONF_REMOTE_COMMANDS = "remote_commands"
CONF_MOWER_ZONE = "mower_zone"
CONF_MOWER_CUTTING_HEIGHT = "mower_cutting_height"
CONF_APPLIANCE_PROGRAM = "appliance_program"
CONF_DELAY_START_MINUTES = "delay_start_minutes"
CONF_FRIDGE_TEMPERATURE = "fridge_temperature"
CONF_FREEZER_TEMPERATURE = "freezer_temperature"
CONF_DOORBELL_CHIME = "doorbell_chime"

# 设备类型
DEVICE_TYPE_SWITCH = "switch"
DEVICE_TYPE_LIGHT = "light"
DEVICE_TYPE_CLIMATE = "climate"
DEVICE_TYPE_COVER = "cover"
DEVICE_TYPE_FAN = "fan"
DEVICE_TYPE_SENSOR = "sensor"
DEVICE_TYPE_BINARY_SENSOR = "binary_sensor"
DEVICE_TYPE_BUTTON = "button"
DEVICE_TYPE_SCENE = "scene"
DEVICE_TYPE_MEDIA_PLAYER = "media_player"
DEVICE_TYPE_VACUUM = "vacuum"
DEVICE_TYPE_WEATHER = "weather"
DEVICE_TYPE_CAMERA = "camera"
DEVICE_TYPE_LOCK = "lock"
DEVICE_TYPE_VALVE = "valve"
DEVICE_TYPE_WATER_HEATER = "water_heater"
DEVICE_TYPE_HUMIDIFIER = "humidifier"
DEVICE_TYPE_AIR_PURIFIER = "air_purifier"
DEVICE_TYPE_WASHER = "washer"
DEVICE_TYPE_DRYER = "dryer"
DEVICE_TYPE_SIREN = "siren"
DEVICE_TYPE_ALARM_CONTROL_PANEL = "alarm_control_panel"
DEVICE_TYPE_REMOTE = "remote"
DEVICE_TYPE_LAWN_MOWER = "lawn_mower"
DEVICE_TYPE_DEHUMIDIFIER = "dehumidifier"
DEVICE_TYPE_DISHWASHER = "dishwasher"
DEVICE_TYPE_REFRIGERATOR = "refrigerator"
DEVICE_TYPE_DOORBELL = "doorbell"


@dataclass
class DeviceTypeInfo:
    """Information about a device type.

    Attributes:
        key: The unique identifier for the device type (e.g., "light", "switch")
        display_name_key: Translation key for the display name
        icon: Material Design Icon identifier (e.g., "mdi:lightbulb")
        default_config: Default configuration dictionary for this device type
        schema_builder: Optional callable that returns device-specific schema fields
    """
    key: str
    display_name_key: str
    icon: str
    default_config: dict[str, Any] = field(default_factory=dict)
    schema_builder: Callable[[], dict[str, Any]] | None = None


# 支持的设备类型 - 使用常量键值，翻译由翻译文件处理
DEVICE_TYPES = {
    DEVICE_TYPE_LIGHT: DEVICE_TYPE_LIGHT,
    DEVICE_TYPE_SWITCH: DEVICE_TYPE_SWITCH,
    DEVICE_TYPE_CLIMATE: DEVICE_TYPE_CLIMATE,
    DEVICE_TYPE_COVER: DEVICE_TYPE_COVER,
    DEVICE_TYPE_FAN: DEVICE_TYPE_FAN,
    DEVICE_TYPE_SENSOR: DEVICE_TYPE_SENSOR,
    DEVICE_TYPE_BINARY_SENSOR: DEVICE_TYPE_BINARY_SENSOR,
    DEVICE_TYPE_BUTTON: DEVICE_TYPE_BUTTON,
    DEVICE_TYPE_SCENE: DEVICE_TYPE_SCENE,
    DEVICE_TYPE_MEDIA_PLAYER: DEVICE_TYPE_MEDIA_PLAYER,
    DEVICE_TYPE_VACUUM: DEVICE_TYPE_VACUUM,
    DEVICE_TYPE_WEATHER: DEVICE_TYPE_WEATHER,
    DEVICE_TYPE_CAMERA: DEVICE_TYPE_CAMERA,
    DEVICE_TYPE_LOCK: DEVICE_TYPE_LOCK,
    DEVICE_TYPE_VALVE: DEVICE_TYPE_VALVE,
    DEVICE_TYPE_WATER_HEATER: DEVICE_TYPE_WATER_HEATER,
    DEVICE_TYPE_HUMIDIFIER: DEVICE_TYPE_HUMIDIFIER,
    DEVICE_TYPE_AIR_PURIFIER: DEVICE_TYPE_AIR_PURIFIER,
    DEVICE_TYPE_WASHER: DEVICE_TYPE_WASHER,
    DEVICE_TYPE_DRYER: DEVICE_TYPE_DRYER,
    DEVICE_TYPE_SIREN: DEVICE_TYPE_SIREN,
    DEVICE_TYPE_ALARM_CONTROL_PANEL: DEVICE_TYPE_ALARM_CONTROL_PANEL,
    DEVICE_TYPE_REMOTE: DEVICE_TYPE_REMOTE,
    DEVICE_TYPE_LAWN_MOWER: DEVICE_TYPE_LAWN_MOWER,
    DEVICE_TYPE_DEHUMIDIFIER: DEVICE_TYPE_DEHUMIDIFIER,
    DEVICE_TYPE_DISHWASHER: DEVICE_TYPE_DISHWASHER,
    DEVICE_TYPE_REFRIGERATOR: DEVICE_TYPE_REFRIGERATOR,
    DEVICE_TYPE_DOORBELL: DEVICE_TYPE_DOORBELL,
}

SIREN_TONES = {
    "alarm": "alarm",
    "fire": "fire",
    "police": "police",
    "doorbell": "doorbell",
    "chime": "chime",
}

ALARM_STATES = {
    "disarmed": "disarmed",
    "armed_home": "armed_home",
    "armed_away": "armed_away",
    "armed_night": "armed_night",
    "armed_vacation": "armed_vacation",
    "armed_custom_bypass": "armed_custom_bypass",
    "triggered": "triggered",
}

REMOTE_ACTIVITIES = {
    "tv": "tv",
    "movie": "movie",
    "music": "music",
    "game": "game",
}

MOWER_ZONES = {
    "front_yard": "front_yard",
    "back_yard": "back_yard",
    "full_lawn": "full_lawn",
}

DISHWASHER_PROGRAMS = {
    "eco": "eco",
    "auto": "auto",
    "intensive": "intensive",
    "quick": "quick",
    "rinse": "rinse",
}

REFRIGERATOR_MODES = {
    "normal": "normal",
    "eco": "eco",
    "quick_cool": "quick_cool",
    "vacation": "vacation",
}

DOORBELL_CHIMES = {
    "classic": "classic",
    "digital": "digital",
    "westminster": "westminster",
    "silent": "silent",
}

# 灯光支持的功能
CONF_BRIGHTNESS = "brightness"
CONF_COLOR_TEMP = "color_temp"
CONF_RGB = "rgb"
CONF_EFFECT = "effect"
CONF_COLOR_MODE = "color_mode"

LIGHT_FEATURES = {
    CONF_BRIGHTNESS: "brightness_control",
    CONF_COLOR_TEMP: "color_temp_control",
    CONF_RGB: "rgb_color",
    CONF_EFFECT: "effects",
}

# 窗帘类型
COVER_TYPES = {
    "blind": "blind",
    "curtain": "curtain",
    "damper": "damper",
    "door": "door",
    "garage": "garage",
    "shade": "shade",
    "shutter": "shutter",
    "window": "window",
}

# 传感器类型
SENSOR_TYPES = {
    "temperature": "temperature",
    "humidity": "humidity",
    "pressure": "pressure",
    "illuminance": "illuminance",
    "power": "power",
    "energy": "energy",
    "voltage": "voltage",
    "current": "current",
    "battery": "battery",
    "signal_strength": "signal_strength",
    "pm25": "pm25",
    "pm10": "pm10",
    "co2": "co2",
    "voc": "voc",
    "formaldehyde": "formaldehyde",
    "noise": "noise",
    "uv_index": "uv_index",
    "rainfall": "rainfall",
    "wind_speed": "wind_speed",
    "water_quality": "water_quality",
    "ph": "ph",
}

# 二进制传感器类型
BINARY_SENSOR_TYPES = {
    "motion": "motion",
    "door": "door",
    "window": "window",
    "smoke": "smoke",
    "gas": "gas",
    "moisture": "moisture",
    "occupancy": "occupancy",
    "opening": "opening",
    "presence": "presence",
    "problem": "problem",
    "safety": "safety",
    "sound": "sound",
    "vibration": "vibration",
}

# 按钮类型
BUTTON_TYPES = {
    "generic": "generic",
    "restart": "restart",
    "update": "update",
    "identify": "identify",
}

# 媒体播放器功能
CONF_MEDIA_SOURCE_LIST = "media_source_list"
CONF_MEDIA_CONTENT_TYPE = "media_content_type"
CONF_MEDIA_DURATION = "media_duration"
CONF_MEDIA_POSITION = "media_position"
CONF_MEDIA_VOLUME_LEVEL = "volume_level"
CONF_MEDIA_VOLUME_MUTED = "volume_muted"
CONF_MEDIA_REPEAT = "repeat"
CONF_MEDIA_SHUFFLE = "shuffle"
CONF_MEDIA_SUPPORTS_SEEK = "supports_seek"

# 扫地机器人功能
CONF_VACUUM_STATUS = "vacuum_status"
CONF_VACUUM_FAN_SPEED = "fan_speed"

# 摄像头功能
CONF_CAMERA_STREAM_SOURCE = "stream_source"
CONF_CAMERA_RECORDING = "recording"
CONF_CAMERA_MOTION_DETECTION = "motion_detection"

# 锁功能
CONF_LOCK_STATE = "lock_state"

# 水阀功能
CONF_VALVE_POSITION = "valve_position"
CONF_VALVE_REPORTS_POSITION = "reports_position"

# 运行时间配置
CONF_TRAVEL_TIME = "travel_time"

# 默认值
DEFAULT_ENTITY_COUNT = 1
DEFAULT_MIN_TEMP = 16
DEFAULT_MAX_TEMP = 35
DEFAULT_TEMP_STEP = 1

# 实体类别配置
ENTITY_CATEGORIES = {
    "temperature": EntityCategory.DIAGNOSTIC,
    "humidity": EntityCategory.DIAGNOSTIC,
    "pressure": EntityCategory.DIAGNOSTIC,
    "illuminance": EntityCategory.DIAGNOSTIC,
    "power": EntityCategory.DIAGNOSTIC,
    "energy": EntityCategory.DIAGNOSTIC,
    "voltage": EntityCategory.DIAGNOSTIC,
    "current": EntityCategory.DIAGNOSTIC,
    "battery": EntityCategory.DIAGNOSTIC,
    "signal_strength": EntityCategory.DIAGNOSTIC,
    "motion": EntityCategory.DIAGNOSTIC,
    "door": EntityCategory.DIAGNOSTIC,
    "window": EntityCategory.DIAGNOSTIC,
    "smoke": EntityCategory.DIAGNOSTIC,
    "gas": EntityCategory.DIAGNOSTIC,
    "moisture": EntityCategory.DIAGNOSTIC,
    "occupancy": EntityCategory.DIAGNOSTIC,
    "opening": EntityCategory.DIAGNOSTIC,
    "presence": EntityCategory.DIAGNOSTIC,
    "problem": EntityCategory.DIAGNOSTIC,
    "safety": EntityCategory.DIAGNOSTIC,
    "sound": EntityCategory.DIAGNOSTIC,
    "vibration": EntityCategory.DIAGNOSTIC,
}

# 媒体播放器类型配置
MEDIA_PLAYER_TYPES = {
    "tv": "tv",
    "speaker": "speaker",
    "receiver": "receiver",
    "streaming": "streaming",
    "game_console": "game_console",
    "computer": "computer",
}

# 扫地机器人状态
VACUUM_STATUS_TYPES = {
    "idle": "idle",
    "cleaning": "cleaning",
    "returning": "returning",
    "docked": "docked",
    "error": "error",
}

VACUUM_FAN_SPEEDS = {
    "quiet": "quiet",
    "low": "low",
    "medium": "medium",
    "high": "high",
    "turbo": "turbo",
}

# 摄像头类型
CAMERA_TYPES = {
    "indoor": "indoor",
    "outdoor": "outdoor",
    "doorbell": "doorbell",
    "ptz": "ptz",
    "baby_monitor": "baby_monitor",
}

# 摄像头镜头类型
CAMERA_LENS_TYPES = {
    "indoor": "wide_angle_lens",
    "outdoor": "zoom_lens",
    "doorbell": "fisheye_lens",
    "ptz": "ptz_zoom_lens",
    "baby_monitor": "fixed_focus_lens",
    "standard": "standard_lens",
}

# 摄像头存储类型
CAMERA_STORAGE_TYPES = {
    "indoor": "local_storage",
    "outdoor": "sd_card_cloud_storage",
    "doorbell": "cloud_storage",
    "baby_monitor": "local_storage",
    "ptz": "sd_card_cloud_storage",
    "local_storage": "local_storage",
}

# 锁类型
LOCK_TYPES = {
    "deadbolt": "deadbolt",
    "door_lock": "door_lock",
    "padlock": "padlock",
    "smart_lock": "smart_lock",
}

# 水阀类型
VALVE_TYPES = {
    "water_valve": "water_valve",
    "gas_valve": "gas_valve",
    "irrigation": "irrigation",
    "zone_valve": "zone_valve",
}

# 热水器类型
WATER_HEATER_TYPES = {
    "electric": "electric",
    "gas": "gas",
    "solar": "solar",
    "heat_pump": "heat_pump",
    "tankless": "tankless",
}

# 加湿器类型
HUMIDIFIER_TYPES = {
    "ultrasonic": "ultrasonic",
    "evaporative": "evaporative",
    "steam": "steam",
    "impeller": "impeller",
    "warm_mist": "warm_mist",
}

# 空气净化器类型
AIR_PURIFIER_TYPES = {
    "hepa": "hepa",
    "activated_carbon": "activated_carbon",
    "uv_c": "uv_c",
    "ionic": "ionic",
    "ozone": "ozone",
    "hybrid": "hybrid",
}

# 空气净化器滤网类型
AIR_PURIFIER_FILTER_TYPES = {
    "hepa": "hepa_filter",
    "activated_carbon": "activated_carbon_filter",
    "uv_c": "uv_c_filter",
    "ionic": "ionic_filter",
    "ozone": "ozone_filter",
    "hybrid": "hybrid_filter",
    "standard": "standard_filter",
}

# 气象站类型
WEATHER_STATION_TYPES = {
    "basic": "basic",
    "professional": "professional",
    "home": "home",
    "outdoor": "outdoor",
    "marine": "marine",
}

# 空气质量相关常量
AQI_LEVELS = {
    "good": {"min": 0, "max": 50, "color": "#00E400", "label": "good"},
    "moderate": {"min": 51, "max": 100, "color": "#FFFF00", "label": "moderate"},
    "unhealthy_sensitive": {"min": 101, "max": 150, "color": "#FF7E00", "label": "unhealthy_sensitive"},
    "unhealthy": {"min": 151, "max": 200, "color": "#FF0000", "label": "unhealthy"},
    "very_unhealthy": {"min": 201, "max": 300, "color": "#8F3F97", "label": "very_unhealthy"},
    "hazardous": {"min": 301, "max": 500, "color": "#7E0023", "label": "hazardous"},
}

# 噪音等级常量
NOISE_LEVELS = {
    "silent": "silent",
    "low": "low",
    "medium": "medium",
    "high": "high",
}

# 功率消耗常量
POWER_STATES = {
    "standby": "standby",
    "running": "running",
}

# 加湿器特殊功能常量
HUMIDIFIER_SPECIAL_FEATURES = {
    "ultrasonic": ["ultrasonic_mist", "mist_control"],
    "evaporative": ["no_white_powder", "energy_saving"],
    "steam": ["sterile_humidification", "fast_humidification"],
    "impeller": ["powerful_humidification", "even_distribution"],
    "warm_mist": ["warm_mist", "comfortable"],
    "common": ["water_shortage_protection", "water_level_display"],
}

# 天气状况常量
WEATHER_CONDITIONS = {
    "clear-night": "clear-night",
    "cloudy": "cloudy",
    "fog": "fog",
    "hail": "hail",
    "lightning": "lightning",
    "lightning-rainy": "lightning-rainy",
    "partlycloudy": "partlycloudy",
    "pouring": "pouring",
    "rainy": "rainy",
    "snowy": "snowy",
    "snowy-rainy": "snowy-rainy",
    "sunny": "sunny",
    "windy": "windy",
    "windy-variant": "windy-variant",
}

# 房间位置常量
VACUUM_ROOMS = {
    "living_room": "living_room",
    "bedroom": "bedroom",
    "kitchen": "kitchen",
    "bathroom": "bathroom",
    "study": "study",
    "dining_room": "dining_room",
    "balcony": "balcony",
    "entrance": "entrance",
}

# 吸尘器清洁模式
VACUUM_CLEANING_MODES = {
    "auto_clean": "auto_clean",
    "spot_clean": "spot_clean",
    "edge_clean": "edge_clean",
    "room_clean": "room_clean",
    "single_room_clean": "single_room_clean",
    "point_clean": "point_clean",
}

# 支持模板的设备类型
TEMPLATE_ENABLED_DEVICE_TYPES = {
    DEVICE_TYPE_LIGHT,
    DEVICE_TYPE_SWITCH,
    DEVICE_TYPE_CLIMATE,
    DEVICE_TYPE_COVER,
    DEVICE_TYPE_FAN,
    DEVICE_TYPE_BUTTON,
    DEVICE_TYPE_SCENE,
    DEVICE_TYPE_MEDIA_PLAYER,
    DEVICE_TYPE_VACUUM,
    DEVICE_TYPE_CAMERA,
    DEVICE_TYPE_LOCK,
    DEVICE_TYPE_VALVE,
    DEVICE_TYPE_WATER_HEATER,
    DEVICE_TYPE_HUMIDIFIER,
    DEVICE_TYPE_AIR_PURIFIER,
}

# =============================================================================
# Device Type Registry - Centralized device type definitions
# =============================================================================

DEVICE_TYPE_REGISTRY: dict[str, DeviceTypeInfo] = {
    DEVICE_TYPE_LIGHT: DeviceTypeInfo(
        key=DEVICE_TYPE_LIGHT,
        display_name_key="device_type.light",
        icon="mdi:lightbulb",
        default_config={
            "brightness": True,
            "color_temp": False,
            "rgb": False,
            "effect": False,
        },
    ),
    DEVICE_TYPE_SWITCH: DeviceTypeInfo(
        key=DEVICE_TYPE_SWITCH,
        display_name_key="device_type.switch",
        icon="mdi:electric-switch",
        default_config={},
    ),
    DEVICE_TYPE_CLIMATE: DeviceTypeInfo(
        key=DEVICE_TYPE_CLIMATE,
        display_name_key="device_type.climate",
        icon="mdi:air-conditioner",
        default_config={
            "min_temp": 16,
            "max_temp": 30,
            "enable_humidity_sensor": True,
        },
    ),
    DEVICE_TYPE_COVER: DeviceTypeInfo(
        key=DEVICE_TYPE_COVER,
        display_name_key="device_type.cover",
        icon="mdi:curtains",
        default_config={
            "cover_type": "curtain",
            "travel_time": 15,
        },
    ),
    DEVICE_TYPE_FAN: DeviceTypeInfo(
        key=DEVICE_TYPE_FAN,
        display_name_key="device_type.fan",
        icon="mdi:fan",
        default_config={},
    ),
    DEVICE_TYPE_SENSOR: DeviceTypeInfo(
        key=DEVICE_TYPE_SENSOR,
        display_name_key="device_type.sensor",
        icon="mdi:thermometer",
        default_config={
            "sensor_type": "temperature",
        },
    ),
    DEVICE_TYPE_BINARY_SENSOR: DeviceTypeInfo(
        key=DEVICE_TYPE_BINARY_SENSOR,
        display_name_key="device_type.binary_sensor",
        icon="mdi:motion-sensor",
        default_config={
            "sensor_type": "motion",
        },
    ),
    DEVICE_TYPE_BUTTON: DeviceTypeInfo(
        key=DEVICE_TYPE_BUTTON,
        display_name_key="device_type.button",
        icon="mdi:gesture-tap-button",
        default_config={
            "button_type": "generic",
        },
    ),
    DEVICE_TYPE_SCENE: DeviceTypeInfo(
        key=DEVICE_TYPE_SCENE,
        display_name_key="device_type.scene",
        icon="mdi:palette",
        default_config={},
    ),
    DEVICE_TYPE_MEDIA_PLAYER: DeviceTypeInfo(
        key=DEVICE_TYPE_MEDIA_PLAYER,
        display_name_key="device_type.media_player",
        icon="mdi:speaker",
        default_config={
            "media_player_type": "speaker",
            "media_source_list": ["local_music", "online_radio"],
            "supports_seek": False,
        },
    ),
    DEVICE_TYPE_VACUUM: DeviceTypeInfo(
        key=DEVICE_TYPE_VACUUM,
        display_name_key="device_type.vacuum",
        icon="mdi:robot-vacuum",
        default_config={
            "vacuum_status": "docked",
            "fan_speed": "medium",
        },
    ),
    DEVICE_TYPE_WEATHER: DeviceTypeInfo(
        key=DEVICE_TYPE_WEATHER,
        display_name_key="device_type.weather",
        icon="mdi:weather-partly-cloudy",
        default_config={
            "weather_station_type": "home",
            "temperature_unit": "celsius",
            "wind_speed_unit": "kmh",
            "pressure_unit": "hPa",
            "visibility_unit": "km",
        },
    ),
    DEVICE_TYPE_CAMERA: DeviceTypeInfo(
        key=DEVICE_TYPE_CAMERA,
        display_name_key="device_type.camera",
        icon="mdi:cctv",
        default_config={
            "camera_type": "indoor",
            "recording": False,
            "motion_detection": True,
            "night_vision": True,
        },
    ),
    DEVICE_TYPE_LOCK: DeviceTypeInfo(
        key=DEVICE_TYPE_LOCK,
        display_name_key="device_type.lock",
        icon="mdi:lock",
        default_config={
            "lock_type": "smart_lock",
            "access_code": "1234",
            "auto_lock": True,
            "auto_lock_delay": 30,
        },
    ),
    DEVICE_TYPE_VALVE: DeviceTypeInfo(
        key=DEVICE_TYPE_VALVE,
        display_name_key="device_type.valve",
        icon="mdi:valve",
        default_config={
            "valve_type": "water_valve",
            "valve_size": 25,
            "reports_position": True,
            "travel_time": 10,
        },
    ),
    DEVICE_TYPE_WATER_HEATER: DeviceTypeInfo(
        key=DEVICE_TYPE_WATER_HEATER,
        display_name_key="device_type.water_heater",
        icon="mdi:water-boiler",
        default_config={
            "heater_type": "electric",
            "current_temperature": 25,
            "target_temperature": 60,
            "tank_capacity": 80,
            "efficiency": 0.9,
        },
    ),
    DEVICE_TYPE_HUMIDIFIER: DeviceTypeInfo(
        key=DEVICE_TYPE_HUMIDIFIER,
        display_name_key="device_type.humidifier",
        icon="mdi:air-humidifier",
        default_config={
            "humidifier_type": "ultrasonic",
            "current_humidity": 45,
            "target_humidity": 60,
            "water_level": 80,
            "tank_capacity": 4.0,
        },
    ),
    DEVICE_TYPE_AIR_PURIFIER: DeviceTypeInfo(
        key=DEVICE_TYPE_AIR_PURIFIER,
        display_name_key="device_type.air_purifier",
        icon="mdi:air-purifier",
        default_config={
            "purifier_type": "hepa",
            "room_volume": 50,
            "pm25": 35,
            "pm10": 50,
            "filter_life": 80,
        },
    ),
    DEVICE_TYPE_WASHER: DeviceTypeInfo(
        key=DEVICE_TYPE_WASHER,
        display_name_key="device_type.washer",
        icon="mdi:washing-machine",
        default_config={
            CONF_LAUNDRY_MODE: "quick",
            CONF_CYCLE_DURATION_MINUTES: 45,
            CONF_SUPPORTS_PAUSE: True,
        },
    ),
    DEVICE_TYPE_DRYER: DeviceTypeInfo(
        key=DEVICE_TYPE_DRYER,
        display_name_key="device_type.dryer",
        icon="mdi:tumble-dryer",
        default_config={
            CONF_LAUNDRY_MODE: "quick_dry",
            CONF_CYCLE_DURATION_MINUTES: 60,
            CONF_SUPPORTS_PAUSE: True,
        },
    ),
    DEVICE_TYPE_SIREN: DeviceTypeInfo(
        key=DEVICE_TYPE_SIREN,
        display_name_key="device_type.siren",
        icon="mdi:bullhorn",
        default_config={
            CONF_SIREN_TONE: "alarm",
            CONF_SIREN_DURATION: 30,
            CONF_SIREN_VOLUME: 1.0,
        },
    ),
    DEVICE_TYPE_ALARM_CONTROL_PANEL: DeviceTypeInfo(
        key=DEVICE_TYPE_ALARM_CONTROL_PANEL,
        display_name_key="device_type.alarm_control_panel",
        icon="mdi:shield-home",
        default_config={
            CONF_ALARM_CODE: "1234",
            CONF_ALARM_TRIGGER_TIME: 180,
            CONF_SUPPORTS_ARM_NIGHT: True,
            CONF_SUPPORTS_ARM_VACATION: True,
        },
    ),
    DEVICE_TYPE_REMOTE: DeviceTypeInfo(
        key=DEVICE_TYPE_REMOTE,
        display_name_key="device_type.remote",
        icon="mdi:remote",
        default_config={
            CONF_REMOTE_ACTIVITY: "tv",
            CONF_REMOTE_COMMANDS: ["power", "volume_up", "volume_down", "mute", "channel_up", "channel_down"],
        },
    ),
    DEVICE_TYPE_LAWN_MOWER: DeviceTypeInfo(
        key=DEVICE_TYPE_LAWN_MOWER,
        display_name_key="device_type.lawn_mower",
        icon="mdi:robot-mower",
        default_config={
            CONF_MOWER_ZONE: "full_lawn",
            CONF_MOWER_CUTTING_HEIGHT: 45,
        },
    ),
    DEVICE_TYPE_DEHUMIDIFIER: DeviceTypeInfo(
        key=DEVICE_TYPE_DEHUMIDIFIER,
        display_name_key="device_type.dehumidifier",
        icon="mdi:air-humidifier-off",
        default_config={
            "humidifier_type": "compressor",
            "current_humidity": 60,
            "target_humidity": 45,
            "water_level": 20,
            "tank_capacity": 3.0,
        },
    ),
    DEVICE_TYPE_DISHWASHER: DeviceTypeInfo(
        key=DEVICE_TYPE_DISHWASHER,
        display_name_key="device_type.dishwasher",
        icon="mdi:dishwasher",
        default_config={
            CONF_APPLIANCE_PROGRAM: "eco",
            CONF_CYCLE_DURATION_MINUTES: 120,
            CONF_DELAY_START_MINUTES: 0,
        },
    ),
    DEVICE_TYPE_REFRIGERATOR: DeviceTypeInfo(
        key=DEVICE_TYPE_REFRIGERATOR,
        display_name_key="device_type.refrigerator",
        icon="mdi:fridge-outline",
        default_config={
            "refrigerator_mode": "normal",
            CONF_FRIDGE_TEMPERATURE: 4,
            CONF_FREEZER_TEMPERATURE: -18,
        },
    ),
    DEVICE_TYPE_DOORBELL: DeviceTypeInfo(
        key=DEVICE_TYPE_DOORBELL,
        display_name_key="device_type.doorbell",
        icon="mdi:doorbell-video",
        default_config={
            CONF_DOORBELL_CHIME: "classic",
            "camera_type": "doorbell",
            "motion_detection": True,
            "recording": False,
            "night_vision": True,
        },
    ),
}


def get_device_type_info(device_type: str) -> DeviceTypeInfo | None:
    """Get device type information from registry.

    Args:
        device_type: The device type key (e.g., "light", "switch")

    Returns:
        DeviceTypeInfo object if found, None otherwise
    """
    return DEVICE_TYPE_REGISTRY.get(device_type)


def get_all_device_types() -> list[str]:
    """Get list of all supported device types.

    Returns:
        List of device type keys
    """
    return list(DEVICE_TYPE_REGISTRY.keys())


def get_device_type_display_name(device_type: str) -> str:
    """Get the display name for a device type.

    This is a fallback function that returns a formatted device type name.
    For translated names, use the translation system with display_name_key.

    Args:
        device_type: The device type key

    Returns:
        Formatted display name (e.g., "Light", "Binary Sensor")
    """
    info = DEVICE_TYPE_REGISTRY.get(device_type)
    if info:
        # Return a formatted version of the key as fallback
        return device_type.replace("_", " ").title()
    return device_type


def get_device_icon(device_type: str) -> str:
    """Get the icon for a device type.

    Args:
        device_type: The device type key

    Returns:
        Material Design Icon identifier (e.g., "mdi:lightbulb")
    """
    info = DEVICE_TYPE_REGISTRY.get(device_type)
    return info.icon if info else "mdi:help-circle"


def get_default_entity_config(device_type: str) -> dict[str, Any]:
    """Get default entity configuration for a device type.

    Args:
        device_type: The device type key

    Returns:
        Copy of the default configuration dictionary
    """
    info = DEVICE_TYPE_REGISTRY.get(device_type)
    return info.default_config.copy() if info else {}
