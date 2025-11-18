"""Environment monitoring domain service for sensors and binary sensors."""
from __future__ import annotations

import logging
import random
from datetime import datetime
from typing import Any, Dict, List, Optional

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfPressure,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .base_service import BaseVirtualEntity, VirtualDeviceService
from .const import (
    CONF_ENTITIES,
    CONF_ENTITY_NAME,
    DEVICE_TYPE_SENSOR,
    DEVICE_TYPE_BINARY_SENSOR,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

# Sensor type configurations
SENSOR_TYPE_CONFIG = {
    "temperature": {
        "device_class": SensorDeviceClass.TEMPERATURE,
        "unit": UnitOfTemperature.CELSIUS,
        "state_class": SensorStateClass.MEASUREMENT,
        "range": (-30, 50),
        "icon": "mdi:thermometer",
    },
    "humidity": {
        "device_class": SensorDeviceClass.HUMIDITY,
        "unit": PERCENTAGE,
        "state_class": SensorStateClass.MEASUREMENT,
        "range": (0, 100),
        "icon": "mdi:water-percent",
    },
    "pressure": {
        "device_class": SensorDeviceClass.PRESSURE,
        "unit": UnitOfPressure.HPA,
        "state_class": SensorStateClass.MEASUREMENT,
        "range": (950, 1050),
        "icon": "mdi:gauge",
    },
    "illuminance": {
        "device_class": None,
        "unit": "lx",
        "state_class": SensorStateClass.MEASUREMENT,
        "range": (0, 100000),
        "icon": "mdi:brightness-6",
    },
    "power": {
        "device_class": SensorDeviceClass.POWER,
        "unit": UnitOfPower.WATT,
        "state_class": SensorStateClass.MEASUREMENT,
        "range": (0, 5000),
        "icon": "mdi:flash",
    },
    "energy": {
        "device_class": SensorDeviceClass.ENERGY,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "range": (0, 10000),
        "icon": "mdi:lightning-bolt",
    },
    "voltage": {
        "device_class": SensorDeviceClass.VOLTAGE,
        "unit": UnitOfElectricPotential.VOLT,
        "state_class": SensorStateClass.MEASUREMENT,
        "range": (0, 500),
        "icon": "mdi:lightning-bolt-outline",
    },
    "current": {
        "device_class": SensorDeviceClass.CURRENT,
        "unit": UnitOfElectricCurrent.AMPERE,
        "state_class": SensorStateClass.MEASUREMENT,
        "range": (0, 50),
        "icon": "mdi:current-ac",
    },
    "battery": {
        "device_class": SensorDeviceClass.BATTERY,
        "unit": PERCENTAGE,
        "state_class": SensorStateClass.MEASUREMENT,
        "range": (0, 100),
        "icon": "mdi:battery",
    },
    "pm25": {
        "device_class": SensorDeviceClass.PM25,
        "unit": "µg/m³",
        "state_class": SensorStateClass.MEASUREMENT,
        "range": (0, 500),
        "icon": "mdi:air-filter",
    },
    "co2": {
        "device_class": SensorDeviceClass.CO2,
        "unit": "ppm",
        "state_class": SensorStateClass.MEASUREMENT,
        "range": (400, 5000),
        "icon": "mdi:molecule-co2",
    },
}

# Binary sensor type configurations
BINARY_SENSOR_TYPE_CONFIG = {
    "motion": {
        "device_class": BinarySensorDeviceClass.MOTION,
        "icon": "mdi:motion-sensor",
    },
    "door": {
        "device_class": BinarySensorDeviceClass.DOOR,
        "icon": "mdi:door-open",
    },
    "window": {
        "device_class": BinarySensorDeviceClass.WINDOW,
        "icon": "mdi:window-open-variant",
    },
    "smoke": {
        "device_class": BinarySensorDeviceClass.SMOKE,
        "icon": "mdi:smoke-detector",
    },
    "gas": {
        "device_class": BinarySensorDeviceClass.GAS,
        "icon": "mdi:fire",
    },
    "water": {
        "device_class": BinarySensorDeviceClass.MOISTURE,
        "icon": "mdi:water-alert",
    },
    "connectivity": {
        "device_class": BinarySensorDeviceClass.CONNECTIVITY,
        "icon": "mdi:server-network",
    },
    "power": {
        "device_class": BinarySensorDeviceClass.POWER,
        "icon": "mdi:power-cycle",
    },
    "battery_charging": {
        "device_class": BinarySensorDeviceClass.BATTERY_CHARGING,
        "icon": "mdi:battery-charging",
    },
    "cold": {
        "device_class": BinarySensorDeviceClass.COLD,
        "icon": "mdi:snowflake",
    },
    "heat": {
        "device_class": BinarySensorDeviceClass.HEAT,
        "icon": "mdi:fire",
    },
    "light": {
        "device_class": BinarySensorDeviceClass.LIGHT,
        "icon": "mdi:brightness-5",
    },
    "lock": {
        "device_class": BinarySensorDeviceClass.LOCK,
        "icon": "mdi:lock",
    },
    "tamper": {
        "device_class": BinarySensorDeviceClass.TAMPER,
        "icon": "mdi:shield-alert",
    },
    "vibration": {
        "device_class": BinarySensorDeviceClass.VIBRATION,
        "icon": "mdi:vibrate",
    },
    "opening": {
        "device_class": BinarySensorDeviceClass.OPENING,
        "icon": "mdi:door",
    },
}


class VirtualSensor(BaseVirtualEntity, SensorEntity):
    """Representation of a virtual sensor."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry_id: str,
        entity_config: dict[str, Any],
        index: int,
        device_info: dict[str, Any],
    ) -> None:
        """Initialize the virtual sensor."""
        super().__init__(hass, config_entry_id, entity_config, index, device_info, "sensor")

        # Sensor specific configuration
        sensor_type = entity_config.get("sensor_type", "temperature")
        self._sensor_type = sensor_type

        # Get configuration for sensor type
        type_config = SENSOR_TYPE_CONFIG.get(sensor_type, {})
        self._type_config = type_config

        # Set sensor attributes based on type
        self._attr_device_class = type_config.get("device_class")
        self._attr_native_unit_of_measurement = type_config.get("unit")
        self._attr_state_class = type_config.get("state_class")
        self._attr_icon = type_config.get("icon", "mdi:eye")

        # Sensor specific state
        self._attr_native_value = self._generate_initial_value()

        # Simulation settings
        self._simulation_enabled = entity_config.get("enable_simulation", True)
        self._update_frequency = entity_config.get("update_frequency", 30)  # seconds
        self._last_update = datetime.now()

    def _generate_initial_value(self) -> Any:
        """Generate initial sensor value based on type."""
        if self._sensor_type == "temperature":
            return round(random.uniform(18, 25), 1)
        elif self._sensor_type == "humidity":
            return round(random.uniform(30, 70), 1)
        elif self._sensor_type == "pressure":
            return round(random.uniform(980, 1020), 1)
        elif self._sensor_type == "illuminance":
            return round(random.uniform(100, 1000), 1)
        elif self._sensor_type in ["power", "voltage", "current"]:
            range_vals = self._type_config.get("range", (0, 100))
            return round(random.uniform(range_vals[0], range_vals[1]), 1)
        elif self._sensor_type == "battery":
            return random.randint(20, 100)
        elif self._sensor_type == "pm25":
            return round(random.uniform(5, 50), 1)
        elif self._sensor_type == "co2":
            return random.randint(400, 1200)
        else:
            return 0

    def _simulate_value_change(self) -> Any:
        """Simulate value change based on sensor type."""
        if not self._simulation_enabled:
            return self._attr_native_value

        current_value = self._attr_native_value if isinstance(self._attr_native_value, (int, float)) else 0
        range_vals = self._type_config.get("range", (0, 100))

        # Small random change
        change = random.uniform(-range_vals[1] * 0.02, range_vals[1] * 0.02)
        new_value = current_value + change

        # Clamp to range
        new_value = max(range_vals[0], min(range_vals[1], new_value))

        # Format based on type
        if self._sensor_type in ["temperature", "humidity", "pressure", "illuminance", "power", "voltage", "current", "pm25"]:
            return round(new_value, 1)
        elif self._sensor_type in ["battery", "co2"]:
            return int(new_value)
        else:
            return new_value

    async def _apply_loaded_state(self) -> None:
        """Apply loaded state to sensor entity."""
        self._attr_native_value = self._state.get("native_value", self._generate_initial_value())

    async def _initialize_default_state(self) -> None:
        """Initialize default sensor state."""
        self._attr_native_value = self._generate_initial_value()
        self._state = {
            "native_value": self._attr_native_value,
        }

    def update(self) -> None:
        """Update sensor value if simulation is enabled."""
        now = datetime.now()
        if self._simulation_enabled and (now - self._last_update).total_seconds() >= self._update_frequency:
            self._attr_native_value = self._simulate_value_change()
            self._state["native_value"] = self._attr_native_value
            self._last_update = now
            self.schedule_update_ha_state()
            # Save state asynchronously (non-blocking)
            self.hass.async_create_task(self.async_save_state())


class VirtualBinarySensor(BaseVirtualEntity, BinarySensorEntity):
    """Representation of a virtual binary sensor."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry_id: str,
        entity_config: dict[str, Any],
        index: int,
        device_info: dict[str, Any],
    ) -> None:
        """Initialize the virtual binary sensor."""
        super().__init__(hass, config_entry_id, entity_config, index, device_info, "binary_sensor")

        # Binary sensor specific configuration
        sensor_type = entity_config.get("sensor_type", "motion")
        self._sensor_type = sensor_type

        # Get configuration for sensor type
        type_config = BINARY_SENSOR_TYPE_CONFIG.get(sensor_type, {})
        self._type_config = type_config

        # Set sensor attributes based on type
        self._attr_device_class = type_config.get("device_class")
        self._attr_icon = type_config.get("icon", "mdi:eye")

        # Binary sensor specific state
        self._attr_is_on = False

        # Simulation settings
        self._simulation_enabled = entity_config.get("enable_simulation", True)
        self._update_frequency = entity_config.get("update_frequency", 30)  # seconds
        self._trigger_probability = entity_config.get("trigger_probability", 0.1)  # probability of being ON
        self._last_update = datetime.now()

    def _should_be_on(self) -> bool:
        """Determine if sensor should be ON based on simulation."""
        if not self._simulation_enabled:
            return self._attr_is_on

        # Some sensors have special logic
        if self._sensor_type == "connectivity":
            # Connectivity is usually ON
            return random.random() > 0.05  # 95% uptime
        elif self._sensor_type == "battery_charging":
            # Battery charging state changes less frequently
            return random.random() > 0.7  # 30% charging
        else:
            # Standard random behavior
            return random.random() < self._trigger_probability

    async def _apply_loaded_state(self) -> None:
        """Apply loaded state to binary sensor entity."""
        self._attr_is_on = self._state.get("is_on", False)

    async def _initialize_default_state(self) -> None:
        """Initialize default binary sensor state."""
        self._attr_is_on = self._should_be_on()
        self._state = {
            "is_on": self._attr_is_on,
        }

    def update(self) -> None:
        """Update binary sensor value if simulation is enabled."""
        now = datetime.now()
        if self._simulation_enabled and (now - self._last_update).total_seconds() >= self._update_frequency:
            self._attr_is_on = self._should_be_on()
            self._state["is_on"] = self._attr_is_on
            self._last_update = now
            self.schedule_update_ha_state()
            # Save state asynchronously (non-blocking)
            self.hass.async_create_task(self.async_save_state())


class EnvironmentMonitoringService(VirtualDeviceService):
    """Environment monitoring domain service."""

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialize the environment monitoring service."""
        super().__init__(hass, "environment_monitoring")
        self._supported_device_types = [
            DEVICE_TYPE_SENSOR,
            DEVICE_TYPE_BINARY_SENSOR,
        ]

    async def async_setup_entry(
        self,
        config_entry: ConfigEntry,
        async_add_entities,
    ) -> None:
        """Set up environment monitoring entities."""
        device_type = config_entry.data.get("device_type")

        if not self.is_device_type_supported(device_type):
            return

        device_info = self._get_device_info(config_entry)
        entities_config = self._get_entities_config(config_entry)
        entities = []

        for idx, entity_config in enumerate(entities_config):
            if device_type == DEVICE_TYPE_SENSOR:
                entity = VirtualSensor(self._hass, config_entry.entry_id, entity_config, idx, device_info)
            elif device_type == DEVICE_TYPE_BINARY_SENSOR:
                entity = VirtualBinarySensor(self._hass, config_entry.entry_id, entity_config, idx, device_info)
            else:
                continue

            entities.append(entity)

        if entities:
            async_add_entities(entities)
            _LOGGER.info(f"Added {len(entities)} environment monitoring entities for {device_type}")

            # Start periodic updates for sensors with simulation enabled
            for entity in entities:
                if entity._simulation_enabled:
                    # Use async_track_time_interval for periodic updates
                    from homeassistant.helpers.event import async_track_time_interval
                    from datetime import timedelta

                    async_track_time_interval(
                        self._hass,
                        lambda _: entity.update(),
                        timedelta(seconds=entity._update_frequency)
                    )