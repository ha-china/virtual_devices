"""Sensor platform for virtual devices integration."""
from __future__ import annotations

import logging
import random
from typing import Any

from homeassistant.components.sensor import (
    RestoreSensor,
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    DEGREE,
    PERCENTAGE,
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    UnitOfApparentPower,
    UnitOfArea,
    UnitOfBloodGlucoseConcentration,
    UnitOfConductivity,
    UnitOfDataRate,
    UnitOfDensity,
    UnitOfEnergyDistance,
    UnitOfFrequency,
    UnitOfInformation,
    UnitOfIrradiance,
    UnitOfLength,
    UnitOfMass,
    UnitOfPrecipitationDepth,
    UnitOfPressure,
    UnitOfRadioactivity,
    UnitOfRatio,
    UnitOfReactiveEnergy,
    UnitOfReactivePower,
    UnitOfSoundPressure,
    UnitOfSpeed,
    UnitOfTemperature,
    UnitOfTime,
    UnitOfVolume,
    UnitOfVolumeFlowRate,
    UnitOfVolumetricFlux,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfPower,
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
    DEVICE_TYPE_VEHICLE,
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
        "default_name": "Temperature",
    },
    "humidity": {
        "device_class": SensorDeviceClass.HUMIDITY,
        "unit": PERCENTAGE,
        "state_class": SensorStateClass.MEASUREMENT,
        "range": (0, 100),
        "icon": "mdi:water-percent",
        "default_name": "Humidity",
    },
    "pressure": {
        "device_class": SensorDeviceClass.PRESSURE,
        "unit": UnitOfPressure.HPA,
        "state_class": SensorStateClass.MEASUREMENT,
        "range": (950, 1050),
        "icon": "mdi:gauge",
        "default_name": "Pressure",
    },
    "illuminance": {
        "device_class": SensorDeviceClass.ILLUMINANCE,
        "unit": "lx",
        "state_class": SensorStateClass.MEASUREMENT,
        "range": (0, 100000),
        "icon": "mdi:brightness-6",
        "default_name": "Illuminance",
    },
    "power": {
        "device_class": SensorDeviceClass.POWER,
        "unit": UnitOfPower.WATT,
        "state_class": SensorStateClass.MEASUREMENT,
        "range": (0, 5000),
        "icon": "mdi:flash",
        "default_name": "Power Consumption",
    },
    "energy": {
        "device_class": SensorDeviceClass.ENERGY,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "range": (0, 10000),
        "icon": "mdi:lightning-bolt",
        "default_name": "Total Energy kWh",
    },
    "gas": {
        "device_class": SensorDeviceClass.GAS,
        "unit": UnitOfVolume.CUBIC_METERS,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "range": (0, 10000),
        "icon": "mdi:fire",
        "default_name": "Gas Consumption",
    },
    "water": {
        "device_class": SensorDeviceClass.WATER,
        "unit": UnitOfVolume.CUBIC_METERS,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "range": (0, 100000),
        "icon": "mdi:water",
        "default_name": "Water Consumption",
    },
    "solar_energy": {
        "device_class": SensorDeviceClass.ENERGY,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "range": (0, 10000),
        "icon": "mdi:solar-power",
        "default_name": "Solar Production",
    },
    "battery_charge": {
        "device_class": SensorDeviceClass.ENERGY,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "range": (0, 10000),
        "icon": "mdi:battery-charging",
        "default_name": "Battery Charge",
    },
    "battery_discharge": {
        "device_class": SensorDeviceClass.ENERGY,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "range": (0, 10000),
        "icon": "mdi:battery-discharge",
        "default_name": "Battery Discharge",
    },
    "gas_flow_rate": {
        "device_class": SensorDeviceClass.VOLUME_FLOW_RATE,
        "unit": UnitOfVolumeFlowRate.CUBIC_METERS_PER_HOUR,
        "state_class": SensorStateClass.MEASUREMENT,
        "range": (0, 10),
        "icon": "mdi:pipe",
        "default_name": "Gas Flow Rate",
    },
    "water_flow_rate": {
        "device_class": SensorDeviceClass.VOLUME_FLOW_RATE,
        "unit": UnitOfVolumeFlowRate.LITERS_PER_MINUTE,
        "state_class": SensorStateClass.MEASUREMENT,
        "range": (0, 50),
        "icon": "mdi:water-pump",
        "default_name": "Water Flow Rate",
    },
    "voltage": {
        "device_class": SensorDeviceClass.VOLTAGE,
        "unit": UnitOfElectricPotential.VOLT,
        "state_class": SensorStateClass.MEASUREMENT,
        "range": (0, 500),
        "icon": "mdi:lightning-bolt-outline",
        "default_name": "Voltage",
    },
    "current": {
        "device_class": SensorDeviceClass.CURRENT,
        "unit": UnitOfElectricCurrent.AMPERE,
        "state_class": SensorStateClass.MEASUREMENT,
        "range": (0, 50),
        "icon": "mdi:current-ac",
        "default_name": "Current",
    },
    "battery": {
        "device_class": SensorDeviceClass.BATTERY,
        "unit": PERCENTAGE,
        "state_class": SensorStateClass.MEASUREMENT,
        "range": (0, 100),
        "icon": "mdi:battery",
        "default_name": "Battery",
    },
    "signal_strength": {
        "device_class": SensorDeviceClass.SIGNAL_STRENGTH,
        "unit": SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        "state_class": SensorStateClass.MEASUREMENT,
        "range": (-100, 0),
        "icon": "mdi:wifi",
        "default_name": "Signal Strength",
    },
    "pm25": {
        "device_class": SensorDeviceClass.PM25,
        "unit": UnitOfDensity.MICROGRAMS_PER_CUBIC_METER,
        "state_class": SensorStateClass.MEASUREMENT,
        "range": (0, 500),
        "icon": "mdi:blur",
        "default_name": "PM2.5",
    },
    "pm10": {
        "device_class": SensorDeviceClass.PM10,
        "unit": UnitOfDensity.MICROGRAMS_PER_CUBIC_METER,
        "state_class": SensorStateClass.MEASUREMENT,
        "range": (0, 600),
        "icon": "mdi:blur",
        "default_name": "PM10",
    },
    "pm1": {
        "device_class": SensorDeviceClass.PM1,
        "unit": UnitOfDensity.MICROGRAMS_PER_CUBIC_METER,
        "state_class": SensorStateClass.MEASUREMENT,
        "range": (0, 300),
        "icon": "mdi:blur",
        "default_name": "PM1",
    },
    "pm4": {
        "device_class": SensorDeviceClass.PM4,
        "unit": UnitOfDensity.MICROGRAMS_PER_CUBIC_METER,
        "state_class": SensorStateClass.MEASUREMENT,
        "range": (0, 500),
        "icon": "mdi:blur",
        "default_name": "PM4",
    },
    "co2": {
        "device_class": SensorDeviceClass.CO2,
        "unit": UnitOfRatio.PARTS_PER_MILLION,
        "state_class": SensorStateClass.MEASUREMENT,
        "range": (300, 5000),
        "icon": "mdi:molecule-co2",
        "default_name": "CO2",
    },
    "voc": {
        "device_class": SensorDeviceClass.VOLATILE_ORGANIC_COMPOUNDS,
        "unit": UnitOfDensity.MICROGRAMS_PER_CUBIC_METER,
        "state_class": SensorStateClass.MEASUREMENT,
        "range": (0, 1000),
        "icon": "mdi:cloud",
        "default_name": "VOC",
    },
    "formaldehyde": {
        # No standard SensorDeviceClass for formaldehyde in HA Core
        "device_class": None,
        "unit": UnitOfDensity.MICROGRAMS_PER_CUBIC_METER,
        "state_class": SensorStateClass.MEASUREMENT,
        "range": (0, 100),
        "icon": "mdi:flask",
        "default_name": "Formaldehyde",
    },
    "carbon_monoxide": {
        "device_class": SensorDeviceClass.CO,
        "unit": UnitOfDensity.MICROGRAMS_PER_CUBIC_METER,
        "state_class": SensorStateClass.MEASUREMENT,
        "range": (0, 100),
        "icon": "mdi:molecule-co",
        "default_name": "Carbon Monoxide",
    },
    "nitrogen_monoxide": {
        "device_class": SensorDeviceClass.NITROGEN_MONOXIDE,
        "unit": UnitOfDensity.MICROGRAMS_PER_CUBIC_METER,
        "state_class": SensorStateClass.MEASUREMENT,
        "range": (0, 200),
        "icon": "mdi:molecule-co",
        "default_name": "Nitrogen Monoxide",
    },
    "nitrogen_dioxide": {
        "device_class": SensorDeviceClass.NITROGEN_DIOXIDE,
        "unit": UnitOfDensity.MICROGRAMS_PER_CUBIC_METER,
        "state_class": SensorStateClass.MEASUREMENT,
        "range": (0, 200),
        "icon": "mdi:chemical-weapon",
        "default_name": "Nitrogen Dioxide",
    },
    "nitrous_oxide": {
        "device_class": SensorDeviceClass.NITROUS_OXIDE,
        "unit": UnitOfDensity.MICROGRAMS_PER_CUBIC_METER,
        "state_class": SensorStateClass.MEASUREMENT,
        "range": (0, 200),
        "icon": "mdi:cloud",
        "default_name": "Nitrous Oxide",
    },
    "ozone": {
        "device_class": SensorDeviceClass.OZONE,
        "unit": UnitOfDensity.MICROGRAMS_PER_CUBIC_METER,
        "state_class": SensorStateClass.MEASUREMENT,
        "range": (0, 500),
        "icon": "mdi:weather-sunny",
        "default_name": "Ozone",
    },
    "sulphur_dioxide": {
        "device_class": SensorDeviceClass.SULPHUR_DIOXIDE,
        "unit": UnitOfDensity.MICROGRAMS_PER_CUBIC_METER,
        "state_class": SensorStateClass.MEASUREMENT,
        "range": (0, 500),
        "icon": "mdi:chemical-weapon",
        "default_name": "Sulphur Dioxide",
    },
    "aqi": {
        "device_class": SensorDeviceClass.AQI,
        "unit": None,
        "state_class": SensorStateClass.MEASUREMENT,
        "range": (0, 500),
        "icon": "mdi:air-filter",
        "default_name": "Air Quality Index",
    },
    "radon": {
        "device_class": SensorDeviceClass.RADON,
        "unit": UnitOfRadioactivity.BECQUEREL_PER_CUBIC_METER,
        "state_class": SensorStateClass.MEASUREMENT,
        "range": (0, 1000),
        "icon": "mdi:radioactive",
        "default_name": "Radon",
    },
    "noise": {
        "device_class": SensorDeviceClass.SOUND_PRESSURE,
        "unit": UnitOfSoundPressure.DECIBEL,
        "state_class": SensorStateClass.MEASUREMENT,
        "range": (20, 120),
        "icon": "mdi:volume-high",
        "default_name": "Noise",
    },
    "uv_index": {
        # No SensorDeviceClass.EMISSIVITY/UV_INDEX in HA Core; uv_index is a
        # dimensionless measurement (weather entities expose it as a state attr).
        "device_class": None,
        "unit": None,
        "state_class": SensorStateClass.MEASUREMENT,
        "range": (0, 12),
        "icon": "mdi:weather-sunny",
        "default_name": "UV Index",
    },
    "rainfall": {
        "device_class": SensorDeviceClass.PRECIPITATION,
        "unit": UnitOfPrecipitationDepth.MILLIMETERS,
        "state_class": SensorStateClass.MEASUREMENT,
        "range": (0, 200),
        "icon": "mdi:weather-pouring",
        "default_name": "Rainfall",
    },
    "wind_speed": {
        "device_class": SensorDeviceClass.WIND_SPEED,
        "unit": UnitOfSpeed.KILOMETERS_PER_HOUR,
        "state_class": SensorStateClass.MEASUREMENT,
        "range": (0, 200),
        "icon": "mdi:weather-windy",
        "default_name": "Wind Speed",
    },
    "water_quality": {
        # No standard SensorDeviceClass for generic water quality index
        "device_class": None,
        "unit": None,
        "state_class": SensorStateClass.MEASUREMENT,
        "range": (0, 100),
        "icon": "mdi:water-check",
        "default_name": "Water Quality",
    },
    "ph": {
        "device_class": SensorDeviceClass.PH,
        "unit": None,
        "state_class": SensorStateClass.MEASUREMENT,
        "range": (0, 14),
        "icon": "mdi:water",
        "default_name": "pH",
    },
    "volume": {
        "device_class": SensorDeviceClass.VOLUME,
        "unit": UnitOfVolume.LITERS,
        "state_class": SensorStateClass.MEASUREMENT,
        "range": (0, 10000),
        "icon": "mdi:water",
        "default_name": "Volume",
    },
    "weight": {
        "device_class": SensorDeviceClass.WEIGHT,
        "unit": UnitOfMass.KILOGRAMS,
        "state_class": SensorStateClass.MEASUREMENT,
        "range": (0, 500),
        "icon": "mdi:scale",
        "default_name": "Weight",
    },
    "distance": {
        "device_class": SensorDeviceClass.DISTANCE,
        "unit": UnitOfLength.METERS,
        "state_class": SensorStateClass.MEASUREMENT,
        "range": (0, 1000),
        "icon": "mdi:ruler",
        "default_name": "Distance",
    },
    "irradiance": {
        "device_class": SensorDeviceClass.IRRADIANCE,
        "unit": UnitOfIrradiance.WATTS_PER_SQUARE_METER,
        "state_class": SensorStateClass.MEASUREMENT,
        "range": (0, 1500),
        "icon": "mdi:solar-power",
        "default_name": "Irradiance",
    },
    "moisture": {
        "device_class": SensorDeviceClass.MOISTURE,
        "unit": PERCENTAGE,
        "state_class": SensorStateClass.MEASUREMENT,
        "range": (0, 100),
        "icon": "mdi:water-percent",
        "default_name": "Soil Moisture",
    },
    "frequency": {
        "device_class": SensorDeviceClass.FREQUENCY,
        "unit": UnitOfFrequency.HERTZ,
        "state_class": SensorStateClass.MEASUREMENT,
        "range": (0, 1000000),
        "icon": "mdi:sine-wave",
        "default_name": "Frequency",
    },
    "timestamp": {
        "device_class": SensorDeviceClass.TIMESTAMP,
        "unit": None,
        "state_class": None,
        "range": None,
        "icon": "mdi:clock",
        "default_name": "Timestamp",
    },
    "duration": {
        "device_class": SensorDeviceClass.DURATION,
        "unit": UnitOfTime.SECONDS,
        "state_class": SensorStateClass.MEASUREMENT,
        "range": (0, 86400),
        "icon": "mdi:timer",
        "default_name": "Duration",
    },
    "absolute_humidity": {
        "device_class": SensorDeviceClass.ABSOLUTE_HUMIDITY,
        "unit": UnitOfDensity.GRAMS_PER_CUBIC_METER,
        "state_class": SensorStateClass.MEASUREMENT,
        "range": (0, 100),
        "icon": "mdi:water-percent",
        "default_name": "Absolute Humidity",
    },
    "apparent_power": {
        "device_class": SensorDeviceClass.APPARENT_POWER,
        "unit": UnitOfApparentPower.VOLT_AMPERE,
        "state_class": SensorStateClass.MEASUREMENT,
        "range": (0, 5000),
        "icon": "mdi:flash",
        "default_name": "Apparent Power",
    },
    "area": {
        "device_class": SensorDeviceClass.AREA,
        "unit": UnitOfArea.SQUARE_METERS,
        "state_class": SensorStateClass.MEASUREMENT,
        "range": (0, 10000),
        "icon": "mdi:select-compare",
        "default_name": "Area",
    },
    "blood_glucose_concentration": {
        "device_class": SensorDeviceClass.BLOOD_GLUCOSE_CONCENTRATION,
        "unit": UnitOfBloodGlucoseConcentration.MILLIGRAMS_PER_DECILITER,
        "state_class": SensorStateClass.MEASUREMENT,
        "range": (20, 600),
        "icon": "mdi:water",
        "default_name": "Blood Glucose",
    },
    "conductivity": {
        "device_class": SensorDeviceClass.CONDUCTIVITY,
        "unit": UnitOfConductivity.MICROSIEMENS_PER_CM,
        "state_class": SensorStateClass.MEASUREMENT,
        "range": (0, 100000),
        "icon": "mdi:waves",
        "default_name": "Conductivity",
    },
    "data_rate": {
        "device_class": SensorDeviceClass.DATA_RATE,
        "unit": UnitOfDataRate.KILOBITS_PER_SECOND,
        "state_class": SensorStateClass.MEASUREMENT,
        "range": (0, 1000000),
        "icon": "mdi:speedometer",
        "default_name": "Data Rate",
    },
    "data_size": {
        "device_class": SensorDeviceClass.DATA_SIZE,
        "unit": UnitOfInformation.MEGABYTES,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "range": (0, 1000000),
        "icon": "mdi:database",
        "default_name": "Data Size",
    },
    "energy_distance": {
        "device_class": SensorDeviceClass.ENERGY_DISTANCE,
        "unit": UnitOfEnergyDistance.KILO_WATT_HOURS_PER_100_KILOMETERS,
        "state_class": SensorStateClass.MEASUREMENT,
        "range": (0, 100),
        "icon": "mdi:lightning-bolt",
        "default_name": "Energy Distance",
    },
    "energy_storage": {
        "device_class": SensorDeviceClass.ENERGY_STORAGE,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "state_class": SensorStateClass.MEASUREMENT,
        "range": (0, 10000),
        "icon": "mdi:battery",
        "default_name": "Energy Storage",
    },
    "monetary": {
        "device_class": SensorDeviceClass.MONETARY,
        "unit": "CNY",
        "state_class": SensorStateClass.TOTAL,
        "range": (0, 100000),
        "icon": "mdi:cash",
        "default_name": "Monetary",
    },
    "power_factor": {
        "device_class": SensorDeviceClass.POWER_FACTOR,
        "unit": None,
        "state_class": SensorStateClass.MEASUREMENT,
        "range": (0, 1),
        "icon": "mdi:flash",
        "default_name": "Power Factor",
    },
    "precipitation_intensity": {
        "device_class": SensorDeviceClass.PRECIPITATION_INTENSITY,
        "unit": UnitOfVolumetricFlux.MILLIMETERS_PER_HOUR,
        "state_class": SensorStateClass.MEASUREMENT,
        "range": (0, 100),
        "icon": "mdi:weather-pouring",
        "default_name": "Precipitation Intensity",
    },
    "reactive_energy": {
        "device_class": SensorDeviceClass.REACTIVE_ENERGY,
        "unit": UnitOfReactiveEnergy.KILO_VOLT_AMPERE_REACTIVE_HOUR,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "range": (0, 10000),
        "icon": "mdi:lightning-bolt",
        "default_name": "Reactive Energy",
    },
    "reactive_power": {
        "device_class": SensorDeviceClass.REACTIVE_POWER,
        "unit": UnitOfReactivePower.KILO_VOLT_AMPERE_REACTIVE,
        "state_class": SensorStateClass.MEASUREMENT,
        "range": (0, 5000),
        "icon": "mdi:flash",
        "default_name": "Reactive Power",
    },
    "speed": {
        "device_class": SensorDeviceClass.SPEED,
        "unit": UnitOfSpeed.METERS_PER_SECOND,
        "state_class": SensorStateClass.MEASUREMENT,
        "range": (0, 100),
        "icon": "mdi:speedometer",
        "default_name": "Speed",
    },
    "temperature_delta": {
        "device_class": SensorDeviceClass.TEMPERATURE_DELTA,
        "unit": UnitOfTemperature.CELSIUS,
        "state_class": SensorStateClass.MEASUREMENT,
        "range": (-50, 100),
        "icon": "mdi:thermometer",
        "default_name": "Temperature Delta",
    },
    "volatile_organic_compounds_parts": {
        "device_class": SensorDeviceClass.VOLATILE_ORGANIC_COMPOUNDS_PARTS,
        "unit": UnitOfRatio.PARTS_PER_MILLION,
        "state_class": SensorStateClass.MEASUREMENT,
        "range": (0, 1000),
        "icon": "mdi:cloud",
        "default_name": "VOC Ratio",
    },
    "volume_storage": {
        "device_class": SensorDeviceClass.VOLUME_STORAGE,
        "unit": UnitOfVolume.LITERS,
        "state_class": SensorStateClass.MEASUREMENT,
        "range": (0, 10000),
        "icon": "mdi:tank",
        "default_name": "Volume Storage",
    },
    "wind_direction": {
        "device_class": SensorDeviceClass.WIND_DIRECTION,
        "unit": DEGREE,
        "state_class": SensorStateClass.MEASUREMENT,
        "range": (0, 360),
        "icon": "mdi:compass",
        "default_name": "Wind Direction",
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
    if device_type not in (DEVICE_TYPE_SENSOR, DEVICE_TYPE_WASHER, DEVICE_TYPE_DRYER, DEVICE_TYPE_DISHWASHER, DEVICE_TYPE_REFRIGERATOR, DEVICE_TYPE_DOORBELL, DEVICE_TYPE_VEHICLE):
        return

    device_info: DeviceInfo = hass.data[DOMAIN][config_entry.entry_id]["device_info"]
    entities: list[VirtualSensor | VirtualLaundrySensor] = []

    if device_type == DEVICE_TYPE_VEHICLE:
        from .vehicle import (
            VehicleDataManager,
            VirtualVehicleSpeedSensor, VirtualVehicleOdometerSensor,
            VirtualVehicleTripDistanceSensor, VirtualVehicleOutsideTempSensor,
            VirtualVehicleInsideTempSensor, VirtualVehicleFuelLevelSensor,
            VirtualVehicleFuelRangeSensor, VirtualVehicleBatteryLevelSensor,
            VirtualVehicleBatteryRangeSensor, VirtualVehicleBatteryVoltageSensor,
            VirtualVehicleBatteryCurrentSensor, VirtualVehicleMotorPowerSensor,
            VirtualVehicleChargeRateSensor, VirtualVehicleChargerPowerSensor,
            VirtualVehicleChargerVoltageSensor, VirtualVehicleChargerCurrentSensor,
            VirtualVehicleChargeEnergyAddedSensor, VirtualVehicleTimeToFullChargeSensor,
            VirtualVehicleTirePressureSensor, VirtualVehicleOilLevelSensor,
            VirtualVehicleCoolantTempSensor, VirtualVehicleBatteryTempSensor,
            VirtualVehicleEstimatedRangeSensor, VirtualVehicleAssistLevelSensor,
            VirtualVehicleTimesChargedSensor, VirtualVehicleBatteryGradeSensor,
            VirtualVehicleTimeLeftSensor, VirtualVehicleCentreCtrlBattSensor,
            VirtualVehicleHDopSensor, VirtualVehicleRidingTimeSensor,
            VirtualVehicleDaysInUseSensor, VirtualVehicleBatteryTempDescSensor,
            VirtualVehicleBatteryLevelBSensor,
        )
        entities_config = config_entry.data.get("entities", [])
        vehicle_type = entities_config[0].get("vehicle_type", "ev") if entities_config else "ev"
        manager = hass.data[DOMAIN][config_entry.entry_id].get("vehicle_manager")
        if not manager:
            entity_name = entities_config[0].get("entity_name", "vehicle") if entities_config else "vehicle"
            manager = VehicleDataManager(hass, config_entry.entry_id, vehicle_type, entity_name)
            await manager.async_load()
            hass.data[DOMAIN][config_entry.entry_id]["vehicle_manager"] = manager
        entity_name = entities_config[0].get("entity_name", "vehicle") if entities_config else "vehicle"
        sens_idx = 0
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
        async_add_entities(entities)
        return

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


class VirtualSensor(BaseVirtualEntity[SensorEntityConfig, SensorState], RestoreSensor, SensorEntity):
    """Representation of a virtual sensor."""

    _attr_should_poll = True

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

        # Use default name from sensor type, ignore config flow default
        self._attr_name = type_config.get("default_name", self._attr_name)

        # Simulation settings
        self._simulation_enabled: bool = entity_config.get("enable_simulation", True)
        self._update_frequency: int = entity_config.get("update_frequency", 30)

        # Initialize native value - will be populated by async_added_to_hass
        self._native_value: float | int | str | None = self._generate_initial_value(type_config)

    async def async_added_to_hass(self) -> None:
        """Restore state when entity is added to Home Assistant."""
        await super().async_added_to_hass()
        if (last_sensor_data := await self.async_get_last_sensor_data()) is not None:
            if last_sensor_data.native_value is not None:
                self._native_value = last_sensor_data.native_value

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
        if self._sensor_type in ("battery",):
            return random.randint(20, 100)
        if self._sensor_type in ("energy", "gas", "water", "solar_energy", "battery_charge", "battery_discharge"):
            return round(random.uniform(0, 10), 2)
        range_vals: tuple[int, int] = type_config.get("range", (0, 100))
        return round(random.uniform(range_vals[0], range_vals[1]), 1)

    async def async_update(self) -> None:
        """Update sensor value if simulation is enabled."""
        if not self._simulation_enabled:
            return

        type_config: dict[str, Any] = SENSOR_TYPE_CONFIG.get(self._sensor_type, {})
        range_vals: tuple[int, int] = type_config.get("range", (0, 100))

        if self._sensor_type == "battery":
            # Battery level drifts slowly within its configured range.
            current: float | int = self._native_value if isinstance(
                self._native_value, (int, float)) else range_vals[1]
            change: float = random.uniform(-5, 5)
            self._native_value = round(
                max(range_vals[0], min(range_vals[1], current + change)))
        elif self._sensor_type in ("energy", "gas", "water", "solar_energy", "battery_charge", "battery_discharge"):
            # TOTAL_INCREASING semantics: value only increases.
            current = self._native_value if isinstance(
                self._native_value, (int, float)) else 0.0
            increment = random.uniform(0.05, 0.5)
            self._native_value = round(
                min(range_vals[1], current + increment), 2)
        elif self._sensor_type in ("gas_flow_rate", "water_flow_rate"):
            # MEASUREMENT flow rate: fluctuates with occasional usage spikes.
            current = self._native_value if isinstance(
                self._native_value, (int, float)) else 0.0
            drift = random.uniform(-0.5, 0.5)
            spike = random.choice([0, 0, 0, 2, 5, 10]) if random.random() < 0.05 else 0
            self._native_value = round(
                max(range_vals[0], min(range_vals[1], current + drift + spike)), 1)
        elif self._sensor_type == "power":
            # Realistic household power simulation: base load + gradual changes + appliance spikes.
            current = self._native_value if isinstance(
                self._native_value, (int, float)) else 200.0
            # Base load (always-on devices: fridge, router, standby)
            base_load = random.uniform(150, 400)
            # Random walk drift
            drift = random.uniform(-50, 50)
            # Occasional appliance spike (e.g., kettle, microwave, oven)
            spike = 0
            if random.random() < 0.05:
                spike = random.choice([800, 1200, 1500, 2000, 2500])
            new_value = current + drift
            # Apply base load tendency (pull toward baseline)
            new_value = new_value * 0.9 + base_load * 0.1 + spike
            self._native_value = round(
                max(range_vals[0], min(range_vals[1], new_value)), 1)
        else:
            # MEASUREMENT-class sensors fluctuate within their configured range.
            self._native_value = round(
                random.uniform(range_vals[0], range_vals[1]), 1)

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
            self._attr_state_class = SensorStateClass.MEASUREMENT
        elif sensor_kind in ("remaining_time", "total_time"):
            self._attr_device_class = SensorDeviceClass.DURATION
            self._attr_native_unit_of_measurement = UnitOfTime.MINUTES
            self._attr_state_class = SensorStateClass.MEASUREMENT
        elif sensor_kind == "finish_time":
            self._attr_device_class = SensorDeviceClass.TIMESTAMP
        elif sensor_kind == "operation_state":
            self._attr_device_class = SensorDeviceClass.ENUM
            self._attr_options = [
                "ready", "delayedstart", "run", "pause", "finished", "inactive",
            ]

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
            self._attr_device_class = SensorDeviceClass.DURATION
            self._attr_native_unit_of_measurement = UnitOfTime.MINUTES
            self._attr_state_class = SensorStateClass.MEASUREMENT
        elif sensor_kind in ("fridge_temperature", "freezer_temperature"):
            self._attr_device_class = SensorDeviceClass.TEMPERATURE
            self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
            self._attr_state_class = SensorStateClass.MEASUREMENT
        elif sensor_kind == "finish_time":
            self._attr_device_class = SensorDeviceClass.TIMESTAMP
        elif sensor_kind == "mode":
            self._attr_device_class = SensorDeviceClass.ENUM
            self._attr_options = ["normal", "eco", "quick_cool", "vacation"]
        elif sensor_kind == "last_ring":
            self._attr_device_class = SensorDeviceClass.TIMESTAMP
        elif sensor_kind == "operation_state":
            self._attr_device_class = SensorDeviceClass.ENUM
            self._attr_options = [
                "ready", "delayedstart", "run", "pause", "finished", "inactive",
            ]

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
