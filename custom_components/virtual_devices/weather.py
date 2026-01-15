"""Platform for virtual weather integration."""
from __future__ import annotations

import logging
import random
from datetime import datetime, timedelta
from typing import Any

from homeassistant.components.weather import (
    ATTR_FORECAST_CONDITION,
    ATTR_FORECAST_IS_DAYTIME,
    ATTR_FORECAST_NATIVE_PRECIPITATION,
    ATTR_FORECAST_NATIVE_PRESSURE,
    ATTR_FORECAST_NATIVE_TEMP,
    ATTR_FORECAST_NATIVE_TEMP_LOW,
    ATTR_FORECAST_NATIVE_WIND_SPEED,
    Forecast,
    WeatherEntity,
    WeatherEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    UnitOfLength,
    UnitOfPressure,
    UnitOfSpeed,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.storage import Store

from .base_entity import STORAGE_VERSION
from .const import (
    CONF_ENTITIES,
    CONF_ENTITY_NAME,
    DEVICE_TYPE_WEATHER,
    DOMAIN,
    WEATHER_CONDITIONS,
)
from .types import WeatherEntityConfig, WeatherState

_LOGGER = logging.getLogger(__name__)

WEATHER_CONDITIONS_LIST: list[str] = list(WEATHER_CONDITIONS.keys())


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up virtual weather entities."""
    device_type: str | None = config_entry.data.get("device_type")

    if device_type != DEVICE_TYPE_WEATHER:
        return

    device_info: DeviceInfo = hass.data[DOMAIN][config_entry.entry_id]["device_info"]
    entities: list[VirtualWeather] = []
    entities_config: list[WeatherEntityConfig] = config_entry.data.get(CONF_ENTITIES, [])

    for idx, entity_config in enumerate(entities_config):
        entity = VirtualWeather(
            hass,
            config_entry.entry_id,
            entity_config,
            idx,
            device_info,
        )
        entities.append(entity)

    async_add_entities(entities)


class VirtualWeather(WeatherEntity):
    """Representation of a virtual weather station.

    This entity implements state persistence using the same pattern as BaseVirtualEntity.
    """

    _attr_should_poll: bool = True
    _attr_entity_registry_enabled_default: bool = True

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry_id: str,
        entity_config: WeatherEntityConfig,
        index: int,
        device_info: DeviceInfo,
    ) -> None:
        """Initialize the virtual weather station."""
        self._hass = hass
        self._config_entry_id = config_entry_id
        self._entity_config = entity_config
        self._index = index

        entity_name: str = entity_config.get(CONF_ENTITY_NAME, f"weather_{index + 1}")
        self._attr_name = entity_name
        self._attr_unique_id = f"{config_entry_id}_weather_{index}"
        self._attr_device_info = device_info
        self._attr_icon = "mdi:weather-partly-cloudy"

        # Template support
        self._templates: dict[str, Any] = entity_config.get("templates", {})

        # Storage for state persistence
        self._store: Store[WeatherState] = Store(
            hass, STORAGE_VERSION, f"virtual_devices_weather_{config_entry_id}_{index}"
        )

        # Supported features
        self._attr_supported_features: WeatherEntityFeature = (
            WeatherEntityFeature.FORECAST_DAILY | WeatherEntityFeature.FORECAST_HOURLY
        )

        # Unit settings
        self._attr_native_temperature_unit = UnitOfTemperature.CELSIUS
        self._attr_native_pressure_unit = UnitOfPressure.HPA
        self._attr_native_wind_speed_unit = UnitOfSpeed.KILOMETERS_PER_HOUR
        self._attr_native_visibility_unit = UnitOfLength.KILOMETERS
        self._attr_native_precipitation_unit = UnitOfLength.MILLIMETERS

        # Initialize weather state
        self._attr_condition: str = self._get_random_condition()
        self._attr_native_temperature: float = self._generate_temperature()
        self._attr_native_humidity: int = self._generate_humidity()
        self._attr_native_pressure: float = self._generate_pressure()
        self._attr_native_wind_speed: float = self._generate_wind_speed()
        self._attr_wind_bearing: int = random.randint(0, 360)
        self._attr_native_visibility: float = self._generate_visibility()
        self._attr_uv_index: float = self._generate_uv_index()
        self._attr_precipitation: float = self._generate_precipitation()
        self._attr_native_apparent_temperature: float = self._generate_apparent_temperature()
        self._attr_native_dew_point: float = self._generate_dew_point()

        # Forecast data
        self._attr_forecast: list[Forecast] = self._generate_forecast()

        # Cloud coverage and ozone
        self._attr_cloud_coverage: int = random.randint(0, 100)
        self._attr_ozone: float = random.uniform(100, 400)

        # Update time
        self._last_update: datetime = datetime.now()

        _LOGGER.info(f"Virtual weather '{self._attr_name}' initialized")

    def get_default_state(self) -> WeatherState:
        """Return the default state for this entity type."""
        return {
            "condition": "sunny",
            "temperature": 20.0,
            "humidity": 50.0,
            "pressure": 1013.0,
            "wind_speed": 10.0,
        }

    def apply_state(self, state: WeatherState) -> None:
        """Apply loaded state to entity attributes."""
        self._attr_condition = state.get("condition", "sunny")
        self._attr_native_temperature = state.get("temperature", 20.0)
        self._attr_native_humidity = int(state.get("humidity", 50.0))
        self._attr_native_pressure = state.get("pressure", 1013.0)
        self._attr_native_wind_speed = state.get("wind_speed", 10.0)

    def get_current_state(self) -> WeatherState:
        """Get current state for persistence."""
        return {
            "condition": self._attr_condition,
            "temperature": self._attr_native_temperature,
            "humidity": float(self._attr_native_humidity),
            "pressure": self._attr_native_pressure,
            "wind_speed": self._attr_native_wind_speed,
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
                _LOGGER.debug(f"Weather '{self._attr_name}' state loaded")
        except Exception as ex:
            _LOGGER.error(f"Failed to load state for weather '{self._attr_name}': {ex}")
            self.apply_state(self.get_default_state())

    async def async_save_state(self) -> None:
        """Save current state to storage."""
        try:
            data = self.get_current_state()
            await self._store.async_save(data)
            _LOGGER.debug(f"Weather '{self._attr_name}' state saved")
        except Exception as ex:
            _LOGGER.error(f"Failed to save state for weather '{self._attr_name}': {ex}")

    async def async_added_to_hass(self) -> None:
        """Call when entity is added to hass."""
        await super().async_added_to_hass()
        await self.async_load_state()
        self.async_write_ha_state()
        _LOGGER.info(f"Virtual weather '{self._attr_name}' added to Home Assistant")

    def fire_template_event(self, action: str, **kwargs: Any) -> None:
        """Fire a template update event if templates are configured."""
        if self._templates:
            self._hass.bus.async_fire(
                f"{DOMAIN}_weather_template_update",
                {
                    "entity_id": self.entity_id,
                    "device_id": self._config_entry_id,
                    "action": action,
                    **kwargs,
                },
            )

    def _get_random_condition(self) -> str:
        """Get random weather condition based on probability."""
        conditions: list[tuple[str, int]] = [
            ("sunny", 30), ("partlycloudy", 25), ("cloudy", 20),
            ("rainy", 15), ("snowy", 5), ("fog", 3), ("windy", 2),
        ]

        month = datetime.now().month
        if month in [12, 1, 2]:
            conditions.append(("snowy", 15))

        total_weight = sum(weight for _, weight in conditions)
        rand = random.uniform(0, total_weight)
        current = 0

        for condition, weight in conditions:
            current += weight
            if rand <= current:
                return condition

        return "sunny"

    def _generate_temperature(self) -> float:
        """Generate realistic temperature based on current time and season."""
        now = datetime.now()
        hour = now.hour
        month = now.month

        if month in [12, 1, 2]:
            base_temp = random.uniform(-5, 10)
        elif month in [3, 4, 5]:
            base_temp = random.uniform(10, 25)
        elif month in [6, 7, 8]:
            base_temp = random.uniform(20, 35)
        else:
            base_temp = random.uniform(10, 20)

        hour_factor = 1 + 0.3 * abs(hour - 12) / 12 if 6 <= hour <= 18 else 0.7
        temperature = base_temp * hour_factor + random.uniform(-3, 3)
        return round(temperature, 1)

    def _generate_apparent_temperature(self) -> float:
        """Generate apparent temperature."""
        apparent_temp = self._attr_native_temperature
        if self._attr_native_humidity > 70:
            apparent_temp += random.uniform(1, 3)
        if self._attr_native_wind_speed > 20:
            apparent_temp -= random.uniform(2, 5)
        return round(apparent_temp, 1)

    def _generate_pressure(self) -> float:
        """Generate realistic atmospheric pressure."""
        if self._attr_condition in ["rainy", "pouring", "lightning-rainy"]:
            pressure = random.uniform(990, 1010)
        elif self._attr_condition in ["sunny", "partlycloudy"]:
            pressure = random.uniform(1015, 1030)
        else:
            pressure = random.uniform(1000, 1020)
        return round(pressure, 1)

    def _generate_humidity(self) -> int:
        """Generate realistic humidity."""
        if self._attr_condition in ["rainy", "pouring", "fog"]:
            return random.randint(70, 95)
        elif self._attr_condition in ["sunny", "partlycloudy"]:
            return random.randint(30, 60)
        elif self._attr_condition in ["snowy", "snowy-rainy"]:
            return random.randint(60, 80)
        return random.randint(40, 70)

    def _generate_wind_speed(self) -> float:
        """Generate realistic wind speed."""
        if self._attr_condition in ["windy", "windy-variant"]:
            wind_speed = random.uniform(20, 50)
        elif self._attr_condition in ["lightning", "lightning-rainy", "pouring"]:
            wind_speed = random.uniform(15, 35)
        elif self._attr_condition in ["sunny"]:
            wind_speed = random.uniform(0, 15)
        else:
            wind_speed = random.uniform(5, 25)
        return round(wind_speed, 1)

    def _generate_visibility(self) -> float:
        """Generate realistic visibility."""
        if self._attr_condition == "fog":
            return round(random.uniform(0.1, 1), 1)
        elif self._attr_condition in ["rainy", "pouring", "snowy"]:
            return round(random.uniform(1, 10), 1)
        elif self._attr_condition == "sunny":
            return round(random.uniform(10, 20), 1)
        return round(random.uniform(5, 15), 1)

    def _generate_dew_point(self) -> float:
        """Generate dew point temperature."""
        temp = self._attr_native_temperature
        humidity = self._attr_native_humidity
        dew_point = temp - ((100 - humidity) / 5)
        return round(dew_point, 1)

    def _generate_uv_index(self) -> float:
        """Generate UV index based on condition and time."""
        now = datetime.now()
        hour = now.hour
        month = now.month

        if hour < 6 or hour > 18:
            return 0

        uv_factor = {"sunny": 1.0, "partlycloudy": 0.7, "cloudy": 0.3}.get(self._attr_condition, 0.1)

        if month in [6, 7, 8]:
            base_uv = random.uniform(6, 11)
        elif month in [3, 4, 5, 9, 10, 11]:
            base_uv = random.uniform(3, 8)
        else:
            base_uv = random.uniform(1, 4)

        return round(base_uv * uv_factor, 1)

    def _generate_precipitation(self) -> float:
        """Generate precipitation based on weather condition."""
        precip_map: dict[str, tuple[float, float]] = {
            "pouring": (10, 50), "rainy": (1, 10), "lightning-rainy": (5, 25),
            "snowy": (0.5, 5), "snowy-rainy": (0.5, 5),
        }
        if self._attr_condition in precip_map:
            min_val, max_val = precip_map[self._attr_condition]
            return round(random.uniform(min_val, max_val), 1)
        return 0

    def _generate_forecast(self) -> list[Forecast]:
        """Generate weather forecast for next 5 days."""
        forecast: list[Forecast] = []
        base_date = datetime.now()

        for i in range(5):
            forecast_date = base_date + timedelta(days=i + 1)
            condition = self._get_random_condition()

            temp_change = random.uniform(-5, 5)
            high_temp = max(self._attr_native_temperature + temp_change + random.uniform(3, 8), -20)
            low_temp = high_temp - random.uniform(5, 15)

            if condition in ["rainy", "pouring", "lightning-rainy"]:
                precipitation = random.uniform(1, 20)
                pressure = random.uniform(990, 1010)
            elif condition in ["sunny", "partlycloudy"]:
                precipitation = 0
                pressure = random.uniform(1015, 1030)
            else:
                precipitation = random.uniform(0, 5)
                pressure = random.uniform(1000, 1020)

            forecast_data: dict[str, Any] = {
                "datetime": forecast_date,
                "condition": condition,
                ATTR_FORECAST_NATIVE_TEMP: round(high_temp, 1),
                ATTR_FORECAST_NATIVE_TEMP_LOW: round(low_temp, 1),
                ATTR_FORECAST_NATIVE_PRECIPITATION: round(precipitation, 1),
                ATTR_FORECAST_NATIVE_PRESSURE: round(pressure, 1),
                ATTR_FORECAST_NATIVE_WIND_SPEED: round(random.uniform(5, 30), 1),
                ATTR_FORECAST_IS_DAYTIME: 8 <= forecast_date.hour <= 18,
            }

            forecast.append(Forecast(forecast_data))

        return forecast

    async def async_update(self) -> None:
        """Update weather data."""
        if datetime.now() - self._last_update < timedelta(minutes=5):
            return

        if random.random() < 0.3:
            self._attr_condition = self._get_random_condition()

        self._attr_native_temperature = self._generate_temperature()
        self._attr_native_apparent_temperature = self._generate_apparent_temperature()

        self._attr_native_pressure += random.uniform(-2, 2)
        self._attr_native_pressure = round(self._attr_native_pressure, 1)

        self._attr_native_humidity += random.randint(-5, 5)
        self._attr_native_humidity = max(20, min(100, self._attr_native_humidity))

        self._attr_native_wind_speed += random.uniform(-2, 2)
        self._attr_native_wind_speed = max(0, round(self._attr_native_wind_speed, 1))

        self._attr_wind_bearing = (self._attr_wind_bearing + random.randint(-30, 30)) % 360
        self._attr_native_visibility = self._generate_visibility()
        self._attr_uv_index = self._generate_uv_index()
        self._attr_precipitation = self._generate_precipitation()

        if datetime.now().hour == 0 and datetime.now().minute < 10:
            self._attr_forecast = self._generate_forecast()

        self._last_update = datetime.now()
        await self.async_save_state()
        self.async_write_ha_state()

        self.fire_template_event(
            "update",
            condition=self._attr_condition,
            temperature=self._attr_native_temperature,
            humidity=self._attr_native_humidity,
            pressure=self._attr_native_pressure,
            wind_speed=self._attr_native_wind_speed,
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        attrs: dict[str, Any] = {
            "cloud_coverage": self._attr_cloud_coverage,
            "ozone": round(self._attr_ozone, 1),
        }

        if self._attr_condition in ["sunny", "partlycloudy"]:
            attrs["air_quality_index"] = random.randint(20, 80)
        elif self._attr_condition in ["cloudy", "fog"]:
            attrs["air_quality_index"] = random.randint(50, 100)
        else:
            attrs["air_quality_index"] = random.randint(80, 150)

        return attrs

    async def async_forecast_daily(self) -> list[Forecast] | None:
        """Return the daily forecast."""
        if not self._attr_forecast:
            return []

        forecasts: list[Forecast] = []
        for day_data in self._attr_forecast[:7]:
            forecast = Forecast(
                condition=day_data[ATTR_FORECAST_CONDITION],
                datetime=day_data.get("datetime"),
                native_temperature=day_data[ATTR_FORECAST_NATIVE_TEMP],
                native_templow=day_data[ATTR_FORECAST_NATIVE_TEMP_LOW],
                native_precipitation=day_data.get(ATTR_FORECAST_NATIVE_PRECIPITATION, 0),
                native_pressure=day_data.get(ATTR_FORECAST_NATIVE_PRESSURE),
                native_wind_speed=day_data.get(ATTR_FORECAST_NATIVE_WIND_SPEED),
                is_daytime=day_data.get(ATTR_FORECAST_IS_DAYTIME, True),
            )
            forecasts.append(forecast)

        return forecasts
