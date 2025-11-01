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
    ATTR_FORECAST_PRECIPITATION,
    ATTR_FORECAST_PRESSURE,
    ATTR_FORECAST_TEMP,
    ATTR_FORECAST_TEMP_LOW,
    ATTR_FORECAST_WIND_SPEED,
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
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_ENTITIES,
    CONF_ENTITY_NAME,
    DEVICE_TYPE_WEATHER,
    DOMAIN,
    TEMPLATE_ENABLED_DEVICE_TYPES,
    WEATHER_CONDITIONS,
)

_LOGGER = logging.getLogger(__name__)

# 天气条件列表
WEATHER_CONDITIONS_LIST = list(WEATHER_CONDITIONS.keys())


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up virtual weather entities."""
    device_type = config_entry.data.get("device_type")

    # 只有气象站类型的设备才设置气象站实体
    if device_type != DEVICE_TYPE_WEATHER:
        return

    device_info = hass.data[DOMAIN][config_entry.entry_id]["device_info"]
    entities = []
    entities_config = config_entry.data.get(CONF_ENTITIES, [])

    for idx, entity_config in enumerate(entities_config):
        entity = VirtualWeather(
            config_entry.entry_id,
            entity_config,
            idx,
            device_info,
        )
        entities.append(entity)

    async_add_entities(entities)


class VirtualWeather(WeatherEntity):
    """Representation of a virtual weather station."""

    def __init__(
        self,
        config_entry_id: str,
        entity_config: dict[str, Any],
        index: int,
        device_info: dict[str, Any],
    ) -> None:
        """Initialize the virtual weather station."""
        self._config_entry_id = config_entry_id
        self._entity_config = entity_config
        self._index = index
        self._device_info = device_info

        entity_name = entity_config.get(CONF_ENTITY_NAME, f"weather_{index + 1}")
        self._attr_name = entity_name
        self._attr_unique_id = f"{config_entry_id}_weather_{index}"
        self._attr_device_info = device_info
        self._attr_icon = "mdi:weather-partly-cloudy"

        # Template support
        self._templates = entity_config.get("templates", {})

        # 支持的功能
        self._attr_supported_features = WeatherEntityFeature.FORECAST_DAILY | WeatherEntityFeature.FORECAST_HOURLY

        # 单位设置
        self._attr_native_temperature_unit = UnitOfTemperature.CELSIUS
        self._attr_native_pressure_unit = UnitOfPressure.HPA
        self._attr_native_wind_speed_unit = UnitOfSpeed.KILOMETERS_PER_HOUR
        self._attr_native_visibility_unit = UnitOfLength.KILOMETERS
        self._attr_native_precipitation_unit = UnitOfLength.MILLIMETERS

        # 位置信息（模拟）
        self._attr_location = entity_config.get("location", "virtual_city")
        self._attr_latitude = entity_config.get("latitude", 39.9042)  # Beijing coordinates
        self._attr_longitude = entity_config.get("longitude", 116.4074)

        # 初始化基础天气状态（先生成基础参数）
        self._attr_condition = self._get_random_condition()
        self._attr_native_temperature = self._generate_temperature()
        self._attr_native_humidity = self._generate_humidity()
        self._attr_native_pressure = self._generate_pressure()
        self._attr_native_wind_speed = self._generate_wind_speed()
        self._attr_wind_bearing = random.randint(0, 360)
        self._attr_native_visibility = self._generate_visibility()
        self._attr_uv_index = self._generate_uv_index()
        self._attr_precipitation = self._generate_precipitation()

        # 然后生成依赖其他参数的值
        self._attr_native_apparent_temperature = self._generate_apparent_temperature()
        self._attr_native_dew_point = self._generate_dew_point()
        self._attr_native_precipitation_unit = UnitOfLength.MILLIMETERS

        # 预报数据
        self._attr_forecast = self._generate_forecast()

        # 云量和臭氧层
        self._attr_cloud_coverage = random.randint(0, 100)
        self._attr_ozone = random.uniform(100, 400)

        # 更新时间
        self._last_update = datetime.now()

    def _get_random_condition(self) -> str:
        """Get random weather condition based on probability."""
        # 基于真实天气分布概率
        conditions = [
            ("sunny", 30),        # 30% 晴天
            ("partlycloudy", 25), # 25% 多云
            ("cloudy", 20),       # 20% 阴天
            ("rainy", 15),        # 15% 雨天
            ("snowy", 5),         # 5% 雪天（冬季概率更高）
            ("fog", 3),           # 3% 雾
            ("windy", 2),         # 2% 大风
        ]

        # Increase snow probability in winter
        month = datetime.now().month
        if month in [12, 1, 2]:
            conditions.append(("snowy", 15))  # 冬季雪天概率增加到15%

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

        # 基础温度（根据季节）
        if month in [12, 1, 2]:  # 冬季
            base_temp = random.uniform(-5, 10)
        elif month in [3, 4, 5]:  # 春季
            base_temp = random.uniform(10, 25)
        elif month in [6, 7, 8]:  # 夏季
            base_temp = random.uniform(20, 35)
        else:  # 秋季
            base_temp = random.uniform(10, 20)

        # 根据时间调整温度
        if 6 <= hour <= 18:  # 白天
            hour_factor = 1 + 0.3 * abs(hour - 12) / 12
        else:  # 夜晚
            hour_factor = 0.7

        temperature = base_temp * hour_factor + random.uniform(-3, 3)
        return round(temperature, 1)

    def _generate_apparent_temperature(self) -> float:
        """Generate apparent temperature."""
        # 体感温度考虑湿度和风速影响
        apparent_temp = self._attr_native_temperature

        # 高湿度时体感温度更高
        if self._attr_native_humidity > 70:
            apparent_temp += random.uniform(1, 3)

        # 风速大时体感温度更低
        if self._attr_native_wind_speed > 20:
            apparent_temp -= random.uniform(2, 5)

        return round(apparent_temp, 1)

    def _generate_pressure(self) -> float:
        """Generate realistic atmospheric pressure."""
        # 气压通常在980-1040 hPa之间
        if self._attr_condition in ["rainy", "pouring", "lightning-rainy"]:
            # 雨天气压较低
            pressure = random.uniform(990, 1010)
        elif self._attr_condition in ["sunny", "partlycloudy"]:
            # 晴天气压较高
            pressure = random.uniform(1015, 1030)
        else:
            # 其他情况正常气压
            pressure = random.uniform(1000, 1020)

        return round(pressure, 1)

    def _generate_humidity(self) -> int:
        """Generate realistic humidity."""
        # 根据天气条件生成湿度
        if self._attr_condition in ["rainy", "pouring", "fog"]:
            humidity = random.randint(70, 95)
        elif self._attr_condition in ["sunny", "partlycloudy"]:
            humidity = random.randint(30, 60)
        elif self._attr_condition in ["snowy", "snowy-rainy"]:
            humidity = random.randint(60, 80)
        else:
            humidity = random.randint(40, 70)

        return humidity

    def _generate_wind_speed(self) -> float:
        """Generate realistic wind speed."""
        # 根据天气条件生成风速
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
        # 根据天气条件生成能见度
        if self._attr_condition == "fog":
            visibility = random.uniform(0.1, 1)
        elif self._attr_condition in ["rainy", "pouring", "snowy"]:
            visibility = random.uniform(1, 10)
        elif self._attr_condition == "sunny":
            visibility = random.uniform(10, 20)
        else:
            visibility = random.uniform(5, 15)

        return round(visibility, 1)

    def _generate_dew_point(self) -> float:
        """Generate dew point temperature."""
        # 露点温度基于温度和湿度计算（简化版）
        temp = self._attr_native_temperature
        humidity = self._attr_native_humidity

        # 简化的露点计算公式
        dew_point = temp - ((100 - humidity) / 5)
        return round(dew_point, 1)

    def _generate_uv_index(self) -> float:
        """Generate UV index based on condition and time."""
        now = datetime.now()
        hour = now.hour
        month = now.month

        # 夜晚UV指数为0
        if hour < 6 or hour > 18:
            return 0

        # 根据天气条件调整
        if self._attr_condition == "sunny":
            uv_factor = 1.0
        elif self._attr_condition == "partlycloudy":
            uv_factor = 0.7
        elif self._attr_condition == "cloudy":
            uv_factor = 0.3
        else:
            uv_factor = 0.1

        # 夏季UV指数更高
        if month in [6, 7, 8]:
            base_uv = random.uniform(6, 11)
        elif month in [3, 4, 5, 9, 10, 11]:
            base_uv = random.uniform(3, 8)
        else:
            base_uv = random.uniform(1, 4)

        uv_index = base_uv * uv_factor
        return round(uv_index, 1)

    def _generate_precipitation(self) -> float:
        """Generate precipitation based on weather condition."""
        if self._attr_condition in ["pouring"]:
            return round(random.uniform(10, 50), 1)
        elif self._attr_condition in ["rainy"]:
            return round(random.uniform(1, 10), 1)
        elif self._attr_condition in ["lightning-rainy"]:
            return round(random.uniform(5, 25), 1)
        elif self._attr_condition in ["snowy", "snowy-rainy"]:
            return round(random.uniform(0.5, 5), 1)
        else:
            return 0

    def _generate_forecast(self) -> list[Forecast]:
        """Generate weather forecast for next 5 days."""
        forecast = []
        base_date = datetime.now()

        for i in range(5):
            forecast_date = base_date + timedelta(days=i + 1)

            # 生成预测天气
            condition = self._get_random_condition()

            # 生成预测温度（基于当前温度和季节变化）
            temp_change = random.uniform(-5, 5)
            high_temp = max(self._attr_native_temperature + temp_change + random.uniform(3, 8), -20)
            low_temp = high_temp - random.uniform(5, 15)

            # 根据天气生成其他参数
            if condition in ["rainy", "pouring", "lightning-rainy"]:
                precipitation = random.uniform(1, 20)
                pressure = random.uniform(990, 1010)
                humidity = random.randint(70, 95)
            elif condition in ["sunny", "partlycloudy"]:
                precipitation = 0
                pressure = random.uniform(1015, 1030)
                humidity = random.randint(30, 60)
            else:
                precipitation = random.uniform(0, 5)
                pressure = random.uniform(1000, 1020)
                humidity = random.randint(50, 80)

            forecast_data = {
                "datetime": forecast_date,
                "condition": condition,
                ATTR_FORECAST_NATIVE_TEMP: round(high_temp, 1),
                ATTR_FORECAST_NATIVE_TEMP_LOW: round(low_temp, 1),
                ATTR_FORECAST_NATIVE_PRECIPITATION: round(precipitation, 1),
                ATTR_FORECAST_NATIVE_PRESSURE: round(pressure, 1),
                ATTR_FORECAST_NATIVE_WIND_SPEED: round(random.uniform(5, 30), 1),
                "humidity": humidity,
                ATTR_FORECAST_IS_DAYTIME: 8 <= forecast_date.hour <= 18,
            }

            forecast.append(Forecast(forecast_data))

        return forecast

    async def async_update(self) -> None:
        """Update weather data."""
        # 检查是否需要更新（至少间隔5分钟）
        if datetime.now() - self._last_update < timedelta(minutes=5):
            return

        # 更新天气条件（小概率变化）
        if random.random() < 0.3:  # 30% 概率天气变化
            self._attr_condition = self._get_random_condition()

        # 更新温度
        self._attr_native_temperature = self._generate_temperature()
        self._attr_native_apparent_temperature = self._generate_apparent_temperature()

        # 更新其他参数
        self._attr_native_pressure += random.uniform(-2, 2)  # 气压小幅变化
        self._attr_native_pressure = round(self._attr_native_pressure, 1)

        self._attr_native_humidity += random.randint(-5, 5)
        self._attr_native_humidity = max(20, min(100, self._attr_native_humidity))

        self._attr_native_wind_speed += random.uniform(-2, 2)
        self._attr_native_wind_speed = max(0, round(self._attr_native_wind_speed, 1))

        # 更新其他参数
        self._attr_wind_bearing = (self._attr_wind_bearing + random.randint(-30, 30)) % 360
        self._attr_native_visibility = self._generate_visibility()
        self._attr_uv_index = self._generate_uv_index()
        self._attr_precipitation = self._generate_precipitation()

        # 更新预报（每天更新一次）
        if datetime.now().hour == 0 and datetime.now().minute < 10:
            self._attr_forecast = self._generate_forecast()

        self._last_update = datetime.now()
        self.async_write_ha_state()

        # 触发模板更新事件
        if self._templates:
            self.hass.bus.async_fire(
                f"{DOMAIN}_weather_template_update",
                {
                    "entity_id": self.entity_id,
                    "device_id": self._config_entry_id,
                    "condition": self._attr_condition,
                    "temperature": self._attr_native_temperature,
                    "humidity": self._attr_native_humidity,
                    "pressure": self._attr_native_pressure,
                    "wind_speed": self._attr_native_wind_speed,
                },
            )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        attrs = {
            "cloud_coverage": self._attr_cloud_coverage,
            "ozone": round(self._attr_ozone, 1),
            "forecast_hours": len([f for f in self._attr_forecast if f[ATTR_FORECAST_IS_DAYTIME]]),
        }

        # 添加空气质量指数（模拟）
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

        # 将内部格式转换为Forecast对象
        forecasts = []
        for day_data in self._attr_forecast[:7]:  # 最多7天预报
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