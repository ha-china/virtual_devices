"""Platform for virtual vehicle integration (Tesla Fleet style).

Supports car (ICE), ev (electric vehicle), and ebike (electric bicycle/scooter).
"""
from __future__ import annotations

import logging
import random
from datetime import datetime
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.components.button import ButtonEntity
from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.components.cover import (
    CoverDeviceClass,
    CoverEntity,
    CoverEntityFeature,
)
from homeassistant.components.device_tracker import SourceType
from homeassistant.components.device_tracker import TrackerEntity
from homeassistant.components.lock import LockEntity
from homeassistant.components.number import NumberEntity
from homeassistant.components.select import SelectEntity
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.components.switch import SwitchEntity
from homeassistant.components.update import UpdateEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfLength,
    UnitOfPower,
    UnitOfPressure,
    UnitOfSpeed,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.storage import Store

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

STORAGE_VERSION = 1

VEHICLE_TYPES = ("car", "ev", "ebike")

STATE_KEY_SPEED = "speed"
STATE_KEY_ODOMETER = "odometer"
STATE_KEY_LATITUDE = "latitude"
STATE_KEY_LONGITUDE = "longitude"
STATE_KEY_IS_LOCKED = "is_locked"
STATE_KEY_IS_ON = "is_on"
STATE_KEY_PARKING_BRAKE = "parking_brake"
STATE_KEY_USER_PRESENT = "user_present"
STATE_KEY_OUTSIDE_TEMP = "outside_temp"
STATE_KEY_INSIDE_TEMP = "inside_temp"
STATE_KEY_FUEL_LEVEL = "fuel_level"
STATE_KEY_FUEL_RANGE = "fuel_range"
STATE_KEY_BATTERY_LEVEL = "battery_level"
STATE_KEY_BATTERY_RANGE = "battery_range"
STATE_KEY_BATTERY_VOLTAGE = "battery_voltage"
STATE_KEY_BATTERY_CURRENT = "battery_current"
STATE_KEY_MOTOR_POWER = "motor_power"
STATE_KEY_CHARGING = "charging"
STATE_KEY_CHARGE_CABLE_CONNECTED = "charge_cable_connected"
STATE_KEY_CHARGE_LIMIT = "charge_limit"
STATE_KEY_CHARGE_CURRENT = "charge_current"
STATE_KEY_CHARGE_RATE = "charge_rate"
STATE_KEY_CHARGER_POWER = "charger_power"
STATE_KEY_CHARGER_VOLTAGE = "charger_voltage"
STATE_KEY_CHARGER_CURRENT = "charger_current"
STATE_KEY_CHARGE_ENERGY_ADDED = "charge_energy_added"
STATE_KEY_TIME_TO_FULL_CHARGE = "time_to_full_charge"
STATE_KEY_SENTRY_MODE = "sentry_mode"
STATE_KEY_CLIMATE_ON = "climate_on"
STATE_KEY_TARGET_TEMP = "target_temp"
STATE_KEY_DEFROST = "defrost"
STATE_KEY_CABIN_OVERHEAT_PROTECTION = "cabin_overheat_protection"
STATE_KEY_DRIVE_MODE = "drive_mode"
STATE_KEY_SEAT_HEATER_FRONT_LEFT = "seat_heater_front_left"
STATE_KEY_SEAT_HEATER_FRONT_RIGHT = "seat_heater_front_right"
STATE_KEY_SEAT_HEATER_REAR_LEFT = "seat_heater_rear_left"
STATE_KEY_SEAT_HEATER_REAR_CENTER = "seat_heater_rear_center"
STATE_KEY_SEAT_HEATER_REAR_RIGHT = "seat_heater_rear_right"
STATE_KEY_STEERING_WHEEL_HEATER = "steering_wheel_heater"
STATE_KEY_AUTO_SEAT_CLIMATE_LEFT = "auto_seat_climate_left"
STATE_KEY_AUTO_SEAT_CLIMATE_RIGHT = "auto_seat_climate_right"
STATE_KEY_AUTO_STEERING_WHEEL_HEATER = "auto_steering_wheel_heater"
STATE_KEY_CHARGE_PORT_OPEN = "charge_port_open"
STATE_KEY_FRUNK_OPEN = "frunk_open"
STATE_KEY_TRUNK_OPEN = "trunk_open"
STATE_KEY_SUNROOF_POSITION = "sunroof_position"
STATE_KEY_WINDOW_FL = "window_fl"
STATE_KEY_WINDOW_FR = "window_fr"
STATE_KEY_WINDOW_RL = "window_rl"
STATE_KEY_WINDOW_RR = "window_rr"
STATE_KEY_FRONT_DRIVER_DOOR = "front_driver_door"
STATE_KEY_FRONT_PASSENGER_DOOR = "front_passenger_door"
STATE_KEY_REAR_DRIVER_DOOR = "rear_driver_door"
STATE_KEY_REAR_PASSENGER_DOOR = "rear_passenger_door"
STATE_KEY_HOOD = "hood"
STATE_KEY_TRUNK_LID = "trunk_lid"
STATE_KEY_TIRE_PRESSURE_FL = "tire_pressure_fl"
STATE_KEY_TIRE_PRESSURE_FR = "tire_pressure_fr"
STATE_KEY_TIRE_PRESSURE_RL = "tire_pressure_rl"
STATE_KEY_TIRE_PRESSURE_RR = "tire_pressure_rr"
STATE_KEY_TIRE_WARNING_FL = "tire_warning_fl"
STATE_KEY_TIRE_WARNING_FR = "tire_warning_fr"
STATE_KEY_TIRE_WARNING_RL = "tire_warning_rl"
STATE_KEY_TIRE_WARNING_RR = "tire_warning_rr"
STATE_KEY_OIL_LEVEL = "oil_level"
STATE_KEY_COOLANT_TEMP = "coolant_temp"
STATE_KEY_BATTERY_TEMP = "battery_temp"
STATE_KEY_LIGHT_ON = "light_on"
STATE_KEY_BRAKE_ENGAGED = "brake_engaged"
STATE_KEY_HORN_ON = "horn_on"
STATE_KEY_SPEED_LIMIT = "speed_limit"
STATE_KEY_ASSIST_LEVEL = "assist_level"
STATE_KEY_TRIP_DISTANCE = "trip_distance"
STATE_KEY_ESTIMATED_RANGE = "estimated_range"
STATE_KEY_SOFTWARE_UPDATE_AVAILABLE = "software_update_available"
STATE_KEY_SOFTWARE_UPDATE_VERSION = "software_update_version"
STATE_KEY_SOFTWARE_UPDATE_INSTALLING = "software_update_installing"
STATE_KEY_SOFTWARE_UPDATE_PROGRESS = "software_update_progress"
STATE_KEY_TIMES_CHARGED = "times_charged"
STATE_KEY_BATTERY_GRADE = "battery_grade"
STATE_KEY_TIME_LEFT = "time_left"
STATE_KEY_CENTRE_CTRL_BATT = "centre_ctrl_batt"
STATE_KEY_HDOP = "hdop"
STATE_KEY_RIDING_TIME = "riding_time"
STATE_KEY_DAYS_IN_USE = "days_in_use"
STATE_KEY_LAST_TRACK_START = "last_track_start"
STATE_KEY_LAST_TRACK_END = "last_track_end"
STATE_KEY_LAST_TRACK_DISTANCE = "last_track_distance"
STATE_KEY_LAST_TRACK_AVG_SPEED = "last_track_avg_speed"
STATE_KEY_LAST_TRACK_RIDING_TIME = "last_track_riding_time"
STATE_KEY_BATTERY_TEMP_DESC = "battery_temp_desc"
STATE_KEY_BATTERY_LEVEL_B = "battery_level_b"
STATE_KEY_BATTERY_GRADE_B = "battery_grade_b"

class VehicleDataManager:
    """Manages shared vehicle state and simulation."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry_id: str,
        vehicle_type: str,
        entity_name: str,
    ) -> None:
        self._hass = hass
        self._config_entry_id = config_entry_id
        self._vehicle_type = vehicle_type
        self._entity_name = entity_name
        self._store = Store[dict[str, Any]](hass, STORAGE_VERSION, f"virtual_devices_vehicle_{config_entry_id}")
        self._data: dict[str, Any] = {}
        self._last_update: datetime | None = None
        self._initialized = False

    @property
    def vehicle_type(self) -> str:
        return self._vehicle_type

    def is_car(self) -> bool:
        return self._vehicle_type == "car"

    def is_ev(self) -> bool:
        return self._vehicle_type == "ev"

    def is_ebike(self) -> bool:
        return self._vehicle_type == "ebike"

    def get_state(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set_state(self, key: str, value: Any) -> None:
        self._data[key] = value

    def get_default_data(self) -> dict[str, Any]:
        is_car = self.is_car()
        is_ev = self.is_ev()
        is_ebike = self.is_ebike()
        return {
            STATE_KEY_SPEED: 0.0,
            STATE_KEY_ODOMETER: round(random.uniform(100, 50000), 1),
            STATE_KEY_LATITUDE: 37.7749,
            STATE_KEY_LONGITUDE: -122.4194,
            STATE_KEY_IS_LOCKED: True,
            STATE_KEY_IS_ON: False,
            STATE_KEY_PARKING_BRAKE: True,
            STATE_KEY_USER_PRESENT: True,
            STATE_KEY_OUTSIDE_TEMP: round(random.uniform(5, 35), 1),
            STATE_KEY_INSIDE_TEMP: round(random.uniform(15, 30), 1),
            STATE_KEY_FUEL_LEVEL: random.randint(20, 100) if is_car else 0,
            STATE_KEY_FUEL_RANGE: random.randint(100, 800) if is_car else 0,
            STATE_KEY_BATTERY_LEVEL: random.randint(20, 100) if (is_ev or is_ebike) else 0,
            STATE_KEY_BATTERY_RANGE: random.randint(50, 600) if (is_ev or is_ebike) else 0,
            STATE_KEY_BATTERY_VOLTAGE: round(random.uniform(350, 400), 1) if is_ev else (round(random.uniform(36, 52), 1) if is_ebike else 0),
            STATE_KEY_BATTERY_CURRENT: 0.0,
            STATE_KEY_MOTOR_POWER: 0.0,
            STATE_KEY_CHARGING: False,
            STATE_KEY_CHARGE_CABLE_CONNECTED: False,
            STATE_KEY_CHARGE_LIMIT: 90,
            STATE_KEY_CHARGE_CURRENT: 16,
            STATE_KEY_CHARGE_RATE: 0.0,
            STATE_KEY_CHARGER_POWER: 0.0,
            STATE_KEY_CHARGER_VOLTAGE: 0.0,
            STATE_KEY_CHARGER_CURRENT: 0.0,
            STATE_KEY_CHARGE_ENERGY_ADDED: 0.0,
            STATE_KEY_TIME_TO_FULL_CHARGE: 0,
            STATE_KEY_SENTRY_MODE: False,
            STATE_KEY_CLIMATE_ON: False,
            STATE_KEY_TARGET_TEMP: 22.0,
            STATE_KEY_DEFROST: False,
            STATE_KEY_CABIN_OVERHEAT_PROTECTION: False,
            STATE_KEY_DRIVE_MODE: "Park",
            STATE_KEY_SEAT_HEATER_FRONT_LEFT: "off",
            STATE_KEY_SEAT_HEATER_FRONT_RIGHT: "off",
            STATE_KEY_SEAT_HEATER_REAR_LEFT: "off",
            STATE_KEY_SEAT_HEATER_REAR_CENTER: "off",
            STATE_KEY_SEAT_HEATER_REAR_RIGHT: "off",
            STATE_KEY_STEERING_WHEEL_HEATER: "off",
            STATE_KEY_AUTO_SEAT_CLIMATE_LEFT: False,
            STATE_KEY_AUTO_SEAT_CLIMATE_RIGHT: False,
            STATE_KEY_AUTO_STEERING_WHEEL_HEATER: False,
            STATE_KEY_CHARGE_PORT_OPEN: False,
            STATE_KEY_FRUNK_OPEN: False,
            STATE_KEY_TRUNK_OPEN: False,
            STATE_KEY_SUNROOF_POSITION: 100,
            STATE_KEY_WINDOW_FL: 100,
            STATE_KEY_WINDOW_FR: 100,
            STATE_KEY_WINDOW_RL: 100,
            STATE_KEY_WINDOW_RR: 100,
            STATE_KEY_FRONT_DRIVER_DOOR: False,
            STATE_KEY_FRONT_PASSENGER_DOOR: False,
            STATE_KEY_REAR_DRIVER_DOOR: False,
            STATE_KEY_REAR_PASSENGER_DOOR: False,
            STATE_KEY_HOOD: False,
            STATE_KEY_TRUNK_LID: False,
            STATE_KEY_TIRE_PRESSURE_FL: round(random.uniform(2.2, 2.8), 2),
            STATE_KEY_TIRE_PRESSURE_FR: round(random.uniform(2.2, 2.8), 2),
            STATE_KEY_TIRE_PRESSURE_RL: round(random.uniform(2.2, 2.8), 2),
            STATE_KEY_TIRE_PRESSURE_RR: round(random.uniform(2.2, 2.8), 2),
            STATE_KEY_TIRE_WARNING_FL: False,
            STATE_KEY_TIRE_WARNING_FR: False,
            STATE_KEY_TIRE_WARNING_RL: False,
            STATE_KEY_TIRE_WARNING_RR: False,
            STATE_KEY_OIL_LEVEL: random.randint(50, 100) if is_car else 0,
            STATE_KEY_COOLANT_TEMP: round(random.uniform(80, 95), 1) if is_car else 0,
            STATE_KEY_BATTERY_TEMP: round(random.uniform(20, 40), 1) if (is_ev or is_ebike) else 0,
            STATE_KEY_LIGHT_ON: False,
            STATE_KEY_BRAKE_ENGAGED: True,
            STATE_KEY_HORN_ON: False,
            STATE_KEY_SPEED_LIMIT: 25,
            STATE_KEY_ASSIST_LEVEL: 1,
            STATE_KEY_TRIP_DISTANCE: round(random.uniform(0, 50), 1),
            STATE_KEY_ESTIMATED_RANGE: random.randint(50, 600) if (is_ev or is_ebike) else 0,
            STATE_KEY_SOFTWARE_UPDATE_AVAILABLE: random.choice([True, False]),
            STATE_KEY_SOFTWARE_UPDATE_VERSION: "2025.32.1",
            STATE_KEY_SOFTWARE_UPDATE_INSTALLING: False,
            STATE_KEY_SOFTWARE_UPDATE_PROGRESS: 0,
            STATE_KEY_TIMES_CHARGED: random.randint(10, 200),
            STATE_KEY_BATTERY_GRADE: random.randint(80, 100),
            STATE_KEY_TIME_LEFT: random.randint(1, 8),
            STATE_KEY_CENTRE_CTRL_BATT: random.randint(60, 100),
            STATE_KEY_HDOP: round(random.uniform(0.5, 3.0), 1),
            STATE_KEY_RIDING_TIME: 0,
            STATE_KEY_DAYS_IN_USE: random.randint(30, 500),
            STATE_KEY_LAST_TRACK_START: datetime.now().isoformat(),
            STATE_KEY_LAST_TRACK_END: datetime.now().isoformat(),
            STATE_KEY_LAST_TRACK_DISTANCE: round(random.uniform(1, 20), 1),
            STATE_KEY_LAST_TRACK_AVG_SPEED: round(random.uniform(15, 40), 1),
            STATE_KEY_LAST_TRACK_RIDING_TIME: random.randint(300, 3600),
            STATE_KEY_BATTERY_TEMP_DESC: "Normal",
            STATE_KEY_BATTERY_LEVEL_B: random.randint(20, 100),
            STATE_KEY_BATTERY_GRADE_B: random.randint(80, 100),
        }

    async def async_load(self) -> None:
        try:
            stored = await self._store.async_load()
            if stored is not None:
                self._data.update(stored)
            else:
                self._data = self.get_default_data()
                await self.async_save()
        except Exception as ex:
            _LOGGER.error("Error loading vehicle state: %s", ex)
            self._data = self.get_default_data()
        self._last_update = datetime.now()
        self._initialized = True

    async def async_save(self) -> None:
        try:
            await self._store.async_save(self._data)
        except Exception as ex:
            _LOGGER.error("Error saving vehicle state: %s", ex)

    async def async_simulate(self) -> None:
        now = datetime.now()
        if self._last_update is None:
            self._last_update = now
            return
        delta = (now - self._last_update).total_seconds()
        self._last_update = now
        is_on = self._data.get(STATE_KEY_IS_ON, False)
        speed = self._data.get(STATE_KEY_SPEED, 0.0)
        is_car = self.is_car()
        is_ev = self.is_ev()
        is_ebike = self.is_ebike()
        if is_on and speed > 0:
            speed_variation = random.uniform(-2, 2)
            new_speed = max(0, speed + speed_variation)
            self._data[STATE_KEY_SPEED] = round(new_speed, 1)
            distance_delta = new_speed * delta / 3600
            self._data[STATE_KEY_ODOMETER] = round(self._data.get(STATE_KEY_ODOMETER, 0) + distance_delta, 2)
            if is_ebike:
                self._data[STATE_KEY_TRIP_DISTANCE] = round(self._data.get(STATE_KEY_TRIP_DISTANCE, 0) + distance_delta, 2)
        if is_on:
            parked = speed < 0.5
            self._data[STATE_KEY_PARKING_BRAKE] = parked
            self._data[STATE_KEY_BRAKE_ENGAGED] = parked or random.random() < 0.1
            if not parked:
                self._data[STATE_KEY_DRIVE_MODE] = "Drive"
        if is_car and is_on and speed > 0:
            fuel_consumption = speed * delta / 3600 * random.uniform(0.05, 0.15)
            current_fuel = self._data.get(STATE_KEY_FUEL_LEVEL, 100)
            new_fuel = max(0, current_fuel - fuel_consumption)
            self._data[STATE_KEY_FUEL_LEVEL] = round(new_fuel, 1)
            self._data[STATE_KEY_FUEL_RANGE] = round(new_fuel / 100 * random.uniform(500, 800), 1) if new_fuel > 0 else 0
        if (is_ev or is_ebike) and is_on and speed > 0:
            consumption = speed * delta / 3600 * random.uniform(0.15, 0.3)
            current_bat = self._data.get(STATE_KEY_BATTERY_LEVEL, 100)
            new_bat = max(0, current_bat - consumption)
            self._data[STATE_KEY_BATTERY_LEVEL] = round(new_bat, 1)
            if new_bat > 0:
                range_km = new_bat / 100 * random.uniform(300, 600)
                self._data[STATE_KEY_BATTERY_RANGE] = round(range_km, 1)
                self._data[STATE_KEY_ESTIMATED_RANGE] = round(range_km, 1)
            else:
                self._data[STATE_KEY_BATTERY_RANGE] = 0
                self._data[STATE_KEY_ESTIMATED_RANGE] = 0
        if (is_ev or is_ebike) and is_on:
            power = speed * random.uniform(5, 15) if speed > 0 else 0
            self._data[STATE_KEY_MOTOR_POWER] = round(power, 1)
            voltage = self._data.get(STATE_KEY_BATTERY_VOLTAGE, 400)
            self._data[STATE_KEY_BATTERY_CURRENT] = round(power / voltage, 2) if voltage > 0 else 0.0
        if (is_ev or is_ebike) and self._data.get(STATE_KEY_CHARGING, False):
            charge_rate = random.uniform(0.5, 1.0)
            current_bat = self._data.get(STATE_KEY_BATTERY_LEVEL, 0)
            charge_limit = self._data.get(STATE_KEY_CHARGE_LIMIT, 90)
            if current_bat < charge_limit:
                new_bat = min(charge_limit, current_bat + charge_rate * delta / 60)
                self._data[STATE_KEY_BATTERY_LEVEL] = round(new_bat, 1)
                remaining = charge_limit - new_bat
                self._data[STATE_KEY_TIME_TO_FULL_CHARGE] = max(0, int(remaining / charge_rate))
                self._data[STATE_KEY_CHARGE_ENERGY_ADDED] = round(self._data.get(STATE_KEY_CHARGE_ENERGY_ADDED, 0) + charge_rate * delta / 3600, 2)
                self._data[STATE_KEY_CHARGE_RATE] = round(charge_rate * 60, 1)
                self._data[STATE_KEY_CHARGER_POWER] = round(charge_rate * 2.5, 1)
                self._data[STATE_KEY_CHARGER_VOLTAGE] = round(random.uniform(230, 240), 1)
                self._data[STATE_KEY_CHARGER_CURRENT] = round(charge_rate * 2.5 * 1000 / 240, 1)
            else:
                self._data[STATE_KEY_CHARGING] = False
                self._data[STATE_KEY_CHARGE_RATE] = 0.0
                self._data[STATE_KEY_CHARGER_POWER] = 0.0
                self._data[STATE_KEY_CHARGER_VOLTAGE] = 0.0
                self._data[STATE_KEY_CHARGER_CURRENT] = 0.0
                self._data[STATE_KEY_TIME_TO_FULL_CHARGE] = 0
        if (is_ev or is_ebike) and not self._data.get(STATE_KEY_CHARGING, False):
            if self._data.get(STATE_KEY_CHARGE_CABLE_CONNECTED, False):
                self._data[STATE_KEY_CHARGE_RATE] = 0.0
                self._data[STATE_KEY_CHARGER_POWER] = 0.0
                self._data[STATE_KEY_CHARGER_VOLTAGE] = 0.0
                self._data[STATE_KEY_CHARGER_CURRENT] = 0.0
        outside_temp = self._data.get(STATE_KEY_OUTSIDE_TEMP, 20.0)
        inside_temp = self._data.get(STATE_KEY_INSIDE_TEMP, 22.0)
        if is_car or is_ev:
            if self._data.get(STATE_KEY_CLIMATE_ON, False):
                target = self._data.get(STATE_KEY_TARGET_TEMP, 22.0)
                if abs(inside_temp - target) > 0.5:
                    inside_temp += (target - inside_temp) * 0.1 * delta / 60
                self._data[STATE_KEY_INSIDE_TEMP] = round(inside_temp, 1)
            else:
                drift = (outside_temp - inside_temp) * 0.05 * delta / 60
                self._data[STATE_KEY_INSIDE_TEMP] = round(inside_temp + drift, 1)
        outside_drift = random.uniform(-0.1, 0.1) * delta / 60
        self._data[STATE_KEY_OUTSIDE_TEMP] = round(outside_temp + outside_drift, 1)
        if is_ev or is_ebike:
            bat_temp = self._data.get(STATE_KEY_BATTERY_TEMP, 25.0)
            if self._data.get(STATE_KEY_CHARGING, False):
                bat_temp += 0.1 * delta / 60
            elif is_on and speed > 0:
                bat_temp += 0.05 * delta / 60
            else:
                bat_temp -= 0.02 * delta / 60
            self._data[STATE_KEY_BATTERY_TEMP] = round(max(5, min(60, bat_temp)), 1)
        if is_ebike:
            if is_on and speed > 0:
                self._data[STATE_KEY_RIDING_TIME] = self._data.get(STATE_KEY_RIDING_TIME, 0) + int(delta)
            if self._data.get(STATE_KEY_CHARGING, False):
                was_charging = self._data.get("_was_charging", False)
                if not was_charging:
                    self._data[STATE_KEY_TIMES_CHARGED] = self._data.get(STATE_KEY_TIMES_CHARGED, 0) + 1
                self._data["_was_charging"] = True
            else:
                self._data["_was_charging"] = False
            ctrl_batt = self._data.get(STATE_KEY_CENTRE_CTRL_BATT, 100)
            ctrl_batt -= 0.001 * delta / 60
            self._data[STATE_KEY_CENTRE_CTRL_BATT] = round(max(0, ctrl_batt), 1)
            hdop = self._data.get(STATE_KEY_HDOP, 1.0)
            hdop += random.uniform(-0.1, 0.1) * delta / 60
            self._data[STATE_KEY_HDOP] = round(max(0.5, min(10.0, hdop)), 1)
            if self._data.get(STATE_KEY_BATTERY_TEMP, 25.0) < 15:
                self._data[STATE_KEY_BATTERY_TEMP_DESC] = "Cold"
            elif bat_temp > 40:
                self._data[STATE_KEY_BATTERY_TEMP_DESC] = "High"
            else:
                self._data[STATE_KEY_BATTERY_TEMP_DESC] = "Normal"
        if is_car and is_on:
            coolant = self._data.get(STATE_KEY_COOLANT_TEMP, 85.0)
            target_coolant = 85 + speed * 0.1
            coolant += (target_coolant - coolant) * 0.05 * delta / 60
            self._data[STATE_KEY_COOLANT_TEMP] = round(max(20, min(120, coolant)), 1)
        if speed < 0.5:
            lat = self._data.get(STATE_KEY_LATITUDE, 37.7749)
            lon = self._data.get(STATE_KEY_LONGITUDE, -122.4194)
            lat += random.uniform(-0.00001, 0.00001) * delta / 60
            lon += random.uniform(-0.00001, 0.00001) * delta / 60
            self._data[STATE_KEY_LATITUDE] = round(lat, 6)
            self._data[STATE_KEY_LONGITUDE] = round(lon, 6)
        for wheel in ["fl", "fr", "rl", "rr"]:
            key = f"tire_warning_{wheel}"
            if random.random() < 0.001:
                self._data[key] = True
            elif self._data.get(key, False) and random.random() < 0.05:
                self._data[key] = False
        await self.async_save()

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    device_type: str | None = config_entry.data.get("device_type")
    if device_type != "vehicle":
        return

    vehicle_type: str = config_entry.data.get("vehicle_type", "ev")
    if vehicle_type not in VEHICLE_TYPES:
        _LOGGER.error("Unknown vehicle type: %s", vehicle_type)
        return

    device_info: DeviceInfo = hass.data[DOMAIN][config_entry.entry_id]["device_info"]
    entities_config: list[dict[str, Any]] = config_entry.data.get("entities", [])
    if not entities_config:
        return

    entity_config = entities_config[0]
    entity_name = entity_config.get("entity_name", f"vehicle_{vehicle_type}")

    manager = VehicleDataManager(hass, config_entry.entry_id, vehicle_type, entity_name)
    await manager.async_load()
    hass.data[DOMAIN][config_entry.entry_id]["vehicle_manager"] = manager

    entities: list[Any] = []

    # Lock
    entities.append(VirtualVehicleLock(hass, config_entry.entry_id, entity_name, 0, device_info, manager))

    # Device tracker
    entities.append(VirtualVehicleTracker(hass, config_entry.entry_id, entity_name, 1, device_info, manager))

    # Binary sensors
    bin_idx = 2
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

    # Sensors
    sens_idx = 100
    entities.append(VirtualVehicleSpeedSensor(hass, config_entry.entry_id, entity_name, sens_idx, device_info, manager))
    sens_idx += 1
    entities.append(VirtualVehicleOdometerSensor(hass, config_entry.entry_id, entity_name, sens_idx, device_info, manager))
    sens_idx += 1
    if vehicle_type == "ebike":
        entities.append(VirtualVehicleTripDistanceSensor(hass, config_entry.entry_id, entity_name, sens_idx, device_info, manager))
        sens_idx += 1
    entities.append(VirtualVehicleOutsideTempSensor(hass, config_entry.entry_id, entity_name, sens_idx, device_info, manager))
    sens_idx += 1
    if vehicle_type in ("car", "ev"):
        entities.append(VirtualVehicleInsideTempSensor(hass, config_entry.entry_id, entity_name, sens_idx, device_info, manager))
        sens_idx += 1
    if vehicle_type == "car":
        entities.append(VirtualVehicleFuelLevelSensor(hass, config_entry.entry_id, entity_name, sens_idx, device_info, manager))
        sens_idx += 1
        entities.append(VirtualVehicleFuelRangeSensor(hass, config_entry.entry_id, entity_name, sens_idx, device_info, manager))
        sens_idx += 1
    if vehicle_type in ("ev", "ebike"):
        entities.append(VirtualVehicleBatteryLevelSensor(hass, config_entry.entry_id, entity_name, sens_idx, device_info, manager))
        sens_idx += 1
        entities.append(VirtualVehicleBatteryRangeSensor(hass, config_entry.entry_id, entity_name, sens_idx, device_info, manager))
        sens_idx += 1
        entities.append(VirtualVehicleBatteryVoltageSensor(hass, config_entry.entry_id, entity_name, sens_idx, device_info, manager))
        sens_idx += 1
        entities.append(VirtualVehicleBatteryCurrentSensor(hass, config_entry.entry_id, entity_name, sens_idx, device_info, manager))
        sens_idx += 1
        entities.append(VirtualVehicleMotorPowerSensor(hass, config_entry.entry_id, entity_name, sens_idx, device_info, manager))
        sens_idx += 1
    if vehicle_type == "ev":
        entities.append(VirtualVehicleChargeRateSensor(hass, config_entry.entry_id, entity_name, sens_idx, device_info, manager))
        sens_idx += 1
        entities.append(VirtualVehicleChargerPowerSensor(hass, config_entry.entry_id, entity_name, sens_idx, device_info, manager))
        sens_idx += 1
        entities.append(VirtualVehicleChargerVoltageSensor(hass, config_entry.entry_id, entity_name, sens_idx, device_info, manager))
        sens_idx += 1
        entities.append(VirtualVehicleChargerCurrentSensor(hass, config_entry.entry_id, entity_name, sens_idx, device_info, manager))
        sens_idx += 1
        entities.append(VirtualVehicleChargeEnergyAddedSensor(hass, config_entry.entry_id, entity_name, sens_idx, device_info, manager))
        sens_idx += 1
        entities.append(VirtualVehicleTimeToFullChargeSensor(hass, config_entry.entry_id, entity_name, sens_idx, device_info, manager))
        sens_idx += 1
    if vehicle_type in ("car", "ev"):
        for wheel in ["FL", "FR", "RL", "RR"]:
            entities.append(VirtualVehicleTirePressureSensor(hass, config_entry.entry_id, entity_name, sens_idx, device_info, manager, wheel))
            sens_idx += 1
    if vehicle_type == "car":
        entities.append(VirtualVehicleOilLevelSensor(hass, config_entry.entry_id, entity_name, sens_idx, device_info, manager))
        sens_idx += 1
        entities.append(VirtualVehicleCoolantTempSensor(hass, config_entry.entry_id, entity_name, sens_idx, device_info, manager))
        sens_idx += 1
    if vehicle_type in ("ev", "ebike"):
        entities.append(VirtualVehicleBatteryTempSensor(hass, config_entry.entry_id, entity_name, sens_idx, device_info, manager))
        sens_idx += 1
        entities.append(VirtualVehicleEstimatedRangeSensor(hass, config_entry.entry_id, entity_name, sens_idx, device_info, manager))
        sens_idx += 1
    if vehicle_type == "ebike":
        entities.append(VirtualVehicleAssistLevelSensor(hass, config_entry.entry_id, entity_name, sens_idx, device_info, manager))
        sens_idx += 1
        entities.append(VirtualVehicleTimesChargedSensor(hass, config_entry.entry_id, entity_name, sens_idx, device_info, manager))
        sens_idx += 1
        entities.append(VirtualVehicleBatteryGradeSensor(hass, config_entry.entry_id, entity_name, sens_idx, device_info, manager))
        sens_idx += 1
        entities.append(VirtualVehicleBatteryGradeSensor(hass, config_entry.entry_id, entity_name, sens_idx, device_info, manager, " B"))
        sens_idx += 1
        entities.append(VirtualVehicleTimeLeftSensor(hass, config_entry.entry_id, entity_name, sens_idx, device_info, manager))
        sens_idx += 1
        entities.append(VirtualVehicleCentreCtrlBattSensor(hass, config_entry.entry_id, entity_name, sens_idx, device_info, manager))
        sens_idx += 1
        entities.append(VirtualVehicleHDopSensor(hass, config_entry.entry_id, entity_name, sens_idx, device_info, manager))
        sens_idx += 1
        entities.append(VirtualVehicleRidingTimeSensor(hass, config_entry.entry_id, entity_name, sens_idx, device_info, manager))
        sens_idx += 1
        entities.append(VirtualVehicleDaysInUseSensor(hass, config_entry.entry_id, entity_name, sens_idx, device_info, manager))
        sens_idx += 1
        entities.append(VirtualVehicleBatteryTempDescSensor(hass, config_entry.entry_id, entity_name, sens_idx, device_info, manager))
        sens_idx += 1
        entities.append(VirtualVehicleBatteryLevelBSensor(hass, config_entry.entry_id, entity_name, sens_idx, device_info, manager))
        sens_idx += 1

    # Buttons
    btn_idx = 200
    entities.append(VirtualVehicleFlashLightsButton(hass, config_entry.entry_id, entity_name, btn_idx, device_info, manager))
    btn_idx += 1
    if vehicle_type in ("car", "ev"):
        entities.append(VirtualVehicleHonkHornButton(hass, config_entry.entry_id, entity_name, btn_idx, device_info, manager))
        btn_idx += 1
    if vehicle_type == "ev":
        entities.append(VirtualVehicleWakeButton(hass, config_entry.entry_id, entity_name, btn_idx, device_info, manager))
        btn_idx += 1
        entities.append(VirtualVehicleKeylessDrivingButton(hass, config_entry.entry_id, entity_name, btn_idx, device_info, manager))
        btn_idx += 1

    # Switches
    sw_idx = 300
    if vehicle_type == "ev":
        entities.append(VirtualVehicleSentryModeSwitch(hass, config_entry.entry_id, entity_name, sw_idx, device_info, manager))
        sw_idx += 1
        entities.append(VirtualVehicleChargeSwitch(hass, config_entry.entry_id, entity_name, sw_idx, device_info, manager))
        sw_idx += 1
    if vehicle_type in ("car", "ev"):
        entities.append(VirtualVehicleDefrostSwitch(hass, config_entry.entry_id, entity_name, sw_idx, device_info, manager))
        sw_idx += 1
    if vehicle_type == "ev":
        entities.append(VirtualVehicleAutoSeatClimateLeftSwitch(hass, config_entry.entry_id, entity_name, sw_idx, device_info, manager))
        sw_idx += 1
        entities.append(VirtualVehicleAutoSeatClimateRightSwitch(hass, config_entry.entry_id, entity_name, sw_idx, device_info, manager))
        sw_idx += 1
        entities.append(VirtualVehicleAutoSteeringWheelHeaterSwitch(hass, config_entry.entry_id, entity_name, sw_idx, device_info, manager))
        sw_idx += 1
    if vehicle_type == "ebike":
        entities.append(VirtualVehicleLightSwitch(hass, config_entry.entry_id, entity_name, sw_idx, device_info, manager))
        sw_idx += 1
        entities.append(VirtualVehicleHornSwitch(hass, config_entry.entry_id, entity_name, sw_idx, device_info, manager))
        sw_idx += 1

    # Numbers
    num_idx = 400
    if vehicle_type == "ev":
        entities.append(VirtualVehicleChargeLimitNumber(hass, config_entry.entry_id, entity_name, num_idx, device_info, manager))
        num_idx += 1
        entities.append(VirtualVehicleChargeCurrentNumber(hass, config_entry.entry_id, entity_name, num_idx, device_info, manager))
        num_idx += 1
    if vehicle_type in ("car", "ev"):
        entities.append(VirtualVehicleTargetTempNumber(hass, config_entry.entry_id, entity_name, num_idx, device_info, manager))
        num_idx += 1
    if vehicle_type == "ebike":
        entities.append(VirtualVehicleSpeedLimitNumber(hass, config_entry.entry_id, entity_name, num_idx, device_info, manager))
        num_idx += 1
        entities.append(VirtualVehicleAssistLevelNumber(hass, config_entry.entry_id, entity_name, num_idx, device_info, manager))
        num_idx += 1

    # Selects
    sel_idx = 500
    if vehicle_type == "ev":
        for pos in ["Front Left", "Front Right", "Rear Left", "Rear Center", "Rear Right"]:
            entities.append(VirtualVehicleSeatHeaterSelect(hass, config_entry.entry_id, entity_name, sel_idx, device_info, manager, pos))
            sel_idx += 1
        entities.append(VirtualVehicleSteeringWheelHeaterSelect(hass, config_entry.entry_id, entity_name, sel_idx, device_info, manager))
        sel_idx += 1
    if vehicle_type in ("car", "ev"):
        entities.append(VirtualVehicleDriveModeSelect(hass, config_entry.entry_id, entity_name, sel_idx, device_info, manager))
        sel_idx += 1

    # Covers
    cov_idx = 600
    if vehicle_type == "ev":
        entities.append(VirtualVehicleChargePortCover(hass, config_entry.entry_id, entity_name, cov_idx, device_info, manager))
        cov_idx += 1
        entities.append(VirtualVehicleFrunkCover(hass, config_entry.entry_id, entity_name, cov_idx, device_info, manager))
        cov_idx += 1
    if vehicle_type in ("car", "ev"):
        entities.append(VirtualVehicleTrunkCover(hass, config_entry.entry_id, entity_name, cov_idx, device_info, manager))
        cov_idx += 1
        entities.append(VirtualVehicleSunroofCover(hass, config_entry.entry_id, entity_name, cov_idx, device_info, manager))
        cov_idx += 1
        entities.append(VirtualVehicleWindowsCover(hass, config_entry.entry_id, entity_name, cov_idx, device_info, manager))
        cov_idx += 1
        for window in ["FL", "FR", "RL", "RR"]:
            entities.append(VirtualVehicleWindowCover(hass, config_entry.entry_id, entity_name, cov_idx, device_info, manager, window))
            cov_idx += 1

    # Climate
    if vehicle_type in ("car", "ev"):
        entities.append(VirtualVehicleClimate(hass, config_entry.entry_id, entity_name, 700, device_info, manager))
        if vehicle_type == "ev":
            entities.append(VirtualVehicleCabinOverheatProtectionSwitch(hass, config_entry.entry_id, entity_name, 701, device_info, manager))

    # Update
    if vehicle_type == "ev":
        entities.append(VirtualVehicleUpdate(hass, config_entry.entry_id, entity_name, 800, device_info, manager))

    async_add_entities(entities)
    _LOGGER.info("Set up %d entities for vehicle '%s' (%s)", len(entities), entity_name, vehicle_type)

class VirtualVehicleLock(LockEntity):
    """Vehicle door lock."""

    _attr_should_poll = True

    def __init__(self, hass, config_entry_id, entity_name, index, device_info, manager):
        self._hass = hass
        self._manager = manager
        self._attr_name = f"{entity_name} Door Lock"
        self._attr_unique_id = f"{config_entry_id}_vehicle_{index}_lock"
        self._attr_device_info = device_info
        self._attr_icon = "mdi:car-door-lock"

    @property
    def is_locked(self) -> bool | None:
        return self._manager.get_state(STATE_KEY_IS_LOCKED, True)

    async def async_lock(self, **kwargs):
        self._manager.set_state(STATE_KEY_IS_LOCKED, True)
        await self._manager.async_save()
        self.async_write_ha_state()

    async def async_unlock(self, **kwargs):
        self._manager.set_state(STATE_KEY_IS_LOCKED, False)
        await self._manager.async_save()
        self.async_write_ha_state()

    async def async_update(self):
        await self._manager.async_simulate()


class VirtualVehicleTracker(TrackerEntity):
    """Vehicle GPS location tracker."""

    _attr_should_poll = True

    def __init__(self, hass, config_entry_id, entity_name, index, device_info, manager):
        self._hass = hass
        self._manager = manager
        self._attr_name = f"{entity_name} Location"
        self._attr_unique_id = f"{config_entry_id}_vehicle_{index}_tracker"
        self._attr_device_info = device_info
        self._attr_icon = "mdi:map-marker"

    @property
    def source_type(self) -> SourceType:
        return SourceType.GPS

    @property
    def latitude(self) -> float | None:
        return self._manager.get_state(STATE_KEY_LATITUDE)

    @property
    def longitude(self) -> float | None:
        return self._manager.get_state(STATE_KEY_LONGITUDE)

    async def async_update(self):
        await self._manager.async_simulate()


class VirtualVehicleDoorSensor(BinarySensorEntity):
    """Vehicle door open/closed sensor."""

    _attr_should_poll = True
    _attr_device_class = BinarySensorDeviceClass.DOOR

    def __init__(self, hass, config_entry_id, entity_name, index, device_info, manager, door_name):
        self._hass = hass
        self._manager = manager
        self._door_name = door_name
        self._attr_name = f"{entity_name} {door_name}"
        self._attr_unique_id = f"{config_entry_id}_vehicle_{index}_door_{door_name.lower().replace(' ', '_')}"
        self._attr_device_info = device_info

    @property
    def is_on(self) -> bool:
        key_map = {
            "Front Driver Door": STATE_KEY_FRONT_DRIVER_DOOR,
            "Front Passenger Door": STATE_KEY_FRONT_PASSENGER_DOOR,
            "Rear Driver Door": STATE_KEY_REAR_DRIVER_DOOR,
            "Rear Passenger Door": STATE_KEY_REAR_PASSENGER_DOOR,
        }
        return self._manager.get_state(key_map.get(self._door_name, ""), False)

    async def async_update(self):
        await self._manager.async_simulate()


class VirtualVehicleTrunkSensor(BinarySensorEntity):
    """Trunk open/closed sensor."""

    _attr_should_poll = True
    _attr_device_class = BinarySensorDeviceClass.DOOR

    def __init__(self, hass, config_entry_id, entity_name, index, device_info, manager):
        self._hass = hass
        self._manager = manager
        self._attr_name = f"{entity_name} Trunk"
        self._attr_unique_id = f"{config_entry_id}_vehicle_{index}_trunk"
        self._attr_device_info = device_info
        self._attr_icon = "mdi:car-back"

    @property
    def is_on(self) -> bool:
        return self._manager.get_state(STATE_KEY_TRUNK_LID, False)

    async def async_update(self):
        await self._manager.async_simulate()


class VirtualVehicleHoodSensor(BinarySensorEntity):
    """Hood open/closed sensor."""

    _attr_should_poll = True
    _attr_device_class = BinarySensorDeviceClass.DOOR

    def __init__(self, hass, config_entry_id, entity_name, index, device_info, manager):
        self._hass = hass
        self._manager = manager
        self._attr_name = f"{entity_name} Hood"
        self._attr_unique_id = f"{config_entry_id}_vehicle_{index}_hood"
        self._attr_device_info = device_info
        self._attr_icon = "mdi:car"

    @property
    def is_on(self) -> bool:
        return self._manager.get_state(STATE_KEY_HOOD, False)

    async def async_update(self):
        await self._manager.async_simulate()


class VirtualVehicleEngineStatusSensor(BinarySensorEntity):
    """Engine/power status sensor."""

    _attr_should_poll = True

    def __init__(self, hass, config_entry_id, entity_name, index, device_info, manager, vtype):
        self._hass = hass
        self._manager = manager
        label = "Engine Status" if vtype == "car" else "Power Status"
        self._attr_name = f"{entity_name} {label}"
        self._attr_unique_id = f"{config_entry_id}_vehicle_{index}_engine_status"
        self._attr_device_info = device_info
        self._attr_device_class = BinarySensorDeviceClass.POWER
        self._attr_icon = "mdi:engine" if vtype == "car" else "mdi:lightning-bolt"

    @property
    def is_on(self) -> bool:
        return self._manager.get_state(STATE_KEY_IS_ON, False)

    async def async_update(self):
        await self._manager.async_simulate()


class VirtualVehicleUserPresentSensor(BinarySensorEntity):
    """User present (key detected) sensor."""

    _attr_should_poll = True
    _attr_device_class = BinarySensorDeviceClass.PRESENCE

    def __init__(self, hass, config_entry_id, entity_name, index, device_info, manager):
        self._hass = hass
        self._manager = manager
        self._attr_name = f"{entity_name} User Present"
        self._attr_unique_id = f"{config_entry_id}_vehicle_{index}_user_present"
        self._attr_device_info = device_info
        self._attr_icon = "mdi:account"

    @property
    def is_on(self) -> bool:
        return self._manager.get_state(STATE_KEY_USER_PRESENT, True)

    async def async_update(self):
        await self._manager.async_simulate()


class VirtualVehicleParkingBrakeSensor(BinarySensorEntity):
    """Parking brake engaged sensor."""

    _attr_should_poll = True

    def __init__(self, hass, config_entry_id, entity_name, index, device_info, manager):
        self._hass = hass
        self._manager = manager
        self._attr_name = f"{entity_name} Parking Brake"
        self._attr_unique_id = f"{config_entry_id}_vehicle_{index}_parking_brake"
        self._attr_device_info = device_info
        self._attr_icon = "mdi:car-brake-parking"

    @property
    def is_on(self) -> bool:
        return self._manager.get_state(STATE_KEY_PARKING_BRAKE, True)

    async def async_update(self):
        await self._manager.async_simulate()


class VirtualVehicleTireWarningSensor(BinarySensorEntity):
    """Tire pressure warning sensor."""

    _attr_should_poll = True
    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(self, hass, config_entry_id, entity_name, index, device_info, manager, wheel):
        self._hass = hass
        self._manager = manager
        self._wheel = wheel
        self._attr_name = f"{entity_name} Tire Pressure Warning {wheel}"
        self._attr_unique_id = f"{config_entry_id}_vehicle_{index}_tire_warning_{wheel.lower()}"
        self._attr_device_info = device_info
        self._attr_icon = "mdi:tire"

    @property
    def is_on(self) -> bool:
        return self._manager.get_state(f"tire_warning_{self._wheel.lower()}", False)

    async def async_update(self):
        await self._manager.async_simulate()


class VirtualVehicleChargingSensor(BinarySensorEntity):
    """Charging status sensor."""

    _attr_should_poll = True
    _attr_device_class = BinarySensorDeviceClass.POWER

    def __init__(self, hass, config_entry_id, entity_name, index, device_info, manager):
        self._hass = hass
        self._manager = manager
        self._attr_name = f"{entity_name} Charging"
        self._attr_unique_id = f"{config_entry_id}_vehicle_{index}_charging"
        self._attr_device_info = device_info
        self._attr_icon = "mdi:lightning-bolt"

    @property
    def is_on(self) -> bool:
        return self._manager.get_state(STATE_KEY_CHARGING, False)

    async def async_update(self):
        await self._manager.async_simulate()


class VirtualVehicleChargeCableSensor(BinarySensorEntity):
    """Charge cable connected sensor."""

    _attr_should_poll = True

    def __init__(self, hass, config_entry_id, entity_name, index, device_info, manager):
        self._hass = hass
        self._manager = manager
        self._attr_name = f"{entity_name} Charge Cable Connected"
        self._attr_unique_id = f"{config_entry_id}_vehicle_{index}_charge_cable"
        self._attr_device_info = device_info
        self._attr_icon = "mdi:power-plug"

    @property
    def is_on(self) -> bool:
        return self._manager.get_state(STATE_KEY_CHARGE_CABLE_CONNECTED, False)

    async def async_update(self):
        await self._manager.async_simulate()


class VirtualVehicleLightOnSensor(BinarySensorEntity):
    """Light on/off sensor (ebike)."""

    _attr_should_poll = True
    _attr_device_class = BinarySensorDeviceClass.LIGHT

    def __init__(self, hass, config_entry_id, entity_name, index, device_info, manager):
        self._hass = hass
        self._manager = manager
        self._attr_name = f"{entity_name} Light On"
        self._attr_unique_id = f"{config_entry_id}_vehicle_{index}_light_on"
        self._attr_device_info = device_info
        self._attr_icon = "mdi:lightbulb"

    @property
    def is_on(self) -> bool:
        return self._manager.get_state(STATE_KEY_LIGHT_ON, False)

    async def async_update(self):
        await self._manager.async_simulate()


class VirtualVehicleBrakeEngagedSensor(BinarySensorEntity):
    """Brake engaged sensor (ebike)."""

    _attr_should_poll = True

    def __init__(self, hass, config_entry_id, entity_name, index, device_info, manager):
        self._hass = hass
        self._manager = manager
        self._attr_name = f"{entity_name} Brake Engaged"
        self._attr_unique_id = f"{config_entry_id}_vehicle_{index}_brake_engaged"
        self._attr_device_info = device_info
        self._attr_icon = "mdi:car-brake-hold"

    @property
    def is_on(self) -> bool:
        return self._manager.get_state(STATE_KEY_BRAKE_ENGAGED, True)

    async def async_update(self):
        await self._manager.async_simulate()

class VirtualVehicleSpeedSensor(SensorEntity):
    _attr_should_poll = True
    _attr_device_class = SensorDeviceClass.SPEED
    _attr_native_unit_of_measurement = UnitOfSpeed.KILOMETERS_PER_HOUR
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, hass, config_entry_id, entity_name, index, device_info, manager):
        self._hass = hass
        self._manager = manager
        self._attr_name = f"{entity_name} Speed"
        self._attr_unique_id = f"{config_entry_id}_vehicle_{index}_speed"
        self._attr_device_info = device_info
        self._attr_icon = "mdi:speedometer"

    @property
    def native_value(self) -> float:
        return self._manager.get_state(STATE_KEY_SPEED, 0.0)

    async def async_update(self):
        await self._manager.async_simulate()


class VirtualVehicleOdometerSensor(SensorEntity):
    _attr_should_poll = True
    _attr_device_class = SensorDeviceClass.DISTANCE
    _attr_native_unit_of_measurement = UnitOfLength.KILOMETERS
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(self, hass, config_entry_id, entity_name, index, device_info, manager):
        self._hass = hass
        self._manager = manager
        self._attr_name = f"{entity_name} Odometer"
        self._attr_unique_id = f"{config_entry_id}_vehicle_{index}_odometer"
        self._attr_device_info = device_info
        self._attr_icon = "mdi:counter"

    @property
    def native_value(self) -> float:
        return self._manager.get_state(STATE_KEY_ODOMETER, 0.0)

    async def async_update(self):
        await self._manager.async_simulate()


class VirtualVehicleTripDistanceSensor(SensorEntity):
    _attr_should_poll = True
    _attr_device_class = SensorDeviceClass.DISTANCE
    _attr_native_unit_of_measurement = UnitOfLength.KILOMETERS
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, hass, config_entry_id, entity_name, index, device_info, manager):
        self._hass = hass
        self._manager = manager
        self._attr_name = f"{entity_name} Trip Distance"
        self._attr_unique_id = f"{config_entry_id}_vehicle_{index}_trip_distance"
        self._attr_device_info = device_info
        self._attr_icon = "mdi:map-marker-distance"

    @property
    def native_value(self) -> float:
        return self._manager.get_state(STATE_KEY_TRIP_DISTANCE, 0.0)

    async def async_update(self):
        await self._manager.async_simulate()


class VirtualVehicleOutsideTempSensor(SensorEntity):
    _attr_should_poll = True
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, hass, config_entry_id, entity_name, index, device_info, manager):
        self._hass = hass
        self._manager = manager
        self._attr_name = f"{entity_name} Outside Temperature"
        self._attr_unique_id = f"{config_entry_id}_vehicle_{index}_outside_temp"
        self._attr_device_info = device_info
        self._attr_icon = "mdi:thermometer"

    @property
    def native_value(self) -> float:
        return self._manager.get_state(STATE_KEY_OUTSIDE_TEMP, 20.0)

    async def async_update(self):
        await self._manager.async_simulate()


class VirtualVehicleInsideTempSensor(SensorEntity):
    _attr_should_poll = True
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, hass, config_entry_id, entity_name, index, device_info, manager):
        self._hass = hass
        self._manager = manager
        self._attr_name = f"{entity_name} Inside Temperature"
        self._attr_unique_id = f"{config_entry_id}_vehicle_{index}_inside_temp"
        self._attr_device_info = device_info
        self._attr_icon = "mdi:thermometer"

    @property
    def native_value(self) -> float:
        return self._manager.get_state(STATE_KEY_INSIDE_TEMP, 22.0)

    async def async_update(self):
        await self._manager.async_simulate()


class VirtualVehicleFuelLevelSensor(SensorEntity):
    _attr_should_poll = True
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, hass, config_entry_id, entity_name, index, device_info, manager):
        self._hass = hass
        self._manager = manager
        self._attr_name = f"{entity_name} Fuel Level"
        self._attr_unique_id = f"{config_entry_id}_vehicle_{index}_fuel_level"
        self._attr_device_info = device_info
        self._attr_icon = "mdi:fuel"

    @property
    def native_value(self) -> float:
        return self._manager.get_state(STATE_KEY_FUEL_LEVEL, 0.0)

    async def async_update(self):
        await self._manager.async_simulate()


class VirtualVehicleFuelRangeSensor(SensorEntity):
    _attr_should_poll = True
    _attr_device_class = SensorDeviceClass.DISTANCE
    _attr_native_unit_of_measurement = UnitOfLength.KILOMETERS
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, hass, config_entry_id, entity_name, index, device_info, manager):
        self._hass = hass
        self._manager = manager
        self._attr_name = f"{entity_name} Fuel Range"
        self._attr_unique_id = f"{config_entry_id}_vehicle_{index}_fuel_range"
        self._attr_device_info = device_info
        self._attr_icon = "mdi:gas-station"

    @property
    def native_value(self) -> float:
        return self._manager.get_state(STATE_KEY_FUEL_RANGE, 0.0)

    async def async_update(self):
        await self._manager.async_simulate()


class VirtualVehicleBatteryLevelSensor(SensorEntity):
    _attr_should_poll = True
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, hass, config_entry_id, entity_name, index, device_info, manager):
        self._hass = hass
        self._manager = manager
        self._attr_name = f"{entity_name} Battery Level"
        self._attr_unique_id = f"{config_entry_id}_vehicle_{index}_battery_level"
        self._attr_device_info = device_info
        self._attr_icon = "mdi:battery"

    @property
    def native_value(self) -> float:
        return self._manager.get_state(STATE_KEY_BATTERY_LEVEL, 0.0)

    async def async_update(self):
        await self._manager.async_simulate()


class VirtualVehicleBatteryRangeSensor(SensorEntity):
    _attr_should_poll = True
    _attr_device_class = SensorDeviceClass.DISTANCE
    _attr_native_unit_of_measurement = UnitOfLength.KILOMETERS
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, hass, config_entry_id, entity_name, index, device_info, manager):
        self._hass = hass
        self._manager = manager
        self._attr_name = f"{entity_name} Battery Range"
        self._attr_unique_id = f"{config_entry_id}_vehicle_{index}_battery_range"
        self._attr_device_info = device_info
        self._attr_icon = "mdi:map-marker-distance"

    @property
    def native_value(self) -> float:
        return self._manager.get_state(STATE_KEY_BATTERY_RANGE, 0.0)

    async def async_update(self):
        await self._manager.async_simulate()


class VirtualVehicleBatteryVoltageSensor(SensorEntity):
    _attr_should_poll = True
    _attr_device_class = SensorDeviceClass.VOLTAGE
    _attr_native_unit_of_measurement = UnitOfElectricPotential.VOLT
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, hass, config_entry_id, entity_name, index, device_info, manager):
        self._hass = hass
        self._manager = manager
        self._attr_name = f"{entity_name} Battery Voltage"
        self._attr_unique_id = f"{config_entry_id}_vehicle_{index}_battery_voltage"
        self._attr_device_info = device_info
        self._attr_icon = "mdi:lightning-bolt-outline"

    @property
    def native_value(self) -> float:
        return self._manager.get_state(STATE_KEY_BATTERY_VOLTAGE, 0.0)

    async def async_update(self):
        await self._manager.async_simulate()


class VirtualVehicleBatteryCurrentSensor(SensorEntity):
    _attr_should_poll = True
    _attr_device_class = SensorDeviceClass.CURRENT
    _attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, hass, config_entry_id, entity_name, index, device_info, manager):
        self._hass = hass
        self._manager = manager
        self._attr_name = f"{entity_name} Battery Current"
        self._attr_unique_id = f"{config_entry_id}_vehicle_{index}_battery_current"
        self._attr_device_info = device_info
        self._attr_icon = "mdi:current-dc"

    @property
    def native_value(self) -> float:
        return self._manager.get_state(STATE_KEY_BATTERY_CURRENT, 0.0)

    async def async_update(self):
        await self._manager.async_simulate()


class VirtualVehicleMotorPowerSensor(SensorEntity):
    _attr_should_poll = True
    _attr_device_class = SensorDeviceClass.POWER
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, hass, config_entry_id, entity_name, index, device_info, manager):
        self._hass = hass
        self._manager = manager
        self._attr_name = f"{entity_name} Motor Power"
        self._attr_unique_id = f"{config_entry_id}_vehicle_{index}_motor_power"
        self._attr_device_info = device_info
        self._attr_icon = "mdi:engine"

    @property
    def native_value(self) -> float:
        return self._manager.get_state(STATE_KEY_MOTOR_POWER, 0.0)

    async def async_update(self):
        await self._manager.async_simulate()


class VirtualVehicleChargeRateSensor(SensorEntity):
    _attr_should_poll = True
    _attr_device_class = SensorDeviceClass.SPEED
    _attr_native_unit_of_measurement = UnitOfSpeed.KILOMETERS_PER_HOUR
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, hass, config_entry_id, entity_name, index, device_info, manager):
        self._hass = hass
        self._manager = manager
        self._attr_name = f"{entity_name} Charge Rate"
        self._attr_unique_id = f"{config_entry_id}_vehicle_{index}_charge_rate"
        self._attr_device_info = device_info
        self._attr_icon = "mdi:lightning-bolt"

    @property
    def native_value(self) -> float:
        return self._manager.get_state(STATE_KEY_CHARGE_RATE, 0.0)

    async def async_update(self):
        await self._manager.async_simulate()


class VirtualVehicleChargerPowerSensor(SensorEntity):
    _attr_should_poll = True
    _attr_device_class = SensorDeviceClass.POWER
    _attr_native_unit_of_measurement = UnitOfPower.KILO_WATT
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, hass, config_entry_id, entity_name, index, device_info, manager):
        self._hass = hass
        self._manager = manager
        self._attr_name = f"{entity_name} Charger Power"
        self._attr_unique_id = f"{config_entry_id}_vehicle_{index}_charger_power"
        self._attr_device_info = device_info
        self._attr_icon = "mdi:flash"

    @property
    def native_value(self) -> float:
        return self._manager.get_state(STATE_KEY_CHARGER_POWER, 0.0)

    async def async_update(self):
        await self._manager.async_simulate()


class VirtualVehicleChargerVoltageSensor(SensorEntity):
    _attr_should_poll = True
    _attr_device_class = SensorDeviceClass.VOLTAGE
    _attr_native_unit_of_measurement = UnitOfElectricPotential.VOLT
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, hass, config_entry_id, entity_name, index, device_info, manager):
        self._hass = hass
        self._manager = manager
        self._attr_name = f"{entity_name} Charger Voltage"
        self._attr_unique_id = f"{config_entry_id}_vehicle_{index}_charger_voltage"
        self._attr_device_info = device_info
        self._attr_icon = "mdi:lightning-bolt-outline"

    @property
    def native_value(self) -> float:
        return self._manager.get_state(STATE_KEY_CHARGER_VOLTAGE, 0.0)

    async def async_update(self):
        await self._manager.async_simulate()


class VirtualVehicleChargerCurrentSensor(SensorEntity):
    _attr_should_poll = True
    _attr_device_class = SensorDeviceClass.CURRENT
    _attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, hass, config_entry_id, entity_name, index, device_info, manager):
        self._hass = hass
        self._manager = manager
        self._attr_name = f"{entity_name} Charger Current"
        self._attr_unique_id = f"{config_entry_id}_vehicle_{index}_charger_current"
        self._attr_device_info = device_info
        self._attr_icon = "mdi:current-ac"

    @property
    def native_value(self) -> float:
        return self._manager.get_state(STATE_KEY_CHARGER_CURRENT, 0.0)

    async def async_update(self):
        await self._manager.async_simulate()


class VirtualVehicleChargeEnergyAddedSensor(SensorEntity):
    _attr_should_poll = True
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(self, hass, config_entry_id, entity_name, index, device_info, manager):
        self._hass = hass
        self._manager = manager
        self._attr_name = f"{entity_name} Charge Energy Added"
        self._attr_unique_id = f"{config_entry_id}_vehicle_{index}_charge_energy_added"
        self._attr_device_info = device_info
        self._attr_icon = "mdi:lightning-bolt"

    @property
    def native_value(self) -> float:
        return self._manager.get_state(STATE_KEY_CHARGE_ENERGY_ADDED, 0.0)

    async def async_update(self):
        await self._manager.async_simulate()


class VirtualVehicleTimeToFullChargeSensor(SensorEntity):
    _attr_should_poll = True
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, hass, config_entry_id, entity_name, index, device_info, manager):
        self._hass = hass
        self._manager = manager
        self._attr_name = f"{entity_name} Time to Full Charge"
        self._attr_unique_id = f"{config_entry_id}_vehicle_{index}_time_to_full_charge"
        self._attr_device_info = device_info
        self._attr_icon = "mdi:timer"

    @property
    def native_value(self) -> float:
        return self._manager.get_state(STATE_KEY_TIME_TO_FULL_CHARGE, 0)

    async def async_update(self):
        await self._manager.async_simulate()


class VirtualVehicleTirePressureSensor(SensorEntity):
    _attr_should_poll = True
    _attr_device_class = SensorDeviceClass.PRESSURE
    _attr_native_unit_of_measurement = UnitOfPressure.BAR
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, hass, config_entry_id, entity_name, index, device_info, manager, wheel):
        self._hass = hass
        self._manager = manager
        self._wheel = wheel
        self._attr_name = f"{entity_name} Tire Pressure {wheel}"
        self._attr_unique_id = f"{config_entry_id}_vehicle_{index}_tire_pressure_{wheel.lower()}"
        self._attr_device_info = device_info
        self._attr_icon = "mdi:car-tire-alert"

    @property
    def native_value(self) -> float:
        return self._manager.get_state(f"tire_pressure_{self._wheel.lower()}", 2.5)

    async def async_update(self):
        await self._manager.async_simulate()


class VirtualVehicleOilLevelSensor(SensorEntity):
    _attr_should_poll = True
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, hass, config_entry_id, entity_name, index, device_info, manager):
        self._hass = hass
        self._manager = manager
        self._attr_name = f"{entity_name} Oil Level"
        self._attr_unique_id = f"{config_entry_id}_vehicle_{index}_oil_level"
        self._attr_device_info = device_info
        self._attr_icon = "mdi:oil"

    @property
    def native_value(self) -> float:
        return self._manager.get_state(STATE_KEY_OIL_LEVEL, 0.0)

    async def async_update(self):
        await self._manager.async_simulate()


class VirtualVehicleCoolantTempSensor(SensorEntity):
    _attr_should_poll = True
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, hass, config_entry_id, entity_name, index, device_info, manager):
        self._hass = hass
        self._manager = manager
        self._attr_name = f"{entity_name} Coolant Temperature"
        self._attr_unique_id = f"{config_entry_id}_vehicle_{index}_coolant_temp"
        self._attr_device_info = device_info
        self._attr_icon = "mdi:coolant-temperature"

    @property
    def native_value(self) -> float:
        return self._manager.get_state(STATE_KEY_COOLANT_TEMP, 0.0)

    async def async_update(self):
        await self._manager.async_simulate()


class VirtualVehicleBatteryTempSensor(SensorEntity):
    _attr_should_poll = True
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, hass, config_entry_id, entity_name, index, device_info, manager):
        self._hass = hass
        self._manager = manager
        self._attr_name = f"{entity_name} Battery Temperature"
        self._attr_unique_id = f"{config_entry_id}_vehicle_{index}_battery_temp"
        self._attr_device_info = device_info
        self._attr_icon = "mdi:battery-thermometer"

    @property
    def native_value(self) -> float:
        return self._manager.get_state(STATE_KEY_BATTERY_TEMP, 25.0)

    async def async_update(self):
        await self._manager.async_simulate()


class VirtualVehicleAssistLevelSensor(SensorEntity):
    _attr_should_poll = True
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, hass, config_entry_id, entity_name, index, device_info, manager):
        self._hass = hass
        self._manager = manager
        self._attr_name = f"{entity_name} Assist Level"
        self._attr_unique_id = f"{config_entry_id}_vehicle_{index}_assist_level"
        self._attr_device_info = device_info
        self._attr_icon = "mdi:stairs"

    @property
    def native_value(self) -> float:
        return self._manager.get_state(STATE_KEY_ASSIST_LEVEL, 1)

    async def async_update(self):
        await self._manager.async_simulate()


class VirtualVehicleTimesChargedSensor(SensorEntity):
    _attr_native_unit_of_measurement = "cycles"
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_should_poll = True
    def __init__(self, hass, config_entry_id, entity_name, idx, device_info, manager):
        self._manager = manager
        self._attr_name = f"{entity_name} Times Charged"
        self._attr_unique_id = f"{config_entry_id}_vehicle_{idx}_times_charged"
        self._attr_device_info = device_info
    @property
    def native_value(self):
        return self._manager.get_state(STATE_KEY_TIMES_CHARGED, 0)
    async def async_update(self):
        pass


class VirtualVehicleBatteryGradeSensor(SensorEntity):
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_should_poll = True
    def __init__(self, hass, config_entry_id, entity_name, idx, device_info, manager, suffix=""):
        self._manager = manager
        self._suffix = suffix
        self._attr_name = f"{entity_name} Battery Grade{suffix}"
        self._attr_unique_id = f"{config_entry_id}_vehicle_{idx}_battery_grade{suffix.lower().replace(' ', '_')}"
        self._attr_device_info = device_info
    @property
    def native_value(self):
        key = STATE_KEY_BATTERY_GRADE_B if self._suffix == " B" else STATE_KEY_BATTERY_GRADE
        return self._manager.get_state(key, 100)
    async def async_update(self):
        pass


class VirtualVehicleTimeLeftSensor(SensorEntity):
    _attr_native_unit_of_measurement = "h"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:av-timer"
    _attr_should_poll = True
    def __init__(self, hass, config_entry_id, entity_name, idx, device_info, manager):
        self._manager = manager
        self._attr_name = f"{entity_name} Time Left"
        self._attr_unique_id = f"{config_entry_id}_vehicle_{idx}_time_left"
        self._attr_device_info = device_info
    @property
    def native_value(self):
        return self._manager.get_state(STATE_KEY_TIME_LEFT, 0)
    async def async_update(self):
        pass


class VirtualVehicleCentreCtrlBattSensor(SensorEntity):
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:car-cruise-control"
    _attr_should_poll = True
    def __init__(self, hass, config_entry_id, entity_name, idx, device_info, manager):
        self._manager = manager
        self._attr_name = f"{entity_name} Centre Ctrl Battery"
        self._attr_unique_id = f"{config_entry_id}_vehicle_{idx}_centre_ctrl_batt"
        self._attr_device_info = device_info
    @property
    def native_value(self):
        return self._manager.get_state(STATE_KEY_CENTRE_CTRL_BATT, 100)
    async def async_update(self):
        pass


class VirtualVehicleHDopSensor(SensorEntity):
    _attr_icon = "mdi:map-marker"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_should_poll = True
    def __init__(self, hass, config_entry_id, entity_name, idx, device_info, manager):
        self._manager = manager
        self._attr_name = f"{entity_name} GPS HDOP"
        self._attr_unique_id = f"{config_entry_id}_vehicle_{idx}_hdop"
        self._attr_device_info = device_info
    @property
    def native_value(self):
        return self._manager.get_state(STATE_KEY_HDOP, 0)
    @property
    def native_unit_of_measurement(self):
        return None
    async def async_update(self):
        pass


class VirtualVehicleRidingTimeSensor(SensorEntity):
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_native_unit_of_measurement = UnitOfTime.SECONDS
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:map-clock"
    _attr_should_poll = True
    def __init__(self, hass, config_entry_id, entity_name, idx, device_info, manager):
        self._manager = manager
        self._attr_name = f"{entity_name} Riding Time"
        self._attr_unique_id = f"{config_entry_id}_vehicle_{idx}_riding_time"
        self._attr_device_info = device_info
    @property
    def native_value(self):
        return self._manager.get_state(STATE_KEY_RIDING_TIME, 0)
    async def async_update(self):
        pass


class VirtualVehicleDaysInUseSensor(SensorEntity):
    _attr_native_unit_of_measurement = "days"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:calendar-today"
    _attr_should_poll = True
    def __init__(self, hass, config_entry_id, entity_name, idx, device_info, manager):
        self._manager = manager
        self._attr_name = f"{entity_name} Days In Use"
        self._attr_unique_id = f"{config_entry_id}_vehicle_{idx}_days_in_use"
        self._attr_device_info = device_info
    @property
    def native_value(self):
        return self._manager.get_state(STATE_KEY_DAYS_IN_USE, 0)
    async def async_update(self):
        pass


class VirtualVehicleBatteryTempDescSensor(SensorEntity):
    _attr_icon = "mdi:thermometer-alert"
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_should_poll = True
    def __init__(self, hass, config_entry_id, entity_name, idx, device_info, manager):
        self._manager = manager
        self._attr_name = f"{entity_name} Battery Temp Status"
        self._attr_unique_id = f"{config_entry_id}_vehicle_{idx}_battery_temp_desc"
        self._attr_device_info = device_info
    @property
    def native_value(self):
        return self._manager.get_state(STATE_KEY_BATTERY_TEMP_DESC, "Normal")
    async def async_update(self):
        pass


class VirtualVehicleBatteryLevelBSensor(SensorEntity):
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:battery-charging-50"
    _attr_should_poll = True
    def __init__(self, hass, config_entry_id, entity_name, idx, device_info, manager):
        self._manager = manager
        self._attr_name = f"{entity_name} Battery B"
        self._attr_unique_id = f"{config_entry_id}_vehicle_{idx}_battery_b"
        self._attr_device_info = device_info
    @property
    def native_value(self):
        return self._manager.get_state(STATE_KEY_BATTERY_LEVEL_B, 100)
    async def async_update(self):
        pass


class VirtualVehicleEstimatedRangeSensor(SensorEntity):
    _attr_should_poll = True
    _attr_device_class = SensorDeviceClass.DISTANCE
    _attr_native_unit_of_measurement = UnitOfLength.KILOMETERS
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, hass, config_entry_id, entity_name, index, device_info, manager):
        self._hass = hass
        self._manager = manager
        self._attr_name = f"{entity_name} Estimated Range"
        self._attr_unique_id = f"{config_entry_id}_vehicle_{index}_estimated_range"
        self._attr_device_info = device_info
        self._attr_icon = "mdi:map-marker-distance"

    @property
    def native_value(self) -> float:
        return self._manager.get_state(STATE_KEY_ESTIMATED_RANGE, 0.0)

    async def async_update(self):
        await self._manager.async_simulate()

class VirtualVehicleFlashLightsButton(ButtonEntity):
    def __init__(self, hass, config_entry_id, entity_name, index, device_info, manager):
        self._hass = hass
        self._manager = manager
        self._attr_name = f"{entity_name} Flash Lights"
        self._attr_unique_id = f"{config_entry_id}_vehicle_{index}_flash_lights"
        self._attr_device_info = device_info
        self._attr_icon = "mdi:car-light-high"

    async def async_press(self):
        _LOGGER.info("Vehicle '%s' flash lights", self._attr_name)
        self._hass.bus.async_fire(
            f"{DOMAIN}_vehicle_flash_lights",
            {"entity_id": self.entity_id, "device_id": self._manager._config_entry_id},
        )


class VirtualVehicleHonkHornButton(ButtonEntity):
    def __init__(self, hass, config_entry_id, entity_name, index, device_info, manager):
        self._hass = hass
        self._manager = manager
        self._attr_name = f"{entity_name} Honk Horn"
        self._attr_unique_id = f"{config_entry_id}_vehicle_{index}_honk_horn"
        self._attr_device_info = device_info
        self._attr_icon = "mdi:bullhorn"

    async def async_press(self):
        _LOGGER.info("Vehicle '%s' honk horn", self._attr_name)
        self._hass.bus.async_fire(
            f"{DOMAIN}_vehicle_honk_horn",
            {"entity_id": self.entity_id, "device_id": self._manager._config_entry_id},
        )


class VirtualVehicleWakeButton(ButtonEntity):
    def __init__(self, hass, config_entry_id, entity_name, index, device_info, manager):
        self._hass = hass
        self._manager = manager
        self._attr_name = f"{entity_name} Wake"
        self._attr_unique_id = f"{config_entry_id}_vehicle_{index}_wake"
        self._attr_device_info = device_info
        self._attr_icon = "mdi:power"

    async def async_press(self):
        _LOGGER.info("Vehicle '%s' wake", self._attr_name)
        self._manager.set_state(STATE_KEY_IS_ON, True)
        await self._manager.async_save()
        self._hass.bus.async_fire(
            f"{DOMAIN}_vehicle_wake",
            {"entity_id": self.entity_id, "device_id": self._manager._config_entry_id},
        )


class VirtualVehicleKeylessDrivingButton(ButtonEntity):
    def __init__(self, hass, config_entry_id, entity_name, index, device_info, manager):
        self._hass = hass
        self._manager = manager
        self._attr_name = f"{entity_name} Keyless Driving"
        self._attr_unique_id = f"{config_entry_id}_vehicle_{index}_keyless_driving"
        self._attr_device_info = device_info
        self._attr_icon = "mdi:car-key"

    async def async_press(self):
        _LOGGER.info("Vehicle '%s' keyless driving started", self._attr_name)
        self._manager.set_state(STATE_KEY_IS_ON, True)
        self._manager.set_state(STATE_KEY_USER_PRESENT, False)
        await self._manager.async_save()
        self._hass.bus.async_fire(
            f"{DOMAIN}_vehicle_keyless_driving",
            {"entity_id": self.entity_id, "device_id": self._manager._config_entry_id},
        )


class VirtualVehicleSentryModeSwitch(SwitchEntity):
    _attr_should_poll = True

    def __init__(self, hass, config_entry_id, entity_name, index, device_info, manager):
        self._hass = hass
        self._manager = manager
        self._attr_name = f"{entity_name} Sentry Mode"
        self._attr_unique_id = f"{config_entry_id}_vehicle_{index}_sentry_mode"
        self._attr_device_info = device_info
        self._attr_icon = "mdi:shield-car"

    @property
    def is_on(self) -> bool:
        return self._manager.get_state(STATE_KEY_SENTRY_MODE, False)

    async def async_turn_on(self, **kwargs):
        self._manager.set_state(STATE_KEY_SENTRY_MODE, True)
        await self._manager.async_save()
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        self._manager.set_state(STATE_KEY_SENTRY_MODE, False)
        await self._manager.async_save()
        self.async_write_ha_state()

    async def async_update(self):
        await self._manager.async_simulate()


class VirtualVehicleChargeSwitch(SwitchEntity):
    _attr_should_poll = True

    def __init__(self, hass, config_entry_id, entity_name, index, device_info, manager):
        self._hass = hass
        self._manager = manager
        self._attr_name = f"{entity_name} Charge"
        self._attr_unique_id = f"{config_entry_id}_vehicle_{index}_charge"
        self._attr_device_info = device_info
        self._attr_icon = "mdi:lightning-bolt"

    @property
    def is_on(self) -> bool:
        return self._manager.get_state(STATE_KEY_CHARGING, False)

    async def async_turn_on(self, **kwargs):
        self._manager.set_state(STATE_KEY_CHARGING, True)
        self._manager.set_state(STATE_KEY_CHARGE_CABLE_CONNECTED, True)
        await self._manager.async_save()
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        self._manager.set_state(STATE_KEY_CHARGING, False)
        await self._manager.async_save()
        self.async_write_ha_state()

    async def async_update(self):
        await self._manager.async_simulate()


class VirtualVehicleDefrostSwitch(SwitchEntity):
    _attr_should_poll = True

    def __init__(self, hass, config_entry_id, entity_name, index, device_info, manager):
        self._hass = hass
        self._manager = manager
        self._attr_name = f"{entity_name} Defrost"
        self._attr_unique_id = f"{config_entry_id}_vehicle_{index}_defrost"
        self._attr_device_info = device_info
        self._attr_icon = "mdi:car-defrost-front"

    @property
    def is_on(self) -> bool:
        return self._manager.get_state(STATE_KEY_DEFROST, False)

    async def async_turn_on(self, **kwargs):
        self._manager.set_state(STATE_KEY_DEFROST, True)
        await self._manager.async_save()
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        self._manager.set_state(STATE_KEY_DEFROST, False)
        await self._manager.async_save()
        self.async_write_ha_state()

    async def async_update(self):
        await self._manager.async_simulate()


class VirtualVehicleAutoSeatClimateLeftSwitch(SwitchEntity):
    _attr_should_poll = True

    def __init__(self, hass, config_entry_id, entity_name, index, device_info, manager):
        self._hass = hass
        self._manager = manager
        self._attr_name = f"{entity_name} Auto Seat Climate Left"
        self._attr_unique_id = f"{config_entry_id}_vehicle_{index}_auto_seat_climate_left"
        self._attr_device_info = device_info
        self._attr_icon = "mdi:seat"

    @property
    def is_on(self) -> bool:
        return self._manager.get_state(STATE_KEY_AUTO_SEAT_CLIMATE_LEFT, False)

    async def async_turn_on(self, **kwargs):
        self._manager.set_state(STATE_KEY_AUTO_SEAT_CLIMATE_LEFT, True)
        await self._manager.async_save()
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        self._manager.set_state(STATE_KEY_AUTO_SEAT_CLIMATE_LEFT, False)
        await self._manager.async_save()
        self.async_write_ha_state()

    async def async_update(self):
        await self._manager.async_simulate()


class VirtualVehicleAutoSeatClimateRightSwitch(SwitchEntity):
    _attr_should_poll = True

    def __init__(self, hass, config_entry_id, entity_name, index, device_info, manager):
        self._hass = hass
        self._manager = manager
        self._attr_name = f"{entity_name} Auto Seat Climate Right"
        self._attr_unique_id = f"{config_entry_id}_vehicle_{index}_auto_seat_climate_right"
        self._attr_device_info = device_info
        self._attr_icon = "mdi:seat"

    @property
    def is_on(self) -> bool:
        return self._manager.get_state(STATE_KEY_AUTO_SEAT_CLIMATE_RIGHT, False)

    async def async_turn_on(self, **kwargs):
        self._manager.set_state(STATE_KEY_AUTO_SEAT_CLIMATE_RIGHT, True)
        await self._manager.async_save()
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        self._manager.set_state(STATE_KEY_AUTO_SEAT_CLIMATE_RIGHT, False)
        await self._manager.async_save()
        self.async_write_ha_state()

    async def async_update(self):
        await self._manager.async_simulate()


class VirtualVehicleAutoSteeringWheelHeaterSwitch(SwitchEntity):
    _attr_should_poll = True

    def __init__(self, hass, config_entry_id, entity_name, index, device_info, manager):
        self._hass = hass
        self._manager = manager
        self._attr_name = f"{entity_name} Auto Steering Wheel Heater"
        self._attr_unique_id = f"{config_entry_id}_vehicle_{index}_auto_steering_wheel_heater"
        self._attr_device_info = device_info
        self._attr_icon = "mdi:steering"

    @property
    def is_on(self) -> bool:
        return self._manager.get_state(STATE_KEY_AUTO_STEERING_WHEEL_HEATER, False)

    async def async_turn_on(self, **kwargs):
        self._manager.set_state(STATE_KEY_AUTO_STEERING_WHEEL_HEATER, True)
        await self._manager.async_save()
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        self._manager.set_state(STATE_KEY_AUTO_STEERING_WHEEL_HEATER, False)
        await self._manager.async_save()
        self.async_write_ha_state()

    async def async_update(self):
        await self._manager.async_simulate()


class VirtualVehicleLightSwitch(SwitchEntity):
    _attr_should_poll = True

    def __init__(self, hass, config_entry_id, entity_name, index, device_info, manager):
        self._hass = hass
        self._manager = manager
        self._attr_name = f"{entity_name} Light"
        self._attr_unique_id = f"{config_entry_id}_vehicle_{index}_light"
        self._attr_device_info = device_info
        self._attr_icon = "mdi:lightbulb"

    @property
    def is_on(self) -> bool:
        return self._manager.get_state(STATE_KEY_LIGHT_ON, False)

    async def async_turn_on(self, **kwargs):
        self._manager.set_state(STATE_KEY_LIGHT_ON, True)
        await self._manager.async_save()
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        self._manager.set_state(STATE_KEY_LIGHT_ON, False)
        await self._manager.async_save()
        self.async_write_ha_state()

    async def async_update(self):
        await self._manager.async_simulate()


class VirtualVehicleHornSwitch(SwitchEntity):
    _attr_should_poll = True

    def __init__(self, hass, config_entry_id, entity_name, index, device_info, manager):
        self._hass = hass
        self._manager = manager
        self._attr_name = f"{entity_name} Horn"
        self._attr_unique_id = f"{config_entry_id}_vehicle_{index}_horn"
        self._attr_device_info = device_info
        self._attr_icon = "mdi:bullhorn"

    @property
    def is_on(self) -> bool:
        return self._manager.get_state(STATE_KEY_HORN_ON, False)

    async def async_turn_on(self, **kwargs):
        self._manager.set_state(STATE_KEY_HORN_ON, True)
        await self._manager.async_save()
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        self._manager.set_state(STATE_KEY_HORN_ON, False)
        await self._manager.async_save()
        self.async_write_ha_state()

    async def async_update(self):
        await self._manager.async_simulate()


class VirtualVehicleChargeLimitNumber(NumberEntity):
    _attr_should_poll = True
    _attr_native_min_value = 50.0
    _attr_native_max_value = 100.0
    _attr_native_step = 1.0
    _attr_native_unit_of_measurement = PERCENTAGE

    def __init__(self, hass, config_entry_id, entity_name, index, device_info, manager):
        self._hass = hass
        self._manager = manager
        self._attr_name = f"{entity_name} Charge Limit"
        self._attr_unique_id = f"{config_entry_id}_vehicle_{index}_charge_limit"
        self._attr_device_info = device_info
        self._attr_icon = "mdi:battery-charging-50"

    @property
    def native_value(self) -> float:
        return float(self._manager.get_state(STATE_KEY_CHARGE_LIMIT, 90))

    async def async_set_native_value(self, value):
        self._manager.set_state(STATE_KEY_CHARGE_LIMIT, int(value))
        await self._manager.async_save()
        self.async_write_ha_state()

    async def async_update(self):
        await self._manager.async_simulate()


class VirtualVehicleChargeCurrentNumber(NumberEntity):
    _attr_should_poll = True
    _attr_native_min_value = 5.0
    _attr_native_max_value = 32.0
    _attr_native_step = 1.0
    _attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE

    def __init__(self, hass, config_entry_id, entity_name, index, device_info, manager):
        self._hass = hass
        self._manager = manager
        self._attr_name = f"{entity_name} Charge Current"
        self._attr_unique_id = f"{config_entry_id}_vehicle_{index}_charge_current"
        self._attr_device_info = device_info
        self._attr_icon = "mdi:current-ac"

    @property
    def native_value(self) -> float:
        return float(self._manager.get_state(STATE_KEY_CHARGE_CURRENT, 16))

    async def async_set_native_value(self, value):
        self._manager.set_state(STATE_KEY_CHARGE_CURRENT, int(value))
        await self._manager.async_save()
        self.async_write_ha_state()

    async def async_update(self):
        await self._manager.async_simulate()


class VirtualVehicleTargetTempNumber(NumberEntity):
    _attr_should_poll = True
    _attr_native_min_value = 16.0
    _attr_native_max_value = 30.0
    _attr_native_step = 0.5
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

    def __init__(self, hass, config_entry_id, entity_name, index, device_info, manager):
        self._hass = hass
        self._manager = manager
        self._attr_name = f"{entity_name} Target Temperature"
        self._attr_unique_id = f"{config_entry_id}_vehicle_{index}_target_temp"
        self._attr_device_info = device_info
        self._attr_icon = "mdi:thermometer"

    @property
    def native_value(self) -> float:
        return float(self._manager.get_state(STATE_KEY_TARGET_TEMP, 22.0))

    async def async_set_native_value(self, value):
        self._manager.set_state(STATE_KEY_TARGET_TEMP, value)
        await self._manager.async_save()
        self.async_write_ha_state()

    async def async_update(self):
        await self._manager.async_simulate()


class VirtualVehicleSpeedLimitNumber(NumberEntity):
    _attr_should_poll = True
    _attr_native_min_value = 15.0
    _attr_native_max_value = 45.0
    _attr_native_step = 1.0
    _attr_native_unit_of_measurement = UnitOfSpeed.KILOMETERS_PER_HOUR

    def __init__(self, hass, config_entry_id, entity_name, index, device_info, manager):
        self._hass = hass
        self._manager = manager
        self._attr_name = f"{entity_name} Speed Limit"
        self._attr_unique_id = f"{config_entry_id}_vehicle_{index}_speed_limit"
        self._attr_device_info = device_info
        self._attr_icon = "mdi:speedometer-slow"

    @property
    def native_value(self) -> float:
        return float(self._manager.get_state(STATE_KEY_SPEED_LIMIT, 25))

    async def async_set_native_value(self, value):
        self._manager.set_state(STATE_KEY_SPEED_LIMIT, int(value))
        await self._manager.async_save()
        self.async_write_ha_state()

    async def async_update(self):
        await self._manager.async_simulate()


class VirtualVehicleAssistLevelNumber(NumberEntity):
    _attr_should_poll = True
    _attr_native_min_value = 1.0
    _attr_native_max_value = 5.0
    _attr_native_step = 1.0

    def __init__(self, hass, config_entry_id, entity_name, index, device_info, manager):
        self._hass = hass
        self._manager = manager
        self._attr_name = f"{entity_name} Assist Level"
        self._attr_unique_id = f"{config_entry_id}_vehicle_{index}_assist_level"
        self._attr_device_info = device_info
        self._attr_icon = "mdi:stairs"

    @property
    def native_value(self) -> float:
        return float(self._manager.get_state(STATE_KEY_ASSIST_LEVEL, 1))

    async def async_set_native_value(self, value):
        self._manager.set_state(STATE_KEY_ASSIST_LEVEL, int(value))
        await self._manager.async_save()
        self.async_write_ha_state()

    async def async_update(self):
        await self._manager.async_simulate()

class VirtualVehicleSeatHeaterSelect(SelectEntity):
    _attr_should_poll = True
    _attr_options = ["off", "low", "medium", "high"]

    def __init__(self, hass, config_entry_id, entity_name, index, device_info, manager, position):
        self._hass = hass
        self._manager = manager
        self._position = position
        key = position.lower().replace(" ", "_")
        self._state_key = f"seat_heater_{key}"
        self._attr_name = f"{entity_name} Seat Heater {position}"
        self._attr_unique_id = f"{config_entry_id}_vehicle_{index}_seat_heater_{key}"
        self._attr_device_info = device_info
        self._attr_icon = "mdi:car-seat-heater"

    @property
    def current_option(self) -> str:
        return self._manager.get_state(self._state_key, "off")

    async def async_select_option(self, option):
        self._manager.set_state(self._state_key, option)
        await self._manager.async_save()
        self.async_write_ha_state()

    async def async_update(self):
        await self._manager.async_simulate()


class VirtualVehicleSteeringWheelHeaterSelect(SelectEntity):
    _attr_should_poll = True
    _attr_options = ["off", "on"]

    def __init__(self, hass, config_entry_id, entity_name, index, device_info, manager):
        self._hass = hass
        self._manager = manager
        self._attr_name = f"{entity_name} Steering Wheel Heater"
        self._attr_unique_id = f"{config_entry_id}_vehicle_{index}_steering_wheel_heater"
        self._attr_device_info = device_info
        self._attr_icon = "mdi:steering"

    @property
    def current_option(self) -> str:
        return self._manager.get_state(STATE_KEY_STEERING_WHEEL_HEATER, "off")

    async def async_select_option(self, option):
        self._manager.set_state(STATE_KEY_STEERING_WHEEL_HEATER, option)
        await self._manager.async_save()
        self.async_write_ha_state()

    async def async_update(self):
        await self._manager.async_simulate()


class VirtualVehicleDriveModeSelect(SelectEntity):
    _attr_should_poll = True
    _attr_options = ["Park", "Reverse", "Neutral", "Drive"]

    def __init__(self, hass, config_entry_id, entity_name, index, device_info, manager):
        self._hass = hass
        self._manager = manager
        self._attr_name = f"{entity_name} Drive Mode"
        self._attr_unique_id = f"{config_entry_id}_vehicle_{index}_drive_mode"
        self._attr_device_info = device_info
        self._attr_icon = "mdi:car-shift-pattern"

    @property
    def current_option(self) -> str:
        return self._manager.get_state(STATE_KEY_DRIVE_MODE, "Park")

    async def async_select_option(self, option):
        self._manager.set_state(STATE_KEY_DRIVE_MODE, option)
        await self._manager.async_save()
        self.async_write_ha_state()

    async def async_update(self):
        await self._manager.async_simulate()


class VirtualVehicleChargePortCover(CoverEntity):
    _attr_should_poll = True
    _attr_device_class = CoverDeviceClass.DOOR
    _attr_supported_features = CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE

    def __init__(self, hass, config_entry_id, entity_name, index, device_info, manager):
        self._hass = hass
        self._manager = manager
        self._attr_name = f"{entity_name} Charge Port Door"
        self._attr_unique_id = f"{config_entry_id}_vehicle_{index}_charge_port"
        self._attr_device_info = device_info
        self._attr_icon = "mdi:ev-station"

    @property
    def is_closed(self) -> bool | None:
        return not self._manager.get_state(STATE_KEY_CHARGE_PORT_OPEN, False)

    async def async_open_cover(self, **kwargs):
        self._manager.set_state(STATE_KEY_CHARGE_PORT_OPEN, True)
        await self._manager.async_save()
        self.async_write_ha_state()

    async def async_close_cover(self, **kwargs):
        self._manager.set_state(STATE_KEY_CHARGE_PORT_OPEN, False)
        await self._manager.async_save()
        self.async_write_ha_state()

    async def async_update(self):
        await self._manager.async_simulate()


class VirtualVehicleFrunkCover(CoverEntity):
    _attr_should_poll = True
    _attr_device_class = CoverDeviceClass.DOOR
    _attr_supported_features = CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE

    def __init__(self, hass, config_entry_id, entity_name, index, device_info, manager):
        self._hass = hass
        self._manager = manager
        self._attr_name = f"{entity_name} Frunk"
        self._attr_unique_id = f"{config_entry_id}_vehicle_{index}_frunk"
        self._attr_device_info = device_info
        self._attr_icon = "mdi:car"

    @property
    def is_closed(self) -> bool | None:
        return not self._manager.get_state(STATE_KEY_FRUNK_OPEN, False)

    async def async_open_cover(self, **kwargs):
        self._manager.set_state(STATE_KEY_FRUNK_OPEN, True)
        await self._manager.async_save()
        self.async_write_ha_state()

    async def async_close_cover(self, **kwargs):
        self._manager.set_state(STATE_KEY_FRUNK_OPEN, False)
        await self._manager.async_save()
        self.async_write_ha_state()

    async def async_update(self):
        await self._manager.async_simulate()


class VirtualVehicleTrunkCover(CoverEntity):
    _attr_should_poll = True
    _attr_device_class = CoverDeviceClass.DOOR
    _attr_supported_features = CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE

    def __init__(self, hass, config_entry_id, entity_name, index, device_info, manager):
        self._hass = hass
        self._manager = manager
        self._attr_name = f"{entity_name} Trunk"
        self._attr_unique_id = f"{config_entry_id}_vehicle_{index}_trunk_cover"
        self._attr_device_info = device_info
        self._attr_icon = "mdi:car-back"

    @property
    def is_closed(self) -> bool | None:
        return not self._manager.get_state(STATE_KEY_TRUNK_OPEN, False)

    async def async_open_cover(self, **kwargs):
        self._manager.set_state(STATE_KEY_TRUNK_OPEN, True)
        await self._manager.async_save()
        self.async_write_ha_state()

    async def async_close_cover(self, **kwargs):
        self._manager.set_state(STATE_KEY_TRUNK_OPEN, False)
        await self._manager.async_save()
        self.async_write_ha_state()

    async def async_update(self):
        await self._manager.async_simulate()


class VirtualVehicleSunroofCover(CoverEntity):
    _attr_should_poll = True
    _attr_device_class = CoverDeviceClass.SHADE
    _attr_supported_features = CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE | CoverEntityFeature.SET_POSITION

    def __init__(self, hass, config_entry_id, entity_name, index, device_info, manager):
        self._hass = hass
        self._manager = manager
        self._attr_name = f"{entity_name} Sunroof"
        self._attr_unique_id = f"{config_entry_id}_vehicle_{index}_sunroof"
        self._attr_device_info = device_info
        self._attr_icon = "mdi:car-sunroof"

    @property
    def is_closed(self) -> bool | None:
        return self._manager.get_state(STATE_KEY_SUNROOF_POSITION, 100) <= 0

    @property
    def current_cover_position(self) -> int | None:
        return self._manager.get_state(STATE_KEY_SUNROOF_POSITION, 100)

    async def async_open_cover(self, **kwargs):
        self._manager.set_state(STATE_KEY_SUNROOF_POSITION, 100)
        await self._manager.async_save()
        self.async_write_ha_state()

    async def async_close_cover(self, **kwargs):
        self._manager.set_state(STATE_KEY_SUNROOF_POSITION, 0)
        await self._manager.async_save()
        self.async_write_ha_state()

    async def async_set_cover_position(self, **kwargs):
        position = kwargs.get("position", 100)
        self._manager.set_state(STATE_KEY_SUNROOF_POSITION, position)
        await self._manager.async_save()
        self.async_write_ha_state()

    async def async_update(self):
        await self._manager.async_simulate()


class VirtualVehicleWindowsCover(CoverEntity):
    _attr_should_poll = True
    _attr_device_class = CoverDeviceClass.WINDOW
    _attr_supported_features = CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE

    def __init__(self, hass, config_entry_id, entity_name, index, device_info, manager):
        self._hass = hass
        self._manager = manager
        self._attr_name = f"{entity_name} Windows"
        self._attr_unique_id = f"{config_entry_id}_vehicle_{index}_windows"
        self._attr_device_info = device_info
        self._attr_icon = "mdi:car-window"

    @property
    def is_closed(self) -> bool | None:
        fl = self._manager.get_state(STATE_KEY_WINDOW_FL, 100)
        fr = self._manager.get_state(STATE_KEY_WINDOW_FR, 100)
        rl = self._manager.get_state(STATE_KEY_WINDOW_RL, 100)
        rr = self._manager.get_state(STATE_KEY_WINDOW_RR, 100)
        return fl <= 0 and fr <= 0 and rl <= 0 and rr <= 0

    async def async_open_cover(self, **kwargs):
        for key in [STATE_KEY_WINDOW_FL, STATE_KEY_WINDOW_FR, STATE_KEY_WINDOW_RL, STATE_KEY_WINDOW_RR]:
            self._manager.set_state(key, 100)
        await self._manager.async_save()
        self.async_write_ha_state()

    async def async_close_cover(self, **kwargs):
        for key in [STATE_KEY_WINDOW_FL, STATE_KEY_WINDOW_FR, STATE_KEY_WINDOW_RL, STATE_KEY_WINDOW_RR]:
            self._manager.set_state(key, 0)
        await self._manager.async_save()
        self.async_write_ha_state()

    async def async_update(self):
        await self._manager.async_simulate()


class VirtualVehicleWindowCover(CoverEntity):
    _attr_should_poll = True
    _attr_device_class = CoverDeviceClass.WINDOW
    _attr_supported_features = CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE | CoverEntityFeature.SET_POSITION

    def __init__(self, hass, config_entry_id, entity_name, index, device_info, manager, window):
        self._hass = hass
        self._manager = manager
        self._window = window
        self._state_key = f"window_{window.lower()}"
        self._attr_name = f"{entity_name} Window {window}"
        self._attr_unique_id = f"{config_entry_id}_vehicle_{index}_window_{window.lower()}"
        self._attr_device_info = device_info
        self._attr_icon = "mdi:car-window"

    @property
    def is_closed(self) -> bool | None:
        return self._manager.get_state(self._state_key, 100) <= 0

    @property
    def current_cover_position(self) -> int | None:
        return self._manager.get_state(self._state_key, 100)

    async def async_open_cover(self, **kwargs):
        self._manager.set_state(self._state_key, 100)
        await self._manager.async_save()
        self.async_write_ha_state()

    async def async_close_cover(self, **kwargs):
        self._manager.set_state(self._state_key, 0)
        await self._manager.async_save()
        self.async_write_ha_state()

    async def async_set_cover_position(self, **kwargs):
        position = kwargs.get("position", 100)
        self._manager.set_state(self._state_key, position)
        await self._manager.async_save()
        self.async_write_ha_state()

    async def async_update(self):
        await self._manager.async_simulate()


class VirtualVehicleClimate(ClimateEntity):
    _attr_should_poll = True
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT, HVACMode.COOL, HVACMode.AUTO, HVACMode.DRY, HVACMode.FAN_ONLY]
    _attr_fan_modes = ["auto", "low", "medium", "high"]
    _attr_swing_modes = ["off", "vertical", "horizontal", "all"]
    _attr_target_temperature_step = 0.5
    _attr_max_temp = 30.0
    _attr_min_temp = 16.0
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.FAN_MODE
        | ClimateEntityFeature.SWING_MODE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
    )

    def __init__(self, hass, config_entry_id, entity_name, index, device_info, manager):
        self._hass = hass
        self._manager = manager
        self._attr_name = f"{entity_name} Climate"
        self._attr_unique_id = f"{config_entry_id}_vehicle_{index}_climate"
        self._attr_device_info = device_info
        self._attr_icon = "mdi:air-conditioner"

    @property
    def hvac_mode(self) -> HVACMode:
        if not self._manager.get_state(STATE_KEY_CLIMATE_ON, False):
            return HVACMode.OFF
        current = self._manager.get_state(STATE_KEY_INSIDE_TEMP, 22.0)
        target = self._manager.get_state(STATE_KEY_TARGET_TEMP, 22.0)
        if target > current + 1:
            return HVACMode.HEAT
        if target < current - 1:
            return HVACMode.COOL
        return HVACMode.AUTO

    @property
    def hvac_action(self) -> HVACAction:
        if not self._manager.get_state(STATE_KEY_CLIMATE_ON, False):
            return HVACAction.OFF
        current = self._manager.get_state(STATE_KEY_INSIDE_TEMP, 22.0)
        target = self._manager.get_state(STATE_KEY_TARGET_TEMP, 22.0)
        if abs(current - target) < 0.5:
            return HVACAction.IDLE
        if target > current:
            return HVACAction.HEATING
        return HVACAction.COOLING

    @property
    def current_temperature(self) -> float | None:
        return self._manager.get_state(STATE_KEY_INSIDE_TEMP, 22.0)

    @property
    def target_temperature(self) -> float | None:
        return self._manager.get_state(STATE_KEY_TARGET_TEMP, 22.0)

    @property
    def fan_mode(self) -> str:
        return "auto"

    @property
    def swing_mode(self) -> str:
        return "off"

    async def async_set_hvac_mode(self, hvac_mode):
        self._manager.set_state(STATE_KEY_CLIMATE_ON, hvac_mode != HVACMode.OFF)
        await self._manager.async_save()
        self.async_write_ha_state()

    async def async_set_temperature(self, **kwargs):
        temp = kwargs.get("temperature", 22.0)
        self._manager.set_state(STATE_KEY_TARGET_TEMP, temp)
        self._manager.set_state(STATE_KEY_CLIMATE_ON, True)
        await self._manager.async_save()
        self.async_write_ha_state()

    async def async_set_fan_mode(self, fan_mode):
        self.async_write_ha_state()

    async def async_set_swing_mode(self, swing_mode):
        self.async_write_ha_state()

    async def async_turn_on(self):
        self._manager.set_state(STATE_KEY_CLIMATE_ON, True)
        await self._manager.async_save()
        self.async_write_ha_state()

    async def async_turn_off(self):
        self._manager.set_state(STATE_KEY_CLIMATE_ON, False)
        await self._manager.async_save()
        self.async_write_ha_state()

    async def async_update(self):
        await self._manager.async_simulate()


class VirtualVehicleCabinOverheatProtectionSwitch(SwitchEntity):
    _attr_should_poll = True

    def __init__(self, hass, config_entry_id, entity_name, index, device_info, manager):
        self._hass = hass
        self._manager = manager
        self._attr_name = f"{entity_name} Cabin Overheat Protection"
        self._attr_unique_id = f"{config_entry_id}_vehicle_{index}_cabin_overheat"
        self._attr_device_info = device_info
        self._attr_icon = "mdi:sun-thermometer"

    @property
    def is_on(self) -> bool:
        return self._manager.get_state(STATE_KEY_CABIN_OVERHEAT_PROTECTION, False)

    async def async_turn_on(self, **kwargs):
        self._manager.set_state(STATE_KEY_CABIN_OVERHEAT_PROTECTION, True)
        await self._manager.async_save()
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        self._manager.set_state(STATE_KEY_CABIN_OVERHEAT_PROTECTION, False)
        await self._manager.async_save()
        self.async_write_ha_state()

    async def async_update(self):
        await self._manager.async_simulate()


class VirtualVehicleUpdate(UpdateEntity):
    _attr_should_poll = True

    def __init__(self, hass, config_entry_id, entity_name, index, device_info, manager):
        self._hass = hass
        self._manager = manager
        self._attr_name = f"{entity_name} Update"
        self._attr_unique_id = f"{config_entry_id}_vehicle_{index}_update"
        self._attr_device_info = device_info
        self._attr_icon = "mdi:car-connected"

    @property
    def installed_version(self) -> str | None:
        return self._manager.get_state(STATE_KEY_SOFTWARE_UPDATE_VERSION, "2025.32.1")

    @property
    def latest_version(self) -> str | None:
        if self._manager.get_state(STATE_KEY_SOFTWARE_UPDATE_AVAILABLE, False):
            return "2025.36.2"
        return self._manager.get_state(STATE_KEY_SOFTWARE_UPDATE_VERSION, "2025.32.1")

    @property
    def in_progress(self) -> bool:
        return self._manager.get_state(STATE_KEY_SOFTWARE_UPDATE_INSTALLING, False)

    @property
    def update_percentage(self) -> int | None:
        if self._manager.get_state(STATE_KEY_SOFTWARE_UPDATE_INSTALLING, False):
            return self._manager.get_state(STATE_KEY_SOFTWARE_UPDATE_PROGRESS, 0)
        return None

    async def async_install(self, version=None, backup=False):
        self._manager.set_state(STATE_KEY_SOFTWARE_UPDATE_INSTALLING, True)
        self._manager.set_state(STATE_KEY_SOFTWARE_UPDATE_PROGRESS, 0)
        await self._manager.async_save()
        self.async_write_ha_state()

    async def async_update(self):
        await self._manager.async_simulate()
        if self._manager.get_state(STATE_KEY_SOFTWARE_UPDATE_INSTALLING, False):
            progress = self._manager.get_state(STATE_KEY_SOFTWARE_UPDATE_PROGRESS, 0)
            if progress < 100:
                self._manager.set_state(STATE_KEY_SOFTWARE_UPDATE_PROGRESS, min(100, progress + random.randint(1, 10)))
            else:
                self._manager.set_state(STATE_KEY_SOFTWARE_UPDATE_INSTALLING, False)
                self._manager.set_state(STATE_KEY_SOFTWARE_UPDATE_VERSION, "2025.36.2")
                self._manager.set_state(STATE_KEY_SOFTWARE_UPDATE_AVAILABLE, False)
            await self._manager.async_save()