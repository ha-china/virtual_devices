"""Number platform for virtual laundry and grouped appliances."""
from __future__ import annotations

from typing import Any

from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .appliance import get_appliance_bundles
from .const import DEVICE_TYPE_DISHWASHER, DEVICE_TYPE_DRYER, DEVICE_TYPE_REFRIGERATOR, DEVICE_TYPE_WASHER, DOMAIN
from .laundry import get_laundry_bundles


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up laundry number entities."""
    device_type: str | None = config_entry.data.get("device_type")
    if device_type not in (DEVICE_TYPE_WASHER, DEVICE_TYPE_DRYER, DEVICE_TYPE_DISHWASHER, DEVICE_TYPE_REFRIGERATOR):
        return

    device_info: DeviceInfo = hass.data[DOMAIN][config_entry.entry_id]["device_info"]
    entities: list[VirtualLaundryDelayNumber | VirtualApplianceNumber] = []
    for index, bundle in enumerate(get_laundry_bundles(hass, config_entry.entry_id)):
        entities.append(
            VirtualLaundryDelayNumber(
                config_entry.entry_id,
                bundle.base_name,
                index,
                device_info,
                bundle.manager,
            )
        )
    if device_type == DEVICE_TYPE_DISHWASHER:
        for index, bundle in enumerate(get_appliance_bundles(hass, config_entry.entry_id)):
            entities.append(VirtualApplianceNumber(config_entry.entry_id, bundle.base_name, index, device_info, bundle.manager, "delay_start", 0, 1440, 5))
        async_add_entities(entities)
        return

    if device_type == DEVICE_TYPE_REFRIGERATOR:
        for index, bundle in enumerate(get_appliance_bundles(hass, config_entry.entry_id)):
            entities.append(VirtualApplianceNumber(config_entry.entry_id, bundle.base_name, index, device_info, bundle.manager, "fridge_temperature", 1, 8, 1))
            entities.append(VirtualApplianceNumber(config_entry.entry_id, bundle.base_name, index, device_info, bundle.manager, "freezer_temperature", -30, -10, 1))
        async_add_entities(entities)
        return

    async_add_entities(entities)


class VirtualLaundryDelayNumber(NumberEntity):
    """Delay-start number entity for laundry devices."""

    _attr_should_poll = True
    _attr_native_min_value = 0
    _attr_native_max_value = 1440
    _attr_native_step = 5
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES

    def __init__(
        self,
        config_entry_id: str,
        base_name: str,
        index: int,
        device_info: DeviceInfo,
        manager: Any,
    ) -> None:
        self._manager = manager
        self._attr_name = f"{base_name} Delay Start"
        self._attr_unique_id = f"{config_entry_id}_laundry_{index}_delay_start"
        self._attr_device_info = device_info

    @property
    def native_value(self) -> float:
        """Return delay start in minutes."""
        return float(self._manager.state["delay_start_minutes"])

    async def async_set_native_value(self, value: float) -> None:
        """Set delay start in minutes."""
        await self._manager.async_set_delay_start_minutes(int(value))
        self.async_write_ha_state()

    async def async_update(self) -> None:
        """Refresh shared laundry state."""
        await self._manager.async_refresh()


class VirtualApplianceNumber(NumberEntity):
    """Number entity for grouped appliances."""

    _attr_should_poll = True

    def __init__(self, config_entry_id: str, base_name: str, index: int, device_info: DeviceInfo, manager: Any, number_kind: str, min_value: float, max_value: float, step: float) -> None:
        self._manager = manager
        self._number_kind = number_kind
        self._attr_name = f"{base_name} {number_kind.replace('_', ' ').title()}"
        self._attr_unique_id = f"{config_entry_id}_{manager.device_type}_{index}_{number_kind}_number"
        self._attr_device_info = device_info
        self._attr_native_min_value = min_value
        self._attr_native_max_value = max_value
        self._attr_native_step = step
        self._attr_native_unit_of_measurement = UnitOfTime.MINUTES if number_kind == "delay_start" else None

    @property
    def native_value(self) -> float:
        state = self._manager.state
        if self._number_kind == "delay_start":
            return float(state.get("delay_start_minutes", 0))
        return float(state.get(self._number_kind, 0))

    async def async_set_native_value(self, value: float) -> None:
        if self._number_kind == "delay_start":
            await self._manager.async_set_delay_start_minutes(int(value))
        elif self._number_kind == "fridge_temperature":
            await self._manager.async_set_temps(fridge_temp=int(value))
        else:
            await self._manager.async_set_temps(freezer_temp=int(value))
        self.async_write_ha_state()

    async def async_update(self) -> None:
        await self._manager.async_refresh()
