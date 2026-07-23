"""Platform for virtual lock integration."""
from __future__ import annotations

import logging
import random
from datetime import datetime
from typing import Any

from homeassistant.components.lock import LockEntity, LockEntityFeature
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_call_later

from .base_entity import BaseVirtualEntity
from .const import (
    CONF_ENTITIES,
    CONF_LOCK_STATE,
    DEVICE_TYPE_LOCK,
    DOMAIN,
    LOCK_TYPES,
)
from .types import LockEntityConfig, LockState as LockStateType

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up virtual lock entities."""
    device_type: str | None = config_entry.data.get("device_type")

    if device_type != DEVICE_TYPE_LOCK:
        return

    device_info: DeviceInfo = hass.data[DOMAIN][config_entry.entry_id]["device_info"]
    entities: list[LockEntity | SensorEntity] = []
    entities_config: list[LockEntityConfig] = config_entry.data.get(CONF_ENTITIES, [])

    for idx, entity_config in enumerate(entities_config):
        lock = VirtualLock(
            hass,
            config_entry.entry_id,
            entity_config,
            idx,
            device_info,
        )
        entities.append(lock)

        # Create linked battery sensor
        battery_sensor = VirtualLockBatterySensor(
            hass,
            config_entry.entry_id,
            entity_config,
            idx,
            device_info,
            lock,
        )
        entities.append(battery_sensor)

    async_add_entities(entities)


class VirtualLock(BaseVirtualEntity[LockEntityConfig, LockStateType], LockEntity):
    """Representation of a virtual lock."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry_id: str,
        entity_config: LockEntityConfig,
        index: int,
        device_info: DeviceInfo,
    ) -> None:
        """Initialize the virtual lock."""
        super().__init__(hass, config_entry_id, entity_config, index, device_info, "lock")

        # Lock type
        lock_type: str = entity_config.get("lock_type", "smart_lock")
        self._lock_type = lock_type

        # Set icon based on type
        icon_map: dict[str, str] = {
            "deadbolt": "mdi:lock",
            "door_lock": "mdi:lock-outline",
            "padlock": "mdi:lock-open-variant",
            "smart_lock": "mdi:lock-smart",
        }
        self._attr_icon = icon_map.get(lock_type, "mdi:lock")

        # Initialize state.
        # HA Core `LockEntity.state` is `@final` and derives from the
        # `is_locked`/`is_jammed`/`is_opening`/`is_locking`/`is_open`/
        # `is_unlocking` cached properties, each of which reads the matching
        # `_attr_*` field. Setting `_attr_state` has NO effect (the base
        # class keeps it as the `None` placeholder). Use `_attr_is_locked`
        # to drive the reported state instead.
        initial_state: str = entity_config.get(CONF_LOCK_STATE, "locked")
        self._attr_is_locked: bool | None = initial_state == "locked"

        # `lock.open` requires the OPEN feature flag (LockEntityFeature.OPEN)
        self._attr_supported_features = LockEntityFeature.OPEN

        # Battery level (internal tracking only; exposed via the companion
        # `VirtualLockBatterySensor` — `LockEntity` has no `_attr_battery_level`
        # field, so we keep this private).
        self._battery_level: int = random.randint(20, 100)

        # Lock attributes
        self._attr_is_jammed: bool | None = False
        self._last_access: datetime | None = None
        self._access_code: str = entity_config.get("access_code", "1234")
        self._auto_lock_enabled: bool = entity_config.get("auto_lock", True)
        self._auto_lock_delay: int = entity_config.get("auto_lock_delay", 30)
        self._jamming_enabled: bool = entity_config.get("enable_jamming", False)

    def get_default_state(self) -> LockStateType:
        """Return the default state for this lock entity."""
        return LockStateType(
            state="locked",
        )

    def apply_state(self, state: LockStateType) -> None:
        """Apply loaded state to entity attributes."""
        state_str: str = state.get("state", "locked")
        self._attr_is_locked = state_str == "locked"
        _LOGGER.info("Lock '%s' state loaded from storage", self._attr_name)

    def get_current_state(self) -> LockStateType:
        """Get current state for persistence."""
        return LockStateType(
            state="locked" if self._attr_is_locked else "unlocked",
        )

    @property
    def battery_level_internal(self) -> int:
        """Return the battery level for internal use by battery sensor."""
        return self._battery_level

    async def async_lock(self, **kwargs: Any) -> None:
        """Lock the lock."""
        if self._attr_is_jammed:
            _LOGGER.warning("Virtual lock '%s' is jammed, cannot lock", self._attr_name)
            return

        self._attr_is_locked = True
        self._last_access = datetime.now()
        await self.async_save_state()
        self.async_write_ha_state()
        _LOGGER.debug("Virtual lock '%s' locked", self._attr_name)

        self.fire_template_event("lock.lock", state="locked")

        # Fire lock state changed event
        self._hass.bus.async_fire(
            f"{DOMAIN}_lock_state_changed",
            {
                "entity_id": self.entity_id,
                "device_id": self._config_entry_id,
                "lock_state": "locked",
                "timestamp": self._last_access.isoformat() if self._last_access else None,
            },
        )

    async def async_unlock(self, **kwargs: Any) -> None:
        """Unlock the lock."""
        if self._attr_is_jammed:
            _LOGGER.warning("Virtual lock '%s' is jammed, cannot unlock", self._attr_name)
            return

        self._attr_is_locked = False
        self._last_access = datetime.now()
        await self.async_save_state()
        self.async_write_ha_state()
        _LOGGER.debug("Virtual lock '%s' unlocked", self._attr_name)

        self.fire_template_event("lock.unlock", state="unlocked")

        # Fire lock state changed event
        self._hass.bus.async_fire(
            f"{DOMAIN}_lock_state_changed",
            {
                "entity_id": self.entity_id,
                "device_id": self._config_entry_id,
                "lock_state": "unlocked",
                "timestamp": self._last_access.isoformat() if self._last_access else None,
            },
        )

        # Auto-lock if enabled (uses an async_call_later timer that is
        # automatically cancelled via async_on_remove when the entity is
        # removed from hass).
        if self._auto_lock_enabled:
            async def _auto_lock(*args: Any) -> None:
                if self._attr_is_locked is False and self._auto_lock_enabled:
                    await self.async_lock()
                    _LOGGER.debug("Virtual lock '%s' auto-locked", self._attr_name)
            self._auto_lock_timer = async_call_later(
                self._hass, self._auto_lock_delay, _auto_lock
            )
            self.async_on_remove(lambda: self._auto_lock_timer() if self._auto_lock_timer else None)

    async def async_open(self, **kwargs: Any) -> None:
        """Open the lock (unlocked)."""
        await self.async_unlock(**kwargs)

    async def async_update(self) -> None:
        """Update lock state."""
        # Simulate battery consumption
        if self._attr_is_locked is False:
            self._battery_level = max(0, self._battery_level - random.uniform(0.01, 0.05))
        else:
            self._battery_level = max(0, self._battery_level - random.uniform(0.001, 0.01))

        await self.async_save_state()

        # Simulate random jamming (configurable)
        if self._jamming_enabled and random.random() < 0.01:
            self._attr_is_jammed = True
            self.async_write_ha_state()
            _LOGGER.warning("Virtual lock '%s' is jammed", self._attr_name)
        elif self._attr_is_jammed and random.random() < 0.1:
            self._attr_is_jammed = False
            self.async_write_ha_state()
            _LOGGER.info("Virtual lock '%s' is no longer jammed", self._attr_name)

        self.async_write_ha_state()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes."""
        attrs: dict[str, Any] = {
            "lock_type": LOCK_TYPES.get(self._lock_type, self._lock_type),
            "auto_lock_enabled": self._auto_lock_enabled,
            "auto_lock_delay": self._auto_lock_delay,
            "is_jammed": self._attr_is_jammed,
            "jamming_enabled": self._jamming_enabled,
        }

        if self._last_access:
            attrs["last_access"] = self._last_access.isoformat()

        return attrs


class VirtualLockBatterySensor(SensorEntity):
    """Battery sensor for virtual lock."""

    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_should_poll = True

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry_id: str,
        entity_config: LockEntityConfig,
        index: int,
        device_info: DeviceInfo,
        lock: VirtualLock,
    ) -> None:
        """Initialize the battery sensor."""
        self._hass = hass
        self._lock = lock
        entity_name = entity_config.get("entity_name", f"lock_{index + 1}")
        self._attr_name = f"{entity_name} Battery"
        self._attr_unique_id = f"{config_entry_id}_lock_{index}_battery"
        self._attr_device_info = device_info

    @property
    def native_value(self) -> int:
        """Return the battery level."""
        return self._lock.battery_level_internal

    async def async_update(self) -> None:
        """Update the sensor state."""
        # Battery level is updated by the lock entity, we just read it
        pass
