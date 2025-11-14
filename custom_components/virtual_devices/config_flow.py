"""Config flow for Virtual Devices Multi integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector
from homeassistant.helpers import translation
import homeassistant.helpers.config_validation as cv

from .const import (
    AIR_PURIFIER_TYPES,
    BINARY_SENSOR_TYPES,
    BUTTON_TYPES,
    CAMERA_TYPES,
    CONF_BRIGHTNESS,
    CONF_COLOR_TEMP,
    CONF_DEVICE_NAME,
    CONF_DEVICE_TYPE,
    CONF_EFFECT,
    CONF_ENTITIES,
    CONF_ENTITY_COUNT,
    CONF_ENTITY_NAME,
    CONF_LOCK_BATTERY_LEVEL,
    CONF_MEDIA_SOURCE_LIST,
    CONF_RGB,
    COVER_TYPES,
    DEFAULT_ENTITY_COUNT,
    DEVICE_TYPES,
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
    DEVICE_TYPE_VALVE,
    DEVICE_TYPE_VACUUM,
    DEVICE_TYPE_WATER_HEATER,
    DEVICE_TYPE_WEATHER,
    DOMAIN,
    HUMIDIFIER_TYPES,
    LOCK_TYPES,
    MEDIA_PLAYER_TYPES,
    SENSOR_TYPES,
    VALVE_TYPES,
    VACUUM_FAN_SPEEDS,
    VACUUM_STATUS_TYPES,
    WATER_HEATER_TYPES,
    WEATHER_STATION_TYPES,
)

_LOGGER = logging.getLogger(__name__)


class VirtualDevicesMultiConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Virtual Devices Multi."""

    VERSION = 1

    def __init__(self):
        """Initialize the config flow."""
        self._device_name: str | None = None
        self._device_type: str | None = None
        self._entity_count: int = DEFAULT_ENTITY_COUNT
        self._entities: list[dict[str, Any]] = []
        self._current_entity_index: int = 0
        self._show_back_button: bool = False

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step - device basic info."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Validate input data
            device_name = user_input.get(CONF_DEVICE_NAME, "").strip()
            device_type = user_input.get(CONF_DEVICE_TYPE)
            entity_count = user_input.get(CONF_ENTITY_COUNT, DEFAULT_ENTITY_COUNT)

            # Validate device name
            if not device_name:
                errors[CONF_DEVICE_NAME] = "device_name_required"
            # Validate device type
            elif device_type not in DEVICE_TYPES:
                errors[CONF_DEVICE_TYPE] = "invalid_device_type"
            # Validate entity count - simplified version for debugging
            elif True:  # Ensure this validation also uses elif structure
                _LOGGER.info(f"[DEBUG] Entity count validation - received: {entity_count}, type: {type(entity_count)}")

                # Temporary: skip complex validation, only check basic range
                try:
                    # Ensure it's a number
                    if entity_count is None:
                        entity_count = 1

                    # Convert to integer
                    entity_count = int(entity_count)
                    _LOGGER.info(f"[DEBUG] Entity count after conversion: {entity_count}")

                    # Simple range check
                    if 1 <= entity_count <= 10:
                        _LOGGER.info(f"[DEBUG] Entity count validation PASSED: {entity_count}")
                    else:
                        _LOGGER.error(f"[DEBUG] Entity count validation FAILED - out of range: {entity_count}")
                        errors[CONF_ENTITY_COUNT] = "invalid_entity_count"

                except Exception as e:
                    _LOGGER.error(f"[DEBUG] Entity count validation FAILED - exception: {e}")
                    # Temporary: do not set error, use default value
                    entity_count = 1
                    _LOGGER.info(f"[DEBUG] Using default entity count: {entity_count}")

            # If no errors, save data and continue
            if not errors:
                self._device_name = device_name
                self._device_type = device_type
                self._entity_count = entity_count
                self._entities = []
                self._current_entity_index = 0

                # Jump to configure first entity
                return await self.async_step_entity_config()

        # Debug info: log available device types
        _LOGGER.info(f"Available device types: {list(DEVICE_TYPES.keys())}")
        _LOGGER.info(f"Total device types count: {len(DEVICE_TYPES)}")

        # Default to select light
        default_device_type = DEVICE_TYPE_LIGHT
        # Generate default name based on selected device type
        default_device_name = "Virtual Entity 1"

        _LOGGER.info(f"Device type options: {list(DEVICE_TYPES.keys())}")

        # 构建设备类型选项列表，手动获取翻译
        # SelectSelector 的 options 应该是列表格式，每个选项包含 value 和 label
        device_type_options = []
        translations = await translation.async_get_translations(
            self.hass,
            self.hass.config.language,
            "config",
            [DOMAIN]
        )
        
        for device_key in DEVICE_TYPES.keys():
            # 构建翻译键 - Home Assistant 翻译键格式
            # 格式: component.{domain}.config.step.{step_id}.data.{field_name}.options.{option_value}
            translation_key = f"component.{DOMAIN}.config.step.user.data.{CONF_DEVICE_TYPE}.options.{device_key}"
            
            # 尝试多种可能的翻译键格式
            possible_keys = [
                translation_key,
                f"config.step.user.data.{CONF_DEVICE_TYPE}.options.{device_key}",
                f"{CONF_DEVICE_TYPE}.options.{device_key}",
            ]
            
            translated_label = device_key.capitalize().replace('_', ' ')
            for key in possible_keys:
                if key in translations:
                    translated_label = translations[key]
                    _LOGGER.debug(f"Found translation for '{device_key}': {translated_label} (key: {key})")
                    break
            
            if translated_label == device_key.capitalize().replace('_', ' '):
                _LOGGER.warning(f"No translation found for device type '{device_key}', using default")
            
            # 构建选项字典，包含 value 和 label
            device_type_options.append({
                "value": device_key,
                "label": translated_label
            })

        data_schema = vol.Schema(
            {
                vol.Required(CONF_DEVICE_NAME, default=default_device_name): str,
                vol.Required(
                    CONF_DEVICE_TYPE,
                    default=default_device_type
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        # 使用列表格式，每个选项包含 value 和 label
                        options=device_type_options,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                        multiple=False
                    )
                ),
                vol.Required(CONF_ENTITY_COUNT, default=1): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1,
                        max=10,
                        step=1,
                        mode=selector.NumberSelectorMode.SLIDER
                    )
                ),
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "device_types": ", ".join(DEVICE_TYPES.keys())
            },
        )

    async def async_step_entity_config(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Configure each entity."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Check if "skip remaining" button is clicked
            if user_input.get("skip_remaining", False):
                # Generate default config for remaining entities
                while self._current_entity_index < self._entity_count:
                    entity_num = self._current_entity_index + 1
                    default_name = f"{self._device_name}_{DEVICE_TYPES[self._device_type]}_{entity_num}"

                    entity_config = {CONF_ENTITY_NAME: default_name}

                    # 根据设备类型添加默认配置
                    if self._device_type == DEVICE_TYPE_LIGHT:
                        entity_config.update({
                            CONF_BRIGHTNESS: True,  # 快速模式默认启用亮度
                            CONF_COLOR_TEMP: False,  # 快速模式默认关闭色温
                            CONF_RGB: False,  # 快速模式默认关闭RGB
                            CONF_EFFECT: False,  # 快速模式默认关闭特效
                        })
                    elif self._device_type == DEVICE_TYPE_COVER:
                        entity_config["cover_type"] = "curtain"
                    elif self._device_type == DEVICE_TYPE_SENSOR:
                        entity_config["sensor_type"] = "temperature"
                    elif self._device_type == DEVICE_TYPE_BINARY_SENSOR:
                        entity_config["sensor_type"] = "motion"
                    elif self._device_type == DEVICE_TYPE_BUTTON:
                        entity_config["button_type"] = "generic"
                    elif self._device_type == DEVICE_TYPE_MEDIA_PLAYER:
                        entity_config.update({
                            "media_player_type": "speaker",
                            CONF_MEDIA_SOURCE_LIST: ["local_music", "online_radio"],
                            "supports_seek": False,
                        })
                    elif self._device_type == DEVICE_TYPE_VACUUM:
                        entity_config.update({
                            "vacuum_status": "docked",
                            "fan_speed": "medium",
                            "battery_level": 100,
                        })
                    elif self._device_type == DEVICE_TYPE_CAMERA:
                        entity_config.update({
                            "camera_type": "indoor",
                            "recording": False,
                            "motion_detection": True,
                            "night_vision": True,
                        })
                    elif self._device_type == DEVICE_TYPE_LOCK:
                        entity_config.update({
                            "lock_type": "smart_lock",
                            "access_code": "1234",
                            "auto_lock": True,
                            "auto_lock_delay": 30,
                        })
                    elif self._device_type == DEVICE_TYPE_VALVE:
                        entity_config.update({
                            "valve_type": "water_valve",
                            "valve_size": 25,
                            "reports_position": True,
                        })
                    elif self._device_type == DEVICE_TYPE_WATER_HEATER:
                        entity_config.update({
                            "heater_type": "electric",
                            "current_temperature": 25,
                            "target_temperature": 60,
                            "tank_capacity": 80,
                            "efficiency": 0.9,
                        })
                    elif self._device_type == DEVICE_TYPE_HUMIDIFIER:
                        entity_config.update({
                            "humidifier_type": "ultrasonic",
                            "current_humidity": 45,
                            "target_humidity": 60,
                            "water_level": 80,
                            "tank_capacity": 4.0,
                        })
                    elif self._device_type == DEVICE_TYPE_AIR_PURIFIER:
                        entity_config.update({
                            "purifier_type": "hepa",
                            "room_volume": 50,
                            "pm25": 35,
                            "pm10": 50,
                            "filter_life": 80,
                        })
                    elif self._device_type == DEVICE_TYPE_WEATHER:
                        entity_config.update({
                            "weather_station_type": "home",
                            "temperature_unit": "celsius",
                            "wind_speed_unit": "kmh",
                            "pressure_unit": "hPa",
                            "visibility_unit": "km",
                        })
                    # 场景类型不需要额外配置

                    self._entities.append(entity_config)
                    self._current_entity_index += 1

                # 创建配置条目
                return self.async_create_entry(
                    title=f"{self._device_name} ({DEVICE_TYPES[self._device_type]})",
                    data={
                        CONF_DEVICE_NAME: self._device_name,
                        CONF_DEVICE_TYPE: self._device_type,
                        CONF_ENTITY_COUNT: self._entity_count,
                        CONF_ENTITIES: self._entities,
                    },
                )

            # 保存当前实体配置
            entity_config = {
                CONF_ENTITY_NAME: user_input[CONF_ENTITY_NAME],
            }

            # 根据设备类型添加额外配置
            if self._device_type == DEVICE_TYPE_LIGHT:
                entity_config.update(
                    {
                        CONF_BRIGHTNESS: user_input.get(CONF_BRIGHTNESS, True),
                        CONF_COLOR_TEMP: user_input.get(CONF_COLOR_TEMP, False),  # 只有用户选择时才启用
                        CONF_RGB: user_input.get(CONF_RGB, False),  # 只有用户选择时才启用
                        CONF_EFFECT: user_input.get(CONF_EFFECT, False),
                    }
                )
            elif self._device_type == DEVICE_TYPE_COVER:
                entity_config["cover_type"] = user_input.get("cover_type", "curtain")
            elif self._device_type == DEVICE_TYPE_SENSOR:
                entity_config["sensor_type"] = user_input.get(
                    "sensor_type", "temperature"
                )
            elif self._device_type == DEVICE_TYPE_BINARY_SENSOR:
                entity_config["sensor_type"] = user_input.get("sensor_type", "motion")
            elif self._device_type == DEVICE_TYPE_BUTTON:
                entity_config["button_type"] = user_input.get("button_type", "generic")
            elif self._device_type == DEVICE_TYPE_MEDIA_PLAYER:
                # 处理媒体源列表 - 从逗号分隔的字符串转换为列表
                media_source_str = user_input.get(CONF_MEDIA_SOURCE_LIST, "local_music,online_radio")
                if isinstance(media_source_str, str):
                    # 分割字符串并去除空白
                    media_source_list = [s.strip() for s in media_source_str.split(",") if s.strip()]
                    if not media_source_list:
                        media_source_list = ["local_music"]
                elif isinstance(media_source_str, list):
                    # 如果已经是列表，直接使用
                    media_source_list = media_source_str
                else:
                    media_source_list = ["local_music"]
                
                entity_config.update(
                    {
                        "media_player_type": user_input.get("media_player_type", "speaker"),
                        CONF_MEDIA_SOURCE_LIST: media_source_list,
                        "supports_seek": user_input.get("supports_seek", False),
                    }
                )
            elif self._device_type == DEVICE_TYPE_VACUUM:
                entity_config.update(
                    {
                        "vacuum_status": user_input.get("vacuum_status", "docked"),
                        "fan_speed": user_input.get("fan_speed", "medium"),
                        "battery_level": user_input.get("battery_level", 100),
                    }
                )
            elif self._device_type == DEVICE_TYPE_CAMERA:
                entity_config.update(
                    {
                        "camera_type": user_input.get("camera_type", "indoor"),
                        "recording": user_input.get("recording", False),
                        "motion_detection": user_input.get("motion_detection", True),
                        "night_vision": user_input.get("night_vision", True),
                    }
                )
            elif self._device_type == DEVICE_TYPE_LOCK:
                entity_config.update(
                    {
                        "lock_type": user_input.get("lock_type", "smart_lock"),
                        "access_code": user_input.get("access_code", "1234"),
                        "auto_lock": user_input.get("auto_lock", True),
                        "auto_lock_delay": user_input.get("auto_lock_delay", 30),
                    }
                )
            elif self._device_type == DEVICE_TYPE_VALVE:
                entity_config.update(
                    {
                        "valve_type": user_input.get("valve_type", "water_valve"),
                        "valve_size": user_input.get("valve_size", 25),
                        "reports_position": user_input.get("reports_position", True),
                    }
                )
            elif self._device_type == DEVICE_TYPE_WATER_HEATER:
                entity_config.update(
                    {
                        "heater_type": user_input.get("heater_type", "electric"),
                        "current_temperature": user_input.get("current_temperature", 25),
                        "target_temperature": user_input.get("target_temperature", 60),
                        "tank_capacity": user_input.get("tank_capacity", 80),
                        "efficiency": user_input.get("efficiency", 0.9),
                    }
                )
            elif self._device_type == DEVICE_TYPE_HUMIDIFIER:
                entity_config.update(
                    {
                        "humidifier_type": user_input.get("humidifier_type", "ultrasonic"),
                        "current_humidity": user_input.get("current_humidity", 45),
                        "target_humidity": user_input.get("target_humidity", 60),
                        "water_level": user_input.get("water_level", 80),
                        "tank_capacity": user_input.get("tank_capacity", 4.0),
                    }
                )
            elif self._device_type == DEVICE_TYPE_AIR_PURIFIER:
                entity_config.update(
                    {
                        "purifier_type": user_input.get("purifier_type", "hepa"),
                        "room_volume": user_input.get("room_volume", 50),
                        "pm25": user_input.get("pm25", 35),
                        "pm10": user_input.get("pm10", 50),
                        "filter_life": user_input.get("filter_life", 80),
                    }
                )
            elif self._device_type == DEVICE_TYPE_WEATHER:
                entity_config.update(
                    {
                        "weather_station_type": user_input.get("weather_station_type", "home"),
                        "temperature_unit": user_input.get("temperature_unit", "celsius"),
                        "wind_speed_unit": user_input.get("wind_speed_unit", "kmh"),
                        "pressure_unit": user_input.get("pressure_unit", "hPa"),
                        "visibility_unit": user_input.get("visibility_unit", "km"),
                    }
                )
            # 场景类型不需要额外配置

            self._entities.append(entity_config)
            self._current_entity_index += 1

            # 检查是否还有更多实体需要配置
            if self._current_entity_index < self._entity_count:
                return await self.async_step_entity_config()

            # 所有实体配置完成，创建配置条目
            return self.async_create_entry(
                title=f"{self._device_name} ({DEVICE_TYPES[self._device_type]})",
                data={
                    CONF_DEVICE_NAME: self._device_name,
                    CONF_DEVICE_TYPE: self._device_type,
                    CONF_ENTITY_COUNT: self._entity_count,
                    CONF_ENTITIES: self._entities,
                },
            )

        # 调试信息：记录当前配置的设备类型
        _LOGGER.info(f"Configuring entity for device type: {self._device_type}")
        _LOGGER.info(f"Device type name: {DEVICE_TYPES.get(self._device_type, 'Unknown')}")

        # 构建当前实体的配置表单
        entity_num = self._current_entity_index + 1
        default_name = f"{self._device_name}_{DEVICE_TYPES[self._device_type]}_{entity_num}"

        # 基础配置
        schema_dict = {
            vol.Required(CONF_ENTITY_NAME, default=default_name): str,
        }

        # 根据设备类型添加特定配置
        if self._device_type == DEVICE_TYPE_LIGHT:
            schema_dict.update(
                {
                    vol.Optional(CONF_BRIGHTNESS, default=True): bool,  # 默认启用亮度
                    vol.Optional(CONF_COLOR_TEMP, default=False): bool,  # 默认关闭色温
                    vol.Optional(CONF_RGB, default=False): bool,  # 默认关闭RGB
                    vol.Optional(CONF_EFFECT, default=False): bool,  # 默认关闭特效
                }
            )
        elif self._device_type == DEVICE_TYPE_COVER:
            schema_dict.update({
                vol.Optional("cover_type", default="curtain"): vol.In(["curtain", "blind", "shade", "garage", "gate"]),
            })
        elif self._device_type == DEVICE_TYPE_SENSOR:
            schema_dict.update({
                vol.Optional("sensor_type", default="temperature"): vol.In(["temperature", "humidity", "pressure", "light", "motion", "air_quality"]),
            })
        elif self._device_type == DEVICE_TYPE_BINARY_SENSOR:
            schema_dict.update({
                vol.Optional("sensor_type", default="motion"): vol.In(["motion", "door", "window", "smoke", "gas", "water_leak"]),
            })
        elif self._device_type == DEVICE_TYPE_BUTTON:
            schema_dict.update({
                vol.Optional("button_type", default="generic"): vol.In(["generic", "doorbell", "emergency", "reset"]),
            })
        elif self._device_type == DEVICE_TYPE_MEDIA_PLAYER:
            schema_dict.update(
                {
                    vol.Optional("media_player_type", default="speaker"): vol.In(["speaker", "tv", "receiver", "soundbar"]),
                    # 使用逗号分隔的字符串，然后在处理时转换为列表
                    vol.Optional(CONF_MEDIA_SOURCE_LIST, default="local_music,online_radio"): str,
                    vol.Optional("supports_seek", default=False): bool,
                }
            )
        elif self._device_type == DEVICE_TYPE_VACUUM:
            schema_dict.update(
                {
                    vol.Optional("vacuum_status", default="docked"): vol.In(["docked", "cleaning", "paused", "returning", "error"]),
                    vol.Optional("fan_speed", default="medium"): vol.In(["quiet", "low", "medium", "high", "max"]),
                    vol.Optional("battery_level", default=100): int,
                }
            )
        elif self._device_type == DEVICE_TYPE_CAMERA:
            schema_dict.update(
                {
                    vol.Optional("camera_type", default="indoor"): vol.In(["indoor", "outdoor", "doorbell", "baby_monitor"]),
                    vol.Optional("recording", default=False): bool,
                    vol.Optional("motion_detection", default=True): bool,
                    vol.Optional("night_vision", default=True): bool,
                }
            )
        elif self._device_type == DEVICE_TYPE_LOCK:
            schema_dict.update(
                {
                    vol.Optional("lock_type", default="smart_lock"): vol.In(["smart_lock", "deadbolt", "keypad", "fingerprint"]),
                    vol.Optional("access_code", default="1234"): str,
                    vol.Optional("auto_lock", default=True): bool,
                    vol.Optional("auto_lock_delay", default=30): vol.All(vol.Coerce(int), vol.Range(min=5, max=300)),
                }
            )
        elif self._device_type == DEVICE_TYPE_VALVE:
            schema_dict.update(
                {
                    vol.Optional("valve_type", default="water_valve"): vol.In(["water_valve", "gas_valve", "irrigation", "zone_valve"]),
                    vol.Optional("valve_size", default=25): vol.All(vol.Coerce(int), vol.Range(min=5, max=200)),
                    vol.Optional("reports_position", default=True): bool,
                }
            )
        elif self._device_type == DEVICE_TYPE_WATER_HEATER:
            schema_dict.update(
                {
                    vol.Optional("heater_type", default="electric"): vol.In(["electric", "gas", "solar", "heat_pump", "tankless"]),
                    vol.Optional("current_temperature", default=25): vol.All(vol.Coerce(float), vol.Range(min=5, max=50)),
                    vol.Optional("target_temperature", default=60): vol.All(vol.Coerce(float), vol.Range(min=30, max=90)),
                    vol.Optional("tank_capacity", default=80): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=10, max=200, step=5, unit_of_measurement="L",
                            mode=selector.NumberSelectorMode.SLIDER
                        )
                    ),
                    vol.Optional("efficiency", default=0.9): vol.All(vol.Coerce(float), vol.Range(min=0.1, max=1.0)),
                }
            )
        elif self._device_type == DEVICE_TYPE_HUMIDIFIER:
            schema_dict.update(
                {
                    vol.Optional("humidifier_type", default="ultrasonic"): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            # 使用字典列表格式确保正确序列化
                            options=[
                                {"value": "ultrasonic", "label": "ultrasonic"},
                                {"value": "evaporative", "label": "evaporative"},
                                {"value": "steam", "label": "steam"},
                                {"value": "impeller", "label": "impeller"},
                                {"value": "warm_mist", "label": "warm_mist"},
                            ],
                            mode=selector.SelectSelectorMode.DROPDOWN,
                            translation_key="humidifier_type"
                        )
                    ),
                    vol.Optional("current_humidity", default=45): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=20, max=90, step=1, unit_of_measurement="%",
                            mode=selector.NumberSelectorMode.SLIDER
                        )
                    ),
                    vol.Optional("target_humidity", default=60): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=30, max=90, step=1, unit_of_measurement="%",
                            mode=selector.NumberSelectorMode.SLIDER
                        )
                    ),
                    vol.Optional("water_level", default=80): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=0, max=100, step=5, unit_of_measurement="%",
                            mode=selector.NumberSelectorMode.SLIDER
                        )
                    ),
                    vol.Optional("tank_capacity", default=4.0): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=1.0, max=10.0, step=0.5, unit_of_measurement="L",
                            mode=selector.NumberSelectorMode.SLIDER
                        )
                    ),
                }
            )
        elif self._device_type == DEVICE_TYPE_AIR_PURIFIER:
            schema_dict.update(
                {
                    vol.Optional("purifier_type", default="hepa"): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            # 使用字典列表格式确保正确序列化
                            options=[
                                {"value": "hepa", "label": "hepa"},
                                {"value": "activated_carbon", "label": "activated_carbon"},
                                {"value": "uv_c", "label": "uv_c"},
                                {"value": "ionic", "label": "ionic"},
                                {"value": "ozone", "label": "ozone"},
                                {"value": "hybrid", "label": "hybrid"},
                            ],
                            mode=selector.SelectSelectorMode.DROPDOWN,
                            translation_key="purifier_type"
                        )
                    ),
                    vol.Optional("room_volume", default=50): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=10, max=200, step=5, unit_of_measurement="m³",
                            mode=selector.NumberSelectorMode.SLIDER
                        )
                    ),
                    vol.Optional("pm25", default=35): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=0, max=500, step=1, unit_of_measurement="µg/m³",
                            mode=selector.NumberSelectorMode.SLIDER
                        )
                    ),
                    vol.Optional("pm10", default=50): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=0, max=600, step=1, unit_of_measurement="µg/m³",
                            mode=selector.NumberSelectorMode.SLIDER
                        )
                    ),
                    vol.Optional("filter_life", default=80): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=0, max=100, step=5, unit_of_measurement="%",
                            mode=selector.NumberSelectorMode.SLIDER
                        )
                    ),
                }
            )
        elif self._device_type == DEVICE_TYPE_WEATHER:
            schema_dict.update(
                {
                    vol.Optional("weather_station_type", default="home"): vol.In(["basic", "professional", "home", "outdoor", "marine"]),
                    vol.Optional("temperature_unit", default="celsius"): vol.In(["celsius", "fahrenheit"]),
                    vol.Optional("wind_speed_unit", default="kmh"): vol.In(["kmh", "mph", "ms"]),
                    vol.Optional("pressure_unit", default="hPa"): vol.In(["hPa", "inHg", "mmHg"]),
                    vol.Optional("visibility_unit", default="km"): vol.In(["km", "miles"]),
                }
            )
        # 场景类型不需要额外的配置字段

        # Add "skip remaining" option (if there are more entities to configure)
        if self._entity_count - self._current_entity_index > 1:
            schema_dict[vol.Optional("skip_remaining", default=False)] = bool

        data_schema = vol.Schema(schema_dict)

        return self.async_show_form(
            step_id="entity_config",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "entity_number": str(entity_num),
                "total_entities": str(self._entity_count),
                "device_name": self._device_name,
            },
            last_step=self._current_entity_index == self._entity_count - 1,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for Virtual Devices Multi."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        # 显示当前配置
        config_entry = self.config_entry
        device_name = config_entry.data.get(CONF_DEVICE_NAME)
        device_type = config_entry.data.get(CONF_DEVICE_TYPE)
        entity_count = config_entry.data.get(CONF_ENTITY_COUNT)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({}),
            description_placeholders={
                "device_name": device_name,
                "device_type": DEVICE_TYPES.get(device_type, device_type),
                "entity_count": str(entity_count),
            },
        )
