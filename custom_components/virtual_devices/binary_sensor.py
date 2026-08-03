"""Platform for virtual binary sensor integration."""
from __future__ import annotations

import logging
import random
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .base_entity import BaseVirtualEntity
from .const import (
    CONF_ENTITIES,
    DEVICE_TYPE_BINARY_SENSOR,
    DEVICE_TYPE_DISHWASHER,
    DEVICE_TYPE_DOORBELL,
    DEVICE_TYPE_DRYER,
    DEVICE_TYPE_REFRIGERATOR,
    DEVICE_TYPE_VEHICLE,
    DEVICE_TYPE_WASHER,
    DOMAIN,
)
from .appliance import get_appliance_bundles
from .laundry import get_laundry_bundles
from .entity_category import parse_entity_category
from .types import BinarySensorEntityConfig, BinarySensorState

_LOGGER = logging.getLogger(__name__)

# Binary sensor type mapping
BINARY_SENSOR_TYPE_MAP: dict[str, BinarySensorDeviceClass] = {
    "motion": BinarySensorDeviceClass.MOTION,
    "door": BinarySensorDeviceClass.DOOR,
    "window": BinarySensorDeviceClass.WINDOW,
    "smoke": BinarySensorDeviceClass.SMOKE,
    "gas": BinarySensorDeviceClass.GAS,
    "water_leak": BinarySensorDeviceClass.MOISTURE,
    "moisture": BinarySensorDeviceClass.MOISTURE,
    "occupancy": BinarySensorDeviceClass.OCCUPANCY,
    "opening": BinarySensorDeviceClass.OPENING,
    "presence": BinarySensorDeviceClass.PRESENCE,
    "problem": BinarySensorDeviceClass.PROBLEM,
    "safety": BinarySensorDeviceClass.SAFETY,
    "sound": BinarySensorDeviceClass.SOUND,
    "vibration": BinarySensorDeviceClass.VIBRATION,
    "battery": BinarySensorDeviceClass.BATTERY,
    "cold": BinarySensorDeviceClass.COLD,
    "heat": BinarySensorDeviceClass.HEAT,
    "tamper": BinarySensorDeviceClass.TAMPER,
    "carbon_monoxide": BinarySensorDeviceClass.CO,
    "connectivity": BinarySensorDeviceClass.CONNECTIVITY,
    "running": BinarySensorDeviceClass.RUNNING,
    "update": BinarySensorDeviceClass.UPDATE,
    "power": BinarySensorDeviceClass.POWER,
}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up virtual binary sensor entities."""
    device_type: str | None = config_entry.data.get("device_type")

    if device_type not in (DEVICE_TYPE_BINARY_SENSOR, DEVICE_TYPE_WASHER, DEVICE_TYPE_DRYER, DEVICE_TYPE_DISHWASHER, DEVICE_TYPE_REFRIGERATOR, DEVICE_TYPE_DOORBELL, DEVICE_TYPE_VEHICLE):
        return

    device_info: DeviceInfo = hass.data[DOMAIN][config_entry.entry_id]["device_info"]
    entities: list[VirtualBinarySensor | VirtualLaundryBinarySensor] = []

    if device_type == DEVICE_TYPE_VEHICLE:
        from .vehicle import (
            VehicleDataManager,
            VirtualVehicleDoorSensor, VirtualVehicleTrunkSensor,
            VirtualVehicleHoodSensor, VirtualVehicleEngineStatusSensor,
            VirtualVehicleUserPresentSensor, VirtualVehicleParkingBrakeSensor,
            VirtualVehicleTireWarningSensor, VirtualVehicleChargingSensor,
            VirtualVehicleChargeCableSensor, VirtualVehicleLightOnSensor,
            VirtualVehicleBrakeEngagedSensor,
        )
        vehicle_type = config_entry.data.get("vehicle_type", "ev")
        entities_config = config_entry.data.get("entities", [])
        manager = hass.data[DOMAIN][config_entry.entry_id].get("vehicle_manager")
        if not manager:
            entity_name = entities_config[0].get("entity_name", "vehicle") if entities_config else "vehicle"
            manager = VehicleDataManager(hass, config_entry.entry_id, vehicle_type, entity_name)
            await manager.async_load()
            hass.data[DOMAIN][config_entry.entry_id]["vehicle_manager"] = manager
        entity_name = entities_config[0].get("entity_name", "vehicle") if entities_config else "vehicle"
        bin_idx = 0
        if vehicle_type in ("car", "ev"):
            for door in ["Front Driver Door", "Front Passenger Door", "Rear Driver Door", "Rear Passenger Door"]:
                entities.append(VirtualVehicleDoorSensor(hass, config_entry.entry_id, entity_name, bin_idx, device_info, manager, door))
                bin_idx += 1
            entities.append(VirtualVehicleTrunkSensor(hass, config_entry.entry_id, entity_name, bin_idx, device_info, manager))
            bin_idx += 1
            entities.append(VirtualVehicleHoodSensor(hass, config_entry.entry_id, entity_name, bin_idx, device_info, manager))
            bin_idx += 1
            entities.append(VirtualVehicleParkingBrakeSensor(hass, config_entry.entry_id, entity_name, bin_idx, device_info, manager))
            bin_idx += 1
            for wheel in ["FL", "FR", "RL", "RR"]:
                entities.append(VirtualVehicleTireWarningSensor(hass, config_entry.entry_id, entity_name, bin_idx, device_info, manager, wheel))
                bin_idx += 1
        entities.append(VirtualVehicleEngineStatusSensor(hass, config_entry.entry_id, entity_name, bin_idx, device_info, manager, vehicle_type))
        bin_idx += 1
        entities.append(VirtualVehicleUserPresentSensor(hass, config_entry.entry_id, entity_name, bin_idx, device_info, manager))
        bin_idx += 1
        if vehicle_type in ("ev", "ebike"):
            entities.append(VirtualVehicleChargingSensor(hass, config_entry.entry_id, entity_name, bin_idx, device_info, manager))
            bin_idx += 1
        if vehicle_type == "ev":
            entities.append(VirtualVehicleChargeCableSensor(hass, config_entry.entry_id, entity_name, bin_idx, device_info, manager))
            bin_idx += 1
        if vehicle_type == "ebike":
            entities.append(VirtualVehicleLightOnSensor(hass, config_entry.entry_id, entity_name, bin_idx, device_info, manager))
            bin_idx += 1
            entities.append(VirtualVehicleBrakeEngagedSensor(hass, config_entry.entry_id, entity_name, bin_idx, device_info, manager))
            bin_idx += 1
        async_add_entities(entities)
        return

    if device_type in (DEVICE_TYPE_WASHER, DEVICE_TYPE_DRYER):
        sensor_kinds = ["door", "remote_start", "remote_control"]
        for index, bundle in enumerate(get_laundry_bundles(hass, config_entry.entry_id)):
            for sensor_kind in sensor_kinds:
                entities.append(
                    VirtualLaundryBinarySensor(
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
            entities.append(
                VirtualGroupedBinarySensor(
                    config_entry.entry_id,
                    bundle.base_name,
                    index,
                    device_info,
                    bundle.manager,
                    "door",
                )
            )
        async_add_entities(entities)
        return

    if device_type == DEVICE_TYPE_REFRIGERATOR:
        for index, bundle in enumerate(get_appliance_bundles(hass, config_entry.entry_id)):
            for sensor_kind in ["fridge_door", "freezer_door"]:
                entities.append(
                    VirtualGroupedBinarySensor(
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
                VirtualGroupedBinarySensor(
                    config_entry.entry_id,
                    bundle.base_name,
                    index,
                    device_info,
                    bundle.manager,
                    "motion",
                )
            )
        async_add_entities(entities)
        return

    entities_config: list[BinarySensorEntityConfig] = config_entry.data.get(CONF_ENTITIES, [])

    for idx, entity_config in enumerate(entities_config):
        entity = VirtualBinarySensor(
            hass,
            config_entry.entry_id,
            entity_config,
            idx,
            device_info,
        )
        entities.append(entity)

    async_add_entities(entities)


class VirtualBinarySensor(BaseVirtualEntity[BinarySensorEntityConfig, BinarySensorState], BinarySensorEntity):
    """Representation of a virtual binary sensor."""

    _attr_should_poll = True

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry_id: str,
        entity_config: BinarySensorEntityConfig,
        index: int,
        device_info: DeviceInfo,
    ) -> None:
        """Initialize the virtual binary sensor."""
        super().__init__(hass, config_entry_id, entity_config, index, device_info, "binary_sensor")

        self._attr_entity_category = parse_entity_category(
            entity_config.get("entity_category"),
            context=f"binary_sensor '{self._attr_name}'",
        )

        # Set device class
        sensor_type: str = entity_config.get("sensor_type", "motion")
        self._attr_device_class = BINARY_SENSOR_TYPE_MAP.get(
            sensor_type, BinarySensorDeviceClass.MOTION
        )

        # Initial state
        self._attr_is_on: bool = False

    def get_default_state(self) -> BinarySensorState:
        """Return the default state for this binary sensor entity."""
        return BinarySensorState(is_on=False)

    def apply_state(self, state: BinarySensorState) -> None:
        """Apply loaded state to entity attributes."""
        self._attr_is_on = state.get("is_on", False)
        _LOGGER.info("Loaded state for binary sensor '%s': is_on=%s", self._attr_name, self._attr_is_on)

    def get_current_state(self) -> BinarySensorState:
        """Get current state for persistence."""
        return BinarySensorState(is_on=self._attr_is_on)

    async def async_update(self) -> None:
        """Update the binary sensor state."""
        # Randomly generate state changes
        self._attr_is_on = random.choice([True, False])
        await self.async_save_state()


class VirtualLaundryBinarySensor(BinarySensorEntity):
    """Binary sensors for washer and dryer devices."""

    _attr_should_poll = True

    def __init__(
        self,
        config_entry_id: str,
        base_name: str,
        index: int,
        device_info: DeviceInfo,
        manager: object,
        sensor_kind: str,
    ) -> None:
        self._manager = manager
        self._sensor_kind = sensor_kind
        self._attr_name = f"{base_name} {sensor_kind.replace('_', ' ').title()}"
        self._attr_unique_id = f"{config_entry_id}_laundry_{index}_{sensor_kind}_binary"
        self._attr_device_info = device_info
        class_map = {
            "door": BinarySensorDeviceClass.DOOR,
            "remote_start": None,
            "remote_control": None,
        }
        self._attr_device_class = class_map[sensor_kind]

    @property
    def is_on(self) -> bool:
        """Return binary sensor value."""
        state = self._manager.state
        if self._sensor_kind == "door":
            return state["door_open"]
        if self._sensor_kind == "remote_start":
            return state["remote_start_enabled"]
        return state["remote_control_enabled"]

    async def async_update(self) -> None:
        """Refresh shared laundry state."""
        await self._manager.async_refresh()


class VirtualGroupedBinarySensor(BinarySensorEntity):
    """Binary sensor for grouped appliances."""

    _attr_should_poll = True

    def __init__(self, config_entry_id: str, base_name: str, index: int, device_info: DeviceInfo, manager: Any, sensor_kind: str) -> None:
        self._manager = manager
        self._sensor_kind = sensor_kind
        self._attr_name = f"{base_name} {sensor_kind.replace('_', ' ').title()}"
        self._attr_unique_id = f"{config_entry_id}_{manager.device_type}_{index}_{sensor_kind}_binary"
        self._attr_device_info = device_info
        self._attr_device_class = {
            "door": BinarySensorDeviceClass.DOOR,
            "fridge_door": BinarySensorDeviceClass.DOOR,
            "freezer_door": BinarySensorDeviceClass.DOOR,
            "motion": BinarySensorDeviceClass.MOTION,
        }.get(sensor_kind)

    @property
    def is_on(self) -> bool:
        state = self._manager.state
        if self._sensor_kind == "door":
            return state.get("door_open", False)
        if self._sensor_kind == "fridge_door":
            return state.get("fridge_door_open", False)
        if self._sensor_kind == "freezer_door":
            return state.get("freezer_door_open", False)
        return state.get("motion_detected", False)

    async def async_update(self) -> None:
        await self._manager.async_refresh()
