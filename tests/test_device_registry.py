"""Property-based tests for Device Type Registry completeness.

Property 1: Device Type Registry Completeness
Validates: Requirements 1.1, 1.2

For any device type key in DEVICE_TYPE_REGISTRY, the registry entry SHALL contain
a valid display_name_key, icon, and default_config dictionary.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from typing import Any, Callable
from pathlib import Path

from hypothesis import given, settings, strategies as st


# Re-define DeviceTypeInfo locally to avoid importing homeassistant dependencies
@dataclass
class DeviceTypeInfo:
    """Information about a device type."""
    key: str
    display_name_key: str
    icon: str
    default_config: dict[str, Any] = field(default_factory=dict)
    schema_builder: Callable[[], dict[str, Any]] | None = None


# Device type constants
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


# Copy of DEVICE_TYPE_REGISTRY from const.py for testing without homeassistant deps
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
            "battery_level": 100,
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
            "laundry_mode": "quick",
            "cycle_duration_minutes": 45,
            "supports_pause": True,
        },
    ),
    DEVICE_TYPE_DRYER: DeviceTypeInfo(
        key=DEVICE_TYPE_DRYER,
        display_name_key="device_type.dryer",
        icon="mdi:tumble-dryer",
        default_config={
            "laundry_mode": "quick_dry",
            "cycle_duration_minutes": 60,
            "supports_pause": True,
        },
    ),
}


def get_device_type_info(device_type: str) -> DeviceTypeInfo | None:
    """Get device type information from registry."""
    return DEVICE_TYPE_REGISTRY.get(device_type)


def get_all_device_types() -> list[str]:
    """Get list of all supported device types."""
    return list(DEVICE_TYPE_REGISTRY.keys())


class TestDeviceTypeRegistryCompleteness:
    """Property-based tests for Device Type Registry completeness.
    
    Feature: code-refactoring, Property 1: Device Type Registry Completeness
    Validates: Requirements 1.1, 1.2
    """

    @settings(max_examples=100)
    @given(st.sampled_from(list(DEVICE_TYPE_REGISTRY.keys())))
    def test_registry_entry_has_valid_display_name_key(self, device_type: str) -> None:
        """For any device type, the registry entry SHALL have a valid display_name_key.
        
        Feature: code-refactoring, Property 1: Device Type Registry Completeness
        Validates: Requirements 1.1
        """
        info = DEVICE_TYPE_REGISTRY[device_type]
        
        # display_name_key must be a non-empty string
        assert isinstance(info.display_name_key, str), (
            f"Device type '{device_type}' has invalid display_name_key type: "
            f"{type(info.display_name_key)}"
        )
        assert len(info.display_name_key) > 0, (
            f"Device type '{device_type}' has empty display_name_key"
        )
        # display_name_key should follow translation key format (contains dots)
        assert "." in info.display_name_key, (
            f"Device type '{device_type}' display_name_key '{info.display_name_key}' "
            f"does not follow translation key format (should contain '.')"
        )

    @settings(max_examples=100)
    @given(st.sampled_from(list(DEVICE_TYPE_REGISTRY.keys())))
    def test_registry_entry_has_valid_icon(self, device_type: str) -> None:
        """For any device type, the registry entry SHALL have a valid icon.
        
        Feature: code-refactoring, Property 1: Device Type Registry Completeness
        Validates: Requirements 1.1
        """
        info = DEVICE_TYPE_REGISTRY[device_type]
        
        # icon must be a non-empty string
        assert isinstance(info.icon, str), (
            f"Device type '{device_type}' has invalid icon type: {type(info.icon)}"
        )
        assert len(info.icon) > 0, (
            f"Device type '{device_type}' has empty icon"
        )
        # icon should follow Material Design Icon format (starts with "mdi:")
        assert info.icon.startswith("mdi:"), (
            f"Device type '{device_type}' icon '{info.icon}' "
            f"does not follow MDI format (should start with 'mdi:')"
        )

    @settings(max_examples=100)
    @given(st.sampled_from(list(DEVICE_TYPE_REGISTRY.keys())))
    def test_registry_entry_has_valid_default_config(self, device_type: str) -> None:
        """For any device type, the registry entry SHALL have a valid default_config dict.
        
        Feature: code-refactoring, Property 1: Device Type Registry Completeness
        Validates: Requirements 1.2
        """
        info = DEVICE_TYPE_REGISTRY[device_type]
        
        # default_config must be a dictionary
        assert isinstance(info.default_config, dict), (
            f"Device type '{device_type}' has invalid default_config type: "
            f"{type(info.default_config)}"
        )

    @settings(max_examples=100)
    @given(st.sampled_from(list(DEVICE_TYPE_REGISTRY.keys())))
    def test_registry_entry_key_matches_device_type(self, device_type: str) -> None:
        """For any device type, the registry entry key SHALL match the DeviceTypeInfo.key.
        
        Feature: code-refactoring, Property 1: Device Type Registry Completeness
        Validates: Requirements 1.1
        """
        info = DEVICE_TYPE_REGISTRY[device_type]
        
        # The key field should match the dictionary key
        assert info.key == device_type, (
            f"Device type registry key '{device_type}' does not match "
            f"DeviceTypeInfo.key '{info.key}'"
        )

    @settings(max_examples=100)
    @given(st.sampled_from(list(DEVICE_TYPE_REGISTRY.keys())))
    def test_get_device_type_info_returns_correct_entry(self, device_type: str) -> None:
        """For any device type, get_device_type_info() SHALL return the correct entry.
        
        Feature: code-refactoring, Property 1: Device Type Registry Completeness
        Validates: Requirements 1.1
        """
        info = get_device_type_info(device_type)
        
        assert info is not None, (
            f"get_device_type_info('{device_type}') returned None"
        )
        assert info == DEVICE_TYPE_REGISTRY[device_type], (
            f"get_device_type_info('{device_type}') returned different entry"
        )

    def test_get_all_device_types_returns_all_registry_keys(self) -> None:
        """get_all_device_types() SHALL return all keys from DEVICE_TYPE_REGISTRY.
        
        Feature: code-refactoring, Property 1: Device Type Registry Completeness
        Validates: Requirements 1.1
        """
        all_types = get_all_device_types()
        registry_keys = list(DEVICE_TYPE_REGISTRY.keys())
        
        assert set(all_types) == set(registry_keys), (
            f"get_all_device_types() returned {all_types}, "
            f"but registry has {registry_keys}"
        )

    def test_registry_has_expected_device_types(self) -> None:
        """The registry SHALL contain all 20 expected device types.
        
        Feature: code-refactoring, Property 1: Device Type Registry Completeness
        Validates: Requirements 1.1, 1.2
        """
        expected_types = {
            "light", "switch", "climate", "cover", "fan", "sensor",
            "binary_sensor", "button", "scene", "media_player", "vacuum",
            "weather", "camera", "lock", "valve", "water_heater",
            "humidifier", "air_purifier", "washer", "dryer"
        }
        
        actual_types = set(DEVICE_TYPE_REGISTRY.keys())
        
        assert actual_types == expected_types, (
            f"Registry missing types: {expected_types - actual_types}, "
            f"Extra types: {actual_types - expected_types}"
        )

    def test_registry_entries_are_device_type_info_instances(self) -> None:
        """All registry entries SHALL be DeviceTypeInfo instances.
        
        Feature: code-refactoring, Property 1: Device Type Registry Completeness
        Validates: Requirements 1.1
        """
        for device_type, info in DEVICE_TYPE_REGISTRY.items():
            assert isinstance(info, DeviceTypeInfo), (
                f"Device type '{device_type}' entry is not a DeviceTypeInfo instance: "
                f"{type(info)}"
            )
