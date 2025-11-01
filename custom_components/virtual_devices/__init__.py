"""Virtual Devices Multi integration for Home Assistant."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntry, DeviceInfo

from .const import DOMAIN, MANUFACTURER, MODEL

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [
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
]


def get_device_info(config_entry: ConfigEntry) -> DeviceInfo:
    """Get device information for this integration."""
    device_name = config_entry.data.get("device_name", "Unknown Device")
    device_type = config_entry.data.get("device_type", "unknown")
    entities_config = config_entry.data.get("entities", [])

    # 获取设备类型名称（使用翻译系统时这里只作记录用）
    from .const import DEVICE_TYPES
    device_type_name = DEVICE_TYPES.get(device_type, device_type)

    # 构建设备详细信息
    device_info = {
        "identifiers": {(DOMAIN, config_entry.entry_id)},
        "name": f"{device_name}",
        "manufacturer": MANUFACTURER,
        "model": _get_device_model(device_type, entities_config),
        "sw_version": "2025.10.0",
    }

    # 添加设备类型信息
    device_info["via_device"] = None
    device_info["configuration_url"] = f"https://github.com/yunuo-intelligence/virtual-devices-multi"

    return DeviceInfo(**device_info)


def _get_device_model(device_type: str, entities_config: list) -> str:
    """Get device model based on device type and configuration."""
    if not entities_config:
        return f"{MODEL}-{device_type.upper()}"

    # 获取第一个实体的具体类型配置
    first_entity = entities_config[0] if entities_config else {}

    if device_type == "air_purifier":
        purifier_type = first_entity.get("purifier_type", "hepa")
        from .const import AIR_PURIFIER_TYPES
        type_name = AIR_PURIFIER_TYPES.get(purifier_type, purifier_type)
        return f"air_purifier-{type_name}"

    elif device_type == "camera":
        camera_type = first_entity.get("camera_type", "indoor")
        from .const import CAMERA_TYPES
        type_name = CAMERA_TYPES.get(camera_type, camera_type)
        return f"camera-{type_name}"

    elif device_type == "humidifier":
        humidifier_type = first_entity.get("humidifier_type", "ultrasonic")
        from .const import HUMIDIFIER_TYPES
        type_name = HUMIDIFIER_TYPES.get(humidifier_type, humidifier_type)
        return f"humidifier-{type_name}"

    else:
        return f"{MODEL}-{device_type.upper()}"


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Virtual Devices Multi from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    # 保存配置数据
    hass.data[DOMAIN][entry.entry_id] = {
        "config": entry.data,
        "entities": {},
        "device_info": get_device_info(entry),
    }

    # 设置所有平台
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
