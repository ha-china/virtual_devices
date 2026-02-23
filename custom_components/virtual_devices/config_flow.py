"""Config flow for Virtual Devices Multi integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector
from homeassistant.helpers import translation

from .const import (
    CONF_DEVICE_NAME,
    CONF_DEVICE_TYPE,
    CONF_ENTITIES,
    CONF_ENTITY_COUNT,
    CONF_ENTITY_NAME,
    CONF_MEDIA_SOURCE_LIST,
    DEFAULT_ENTITY_COUNT,
    DEVICE_TYPES,
    DEVICE_TYPE_LIGHT,
    DOMAIN,
    DEVICE_TYPE_REGISTRY,
    get_device_type_display_name,
    get_default_entity_config,
)
from .schema_factory import SchemaFactory

_LOGGER = logging.getLogger(__name__)


# Type definitions for config flow
UserInputDict = dict[str, Any]
ErrorsDict = dict[str, str]


class VirtualDevicesMultiConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Virtual Devices Multi."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._device_name: str | None = None
        self._device_type: str | None = None
        self._entity_count: int = DEFAULT_ENTITY_COUNT
        self._entities: list[dict[str, Any]] = []
        self._current_entity_index: int = 0
        self._show_back_button: bool = False

    async def async_step_user(
        self, user_input: UserInputDict | None = None
    ) -> FlowResult:
        """Handle the initial step - device basic info."""
        errors: ErrorsDict = {}

        if user_input is not None:
            device_type = user_input.get(CONF_DEVICE_TYPE)
            entity_count = user_input.get(CONF_ENTITY_COUNT, DEFAULT_ENTITY_COUNT)

            # Auto-generate device name based on device type
            device_name = get_device_type_display_name(device_type)

            # Validate device type
            if device_type not in DEVICE_TYPE_REGISTRY:
                errors[CONF_DEVICE_TYPE] = "invalid_device_type"
            else:
                # Validate entity count
                try:
                    entity_count = int(entity_count) if entity_count is not None else 1
                    if not 1 <= entity_count <= 10:
                        errors[CONF_ENTITY_COUNT] = "invalid_entity_count"
                except (ValueError, TypeError):
                    entity_count = 1

            if not errors:
                self._device_name = device_name
                self._device_type = device_type
                self._entity_count = entity_count
                self._entities = []
                self._current_entity_index = 0
                return await self.async_step_entity_config()

        # Build device type options with translations
        device_type_options = await self._build_device_type_options()

        data_schema = vol.Schema(
            {
                vol.Required(
                    CONF_DEVICE_TYPE,
                    default=DEVICE_TYPE_LIGHT
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
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
                "device_types": ", ".join(DEVICE_TYPE_REGISTRY.keys())
            },
        )

    async def _build_device_type_options(self) -> list[dict[str, str]]:
        """Build device type options list with translations."""
        translations = await translation.async_get_translations(
            self.hass,
            self.hass.config.language,
            "config",
            [DOMAIN]
        )

        device_type_options: list[dict[str, str]] = []
        for device_key in DEVICE_TYPE_REGISTRY.keys():
            # Try multiple translation key formats
            possible_keys = [
                f"component.{DOMAIN}.config.step.user.data.{CONF_DEVICE_TYPE}.options.{device_key}",
                f"config.step.user.data.{CONF_DEVICE_TYPE}.options.{device_key}",
                f"{CONF_DEVICE_TYPE}.options.{device_key}",
            ]

            translated_label = device_key.capitalize().replace('_', ' ')
            for key in possible_keys:
                if key in translations:
                    translated_label = translations[key]
                    break

            device_type_options.append({
                "value": device_key,
                "label": translated_label
            })

        return device_type_options

    async def async_step_entity_config(
        self, user_input: UserInputDict | None = None
    ) -> FlowResult:
        """Configure each entity."""
        errors: ErrorsDict = {}

        if user_input is not None:
            # Check if "skip remaining" button is clicked
            if user_input.get("skip_remaining", False):
                return await self._skip_remaining_entities()

            # Save current entity configuration
            entity_config = self._build_entity_config(user_input)
            self._entities.append(entity_config)
            self._current_entity_index += 1

            # Check if more entities need configuration
            if self._current_entity_index < self._entity_count:
                return await self.async_step_entity_config()

            # All entities configured, create entry
            return self._create_config_entry()

        # Build schema using SchemaFactory
        entity_num = self._current_entity_index + 1
        include_skip = self._entity_count - self._current_entity_index > 1

        data_schema = SchemaFactory.create_entity_schema(
            device_type=self._device_type,
            entity_num=entity_num,
            device_name=self._device_name,
            include_skip_remaining=include_skip,
        )

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

    def _build_entity_config(self, user_input: UserInputDict) -> dict[str, Any]:
        """Build entity configuration from user input."""
        entity_config: dict[str, Any] = {
            CONF_ENTITY_NAME: user_input[CONF_ENTITY_NAME],
        }

        # Get default config for this device type and update with user input
        default_config = get_default_entity_config(self._device_type)

        for key in default_config:
            if key in user_input:
                value = user_input[key]
                # Handle media source list conversion
                if key == CONF_MEDIA_SOURCE_LIST and isinstance(value, str):
                    value = [s.strip() for s in value.split(",") if s.strip()]
                    value = value or ["local_music"]
                entity_config[key] = value
            else:
                entity_config[key] = default_config[key]

        # Handle additional fields not in default_config
        additional_fields = self._get_additional_fields_for_device_type()
        for key in additional_fields:
            if key in user_input and key not in entity_config:
                entity_config[key] = user_input[key]

        return entity_config

    def _get_additional_fields_for_device_type(self) -> list[str]:
        """Get additional field names for the current device type."""
        # These are fields that may be in the schema but not in default_config
        field_map: dict[str, list[str]] = {
            "light": ["brightness", "color_temp", "rgb", "effect"],
            "cover": ["cover_type", "travel_time"],
            "sensor": ["sensor_type"],
            "binary_sensor": ["sensor_type"],
            "button": ["button_type"],
            "climate": ["min_temp", "max_temp", "enable_humidity_sensor"],
            "media_player": ["media_player_type", "media_source_list", "supports_seek"],
            "vacuum": ["vacuum_status", "fan_speed"],
            "camera": ["camera_type", "recording", "motion_detection", "night_vision"],
            "lock": ["lock_type", "access_code", "auto_lock", "auto_lock_delay"],
            "valve": ["valve_type", "valve_size", "reports_position", "travel_time"],
            "water_heater": [
                "heater_type", "current_temperature", "target_temperature",
                "tank_capacity", "efficiency"
            ],
            "humidifier": [
                "humidifier_type", "current_humidity", "target_humidity",
                "water_level", "tank_capacity"
            ],
            "air_purifier": [
                "purifier_type", "room_volume", "pm25", "pm10", "filter_life"
            ],
            "weather": [
                "weather_station_type", "temperature_unit", "wind_speed_unit",
                "pressure_unit", "visibility_unit"
            ],
        }
        return field_map.get(self._device_type, [])

    async def _skip_remaining_entities(self) -> FlowResult:
        """Generate default config for remaining entities and create entry."""
        while self._current_entity_index < self._entity_count:
            entity_num = self._current_entity_index + 1
            device_type_name = DEVICE_TYPES[self._device_type]
            default_name = f"{self._device_name}_{device_type_name}_{entity_num}"

            entity_config: dict[str, Any] = {CONF_ENTITY_NAME: default_name}

            # Get default config from registry
            default_config = get_default_entity_config(self._device_type)
            entity_config.update(default_config)

            self._entities.append(entity_config)
            self._current_entity_index += 1

        return self._create_config_entry()

    def _create_config_entry(self) -> FlowResult:
        """Create the config entry with all entity configurations."""
        return self.async_create_entry(
            title=f"{self._device_name} ({DEVICE_TYPES[self._device_type]})",
            data={
                CONF_DEVICE_NAME: self._device_name,
                CONF_DEVICE_TYPE: self._device_type,
                CONF_ENTITY_COUNT: self._entity_count,
                CONF_ENTITIES: self._entities,
            },
        )
