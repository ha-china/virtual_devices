"""Platform for virtual binary sensor integration."""
from __future__ import annotations

import logging
import random

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
    DEVICE_TYPE_DRYER,
    DEVICE_TYPE_WASHER,
    DOMAIN,
)
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
    "moisture": BinarySensorDeviceClass.MOISTURE,
    "occupancy": BinarySensorDeviceClass.OCCUPANCY,
    "opening": BinarySensorDeviceClass.OPENING,
    "presence": BinarySensorDeviceClass.PRESENCE,
    "problem": BinarySensorDeviceClass.PROBLEM,
    "safety": BinarySensorDeviceClass.SAFETY,
    "sound": BinarySensorDeviceClass.SOUND,
    "vibration": BinarySensorDeviceClass.VIBRATION,
}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up virtual binary sensor entities."""
    device_type: str | None = config_entry.data.get("device_type")

    if device_type not in (DEVICE_TYPE_BINARY_SENSOR, DEVICE_TYPE_WASHER, DEVICE_TYPE_DRYER):
        return

    device_info: DeviceInfo = hass.data[DOMAIN][config_entry.entry_id]["device_info"]
    entities: list[VirtualBinarySensor | VirtualLaundryBinarySensor] = []

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
