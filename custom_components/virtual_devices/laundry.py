"""Shared laundry device model for washer and dryer virtual devices."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Literal

from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util
from homeassistant.helpers.storage import Store

from .const import (
    CONF_DEVICE_NAME,
    CONF_CYCLE_DURATION_MINUTES,
    CONF_ENTITIES,
    CONF_ENTITY_NAME,
    CONF_LAUNDRY_MODE,
    CONF_SUPPORTS_PAUSE,
    DOMAIN,
    get_default_entity_config,
)
from .types import LaundryEntityConfig, LaundryState

LaundryDeviceType = Literal["washer", "dryer"]

WASHER_PROGRAMS: list[str] = ["quick", "cotton", "eco", "rinse_spin", "delicates"]
DRYER_PROGRAMS: list[str] = ["quick_dry", "cotton", "eco_dry", "mixed", "towels"]
WASHER_TEMPERATURES: list[str] = ["cold", "30C", "40C", "60C"]
WASHER_SPIN_SPEEDS: list[str] = ["off", "800_rpm", "1000_rpm", "1200_rpm", "1400_rpm"]
DRYER_TARGETS: list[str] = ["iron_dry", "cupboard_dry", "cupboard_dry_plus", "extra_dry"]


def get_program_options(device_type: LaundryDeviceType) -> list[str]:
    """Return available program options for a laundry device."""
    return WASHER_PROGRAMS if device_type == "washer" else DRYER_PROGRAMS


@dataclass
class LaundryBundle:
    """Bundle of shared runtime objects for a laundry appliance."""

    manager: "LaundryDeviceManager"
    base_name: str


class LaundryDeviceManager:
    """Manage shared state for a washer or dryer appliance."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry_id: str,
        index: int,
        device_type: LaundryDeviceType,
        entity_config: LaundryEntityConfig,
    ) -> None:
        self.hass = hass
        self.config_entry_id = config_entry_id
        self.index = index
        self.device_type = device_type
        self.entity_config = entity_config
        self.base_name = entity_config.get(CONF_ENTITY_NAME, f"{device_type}_{index + 1}")
        self._store: Store[LaundryState] = Store(
            hass,
            1,
            f"virtual_devices_laundry_{config_entry_id}_{index}",
        )
        self._loaded = False
        self._last_refresh: datetime | None = None
        self._start_time: datetime | None = None
        self._pause_started_at: datetime | None = None
        self._delayed_start_at: datetime | None = None
        self._paused_seconds_total = 0

        default_program = entity_config.get(
            CONF_LAUNDRY_MODE,
            get_program_options(device_type)[0],
        )
        default_duration = int(entity_config.get(CONF_CYCLE_DURATION_MINUTES, 45 if device_type == "washer" else 60))
        supports_pause = bool(entity_config.get(CONF_SUPPORTS_PAUSE, True))

        self._state: LaundryState = {
            "power_on": False,
            "operation_state": "ready",
            "selected_program": default_program,
            "total_seconds": default_duration * 60,
            "remaining_seconds": default_duration * 60,
            "delay_start_minutes": 0,
            "supports_pause": supports_pause,
            "remote_start_enabled": True,
            "remote_control_enabled": True,
            "door_open": False,
        }
        if device_type == "washer":
            self._state["temperature"] = "40C"
            self._state["spin_speed"] = "1200_rpm"
        else:
            self._state["drying_target"] = "cupboard_dry"

    async def async_load(self) -> None:
        """Load stored state once."""
        if self._loaded:
            return
        stored = await self._store.async_load()
        if stored is not None:
            self._state.update(stored)
        self._loaded = True

    async def async_save(self) -> None:
        """Persist current state."""
        await self._store.async_save(self._state)

    async def async_refresh(self) -> None:
        """Refresh dynamic state derived from time."""
        await self.async_load()
        now = dt_util.utcnow()
        if self._last_refresh is None:
            self._last_refresh = now
            return

        if self._state["operation_state"] == "delayedstart" and self._delayed_start_at and now >= self._delayed_start_at:
            self._state["operation_state"] = "run"
            self._start_time = now
            self._delayed_start_at = None

        if self._state["operation_state"] == "run" and self._start_time is not None:
            elapsed = int((now - self._start_time).total_seconds()) - self._paused_seconds_total
            remaining = max(0, self._state["total_seconds"] - elapsed)
            self._state["remaining_seconds"] = remaining
            if remaining == 0:
                self._state["operation_state"] = "finished"
                self._state["power_on"] = False
                self._start_time = None
                self._paused_seconds_total = 0

        self._last_refresh = now

    async def async_set_power(self, power_on: bool) -> None:
        """Turn appliance power on or off."""
        await self.async_load()
        self._state["power_on"] = power_on
        if not power_on:
            await self.async_stop_program()
            self._state["operation_state"] = "inactive"
        elif self._state["operation_state"] == "inactive":
            self._state["operation_state"] = "ready"
        await self.async_save()

    async def async_start_program(self) -> None:
        """Start selected program."""
        await self.async_load()
        if not self._state["power_on"]:
            self._state["power_on"] = True
        self._state["remaining_seconds"] = self._state["total_seconds"]
        self._paused_seconds_total = 0
        self._pause_started_at = None
        delay = self._state["delay_start_minutes"]
        if delay > 0:
            self._state["operation_state"] = "delayedstart"
            self._delayed_start_at = dt_util.utcnow() + timedelta(minutes=delay)
            self._start_time = None
        else:
            self._state["operation_state"] = "run"
            self._start_time = dt_util.utcnow()
            self._delayed_start_at = None
        await self.async_save()

    async def async_pause_program(self) -> None:
        """Pause running program."""
        await self.async_refresh()
        if self._state["supports_pause"] and self._state["operation_state"] == "run":
            self._state["operation_state"] = "pause"
            self._pause_started_at = dt_util.utcnow()
            await self.async_save()

    async def async_resume_program(self) -> None:
        """Resume paused program."""
        await self.async_load()
        if self._state["operation_state"] == "pause":
            if self._pause_started_at is not None:
                self._paused_seconds_total += int((dt_util.utcnow() - self._pause_started_at).total_seconds())
            self._pause_started_at = None
            self._state["operation_state"] = "run"
            if self._start_time is None:
                self._start_time = dt_util.utcnow()
            await self.async_save()

    async def async_stop_program(self) -> None:
        """Stop the active program."""
        await self.async_load()
        self._state["operation_state"] = "ready"
        self._state["remaining_seconds"] = self._state["total_seconds"]
        self._delayed_start_at = None
        self._start_time = None
        self._pause_started_at = None
        self._paused_seconds_total = 0
        await self.async_save()

    async def async_set_program(self, program: str) -> None:
        """Set selected program."""
        await self.async_load()
        self._state["selected_program"] = program
        await self.async_save()

    async def async_set_delay_start_minutes(self, minutes: int) -> None:
        """Set delay start minutes."""
        await self.async_load()
        self._state["delay_start_minutes"] = max(0, minutes)
        await self.async_save()

    async def async_set_temperature(self, temperature: str) -> None:
        """Set washer temperature."""
        await self.async_load()
        self._state["temperature"] = temperature
        await self.async_save()

    async def async_set_spin_speed(self, spin_speed: str) -> None:
        """Set washer spin speed."""
        await self.async_load()
        self._state["spin_speed"] = spin_speed
        await self.async_save()

    async def async_set_drying_target(self, drying_target: str) -> None:
        """Set dryer drying target."""
        await self.async_load()
        self._state["drying_target"] = drying_target
        await self.async_save()

    @property
    def state(self) -> LaundryState:
        """Return shared state."""
        return self._state

    @property
    def progress_percent(self) -> int:
        """Return program progress percent."""
        total = max(1, self._state["total_seconds"])
        complete = total - self._state["remaining_seconds"]
        return int((complete / total) * 100)

    @property
    def finish_time(self) -> datetime | None:
        """Return predicted finish time."""
        if self._state["operation_state"] not in ("run", "delayedstart", "pause"):
            return None
        if self._state["operation_state"] == "delayedstart" and self._delayed_start_at is not None:
            return self._delayed_start_at + timedelta(seconds=self._state["remaining_seconds"])
        return dt_util.utcnow() + timedelta(seconds=self._state["remaining_seconds"])


def get_laundry_bundles(hass: HomeAssistant, config_entry_id: str) -> list[LaundryBundle]:
    """Return shared laundry bundles for a config entry."""
    entry_data: dict[str, Any] = hass.data[DOMAIN][config_entry_id]
    bundles = entry_data.setdefault("laundry_bundles", [])
    if bundles:
        return bundles

    config = entry_data["config"]
    device_type = config.get("device_type")
    if device_type not in ("washer", "dryer"):
        return []

    entity_configs: list[LaundryEntityConfig] = list(config.get(CONF_ENTITIES, []))
    if not entity_configs:
        fallback_name = config.get(CONF_DEVICE_NAME, device_type.title())
        fallback_config: LaundryEntityConfig = {
            CONF_ENTITY_NAME: f"{fallback_name}_{device_type}_1",
            **get_default_entity_config(device_type),
        }
        entity_configs = [fallback_config]

    for index, entity_config in enumerate(entity_configs):
        manager = LaundryDeviceManager(
            hass,
            config_entry_id,
            index,
            device_type,
            entity_config,
        )
        bundles.append(LaundryBundle(manager=manager, base_name=manager.base_name))

    return bundles
