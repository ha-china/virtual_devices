"""Platform for virtual alarm control panel integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.alarm_control_panel import (
    AlarmControlPanelEntity,
    AlarmControlPanelEntityFeature,
    AlarmControlPanelState,
    CodeFormat,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_call_later

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
        self._attr_alarm_state: AlarmControlPanelState = AlarmControlPanelState.DISARMED
        self._pending_state: AlarmControlPanelState | None = None
        self._pending_timer_listener = None
        self._trigger_timer_listener = None
        # Alarm code & arming options
        # `_attr_code_arm_required` defaults to True on the base class.
        # `_attr_code_format` uses the `CodeFormat.NUMBER` enum; the base class
        # `code_format` cached_property reads `self._attr_code_format`.
        self._attr_code_format: CodeFormat | None = CodeFormat.NUMBER
        features = (
            AlarmControlPanelEntityFeature.ARM_HOME
            | AlarmControlPanelEntityFeature.ARM_AWAY
            | AlarmControlPanelEntityFeature.TRIGGER
            | AlarmControlPanelEntityFeature.ARM_CUSTOM_BYPASS
        )
        if self._supports_arm_night:
            features |= AlarmControlPanelEntityFeature.ARM_NIGHT
        if self._supports_arm_vacation:
            features |= AlarmControlPanelEntityFeature.ARM_VACATION
        self._attr_supported_features = features

    def get_default_state(self) -> AlarmControlPanelStateDict:
        return {"state": "disarmed", "pending_state": None}

    def apply_state(self, state: AlarmControlPanelStateDict) -> None:
        state_key = state.get("state", "disarmed")
        self._attr_alarm_state = AlarmControlPanelState(state_key)
        pending = state.get("pending_state")
        self._pending_state = AlarmControlPanelState(pending) if pending else None

    def get_current_state(self) -> AlarmControlPanelStateDict:
        return {"state": self._attr_alarm_state.value, "pending_state": self._pending_state.value if self._pending_state else None}

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "trigger_time": self._trigger_time,
            "supports_arm_night": self._supports_arm_night,
            "supports_arm_vacation": self._supports_arm_vacation,
            "available_states": list(ALARM_STATES.keys()),
            "pending_state": self._pending_state.value if self._pending_state else None,
        }

    def _validate_code(self, code: str | None) -> bool:
        return code == self._alarm_code

    async def async_alarm_disarm(self, code: str | None = None) -> None:
        if not self._validate_code(code):
            return
        self._cancel_pending_timer()
        self._cancel_trigger_timer()
        self._pending_state = None
        self._attr_alarm_state = AlarmControlPanelState.DISARMED
        await self.async_save_state()
        self.async_write_ha_state()
        self.fire_template_event("alarm_control_panel.disarm", state=self._attr_alarm_state.value)

    async def _arm_with_pending(self, target_state: AlarmControlPanelState) -> None:
        """Arm with a pending delay before actual arming."""
        self._cancel_pending_timer()
        self._pending_state = target_state
        self._attr_alarm_state = AlarmControlPanelState.PENDING
        self.async_write_ha_state()

        async def _finalize_arm(_now):
            self._pending_state = None
            self._pending_timer_listener = None
            self._attr_alarm_state = target_state
            await self.async_save_state()
            self.async_write_ha_state()
            self.fire_template_event("alarm_control_panel.arm", state=self._attr_alarm_state.value)

        self._pending_timer_listener = async_call_later(self.hass, 5, _finalize_arm)
        self.async_on_remove(lambda: self._cancel_pending_timer())

    async def async_alarm_arm_home(self, code: str | None = None) -> None:
        if not self._validate_code(code):
            return
        await self._arm_with_pending(AlarmControlPanelState.ARMED_HOME)

    async def async_alarm_arm_away(self, code: str | None = None) -> None:
        if not self._validate_code(code):
            return
        await self._arm_with_pending(AlarmControlPanelState.ARMED_AWAY)

    async def async_alarm_arm_night(self, code: str | None = None) -> None:
        if not self._supports_arm_night or not self._validate_code(code):
            return
        await self._arm_with_pending(AlarmControlPanelState.ARMED_NIGHT)

    async def async_alarm_arm_vacation(self, code: str | None = None) -> None:
        if not self._supports_arm_vacation or not self._validate_code(code):
            return
        await self._arm_with_pending(AlarmControlPanelState.ARMED_VACATION)

    async def async_alarm_arm_custom_bypass(self, code: str | None = None) -> None:
        """Arm custom bypass."""
        if not self._validate_code(code):
            return
        await self._arm_with_pending(AlarmControlPanelState.ARMED_CUSTOM_BYPASS)

    async def async_alarm_trigger(self, code: str | None = None) -> None:
        self._cancel_pending_timer()
        self._pending_state = None
        self._attr_alarm_state = AlarmControlPanelState.TRIGGERED
        await self.async_save_state()
        self.async_write_ha_state()
        self.fire_template_event("alarm_control_panel.trigger", state=self._attr_alarm_state.value)

        async def _auto_disarm(_now):
            self._trigger_timer_listener = None
            self._attr_alarm_state = AlarmControlPanelState.DISARMED
            await self.async_save_state()
            self.async_write_ha_state()
            self.fire_template_event("alarm_control_panel.disarm", state=self._attr_alarm_state.value)

        self._trigger_timer_listener = async_call_later(self.hass, self._trigger_time, _auto_disarm)
        self.async_on_remove(lambda: self._cancel_trigger_timer())

    def _cancel_pending_timer(self) -> None:
        """Cancel pending arm timer."""
        if self._pending_timer_listener is not None:
            self._pending_timer_listener()
            self._pending_timer_listener = None

    def _cancel_trigger_timer(self) -> None:
        """Cancel trigger auto-disarm timer."""
        if self._trigger_timer_listener is not None:
            self._trigger_timer_listener()
            self._trigger_timer_listener = None
