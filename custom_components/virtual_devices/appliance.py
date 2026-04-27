"""Shared device-group models for dishwasher, refrigerator, and doorbell."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Literal

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import (
    CONF_APPLIANCE_PROGRAM,
    CONF_CYCLE_DURATION_MINUTES,
    CONF_DELAY_START_MINUTES,
    CONF_DEVICE_NAME,
    CONF_DOORBELL_CHIME,
    CONF_ENTITIES,
    CONF_ENTITY_NAME,
    CONF_FREEZER_TEMPERATURE,
    CONF_FRIDGE_TEMPERATURE,
    DOMAIN,
    get_default_entity_config,
)

ApplianceDeviceType = Literal["dishwasher", "refrigerator", "doorbell"]


@dataclass
class ApplianceBundle:
    manager: "ApplianceManager"
    base_name: str


class ApplianceManager:
    """Shared state manager for grouped appliance devices."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry_id: str,
        index: int,
        device_type: ApplianceDeviceType,
        entity_config: dict[str, Any],
    ) -> None:
        self.hass = hass
        self.config_entry_id = config_entry_id
        self.index = index
        self.device_type = device_type
        self.entity_config = entity_config
        self.base_name = entity_config.get(CONF_ENTITY_NAME, f"{device_type}_{index + 1}")
        self._store: Store[dict[str, Any]] = Store(
            hass,
            1,
            f"virtual_devices_{device_type}_{config_entry_id}_{index}",
        )
        self._loaded = False
        self._last_refresh: datetime | None = None
        self._start_time: datetime | None = None
        self._delay_start_at: datetime | None = None
        self._pause_started_at: datetime | None = None
        self._paused_seconds_total = 0

        if device_type == "dishwasher":
            duration = int(entity_config.get(CONF_CYCLE_DURATION_MINUTES, 120))
            self._state: dict[str, Any] = {
                "power_on": False,
                "operation_state": "ready",
                "selected_program": entity_config.get(CONF_APPLIANCE_PROGRAM, "eco"),
                "total_seconds": duration * 60,
                "remaining_seconds": duration * 60,
                "delay_start_minutes": int(entity_config.get(CONF_DELAY_START_MINUTES, 0)),
                "door_open": False,
            }
        elif device_type == "refrigerator":
            self._state = {
                "power_on": True,
                "mode": entity_config.get("refrigerator_mode", "normal"),
                "fridge_temperature": int(entity_config.get(CONF_FRIDGE_TEMPERATURE, 4)),
                "freezer_temperature": int(entity_config.get(CONF_FREEZER_TEMPERATURE, -18)),
                "fridge_door_open": False,
                "freezer_door_open": False,
            }
        else:
            self._state = {
                "motion_detected": False,
                "last_ring": None,
                "doorbell_chime": entity_config.get(CONF_DOORBELL_CHIME, "classic"),
                "camera_streaming": False,
            }

    async def async_load(self) -> None:
        if self._loaded:
            return
        stored = await self._store.async_load()
        if stored is not None:
            self._state.update(stored)
        self._loaded = True

    async def async_save(self) -> None:
        await self._store.async_save(self._state)

    async def async_refresh(self) -> None:
        await self.async_load()
        now = dt_util.utcnow()
        if self.device_type == "dishwasher":
            if self._state["operation_state"] == "delayedstart" and self._delay_start_at and now >= self._delay_start_at:
                self._state["operation_state"] = "run"
                self._start_time = now
                self._delay_start_at = None
            if self._state["operation_state"] == "run" and self._start_time is not None:
                elapsed = int((now - self._start_time).total_seconds()) - self._paused_seconds_total
                self._state["remaining_seconds"] = max(0, self._state["total_seconds"] - elapsed)
                if self._state["remaining_seconds"] == 0:
                    self._state["operation_state"] = "finished"
                    self._state["power_on"] = False
                    self._start_time = None
                    self._paused_seconds_total = 0
                    self._pause_started_at = None
            elif self._state["operation_state"] == "ready":
                self._paused_seconds_total = 0
                self._pause_started_at = None
        elif self.device_type == "doorbell":
            last_ring = self._state.get("last_ring")
            if last_ring:
                ring_time = dt_util.parse_datetime(last_ring)
                if ring_time and (now - ring_time).total_seconds() > 20:
                    self._state["motion_detected"] = False
                    self._state["camera_streaming"] = False
        elif self.device_type == "refrigerator":
            if self._state.get("fridge_door_open") or self._state.get("freezer_door_open"):
                self._state["mode"] = self._state.get("mode", "normal")
        self._last_refresh = now

    async def async_set_power(self, power_on: bool) -> None:
        await self.async_load()
        self._state["power_on"] = power_on
        if self.device_type == "dishwasher" and not power_on:
            self._state["operation_state"] = "ready"
            self._state["remaining_seconds"] = self._state.get("total_seconds", 0)
            self._start_time = None
            self._delay_start_at = None
            self._pause_started_at = None
            self._paused_seconds_total = 0
        await self.async_save()

    async def async_set_program(self, program: str) -> None:
        await self.async_load()
        self._state["selected_program"] = program
        if self.device_type == "dishwasher" and self._state.get("operation_state") in ("ready", "finished"):
            self._state["remaining_seconds"] = self._state.get("total_seconds", 0)
        await self.async_save()

    async def async_set_delay_start_minutes(self, minutes: int) -> None:
        await self.async_load()
        self._state["delay_start_minutes"] = minutes
        await self.async_save()

    async def async_start(self) -> None:
        await self.async_load()
        self._state["power_on"] = True
        delay = self._state.get("delay_start_minutes", 0)
        self._state["remaining_seconds"] = self._state.get("total_seconds", 0)
        self._paused_seconds_total = 0
        self._pause_started_at = None
        if delay > 0:
            self._state["operation_state"] = "delayedstart"
            self._delay_start_at = dt_util.utcnow() + timedelta(minutes=delay)
            self._start_time = None
        else:
            self._state["operation_state"] = "run"
            self._start_time = dt_util.utcnow()
        await self.async_save()

    async def async_pause(self) -> None:
        await self.async_load()
        if self._state.get("operation_state") == "run":
            self._state["operation_state"] = "pause"
            self._pause_started_at = dt_util.utcnow()
        await self.async_save()

    async def async_resume(self) -> None:
        await self.async_load()
        if self._state.get("operation_state") == "pause":
            self._state["operation_state"] = "run"
            if self._pause_started_at is not None:
                self._paused_seconds_total += int((dt_util.utcnow() - self._pause_started_at).total_seconds())
            self._pause_started_at = None
            if self._start_time is None:
                self._start_time = dt_util.utcnow()
        await self.async_save()

    async def async_stop(self) -> None:
        await self.async_load()
        self._state["operation_state"] = "ready"
        self._state["remaining_seconds"] = self._state.get("total_seconds", 0)
        self._start_time = None
        self._delay_start_at = None
        self._pause_started_at = None
        self._paused_seconds_total = 0
        await self.async_save()

    async def async_set_mode(self, mode: str) -> None:
        await self.async_load()
        self._state["mode"] = mode
        await self.async_save()

    async def async_set_temps(self, fridge_temp: int | None = None, freezer_temp: int | None = None) -> None:
        await self.async_load()
        if fridge_temp is not None:
            self._state["fridge_temperature"] = fridge_temp
        if freezer_temp is not None:
            self._state["freezer_temperature"] = freezer_temp
        await self.async_save()

    async def async_ring(self) -> None:
        await self.async_load()
        self._state["last_ring"] = dt_util.utcnow().isoformat()
        self._state["motion_detected"] = True
        self._state["camera_streaming"] = True
        await self.async_save()

    async def async_set_chime(self, chime: str) -> None:
        await self.async_load()
        self._state["doorbell_chime"] = chime
        await self.async_save()

    @property
    def state(self) -> dict[str, Any]:
        return self._state

    @property
    def finish_time(self) -> datetime | None:
        if self.device_type != "dishwasher":
            return None
        if self._state["operation_state"] not in ("run", "delayedstart", "pause"):
            return None
        if self._state["operation_state"] == "delayedstart" and self._delay_start_at is not None:
            return self._delay_start_at + timedelta(seconds=self._state["remaining_seconds"])
        return dt_util.utcnow() + timedelta(seconds=self._state["remaining_seconds"])


def get_appliance_bundles(hass: HomeAssistant, config_entry_id: str) -> list[ApplianceBundle]:
    entry_data: dict[str, Any] = hass.data[DOMAIN][config_entry_id]
    config = entry_data["config"]
    device_type = config.get("device_type")
    if device_type not in ("dishwasher", "refrigerator", "doorbell"):
        return []
    key = f"{device_type}_bundles"
    bundles = entry_data.setdefault(key, [])
    if bundles:
        return bundles

    entity_configs: list[dict[str, Any]] = list(config.get(CONF_ENTITIES, []))
    if not entity_configs:
        fallback_name = config.get(CONF_DEVICE_NAME, device_type.title())
        entity_configs = [{CONF_ENTITY_NAME: f"{fallback_name}_{device_type}_1", **get_default_entity_config(device_type)}]

    for index, entity_config in enumerate(entity_configs):
        manager = ApplianceManager(hass, config_entry_id, index, device_type, entity_config)
        bundles.append(ApplianceBundle(manager=manager, base_name=manager.base_name))

    return bundles
