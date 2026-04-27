"""Platform for virtual alarm control panel integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.alarm_control_panel import (
    AlarmControlPanelEntity,
    AlarmControlPanelEntityFeature,
    AlarmControlPanelState,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .base_entity import BaseVirtualEntity
from .const import (
    ALARM_STATES,
    CONF_ALARM_CODE,
    CONF_ALARM_TRIGGER_TIME,
    CONF_ENTITIES,
    CONF_SUPPORTS_ARM_NIGHT,
    CONF_SUPPORTS_ARM_VACATION,
    DEVICE_TYPE_ALARM_CONTROL_PANEL,
    DOMAIN,
)
from .types import AlarmControlPanelEntityConfig, AlarmControlPanelStateDict

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up virtual alarm control panel entities."""
    device_type: str | None = config_entry.data.get("device_type")
    if device_type != DEVICE_TYPE_ALARM_CONTROL_PANEL:
        return

    device_info: DeviceInfo = hass.data[DOMAIN][config_entry.entry_id]["device_info"]
    entities: list[VirtualAlarmControlPanel] = []
    entities_config: list[AlarmControlPanelEntityConfig] = config_entry.data.get(CONF_ENTITIES, [])

    for idx, entity_config in enumerate(entities_config):
        entities.append(
            VirtualAlarmControlPanel(hass, config_entry.entry_id, entity_config, idx, device_info)
        )

    async_add_entities(entities)


class VirtualAlarmControlPanel(
    BaseVirtualEntity[AlarmControlPanelEntityConfig, AlarmControlPanelStateDict],
    AlarmControlPanelEntity,
):
    """Representation of a virtual alarm control panel."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry_id: str,
        entity_config: AlarmControlPanelEntityConfig,
        index: int,
        device_info: DeviceInfo,
    ) -> None:
        super().__init__(
            hass,
            config_entry_id,
            entity_config,
            index,
            device_info,
            "alarm_control_panel",
        )
        self._attr_icon = "mdi:shield-home"
        self._alarm_code = entity_config.get(CONF_ALARM_CODE, "1234")
        self._trigger_time = int(entity_config.get(CONF_ALARM_TRIGGER_TIME, 180))
        self._supports_arm_night = bool(entity_config.get(CONF_SUPPORTS_ARM_NIGHT, True))
        self._supports_arm_vacation = bool(entity_config.get(CONF_SUPPORTS_ARM_VACATION, True))
        self._state: AlarmControlPanelState = AlarmControlPanelState.DISARMED
        features = (
            AlarmControlPanelEntityFeature.ARM_HOME
            | AlarmControlPanelEntityFeature.ARM_AWAY
            | AlarmControlPanelEntityFeature.TRIGGER
        )
        if self._supports_arm_night:
            features |= AlarmControlPanelEntityFeature.ARM_NIGHT
        if self._supports_arm_vacation:
            features |= AlarmControlPanelEntityFeature.ARM_VACATION
        self._attr_supported_features = features

    def get_default_state(self) -> AlarmControlPanelStateDict:
        return {"state": "disarmed"}

    def apply_state(self, state: AlarmControlPanelStateDict) -> None:
        state_key = state.get("state", "disarmed")
        self._state = AlarmControlPanelState(state_key)

    def get_current_state(self) -> AlarmControlPanelStateDict:
        return {"state": self._state.value}

    @property
    def alarm_state(self) -> AlarmControlPanelState | None:
        return self._state

    @property
    def code_arm_required(self) -> bool:
        return True

    @property
    def code_format(self) -> str | None:
        return "number"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "trigger_time": self._trigger_time,
            "supports_arm_night": self._supports_arm_night,
            "supports_arm_vacation": self._supports_arm_vacation,
            "available_states": list(ALARM_STATES.keys()),
        }

    def _validate_code(self, code: str | None) -> bool:
        return code == self._alarm_code

    async def async_alarm_disarm(self, code: str | None = None) -> None:
        if not self._validate_code(code):
            return
        self._state = AlarmControlPanelState.DISARMED
        await self.async_save_state()
        self.async_write_ha_state()
        self.fire_template_event("disarm", state=self._state.value)

    async def async_alarm_arm_home(self, code: str | None = None) -> None:
        if not self._validate_code(code):
            return
        self._state = AlarmControlPanelState.ARMED_HOME
        await self.async_save_state()
        self.async_write_ha_state()
        self.fire_template_event("arm_home", state=self._state.value)

    async def async_alarm_arm_away(self, code: str | None = None) -> None:
        if not self._validate_code(code):
            return
        self._state = AlarmControlPanelState.ARMED_AWAY
        await self.async_save_state()
        self.async_write_ha_state()
        self.fire_template_event("arm_away", state=self._state.value)

    async def async_alarm_arm_night(self, code: str | None = None) -> None:
        if not self._supports_arm_night or not self._validate_code(code):
            return
        self._state = AlarmControlPanelState.ARMED_NIGHT
        await self.async_save_state()
        self.async_write_ha_state()
        self.fire_template_event("arm_night", state=self._state.value)

    async def async_alarm_arm_vacation(self, code: str | None = None) -> None:
        if not self._supports_arm_vacation or not self._validate_code(code):
            return
        self._state = AlarmControlPanelState.ARMED_VACATION
        await self.async_save_state()
        self.async_write_ha_state()
        self.fire_template_event("arm_vacation", state=self._state.value)

    async def async_alarm_trigger(self, code: str | None = None) -> None:
        self._state = AlarmControlPanelState.TRIGGERED
        await self.async_save_state()
        self.async_write_ha_state()
        self.fire_template_event("trigger", state=self._state.value)
