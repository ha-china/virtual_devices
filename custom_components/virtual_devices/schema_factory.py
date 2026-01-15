"""Schema factory for Virtual Devices Multi integration.

This module provides a factory pattern for generating device-specific
configuration schemas, eliminating duplicate schema definitions across
the config flow.
"""
from __future__ import annotations

from typing import Any, Callable

import voluptuous as vol
from homeassistant.helpers import selector

from .const import (
    CONF_BRIGHTNESS,
    CONF_COLOR_TEMP,
    CONF_EFFECT,
    CONF_ENTITY_NAME,
    CONF_MEDIA_SOURCE_LIST,
    CONF_RGB,
    DEVICE_TYPE_AIR_PURIFIER,
    DEVICE_TYPE_BINARY_SENSOR,
    DEVICE_TYPE_BUTTON,
    DEVICE_TYPE_CAMERA,
    DEVICE_TYPE_CLIMATE,
    DEVICE_TYPE_COVER,
    DEVICE_TYPE_FAN,
    DEVICE_TYPE_HUMIDIFIER,
    DEVICE_TYPE_LIGHT,
    DEVICE_TYPE_LOCK,
    DEVICE_TYPE_MEDIA_PLAYER,
    DEVICE_TYPE_SCENE,
    DEVICE_TYPE_SENSOR,
    DEVICE_TYPE_SWITCH,
    DEVICE_TYPE_VACUUM,
    DEVICE_TYPE_VALVE,
    DEVICE_TYPE_WATER_HEATER,
    DEVICE_TYPE_WEATHER,
)


# Type alias for schema builder functions
SchemaBuilderFunc = Callable[[], dict[vol.Marker, Any]]


class SchemaFactory:
    """Factory for creating device configuration schemas.

    This class provides methods to generate voluptuous schemas for
    entity configuration based on device type. It centralizes all
    schema definitions to avoid duplication in the config flow.
    """

    @staticmethod
    def create_entity_schema(
        device_type: str,
        entity_num: int,
        device_name: str,
        include_skip_remaining: bool = False,
    ) -> vol.Schema:
        """Create schema for entity configuration based on device type.

        Args:
            device_type: The type of device (e.g., "light", "switch")
            entity_num: The entity number (1-based index)
            device_name: The name of the parent device
            include_skip_remaining: Whether to include skip_remaining option

        Returns:
            A voluptuous Schema for the entity configuration
        """
        default_name = f"{device_name}_{device_type}_{entity_num}"

        # Base schema with entity name
        schema_dict: dict[vol.Marker, Any] = {
            vol.Required(CONF_ENTITY_NAME, default=default_name): str,
        }

        # Add device-specific fields
        builder = SCHEMA_BUILDERS.get(device_type)
        if builder:
            schema_dict.update(builder())

        # Add skip_remaining option if requested
        if include_skip_remaining:
            schema_dict[vol.Optional("skip_remaining", default=False)] = bool

        return vol.Schema(schema_dict)

    @staticmethod
    def _build_light_schema() -> dict[vol.Marker, Any]:
        """Build schema fields for light entities."""
        return {
            vol.Optional(CONF_BRIGHTNESS, default=True): bool,
            vol.Optional(CONF_COLOR_TEMP, default=False): bool,
            vol.Optional(CONF_RGB, default=False): bool,
            vol.Optional(CONF_EFFECT, default=False): bool,
        }

    @staticmethod
    def _build_switch_schema() -> dict[vol.Marker, Any]:
        """Build schema fields for switch entities."""
        return {}

    @staticmethod
    def _build_climate_schema() -> dict[vol.Marker, Any]:
        """Build schema fields for climate entities."""
        return {
            vol.Optional("min_temp", default=16): vol.All(
                vol.Coerce(int), vol.Range(min=5, max=35)
            ),
            vol.Optional("max_temp", default=30): vol.All(
                vol.Coerce(int), vol.Range(min=10, max=45)
            ),
            vol.Optional("enable_humidity_sensor", default=True): bool,
        }

    @staticmethod
    def _build_cover_schema() -> dict[vol.Marker, Any]:
        """Build schema fields for cover entities."""
        return {
            vol.Optional("cover_type", default="curtain"): vol.In(
                ["curtain", "blind", "shade", "garage", "gate", "damper", "door", "shutter", "window"]
            ),
            vol.Optional("travel_time", default=15): vol.All(
                vol.Coerce(int), vol.Range(min=1, max=60)
            ),
        }

    @staticmethod
    def _build_fan_schema() -> dict[vol.Marker, Any]:
        """Build schema fields for fan entities."""
        return {}

    @staticmethod
    def _build_sensor_schema() -> dict[vol.Marker, Any]:
        """Build schema fields for sensor entities."""
        return {
            vol.Optional("sensor_type", default="temperature"): vol.In(
                [
                    "temperature", "humidity", "pressure", "illuminance",
                    "power", "energy", "voltage", "current", "battery"
                ]
            ),
        }

    @staticmethod
    def _build_binary_sensor_schema() -> dict[vol.Marker, Any]:
        """Build schema fields for binary sensor entities."""
        return {
            vol.Optional("sensor_type", default="motion"): vol.In(
                [
                    "motion", "door", "window", "smoke", "gas", "water_leak",
                    "moisture", "occupancy", "opening", "presence", "problem",
                    "safety", "sound", "vibration"
                ]
            ),
        }

    @staticmethod
    def _build_button_schema() -> dict[vol.Marker, Any]:
        """Build schema fields for button entities."""
        return {
            vol.Optional("button_type", default="generic"): vol.In(
                ["generic", "doorbell", "emergency", "reset"]
            ),
        }

    @staticmethod
    def _build_scene_schema() -> dict[vol.Marker, Any]:
        """Build schema fields for scene entities."""
        return {}

    @staticmethod
    def _build_media_player_schema() -> dict[vol.Marker, Any]:
        """Build schema fields for media player entities."""
        return {
            vol.Optional("media_player_type", default="speaker"): vol.In(
                ["speaker", "tv", "receiver", "soundbar", "streaming", "game_console", "computer"]
            ),
            vol.Optional(CONF_MEDIA_SOURCE_LIST, default="local_music,online_radio"): str,
            vol.Optional("supports_seek", default=False): bool,
        }

    @staticmethod
    def _build_vacuum_schema() -> dict[vol.Marker, Any]:
        """Build schema fields for vacuum entities."""
        return {
            vol.Optional("vacuum_status", default="docked"): vol.In(
                ["docked", "cleaning", "paused", "returning", "error", "idle"]
            ),
            vol.Optional("fan_speed", default="medium"): vol.In(
                ["quiet", "low", "medium", "high", "max", "turbo"]
            ),
            vol.Optional("battery_level", default=100): int,
        }

    @staticmethod
    def _build_camera_schema() -> dict[vol.Marker, Any]:
        """Build schema fields for camera entities."""
        return {
            vol.Optional("camera_type", default="indoor"): vol.In(
                ["indoor", "outdoor", "doorbell", "baby_monitor", "ptz"]
            ),
            vol.Optional("recording", default=False): bool,
            vol.Optional("motion_detection", default=True): bool,
            vol.Optional("night_vision", default=True): bool,
        }

    @staticmethod
    def _build_lock_schema() -> dict[vol.Marker, Any]:
        """Build schema fields for lock entities."""
        return {
            vol.Optional("lock_type", default="smart_lock"): vol.In(
                ["smart_lock", "deadbolt", "keypad", "fingerprint", "door_lock", "padlock"]
            ),
            vol.Optional("access_code", default="1234"): str,
            vol.Optional("auto_lock", default=True): bool,
            vol.Optional("auto_lock_delay", default=30): vol.All(
                vol.Coerce(int), vol.Range(min=5, max=300)
            ),
        }

    @staticmethod
    def _build_valve_schema() -> dict[vol.Marker, Any]:
        """Build schema fields for valve entities."""
        return {
            vol.Optional("valve_type", default="water_valve"): vol.In(
                ["water_valve", "gas_valve", "irrigation", "zone_valve"]
            ),
            vol.Optional("valve_size", default=25): vol.All(
                vol.Coerce(int), vol.Range(min=5, max=200)
            ),
            vol.Optional("reports_position", default=True): bool,
            vol.Optional("travel_time", default=10): vol.All(
                vol.Coerce(int), vol.Range(min=1, max=60)
            ),
        }

    @staticmethod
    def _build_water_heater_schema() -> dict[vol.Marker, Any]:
        """Build schema fields for water heater entities."""
        return {
            vol.Optional("heater_type", default="electric"): vol.In(
                ["electric", "gas", "solar", "heat_pump", "tankless"]
            ),
            vol.Optional("current_temperature", default=25): vol.All(
                vol.Coerce(float), vol.Range(min=5, max=50)
            ),
            vol.Optional("target_temperature", default=60): vol.All(
                vol.Coerce(float), vol.Range(min=30, max=90)
            ),
            vol.Optional("tank_capacity", default=80): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=10,
                    max=200,
                    step=5,
                    unit_of_measurement="L",
                    mode=selector.NumberSelectorMode.SLIDER,
                )
            ),
            vol.Optional("efficiency", default=0.9): vol.All(
                vol.Coerce(float), vol.Range(min=0.1, max=1.0)
            ),
        }

    @staticmethod
    def _build_humidifier_schema() -> dict[vol.Marker, Any]:
        """Build schema fields for humidifier entities."""
        return {
            vol.Optional("humidifier_type", default="ultrasonic"): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        {"value": "ultrasonic", "label": "ultrasonic"},
                        {"value": "evaporative", "label": "evaporative"},
                        {"value": "steam", "label": "steam"},
                        {"value": "impeller", "label": "impeller"},
                        {"value": "warm_mist", "label": "warm_mist"},
                    ],
                    mode=selector.SelectSelectorMode.DROPDOWN,
                    translation_key="humidifier_type",
                )
            ),
            vol.Optional("current_humidity", default=45): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=20,
                    max=90,
                    step=1,
                    unit_of_measurement="%",
                    mode=selector.NumberSelectorMode.SLIDER,
                )
            ),
            vol.Optional("target_humidity", default=60): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=30,
                    max=90,
                    step=1,
                    unit_of_measurement="%",
                    mode=selector.NumberSelectorMode.SLIDER,
                )
            ),
            vol.Optional("water_level", default=80): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0,
                    max=100,
                    step=5,
                    unit_of_measurement="%",
                    mode=selector.NumberSelectorMode.SLIDER,
                )
            ),
            vol.Optional("tank_capacity", default=4.0): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=1.0,
                    max=10.0,
                    step=0.5,
                    unit_of_measurement="L",
                    mode=selector.NumberSelectorMode.SLIDER,
                )
            ),
        }

    @staticmethod
    def _build_air_purifier_schema() -> dict[vol.Marker, Any]:
        """Build schema fields for air purifier entities."""
        return {
            vol.Optional("purifier_type", default="hepa"): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[
                        {"value": "hepa", "label": "hepa"},
                        {"value": "activated_carbon", "label": "activated_carbon"},
                        {"value": "uv_c", "label": "uv_c"},
                        {"value": "ionic", "label": "ionic"},
                        {"value": "ozone", "label": "ozone"},
                        {"value": "hybrid", "label": "hybrid"},
                    ],
                    mode=selector.SelectSelectorMode.DROPDOWN,
                    translation_key="purifier_type",
                )
            ),
            vol.Optional("room_volume", default=50): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=10,
                    max=200,
                    step=5,
                    unit_of_measurement="m³",
                    mode=selector.NumberSelectorMode.SLIDER,
                )
            ),
            vol.Optional("pm25", default=35): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0,
                    max=500,
                    step=1,
                    unit_of_measurement="µg/m³",
                    mode=selector.NumberSelectorMode.SLIDER,
                )
            ),
            vol.Optional("pm10", default=50): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0,
                    max=600,
                    step=1,
                    unit_of_measurement="µg/m³",
                    mode=selector.NumberSelectorMode.SLIDER,
                )
            ),
            vol.Optional("filter_life", default=80): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=0,
                    max=100,
                    step=5,
                    unit_of_measurement="%",
                    mode=selector.NumberSelectorMode.SLIDER,
                )
            ),
        }

    @staticmethod
    def _build_weather_schema() -> dict[vol.Marker, Any]:
        """Build schema fields for weather entities."""
        return {
            vol.Optional("weather_station_type", default="home"): vol.In(
                ["basic", "professional", "home", "outdoor", "marine"]
            ),
            vol.Optional("temperature_unit", default="celsius"): vol.In(
                ["celsius", "fahrenheit"]
            ),
            vol.Optional("wind_speed_unit", default="kmh"): vol.In(
                ["kmh", "mph", "ms"]
            ),
            vol.Optional("pressure_unit", default="hPa"): vol.In(
                ["hPa", "inHg", "mmHg"]
            ),
            vol.Optional("visibility_unit", default="km"): vol.In(
                ["km", "miles"]
            ),
        }


# =============================================================================
# Schema Builders Registry
# =============================================================================

SCHEMA_BUILDERS: dict[str, SchemaBuilderFunc] = {
    DEVICE_TYPE_LIGHT: SchemaFactory._build_light_schema,
    DEVICE_TYPE_SWITCH: SchemaFactory._build_switch_schema,
    DEVICE_TYPE_CLIMATE: SchemaFactory._build_climate_schema,
    DEVICE_TYPE_COVER: SchemaFactory._build_cover_schema,
    DEVICE_TYPE_FAN: SchemaFactory._build_fan_schema,
    DEVICE_TYPE_SENSOR: SchemaFactory._build_sensor_schema,
    DEVICE_TYPE_BINARY_SENSOR: SchemaFactory._build_binary_sensor_schema,
    DEVICE_TYPE_BUTTON: SchemaFactory._build_button_schema,
    DEVICE_TYPE_SCENE: SchemaFactory._build_scene_schema,
    DEVICE_TYPE_MEDIA_PLAYER: SchemaFactory._build_media_player_schema,
    DEVICE_TYPE_VACUUM: SchemaFactory._build_vacuum_schema,
    DEVICE_TYPE_CAMERA: SchemaFactory._build_camera_schema,
    DEVICE_TYPE_LOCK: SchemaFactory._build_lock_schema,
    DEVICE_TYPE_VALVE: SchemaFactory._build_valve_schema,
    DEVICE_TYPE_WATER_HEATER: SchemaFactory._build_water_heater_schema,
    DEVICE_TYPE_HUMIDIFIER: SchemaFactory._build_humidifier_schema,
    DEVICE_TYPE_AIR_PURIFIER: SchemaFactory._build_air_purifier_schema,
    DEVICE_TYPE_WEATHER: SchemaFactory._build_weather_schema,
}


def get_schema_builder(device_type: str) -> SchemaBuilderFunc | None:
    """Get the schema builder function for a device type.

    Args:
        device_type: The device type key (e.g., "light", "switch")

    Returns:
        The schema builder function if found, None otherwise
    """
    return SCHEMA_BUILDERS.get(device_type)


def get_supported_device_types() -> list[str]:
    """Get list of device types that have schema builders.

    Returns:
        List of device type keys with registered schema builders
    """
    return list(SCHEMA_BUILDERS.keys())
