"""Tests for sensor entities."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

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
    CONF_ENABLE_COUNTER,
    CONF_ENABLE_AGE,
    CONF_AGE_UNIT,
    TRIGGER_MODE_BINARY,
)

from .conftest import setup_integration


# ---------------------------------------------------------------------------
# Sensor value tests
# ---------------------------------------------------------------------------


class TestLastDeliverySensor:
    async def test_value_after_delivery(
        self, hass: HomeAssistant, mock_config_entry_binary
    ):
        await setup_integration(hass, mock_config_entry_binary)

        # Trigger a delivery
        hass.states.async_set("binary_sensor.flap", "on")
        await hass.async_block_till_done()
        # Extra block for schedule_update_ha_state callback
        await hass.async_block_till_done()

        entity_state = hass.states.get("sensor.test_mailbox_last_delivery")
        assert entity_state is not None
        assert entity_state.state != "unknown"

    async def test_value_none_when_no_delivery(
        self, hass: HomeAssistant, mock_config_entry_binary
    ):
        await setup_integration(hass, mock_config_entry_binary)

        entity_state = hass.states.get("sensor.test_mailbox_last_delivery")
        assert entity_state is not None
        assert entity_state.state == "unknown"


class TestLastEmptiedSensor:
    async def test_value_after_empty(
        self, hass: HomeAssistant, mock_config_entry_binary
    ):
        await setup_integration(hass, mock_config_entry_binary)

        hass.states.async_set("binary_sensor.door", "on")
        await hass.async_block_till_done()
        await hass.async_block_till_done()

        entity_state = hass.states.get("sensor.test_mailbox_last_emptied")
        assert entity_state is not None
        assert entity_state.state != "unknown"


class TestDeliveryCounterSensor:
    async def test_counter_value(self, hass: HomeAssistant, mock_config_entry_binary):
        await setup_integration(hass, mock_config_entry_binary)

        hass.states.async_set("binary_sensor.flap", "on")
        await hass.async_block_till_done()
        await hass.async_block_till_done()

        entity_state = hass.states.get("sensor.test_mailbox_delivery_counter")
        assert entity_state is not None
        assert entity_state.state == "1"

    async def test_counter_not_created_when_disabled(self, hass: HomeAssistant):
        entry = MockConfigEntry(
            domain=DOMAIN,
            version=2,
            data={
                CONF_NAME: "No Counter",
                CONF_FLAP_ENTITY: "binary_sensor.flap",
                CONF_DOOR_ENTITY: "binary_sensor.door",
                CONF_DEBOUNCE_SECONDS: 3,
                CONF_NOTIFY_ENABLED: False,
                CONF_NOTIFY_SERVICE: [],
                CONF_FLAP_TRIGGER_MODE: TRIGGER_MODE_BINARY,
                CONF_DOOR_TRIGGER_MODE: TRIGGER_MODE_BINARY,
                CONF_ENABLE_COUNTER: False,
            },
            title="No Counter",
        )
        hass.states.async_set("binary_sensor.flap", "off")
        hass.states.async_set("binary_sensor.door", "off")
        entry.add_to_hass(hass)
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        entity_state = hass.states.get(f"sensor.no_counter_delivery_counter")
        assert entity_state is None


class TestMailAgeSensor:
    async def test_age_hours(self, hass: HomeAssistant, mock_config_entry_binary):
        await setup_integration(hass, mock_config_entry_binary)
        state_ref = hass.data[DOMAIN][mock_config_entry_binary.entry_id]["state"]

        # Simulate a delivery 2 hours ago
        two_hours_ago = dt_util.utcnow() - timedelta(hours=2)
        state_ref.post_present = True
        state_ref.last_delivery = two_hours_ago

        # Force update via time interval
        async_fire_time_changed(hass, dt_util.utcnow() + timedelta(minutes=1))
        await hass.async_block_till_done()

        entity_state = hass.states.get(f"sensor.test_mailbox_mail_age")
        assert entity_state is not None
        # Should be approximately 2.0 hours
        value = float(entity_state.state)
        assert 1.9 <= value <= 2.2
        assert entity_state.attributes.get("unit_of_measurement") == "h"

    async def test_age_days(self, hass: HomeAssistant):
        entry = MockConfigEntry(
            domain=DOMAIN,
            version=2,
            data={
                CONF_NAME: "Days Mailbox",
                CONF_FLAP_ENTITY: "binary_sensor.flap",
                CONF_DOOR_ENTITY: "binary_sensor.door",
                CONF_DEBOUNCE_SECONDS: 3,
                CONF_NOTIFY_ENABLED: False,
                CONF_NOTIFY_SERVICE: [],
                CONF_FLAP_TRIGGER_MODE: TRIGGER_MODE_BINARY,
                CONF_DOOR_TRIGGER_MODE: TRIGGER_MODE_BINARY,
                CONF_AGE_UNIT: "days",
            },
            title="Days Mailbox",
        )
        hass.states.async_set("binary_sensor.flap", "off")
        hass.states.async_set("binary_sensor.door", "off")
        entry.add_to_hass(hass)
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        state_ref = hass.data[DOMAIN][entry.entry_id]["state"]
        state_ref.post_present = True
        state_ref.last_delivery = dt_util.utcnow() - timedelta(days=2)

        async_fire_time_changed(hass, dt_util.utcnow() + timedelta(minutes=1))
        await hass.async_block_till_done()

        entity_state = hass.states.get("sensor.days_mailbox_mail_age")
        assert entity_state is not None
        value = float(entity_state.state)
        assert 1.9 <= value <= 2.1
        assert entity_state.attributes.get("unit_of_measurement") == "d"

    async def test_age_none_when_no_post(
        self, hass: HomeAssistant, mock_config_entry_binary
    ):
        await setup_integration(hass, mock_config_entry_binary)
        state_ref = hass.data[DOMAIN][mock_config_entry_binary.entry_id]["state"]

        assert state_ref.post_present is False

        entity_state = hass.states.get(f"sensor.test_mailbox_mail_age")
        assert entity_state is not None
        assert entity_state.state == "unknown"

    async def test_age_not_created_when_disabled(self, hass: HomeAssistant):
        entry = MockConfigEntry(
            domain=DOMAIN,
            version=2,
            data={
                CONF_NAME: "No Age",
                CONF_FLAP_ENTITY: "binary_sensor.flap",
                CONF_DOOR_ENTITY: "binary_sensor.door",
                CONF_DEBOUNCE_SECONDS: 3,
                CONF_NOTIFY_ENABLED: False,
                CONF_NOTIFY_SERVICE: [],
                CONF_FLAP_TRIGGER_MODE: TRIGGER_MODE_BINARY,
                CONF_DOOR_TRIGGER_MODE: TRIGGER_MODE_BINARY,
                CONF_ENABLE_AGE: False,
            },
            title="No Age",
        )
        hass.states.async_set("binary_sensor.flap", "off")
        hass.states.async_set("binary_sensor.door", "off")
        entry.add_to_hass(hass)
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        entity_state = hass.states.get("sensor.no_age_mail_age")
        assert entity_state is None


# ---------------------------------------------------------------------------
# Dispatcher tests
# ---------------------------------------------------------------------------


class TestDispatcher:
    async def test_dispatcher_triggers_sensor_update(
        self, hass: HomeAssistant, mock_config_entry_binary
    ):
        await setup_integration(hass, mock_config_entry_binary)

        # Trigger delivery via flap
        hass.states.async_set("binary_sensor.flap", "on")
        await hass.async_block_till_done()
        await hass.async_block_till_done()

        # Counter sensor should reflect the update
        entity_state = hass.states.get("sensor.test_mailbox_delivery_counter")
        assert entity_state is not None
        assert entity_state.state == "1"
