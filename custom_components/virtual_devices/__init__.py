"""Virtual Devices Multi integration for Home Assistant."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo

from .const import (
    DOMAIN,
    MANUFACTURER,
    MODEL,
    AIR_PURIFIER_TYPES,
    CAMERA_TYPES,
    HUMIDIFIER_TYPES,
    get_device_type_display_name,
)

_LOGGER = logging.getLogger(__name__)

# Supported Home Assistant platforms
PLATFORMS: list[Platform] = [
    Platform.LIGHT,
    Platform.SWITCH,
    Platform.CLIMATE,
    Platform.COVER,
    Platform.FAN,
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.SCENE,
    Platform.MEDIA_PLAYER,
    Platform.VACUUM,
    Platform.WEATHER,
    Platform.CAMERA,
    Platform.LOCK,
    Platform.VALVE,
    Platform.WATER_HEATER,
    Platform.HUMIDIFIER,
    # Note: air_purifier is not a standalone platform, it uses the fan platform
]


def get_device_info(config_entry: ConfigEntry) -> DeviceInfo:
    """Get device information for this integration.

    Args:
        config_entry: The config entry for the device

    Returns:
        DeviceInfo object with device metadata
    """
    device_type: str = config_entry.data.get("device_type", "unknown")
    entities_config: list[dict[str, Any]] = config_entry.data.get("entities", [])

    # Get device name from registry using centralized function
    device_name = get_device_type_display_name(device_type)

    return DeviceInfo(
        identifiers={(DOMAIN, config_entry.entry_id)},
        name=device_name,
        manufacturer=MANUFACTURER,
        model=_get_device_model(device_type, entities_config),
        sw_version="2025.10.0",
        configuration_url="https://github.com/ha-china/virtual_devices",
    )


def _get_device_model(device_type: str, entities_config: list[dict[str, Any]]) -> str:
    """Get device model based on device type and configuration.

    Args:
        device_type: The type of device
        entities_config: List of entity configurations

    Returns:
        Model string for the device
    """
    if not entities_config:
        return f"{MODEL}-{device_type.upper()}"

    first_entity = entities_config[0]

    # Map device types to their specific type fields and type dictionaries
    type_mappings: dict[str, tuple[str, dict[str, str], str]] = {
        "air_purifier": ("purifier_type", AIR_PURIFIER_TYPES, "hepa"),
        "camera": ("camera_type", CAMERA_TYPES, "indoor"),
        "humidifier": ("humidifier_type", HUMIDIFIER_TYPES, "ultrasonic"),
    }

    if device_type in type_mappings:
        field_name, type_dict, default = type_mappings[device_type]
        specific_type = first_entity.get(field_name, default)
        type_name = type_dict.get(specific_type, specific_type)
        return f"{device_type}-{type_name}"

    return f"{MODEL}-{device_type.upper()}"


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Virtual Devices Multi from a config entry.

    Args:
        hass: Home Assistant instance
        entry: Config entry to set up

    Returns:
        True if setup was successful
    """
    hass.data.setdefault(DOMAIN, {})

    hass.data[DOMAIN][entry.entry_id] = {
        "config": entry.data,
        "entities": {},
        "device_info": get_device_info(entry),
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    device_type = entry.data.get("device_type", "unknown")
    _LOGGER.info("Successfully set up virtual device: %s", device_type)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry.

    Args:
        hass: Home Assistant instance
        entry: Config entry to unload

    Returns:
        True if unload was successful
    """
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
