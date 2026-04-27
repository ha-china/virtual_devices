"""Number platform for virtual laundry devices."""
from __future__ import annotations

from typing import Any

from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DEVICE_TYPE_DRYER, DEVICE_TYPE_WASHER, DOMAIN
from .laundry import get_laundry_bundles


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up laundry number entities."""
    device_type: str | None = config_entry.data.get("device_type")
    if device_type not in (DEVICE_TYPE_WASHER, DEVICE_TYPE_DRYER):
        return

    device_info: DeviceInfo = hass.data[DOMAIN][config_entry.entry_id]["device_info"]
    entities: list[VirtualLaundryDelayNumber] = []
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
