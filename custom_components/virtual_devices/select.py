"""Select platform for virtual laundry and grouped appliances."""
from __future__ import annotations

from typing import Any

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .appliance import get_appliance_bundles
from .const import (
    DEVICE_TYPE_DISHWASHER,
    DEVICE_TYPE_DOORBELL,
    DEVICE_TYPE_DRYER,
    DEVICE_TYPE_REFRIGERATOR,
    DEVICE_TYPE_WASHER,
    DISHWASHER_PROGRAMS,
    DOORBELL_CHIMES,
    DOMAIN,
    REFRIGERATOR_MODES,
)
from .laundry import (
    DRYER_TARGETS,
    WASHER_SPIN_SPEEDS,
    WASHER_TEMPERATURES,
    get_laundry_bundles,
    get_program_options,
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up laundry select entities."""
    device_type: str | None = config_entry.data.get("device_type")
    if device_type not in (DEVICE_TYPE_WASHER, DEVICE_TYPE_DRYER, DEVICE_TYPE_DISHWASHER, DEVICE_TYPE_REFRIGERATOR, DEVICE_TYPE_DOORBELL):
        return

    device_info: DeviceInfo = hass.data[DOMAIN][config_entry.entry_id]["device_info"]
    entities: list[VirtualLaundrySelect | VirtualApplianceSelect] = []
    for index, bundle in enumerate(get_laundry_bundles(hass, config_entry.entry_id)):
        entities.append(
            VirtualLaundrySelect(
                config_entry.entry_id,
                bundle.base_name,
                index,
                device_info,
                bundle.manager,
                "program",
                get_program_options(device_type),
            )
        )
        if device_type == DEVICE_TYPE_WASHER:
            entities.append(
                VirtualLaundrySelect(
                    config_entry.entry_id,
                    bundle.base_name,
                    index,
                    device_info,
                    bundle.manager,
                    "temperature",
                    WASHER_TEMPERATURES,
                )
            )
            entities.append(
                VirtualLaundrySelect(
                    config_entry.entry_id,
                    bundle.base_name,
                    index,
                    device_info,
                    bundle.manager,
                    "spin_speed",
                    WASHER_SPIN_SPEEDS,
                )
            )
        else:
            entities.append(
                VirtualLaundrySelect(
                    config_entry.entry_id,
                    bundle.base_name,
                    index,
                    device_info,
                    bundle.manager,
                    "drying_target",
                    DRYER_TARGETS,
                )
            )

    if device_type == DEVICE_TYPE_DISHWASHER:
        for index, bundle in enumerate(get_appliance_bundles(hass, config_entry.entry_id)):
            entities.append(VirtualApplianceSelect(config_entry.entry_id, bundle.base_name, index, device_info, bundle.manager, "program", list(DISHWASHER_PROGRAMS.keys())))
        async_add_entities(entities)
        return

    if device_type == DEVICE_TYPE_REFRIGERATOR:
        for index, bundle in enumerate(get_appliance_bundles(hass, config_entry.entry_id)):
            entities.append(VirtualApplianceSelect(config_entry.entry_id, bundle.base_name, index, device_info, bundle.manager, "mode", list(REFRIGERATOR_MODES.keys())))
        async_add_entities(entities)
        return

    if device_type == DEVICE_TYPE_DOORBELL:
        for index, bundle in enumerate(get_appliance_bundles(hass, config_entry.entry_id)):
            entities.append(VirtualApplianceSelect(config_entry.entry_id, bundle.base_name, index, device_info, bundle.manager, "chime", list(DOORBELL_CHIMES.keys())))
        async_add_entities(entities)
        return

    async_add_entities(entities)


class VirtualLaundrySelect(SelectEntity):
    """Select entity for laundry options."""

    _attr_should_poll = True

    def __init__(
        self,
        config_entry_id: str,
        base_name: str,
        index: int,
        device_info: DeviceInfo,
        manager: Any,
        select_kind: str,
        options: list[str],
    ) -> None:
        self._manager = manager
        self._select_kind = select_kind
        self._attr_options = options
        self._attr_name = f"{base_name} {select_kind.replace('_', ' ').title()}"
        self._attr_unique_id = f"{config_entry_id}_laundry_{index}_{select_kind}_select"
        self._attr_device_info = device_info

    @property
    def current_option(self) -> str | None:
        """Return current selected option."""
        state = self._manager.state
        if self._select_kind == "program":
            return state["selected_program"]
        if self._select_kind == "temperature":
            return state.get("temperature")
        if self._select_kind == "spin_speed":
            return state.get("spin_speed")
        return state.get("drying_target")

    async def async_select_option(self, option: str) -> None:
        """Set selected option."""
        if self._select_kind == "program":
            await self._manager.async_set_program(option)
        elif self._select_kind == "temperature":
            await self._manager.async_set_temperature(option)
        elif self._select_kind == "spin_speed":
            await self._manager.async_set_spin_speed(option)
        else:
            await self._manager.async_set_drying_target(option)
        self.async_write_ha_state()

    async def async_update(self) -> None:
        """Refresh shared laundry state."""
        await self._manager.async_refresh()


class VirtualApplianceSelect(SelectEntity):
    """Select entity for grouped appliance options."""

    _attr_should_poll = True

    def __init__(self, config_entry_id: str, base_name: str, index: int, device_info: DeviceInfo, manager: Any, select_kind: str, options: list[str]) -> None:
        self._manager = manager
        self._select_kind = select_kind
        self._attr_options = options
        self._attr_name = f"{base_name} {select_kind.title()}"
        self._attr_unique_id = f"{config_entry_id}_{manager.device_type}_{index}_{select_kind}_select"
        self._attr_device_info = device_info

    @property
    def current_option(self) -> str | None:
        state = self._manager.state
        if self._select_kind == "program":
            return state.get("selected_program")
        if self._select_kind == "mode":
            return state.get("mode")
        return state.get("doorbell_chime")

    async def async_select_option(self, option: str) -> None:
        if self._select_kind == "program":
            await self._manager.async_set_program(option)
        elif self._select_kind == "mode":
            await self._manager.async_set_mode(option)
        else:
            await self._manager.async_set_chime(option)
        self.async_write_ha_state()

    async def async_update(self) -> None:
        await self._manager.async_refresh()
