"""Sensor platform for virtual devices integration."""
from __future__ import annotations

import logging
import random
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfTime,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfPressure,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .base_entity import BaseVirtualEntity
from .const import (
    CONF_ENTITIES,
    DEVICE_TYPE_DISHWASHER,
    DEVICE_TYPE_DOORBELL,
    DEVICE_TYPE_DRYER,
    DEVICE_TYPE_REFRIGERATOR,
    DEVICE_TYPE_SENSOR,
    DEVICE_TYPE_WASHER,
    DOMAIN,
)
from .appliance import get_appliance_bundles
from .laundry import get_laundry_bundles
from .types import SensorEntityConfig, SensorState

_LOGGER = logging.getLogger(__name__)

# Sensor type configuration mapping
SENSOR_TYPE_CONFIG: dict[str, dict[str, Any]] = {
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
}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up virtual sensor entities."""
    device_type: str | None = config_entry.data.get("device_type")

    # Only set up sensor entities for sensor device type
    if device_type not in (DEVICE_TYPE_SENSOR, DEVICE_TYPE_WASHER, DEVICE_TYPE_DRYER, DEVICE_TYPE_DISHWASHER, DEVICE_TYPE_REFRIGERATOR, DEVICE_TYPE_DOORBELL):
        return

    device_info: DeviceInfo = hass.data[DOMAIN][config_entry.entry_id]["device_info"]
    entities: list[VirtualSensor | VirtualLaundrySensor] = []

    if device_type in (DEVICE_TYPE_WASHER, DEVICE_TYPE_DRYER):
        sensor_kinds = [
            "operation_state",
            "remaining_time",
            "total_time",
            "program_progress",
            "finish_time",
        ]
        for index, bundle in enumerate(get_laundry_bundles(hass, config_entry.entry_id)):
            for sensor_kind in sensor_kinds:
                entities.append(
                    VirtualLaundrySensor(
                        hass,
                        config_entry.entry_id,
                        bundle.base_name,
                        index,
                        device_info,
                        bundle.manager,
                        sensor_kind,
                    )
                )
        async_add_entities(entities)
        return

    if device_type == DEVICE_TYPE_DISHWASHER:
        for index, bundle in enumerate(get_appliance_bundles(hass, config_entry.entry_id)):
            for sensor_kind in ["operation_state", "remaining_time", "total_time", "finish_time"]:
                entities.append(
                    VirtualApplianceSensor(
                        config_entry.entry_id,
                        bundle.base_name,
                        index,
                        device_info,
                        bundle.manager,
                        sensor_kind,
                    )
                )
        async_add_entities(entities)
        return

    if device_type == DEVICE_TYPE_REFRIGERATOR:
        for index, bundle in enumerate(get_appliance_bundles(hass, config_entry.entry_id)):
            for sensor_kind in ["fridge_temperature", "freezer_temperature", "mode"]:
                entities.append(
                    VirtualApplianceSensor(
                        config_entry.entry_id,
                        bundle.base_name,
                        index,
                        device_info,
                        bundle.manager,
                        sensor_kind,
                    )
                )
        async_add_entities(entities)
        return

    if device_type == DEVICE_TYPE_DOORBELL:
        for index, bundle in enumerate(get_appliance_bundles(hass, config_entry.entry_id)):
            entities.append(
                VirtualApplianceSensor(
                    config_entry.entry_id,
                    bundle.base_name,
                    index,
                    device_info,
                    bundle.manager,
                    "last_ring",
                )
            )
        async_add_entities(entities)
        return

    entities_config: list[SensorEntityConfig] = config_entry.data.get(CONF_ENTITIES, [])

    for idx, entity_config in enumerate(entities_config):
        try:
            entity = VirtualSensor(
                hass,
                config_entry.entry_id,
                entity_config,
                idx,
                device_info,
            )
            entities.append(entity)
        except Exception as e:
            _LOGGER.error("Failed to create VirtualSensor %d: %s", idx, e)

    async_add_entities(entities)


class VirtualSensor(BaseVirtualEntity[SensorEntityConfig, SensorState], SensorEntity):
    """Representation of a virtual sensor."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry_id: str,
        entity_config: SensorEntityConfig,
        index: int,
        device_info: DeviceInfo,
    ) -> None:
        """Initialize the virtual sensor."""
        # Set sensor type BEFORE super().__init__() because get_default_state() needs it
        self._sensor_type: str = entity_config.get("sensor_type", "temperature")

        super().__init__(hass, config_entry_id, entity_config, index, device_info, "sensor")

        # Get sensor type configuration
        type_config: dict[str, Any] = SENSOR_TYPE_CONFIG.get(self._sensor_type, {})

        # Set sensor attributes from type configuration
        self._attr_device_class = type_config.get("device_class")
        self._attr_native_unit_of_measurement = type_config.get("unit")
        self._attr_state_class = type_config.get("state_class")
        self._attr_icon = type_config.get("icon", "mdi:eye")

        # Simulation settings
        self._simulation_enabled: bool = entity_config.get("enable_simulation", True)
        self._update_frequency: int = entity_config.get("update_frequency", 30)

        # Initialize native value - will be populated by async_load_state
        self._native_value: float | int | str | None = self._generate_initial_value(type_config)

    def get_default_state(self) -> SensorState:
        """Return the default state for this sensor entity."""
        type_config: dict[str, Any] = SENSOR_TYPE_CONFIG.get(self._sensor_type, {})
        return {
            "native_value": self._generate_initial_value(type_config),
        }

    def apply_state(self, state: SensorState) -> None:
        """Apply loaded state to entity attributes."""
        type_config: dict[str, Any] = SENSOR_TYPE_CONFIG.get(self._sensor_type, {})
        self._native_value = state.get("native_value", self._generate_initial_value(type_config))
        _LOGGER.debug(
            "Applied state for sensor '%s': native_value=%s",
            self._attr_name, self._native_value,
        )

    def get_current_state(self) -> SensorState:
        """Get current state for persistence."""
        return {
            "native_value": self._native_value,
        }

    @property
    def native_value(self) -> float | int | str | None:
        """Return the native value of the sensor."""
        return self._native_value

    def _generate_initial_value(self, type_config: dict[str, Any]) -> float | int:
        """Generate initial value based on sensor type."""
        if self._sensor_type == "temperature":
            return round(random.uniform(18, 25), 1)
        elif self._sensor_type == "humidity":
            return round(random.uniform(30, 70), 1)
        elif self._sensor_type == "pressure":
            return round(random.uniform(980, 1020), 1)
        elif self._sensor_type == "illuminance":
            return round(random.uniform(100, 1000), 1)
        elif self._sensor_type in ("power", "voltage", "current"):
            range_vals: tuple[int, int] = type_config.get("range", (0, 100))
            return round(random.uniform(range_vals[0], range_vals[1]), 1)
        elif self._sensor_type == "battery":
            return random.randint(20, 100)
        else:
            return 0

    async def async_update(self) -> None:
        """Update sensor value if simulation is enabled."""
        if not self._simulation_enabled:
            return

        # Simulate sensor value changes based on sensor type
        if self._sensor_type == "temperature":
            self._native_value = round(random.uniform(18, 28), 1)
        elif self._sensor_type == "humidity":
            self._native_value = round(random.uniform(30, 80), 1)
        elif self._sensor_type == "pressure":
            self._native_value = round(random.uniform(980, 1030), 1)
        elif self._sensor_type == "battery":
            # Battery level changes slowly
            current: float | int = self._native_value if isinstance(self._native_value, (int, float)) else 50
            change: float = random.uniform(-5, 5)
            new_value: float = max(0, min(100, current + change))
            self._native_value = round(new_value)
        elif self._sensor_type == "illuminance":
            self._native_value = round(random.uniform(0, 5000), 1)
        else:
            # Other sensor types
            type_config: dict[str, Any] = SENSOR_TYPE_CONFIG.get(self._sensor_type, {})
            range_vals: tuple[int, int] = type_config.get("range", (0, 100))
            self._native_value = round(random.uniform(range_vals[0], range_vals[1]), 1)

        # Save state to storage
        await self.async_save_state()


class VirtualLaundrySensor(SensorEntity):
    """Core sensors for a washer or dryer."""

    _attr_should_poll = True

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry_id: str,
        base_name: str,
        index: int,
        device_info: DeviceInfo,
        manager: Any,
        sensor_kind: str,
    ) -> None:
        self._hass = hass
        self._manager = manager
        self._sensor_kind = sensor_kind
        self._attr_name = f"{base_name} {sensor_kind.replace('_', ' ').title()}"
        self._attr_unique_id = f"{config_entry_id}_laundry_{index}_{sensor_kind}"
        self._attr_device_info = device_info

        if sensor_kind == "program_progress":
            self._attr_native_unit_of_measurement = PERCENTAGE
        elif sensor_kind in ("remaining_time", "total_time"):
            self._attr_native_unit_of_measurement = UnitOfTime.MINUTES

    @property
    def native_value(self) -> Any:
        """Return current sensor value."""
        state = self._manager.state
        if self._sensor_kind == "operation_state":
            return state["operation_state"]
        if self._sensor_kind == "remaining_time":
            return state["remaining_seconds"] // 60
        if self._sensor_kind == "total_time":
            return state["total_seconds"] // 60
        if self._sensor_kind == "program_progress":
            return self._manager.progress_percent
        finish_time = self._manager.finish_time
        return finish_time.isoformat() if finish_time else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return related laundry state attributes."""
        state = self._manager.state
        attrs: dict[str, Any] = {
            "selected_program": state["selected_program"],
            "power_on": state["power_on"],
            "remote_start_enabled": state["remote_start_enabled"],
            "remote_control_enabled": state["remote_control_enabled"],
        }
        if "temperature" in state:
            attrs["temperature"] = state["temperature"]
        if "spin_speed" in state:
            attrs["spin_speed"] = state["spin_speed"]
        if "drying_target" in state:
            attrs["drying_target"] = state["drying_target"]
        return attrs

    async def async_update(self) -> None:
        """Refresh shared laundry state."""
        await self._manager.async_refresh()


class VirtualApplianceSensor(SensorEntity):
    """Shared sensor for grouped appliances."""

    _attr_should_poll = True

    def __init__(self, config_entry_id: str, base_name: str, index: int, device_info: DeviceInfo, manager: Any, sensor_kind: str) -> None:
        self._manager = manager
        self._sensor_kind = sensor_kind
        self._attr_name = f"{base_name} {sensor_kind.replace('_', ' ').title()}"
        self._attr_unique_id = f"{config_entry_id}_{manager.device_type}_{index}_{sensor_kind}"
        self._attr_device_info = device_info
        if sensor_kind in ("remaining_time", "total_time"):
            self._attr_native_unit_of_measurement = UnitOfTime.MINUTES

    @property
    def native_value(self) -> Any:
        state = self._manager.state
        if self._sensor_kind == "remaining_time":
            return state.get("remaining_seconds", 0) // 60
        if self._sensor_kind == "total_time":
            return state.get("total_seconds", 0) // 60
        if self._sensor_kind == "finish_time":
            finish_time = self._manager.finish_time
            return finish_time.isoformat() if finish_time else None
        return state.get(self._sensor_kind)

    async def async_update(self) -> None:
        await self._manager.async_refresh()
