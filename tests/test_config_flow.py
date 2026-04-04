"""Tests for the config flow and options flow."""

from __future__ import annotations

import pytest
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.smartmailbox.const import (
    DOMAIN,
    CONF_NAME,
    CONF_FLAP_ENTITY,
    CONF_DOOR_ENTITY,
    CONF_DEBOUNCE_SECONDS,
    CONF_NOTIFY_ENABLED,
    CONF_NOTIFY_SERVICE,
    CONF_FLAP_TRIGGER_MODE,
    CONF_DOOR_TRIGGER_MODE,
    CONF_FLAP_THRESHOLD,
    CONF_FLAP_THRESHOLD_DIRECTION,
    CONF_DOOR_THRESHOLD,
    CONF_DOOR_THRESHOLD_DIRECTION,
    CONF_ENABLE_COUNTER,
    CONF_ENABLE_AGE,
    CONF_AGE_UNIT,
    CONF_RESET_ON_EMPTY,
    TRIGGER_MODE_BINARY,
    TRIGGER_MODE_THRESHOLD,
    THRESHOLD_DIRECTION_ABOVE,
)
from custom_components.smartmailbox.config_flow import _is_non_binary

from .conftest import setup_integration


# ---------------------------------------------------------------------------
# Helper function tests
# ---------------------------------------------------------------------------


class TestIsNonBinary:
    def test_sensor_entity(self):
        assert _is_non_binary(None, "sensor.angle") is True

    def test_binary_sensor_entity(self):
        assert _is_non_binary(None, "binary_sensor.flap") is False

    def test_empty_string(self):
        assert _is_non_binary(None, "") is False

    def test_other_domain(self):
        assert _is_non_binary(None, "input_number.test") is True


# ---------------------------------------------------------------------------
# Config flow — user step
# ---------------------------------------------------------------------------


class TestConfigFlowUserStep:
    async def test_shows_form(self, hass: HomeAssistant):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "user"

    async def test_binary_sensors_create_entry_directly(self, hass: HomeAssistant):
        """Both binary_sensor entities → skip step 2, create entry."""
        hass.states.async_set("binary_sensor.flap", "off")
        hass.states.async_set("binary_sensor.door", "off")

        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_NAME: "My Mailbox",
                CONF_FLAP_ENTITY: "binary_sensor.flap",
                CONF_DOOR_ENTITY: "binary_sensor.door",
                CONF_DEBOUNCE_SECONDS: 3,
                CONF_NOTIFY_ENABLED: False,
                CONF_NOTIFY_SERVICE: [],
            },
        )

        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert result["data"][CONF_FLAP_TRIGGER_MODE] == TRIGGER_MODE_BINARY
        assert result["data"][CONF_DOOR_TRIGGER_MODE] == TRIGGER_MODE_BINARY

    async def test_numeric_sensor_goes_to_triggers_step(self, hass: HomeAssistant):
        """Non-binary sensor entity → shows step 2."""
        hass.states.async_set("sensor.flap_angle", "0")
        hass.states.async_set("binary_sensor.door", "off")

        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_NAME: "My Mailbox",
                CONF_FLAP_ENTITY: "sensor.flap_angle",
                CONF_DOOR_ENTITY: "binary_sensor.door",
                CONF_DEBOUNCE_SECONDS: 3,
                CONF_NOTIFY_ENABLED: False,
                CONF_NOTIFY_SERVICE: [],
            },
        )

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "triggers"

    async def test_duplicate_aborts(self, hass: HomeAssistant):
        """Same sensor pair → already_configured."""
        hass.states.async_set("binary_sensor.flap", "off")
        hass.states.async_set("binary_sensor.door", "off")

        # Create first entry
        existing = MockConfigEntry(
            domain=DOMAIN,
            version=2,
            unique_id="binary_sensor.flap_binary_sensor.door",
            data={
                CONF_NAME: "Existing",
                CONF_FLAP_ENTITY: "binary_sensor.flap",
                CONF_DOOR_ENTITY: "binary_sensor.door",
                CONF_DEBOUNCE_SECONDS: 3,
                CONF_NOTIFY_ENABLED: False,
                CONF_NOTIFY_SERVICE: [],
                CONF_FLAP_TRIGGER_MODE: TRIGGER_MODE_BINARY,
                CONF_DOOR_TRIGGER_MODE: TRIGGER_MODE_BINARY,
            },
        )
        existing.add_to_hass(hass)

        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_NAME: "Duplicate",
                CONF_FLAP_ENTITY: "binary_sensor.flap",
                CONF_DOOR_ENTITY: "binary_sensor.door",
                CONF_DEBOUNCE_SECONDS: 3,
                CONF_NOTIFY_ENABLED: False,
                CONF_NOTIFY_SERVICE: [],
            },
        )

        assert result["type"] == FlowResultType.ABORT
        assert result["reason"] == "already_configured"


# ---------------------------------------------------------------------------
# Config flow — triggers step
# ---------------------------------------------------------------------------


class TestConfigFlowTriggersStep:
    async def test_triggers_step_creates_entry(self, hass: HomeAssistant):
        """Complete the two-step flow for a numeric sensor."""
        hass.states.async_set("sensor.flap_angle", "0")
        hass.states.async_set("binary_sensor.door", "off")

        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_NAME: "Angle Mailbox",
                CONF_FLAP_ENTITY: "sensor.flap_angle",
                CONF_DOOR_ENTITY: "binary_sensor.door",
                CONF_DEBOUNCE_SECONDS: 3,
                CONF_NOTIFY_ENABLED: False,
                CONF_NOTIFY_SERVICE: [],
            },
        )
        assert result["step_id"] == "triggers"

        # Complete step 2
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_FLAP_THRESHOLD: 30.0,
                CONF_FLAP_THRESHOLD_DIRECTION: THRESHOLD_DIRECTION_ABOVE,
            },
        )

        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert result["data"][CONF_FLAP_TRIGGER_MODE] == TRIGGER_MODE_THRESHOLD
        assert result["data"][CONF_DOOR_TRIGGER_MODE] == TRIGGER_MODE_BINARY
        assert result["data"][CONF_FLAP_THRESHOLD] == 30.0

    async def test_triggers_step_both_numeric(self, hass: HomeAssistant):
        """Both sensors numeric → both threshold fields shown."""
        hass.states.async_set("sensor.flap_angle", "0")
        hass.states.async_set("sensor.door_angle", "0")

        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_NAME: "Full Angle",
                CONF_FLAP_ENTITY: "sensor.flap_angle",
                CONF_DOOR_ENTITY: "sensor.door_angle",
                CONF_DEBOUNCE_SECONDS: 3,
                CONF_NOTIFY_ENABLED: False,
                CONF_NOTIFY_SERVICE: [],
            },
        )
        assert result["step_id"] == "triggers"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_FLAP_THRESHOLD: 25.0,
                CONF_FLAP_THRESHOLD_DIRECTION: THRESHOLD_DIRECTION_ABOVE,
                CONF_DOOR_THRESHOLD: 40.0,
                CONF_DOOR_THRESHOLD_DIRECTION: THRESHOLD_DIRECTION_ABOVE,
            },
        )

        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert result["data"][CONF_FLAP_THRESHOLD] == 25.0
        assert result["data"][CONF_DOOR_THRESHOLD] == 40.0


# ---------------------------------------------------------------------------
# Options flow
# ---------------------------------------------------------------------------


class TestOptionsFlow:
    async def test_options_shows_form(
        self, hass: HomeAssistant, mock_config_entry_binary
    ):
        await setup_integration(hass, mock_config_entry_binary)

        result = await hass.config_entries.options.async_init(
            mock_config_entry_binary.entry_id
        )

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "init"

    async def test_options_saves_changes(
        self, hass: HomeAssistant, mock_config_entry_binary
    ):
        await setup_integration(hass, mock_config_entry_binary)

        result = await hass.config_entries.options.async_init(
            mock_config_entry_binary.entry_id
        )
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            user_input={
                CONF_ENABLE_COUNTER: False,
                CONF_ENABLE_AGE: True,
                CONF_AGE_UNIT: "days",
                CONF_RESET_ON_EMPTY: True,
                CONF_DEBOUNCE_SECONDS: 5,
                CONF_NOTIFY_ENABLED: False,
                CONF_NOTIFY_SERVICE: [],
                "notify_message": "",
                "door_notify": False,
                "door_notify_service": [],
                "door_notify_message": "",
                CONF_FLAP_ENTITY: "binary_sensor.flap",
                CONF_DOOR_ENTITY: "binary_sensor.door",
            },
        )

        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert result["data"][CONF_ENABLE_COUNTER] is False
        assert result["data"][CONF_AGE_UNIT] == "days"
        assert result["data"][CONF_RESET_ON_EMPTY] is True

    async def test_options_derives_trigger_mode_from_entity(
        self, hass: HomeAssistant, mock_config_entry_binary
    ):
        """Changing entity to sensor.* auto-sets threshold mode in saved data."""
        await setup_integration(hass, mock_config_entry_binary)

        hass.states.async_set("sensor.new_door", "0")

        # The options schema is built based on the current (old) entities,
        # so threshold fields aren't in the schema yet. The trigger mode
        # is derived from the entity_id on submit.
        result = await hass.config_entries.options.async_init(
            mock_config_entry_binary.entry_id
        )
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            user_input={
                CONF_ENABLE_COUNTER: True,
                CONF_ENABLE_AGE: True,
                CONF_AGE_UNIT: "hours",
                CONF_RESET_ON_EMPTY: False,
                CONF_DEBOUNCE_SECONDS: 3,
                CONF_NOTIFY_ENABLED: False,
                CONF_NOTIFY_SERVICE: [],
                "notify_message": "",
                "door_notify": False,
                "door_notify_service": [],
                "door_notify_message": "",
                CONF_FLAP_ENTITY: "binary_sensor.flap",
                CONF_DOOR_ENTITY: "sensor.new_door",
            },
        )

        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert result["data"][CONF_FLAP_TRIGGER_MODE] == TRIGGER_MODE_BINARY
        assert result["data"][CONF_DOOR_TRIGGER_MODE] == TRIGGER_MODE_THRESHOLD
