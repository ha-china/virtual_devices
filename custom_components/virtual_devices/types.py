"""Type definitions for the Virtual Devices Multi integration.

This module provides centralized type definitions using TypedDict and Protocol
for improved type safety and IDE support across the integration.
"""
from __future__ import annotations

from typing import Any, Literal, NotRequired, Protocol, TypedDict


# =============================================================================
# Type Aliases
# =============================================================================

# Common type aliases for frequently used types
TemplateDict = dict[str, Any]
RGBColor = tuple[int, int, int]
ConfigEntryId = str
EntityIndex = int
EntityCategoryOption = Literal["config", "diagnostic"]


# =============================================================================
# Base TypedDict Definitions
# =============================================================================

class EntityConfigBase(TypedDict, total=False):
    """Base configuration for all entity types.

    All entity configurations should extend this base class with their
    specific configuration options.
    """
    entity_name: str
    templates: TemplateDict


class DeviceConfig(TypedDict):
    """Complete device configuration stored in ConfigEntry.data."""
    device_name: str
    device_type: str
    entity_count: int
    entities: list[EntityConfigBase]


class EntityState(TypedDict):
    """Base state structure for persistence.

    Device-specific state classes should extend this base class
    with their specific state fields.
    """
    pass


# =============================================================================
# Protocol Definitions
# =============================================================================

class StatePersistenceProtocol(Protocol):
    """Protocol for entities that support state persistence.

    Entities implementing this protocol can save and restore their state
    across Home Assistant restarts.
    """

    async def async_load_state(self) -> None:
        """Load entity state from storage."""
        ...

    async def async_save_state(self) -> None:
        """Save entity state to storage."""
        ...

    def get_default_state(self) -> EntityState:
        """Return the default state for this entity type."""
        ...


# =============================================================================
# Light Entity Types
# =============================================================================

class LightEntityConfig(EntityConfigBase):
    """Configuration for light entities."""
    brightness: NotRequired[bool]
    color_temp: NotRequired[bool]
    rgb: NotRequired[bool]
    effect: NotRequired[bool]


class LightState(EntityState):
    """State structure for light entities."""
    is_on: bool
    brightness: NotRequired[int]
    rgb_color: NotRequired[RGBColor]
    color_temp_kelvin: NotRequired[int]
    effect: NotRequired[str | None]


# =============================================================================
# Climate Entity Types
# =============================================================================

class ClimateEntityConfig(EntityConfigBase):
    """Configuration for climate entities."""
    min_temp: NotRequired[int]
    max_temp: NotRequired[int]
    temp_step: NotRequired[int]
    enable_humidity_sensor: NotRequired[bool]
    enable_temperature_simulation: NotRequired[bool]


class ClimateState(EntityState):
    """State structure for climate entities."""
    hvac_mode: str
    target_temperature: float
    current_temperature: float
    fan_mode: str
    swing_mode: str
    preset_mode: NotRequired[str | None]
    hvac_action: str
    current_humidity: NotRequired[float]
    target_humidity: NotRequired[float]


# =============================================================================
# Switch Entity Types
# =============================================================================

class SwitchEntityConfig(EntityConfigBase):
    """Configuration for switch entities."""
    pass  # Switch entities only use base config


class SwitchState(EntityState):
    """State structure for switch entities."""
    is_on: bool


# =============================================================================
# Cover Entity Types
# =============================================================================

class CoverEntityConfig(EntityConfigBase):
    """Configuration for cover entities."""
    cover_type: NotRequired[str]
    travel_time: NotRequired[int]


class CoverState(EntityState):
    """State structure for cover entities."""
    position: int
    is_closed: bool
    is_moving: NotRequired[bool]
    target_position: NotRequired[int | None]


# =============================================================================
# Fan Entity Types
# =============================================================================

class FanEntityConfig(EntityConfigBase):
    """Configuration for fan entities."""
    pass  # Fan entities only use base config


class FanState(EntityState):
    """State structure for fan entities."""
    is_on: bool
    percentage: int
    preset_mode: NotRequired[str | None]
    oscillating: bool
    direction: str


# =============================================================================
# Vacuum Entity Types
# =============================================================================

class VacuumEntityConfig(EntityConfigBase):
    """Configuration for vacuum entities."""
    vacuum_status: NotRequired[str]
    fan_speed: NotRequired[str]


class VacuumState(EntityState):
    """State structure for vacuum entities."""
    state: str
    fan_speed: str
    cleaned_area: NotRequired[float]
    cleaning_duration: NotRequired[float]
    current_room: NotRequired[str | None]


# =============================================================================
# Lock Entity Types
# =============================================================================

class LockEntityConfig(EntityConfigBase):
    """Configuration for lock entities."""
    lock_type: NotRequired[str]
    lock_state: NotRequired[str]
    access_code: NotRequired[str]
    auto_lock: NotRequired[bool]
    auto_lock_delay: NotRequired[int]
    enable_jamming: NotRequired[bool]


class LockState(EntityState):
    """State structure for lock entities."""
    state: str


# =============================================================================
# Sensor Entity Types
# =============================================================================

class SensorEntityConfig(EntityConfigBase):
    """Configuration for sensor entities."""
    sensor_type: NotRequired[str]
    enable_simulation: NotRequired[bool]
    update_frequency: NotRequired[int]


class SensorState(EntityState):
    """State structure for sensor entities."""
    native_value: float | int | str | None


# =============================================================================
# Binary Sensor Entity Types
# =============================================================================

class BinarySensorEntityConfig(EntityConfigBase):
    """Configuration for binary sensor entities."""
    sensor_type: NotRequired[str]
    entity_category: NotRequired[EntityCategoryOption]


class BinarySensorState(EntityState):
    """State structure for binary sensor entities."""
    is_on: bool


# =============================================================================
# Button Entity Types
# =============================================================================

class ButtonEntityConfig(EntityConfigBase):
    """Configuration for button entities."""
    button_type: NotRequired[str]


# =============================================================================
# Scene Entity Types
# =============================================================================

class SceneEntityConfig(EntityConfigBase):
    """Configuration for scene entities."""
    pass  # Scene entities only use base config


# =============================================================================
# Media Player Entity Types
# =============================================================================

class MediaPlayerEntityConfig(EntityConfigBase):
    """Configuration for media player entities."""
    media_player_type: NotRequired[str]
    source_list: NotRequired[list[str]]


class MediaPlayerState(EntityState):
    """State structure for media player entities."""
    state: str
    volume_level: NotRequired[float]
    is_volume_muted: NotRequired[bool]
    media_content_type: NotRequired[str | None]
    media_title: NotRequired[str | None]
    source: NotRequired[str | None]
    media_repeat: NotRequired[str]
    media_shuffle: NotRequired[bool]


# =============================================================================
# Camera Entity Types
# =============================================================================

class CameraEntityConfig(EntityConfigBase):
    """Configuration for camera entities."""
    camera_type: NotRequired[str]
    stream_source: NotRequired[str]
    motion_detection: NotRequired[bool]


class CameraState(EntityState):
    """State structure for camera entities."""
    is_recording: bool
    is_streaming: bool
    motion_detection_enabled: bool


# =============================================================================
# Valve Entity Types
# =============================================================================

class ValveEntityConfig(EntityConfigBase):
    """Configuration for valve entities."""
    valve_type: NotRequired[str]
    reports_position: NotRequired[bool]


class ValveState(EntityState):
    """State structure for valve entities."""
    is_open: bool
    position: NotRequired[int]


# =============================================================================
# Water Heater Entity Types
# =============================================================================

class WaterHeaterEntityConfig(EntityConfigBase):
    """Configuration for water heater entities."""
    water_heater_type: NotRequired[str]
    min_temp: NotRequired[int]
    max_temp: NotRequired[int]


class WaterHeaterState(EntityState):
    """State structure for water heater entities."""
    current_operation: str
    target_temperature: float
    current_temperature: float


# =============================================================================
# Humidifier Entity Types
# =============================================================================

class HumidifierEntityConfig(EntityConfigBase):
    """Configuration for humidifier entities."""
    humidifier_type: NotRequired[str]
    min_humidity: NotRequired[int]
    max_humidity: NotRequired[int]


class HumidifierState(EntityState):
    """State structure for humidifier entities."""
    is_on: bool
    target_humidity: int
    current_humidity: NotRequired[int]
    mode: NotRequired[str | None]


# =============================================================================
# Air Purifier Entity Types
# =============================================================================

class AirPurifierEntityConfig(EntityConfigBase):
    """Configuration for air purifier entities."""
    purifier_type: NotRequired[str]


class AirPurifierState(EntityState):
    """State structure for air purifier entities."""
    is_on: bool
    percentage: int
    preset_mode: NotRequired[str | None]
    pm25: NotRequired[int]
    aqi: NotRequired[int]


# =============================================================================
# Weather Entity Types
# =============================================================================

class WeatherEntityConfig(EntityConfigBase):
    """Configuration for weather entities."""
    weather_station_type: NotRequired[str]


class WeatherState(EntityState):
    """State structure for weather entities."""
    condition: str
    temperature: float
    humidity: float
    pressure: float
    wind_speed: float
    wind_bearing: NotRequired[float]


# =============================================================================
# Laundry Entity Types
# =============================================================================

class LaundryEntityConfig(EntityConfigBase):
    """Configuration for washer and dryer entities."""
    laundry_mode: NotRequired[str]
    cycle_duration_minutes: NotRequired[int]
    supports_pause: NotRequired[bool]


class LaundryState(EntityState):
    """State structure for washer and dryer entities."""
    power_on: bool
    operation_state: str
    selected_program: str
    total_seconds: int
    remaining_seconds: int
    delay_start_minutes: int
    supports_pause: bool
    remote_start_enabled: bool
    remote_control_enabled: bool
    door_open: bool
    temperature: NotRequired[str]
    spin_speed: NotRequired[str]
    drying_target: NotRequired[str]


class SirenEntityConfig(EntityConfigBase):
    """Configuration for siren entities."""
    siren_tone: NotRequired[str]
    siren_duration: NotRequired[int]
    siren_volume: NotRequired[float]


class SirenState(EntityState):
    """State structure for siren entities."""
    is_on: bool
    tone: str
    duration: int
    volume_level: float


class AlarmControlPanelEntityConfig(EntityConfigBase):
    """Configuration for alarm control panel entities."""
    alarm_code: NotRequired[str]
    alarm_trigger_time: NotRequired[int]
    supports_arm_night: NotRequired[bool]
    supports_arm_vacation: NotRequired[bool]


class AlarmControlPanelStateDict(EntityState):
    """State structure for alarm control panel entities."""
    state: str


class RemoteEntityConfig(EntityConfigBase):
    """Configuration for remote entities."""
    remote_activity: NotRequired[str]
    remote_commands: NotRequired[list[str] | str]


class RemoteState(EntityState):
    """State structure for remote entities."""
    is_on: bool
    current_activity: str
    last_command: NotRequired[str | None]


class LawnMowerEntityConfig(EntityConfigBase):
    """Configuration for lawn mower entities."""
    mower_zone: NotRequired[str]
    mower_cutting_height: NotRequired[int]


class LawnMowerState(EntityState):
    """State structure for lawn mower entities."""
    state: str
    battery_level: int
    current_zone: str
    cutting_height: int
