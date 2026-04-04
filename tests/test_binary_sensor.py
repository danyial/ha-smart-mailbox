"""Tests for the binary_sensor platform (core trigger logic)."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from custom_components.smartmailbox.const import (
    DOMAIN,
    CONF_FLAP_ENTITY,
    CONF_DOOR_ENTITY,
    CONF_NOTIFY_ENABLED,
    CONF_NOTIFY_SERVICE,
    CONF_DOOR_NOTIFY_ENABLED,
    CONF_DOOR_NOTIFY_SERVICE,
    CONF_RESET_ON_EMPTY,
    CONF_FLAP_TRIGGER_MODE,
    CONF_DOOR_TRIGGER_MODE,
    CONF_FLAP_THRESHOLD,
    CONF_FLAP_THRESHOLD_DIRECTION,
    CONF_DOOR_THRESHOLD,
    CONF_DOOR_THRESHOLD_DIRECTION,
    TRIGGER_MODE_THRESHOLD,
    THRESHOLD_DIRECTION_ABOVE,
    THRESHOLD_DIRECTION_BELOW,
)
from custom_components.smartmailbox.binary_sensor import (
    _is_triggered_threshold,
    _parse_float,
)

from .conftest import setup_integration


# ---------------------------------------------------------------------------
# Unit tests for helper functions
# ---------------------------------------------------------------------------


class TestParseFloat:
    def test_valid_float(self):
        assert _parse_float("3.14") == 3.14

    def test_valid_int_string(self):
        assert _parse_float("42") == 42.0

    def test_invalid_string(self):
        assert _parse_float("abc") is None

    def test_unavailable(self):
        assert _parse_float("unavailable") is None

    def test_none(self):
        assert _parse_float(None) is None


class TestIsTriggeredThreshold:
    """Unit tests for edge-detection logic."""

    def test_above_crossing(self):
        assert _is_triggered_threshold(35.0, 10.0, 30.0, "above") is True

    def test_above_already_above(self):
        assert _is_triggered_threshold(40.0, 35.0, 30.0, "above") is False

    def test_above_still_below(self):
        assert _is_triggered_threshold(20.0, 10.0, 30.0, "above") is False

    def test_above_exact_threshold(self):
        assert _is_triggered_threshold(30.0, 29.0, 30.0, "above") is True

    def test_above_old_none(self):
        assert _is_triggered_threshold(35.0, None, 30.0, "above") is True

    def test_below_crossing(self):
        assert _is_triggered_threshold(25.0, 35.0, 30.0, "below") is True

    def test_below_already_below(self):
        assert _is_triggered_threshold(20.0, 25.0, 30.0, "below") is False

    def test_below_still_above(self):
        assert _is_triggered_threshold(35.0, 40.0, 30.0, "below") is False

    def test_below_exact_threshold(self):
        assert _is_triggered_threshold(30.0, 31.0, 30.0, "below") is True

    def test_below_old_none(self):
        assert _is_triggered_threshold(25.0, None, 30.0, "below") is True


# ---------------------------------------------------------------------------
# Integration tests — binary trigger mode
# ---------------------------------------------------------------------------


class TestBinaryTriggerMode:
    """Test flap/door triggers with binary_sensor entities."""

    async def test_flap_on_triggers_delivery(
        self, hass: HomeAssistant, mock_config_entry_binary
    ):
        await setup_integration(hass, mock_config_entry_binary)
        state = hass.data[DOMAIN][mock_config_entry_binary.entry_id]["state"]

        assert state.post_present is False
        assert state.counter == 0

        hass.states.async_set("binary_sensor.flap", "on")
        await hass.async_block_till_done()

        assert state.post_present is True
        assert state.counter == 1
        assert state.last_delivery is not None

    async def test_flap_off_does_not_trigger(
        self, hass: HomeAssistant, mock_config_entry_binary
    ):
        await setup_integration(hass, mock_config_entry_binary)
        state = hass.data[DOMAIN][mock_config_entry_binary.entry_id]["state"]

        # First set on, then off
        hass.states.async_set("binary_sensor.flap", "on")
        await hass.async_block_till_done()
        counter_after_on = state.counter

        hass.states.async_set("binary_sensor.flap", "off")
        await hass.async_block_till_done()

        assert state.counter == counter_after_on  # no increment on off

    async def test_door_on_triggers_empty(
        self, hass: HomeAssistant, mock_config_entry_binary
    ):
        await setup_integration(hass, mock_config_entry_binary)
        state = hass.data[DOMAIN][mock_config_entry_binary.entry_id]["state"]

        # First deliver mail
        hass.states.async_set("binary_sensor.flap", "on")
        await hass.async_block_till_done()
        assert state.post_present is True

        # Reset flap so door can trigger cleanly
        hass.states.async_set("binary_sensor.flap", "off")
        await hass.async_block_till_done()

        # Open door
        hass.states.async_set("binary_sensor.door", "on")
        await hass.async_block_till_done()

        assert state.post_present is False
        assert state.last_empty is not None

    async def test_door_off_does_not_trigger(
        self, hass: HomeAssistant, mock_config_entry_binary
    ):
        await setup_integration(hass, mock_config_entry_binary)
        state = hass.data[DOMAIN][mock_config_entry_binary.entry_id]["state"]

        # Deliver mail first
        hass.states.async_set("binary_sensor.flap", "on")
        await hass.async_block_till_done()
        assert state.post_present is True

        # door off->off shouldn't trigger
        hass.states.async_set("binary_sensor.door", "off")
        await hass.async_block_till_done()

        assert state.post_present is True  # still present


# ---------------------------------------------------------------------------
# Integration tests — threshold trigger mode
# ---------------------------------------------------------------------------


class TestThresholdTriggerMode:
    """Test flap/door triggers with numeric sensor entities."""

    async def test_threshold_above_triggers_on_crossing(
        self, hass: HomeAssistant, mock_config_entry_threshold
    ):
        await setup_integration(hass, mock_config_entry_threshold)
        state = hass.data[DOMAIN][mock_config_entry_threshold.entry_id]["state"]

        # Set to 10 first (below threshold of 30)
        hass.states.async_set("sensor.flap_angle", "10")
        await hass.async_block_till_done()

        # Cross threshold
        hass.states.async_set("sensor.flap_angle", "35")
        await hass.async_block_till_done()

        assert state.post_present is True
        assert state.counter == 1

    async def test_threshold_above_no_trigger_already_above(
        self, hass: HomeAssistant, mock_config_entry_threshold
    ):
        await setup_integration(hass, mock_config_entry_threshold)
        state = hass.data[DOMAIN][mock_config_entry_threshold.entry_id]["state"]

        # Cross threshold first
        hass.states.async_set("sensor.flap_angle", "10")
        await hass.async_block_till_done()
        hass.states.async_set("sensor.flap_angle", "35")
        await hass.async_block_till_done()
        assert state.counter == 1

        # Wait for debounce
        now = dt_util.utcnow() + timedelta(seconds=5)
        with patch(
            "custom_components.smartmailbox.binary_sensor.dt_util.utcnow",
            return_value=now,
        ):
            hass.states.async_set("sensor.flap_angle", "40")
            await hass.async_block_till_done()

        # 35 -> 40: both above threshold, no edge crossing
        assert state.counter == 1

    async def test_threshold_above_no_trigger_below(
        self, hass: HomeAssistant, mock_config_entry_threshold
    ):
        await setup_integration(hass, mock_config_entry_threshold)
        state = hass.data[DOMAIN][mock_config_entry_threshold.entry_id]["state"]

        hass.states.async_set("sensor.flap_angle", "10")
        await hass.async_block_till_done()
        hass.states.async_set("sensor.flap_angle", "20")
        await hass.async_block_till_done()

        assert state.post_present is False
        assert state.counter == 0

    async def test_threshold_non_numeric_ignored(
        self, hass: HomeAssistant, mock_config_entry_threshold
    ):
        await setup_integration(hass, mock_config_entry_threshold)
        state = hass.data[DOMAIN][mock_config_entry_threshold.entry_id]["state"]

        hass.states.async_set("sensor.flap_angle", "10")
        await hass.async_block_till_done()
        hass.states.async_set("sensor.flap_angle", "abc")
        await hass.async_block_till_done()

        assert state.counter == 0

    async def test_mixed_mode_binary_flap_threshold_door(
        self, hass: HomeAssistant, mock_config_entry_mixed
    ):
        """Issue #1 use case: binary flap + angle door."""
        await setup_integration(hass, mock_config_entry_mixed)
        state = hass.data[DOMAIN][mock_config_entry_mixed.entry_id]["state"]

        # Binary flap triggers delivery
        hass.states.async_set("binary_sensor.flap", "on")
        await hass.async_block_till_done()
        assert state.post_present is True
        assert state.counter == 1

        hass.states.async_set("binary_sensor.flap", "off")
        await hass.async_block_till_done()

        # Threshold door triggers empty
        hass.states.async_set("sensor.door_angle", "10")
        await hass.async_block_till_done()
        hass.states.async_set("sensor.door_angle", "35")
        await hass.async_block_till_done()

        assert state.post_present is False
        assert state.last_empty is not None


# ---------------------------------------------------------------------------
# Startup guard tests
# ---------------------------------------------------------------------------


class TestStartupGuard:
    async def test_ignores_unavailable_to_on(
        self, hass: HomeAssistant, mock_config_entry_binary
    ):
        await setup_integration(hass, mock_config_entry_binary)
        state = hass.data[DOMAIN][mock_config_entry_binary.entry_id]["state"]

        # Simulate startup: unavailable -> on
        hass.states.async_set("binary_sensor.flap", "unavailable")
        await hass.async_block_till_done()
        hass.states.async_set("binary_sensor.flap", "on")
        await hass.async_block_till_done()

        assert state.post_present is False
        assert state.counter == 0

    async def test_ignores_unknown_to_on(
        self, hass: HomeAssistant, mock_config_entry_binary
    ):
        await setup_integration(hass, mock_config_entry_binary)
        state = hass.data[DOMAIN][mock_config_entry_binary.entry_id]["state"]

        hass.states.async_set("binary_sensor.flap", "unknown")
        await hass.async_block_till_done()
        hass.states.async_set("binary_sensor.flap", "on")
        await hass.async_block_till_done()

        assert state.post_present is False
        assert state.counter == 0

    async def test_ignores_transition_to_unavailable(
        self, hass: HomeAssistant, mock_config_entry_binary
    ):
        await setup_integration(hass, mock_config_entry_binary)
        state = hass.data[DOMAIN][mock_config_entry_binary.entry_id]["state"]

        # Normal off, then goes unavailable
        hass.states.async_set("binary_sensor.flap", "unavailable")
        await hass.async_block_till_done()

        assert state.post_present is False


# ---------------------------------------------------------------------------
# Debounce tests
# ---------------------------------------------------------------------------


class TestDebounce:
    async def test_debounce_blocks_rapid_flap(
        self, hass: HomeAssistant, mock_config_entry_binary
    ):
        await setup_integration(hass, mock_config_entry_binary)
        state = hass.data[DOMAIN][mock_config_entry_binary.entry_id]["state"]

        hass.states.async_set("binary_sensor.flap", "on")
        await hass.async_block_till_done()
        assert state.counter == 1

        # Quick off-on within debounce
        hass.states.async_set("binary_sensor.flap", "off")
        await hass.async_block_till_done()
        hass.states.async_set("binary_sensor.flap", "on")
        await hass.async_block_till_done()

        assert state.counter == 1  # blocked by debounce

    async def test_debounce_allows_after_interval(
        self, hass: HomeAssistant, mock_config_entry_binary
    ):
        await setup_integration(hass, mock_config_entry_binary)
        state = hass.data[DOMAIN][mock_config_entry_binary.entry_id]["state"]

        hass.states.async_set("binary_sensor.flap", "on")
        await hass.async_block_till_done()
        assert state.counter == 1

        hass.states.async_set("binary_sensor.flap", "off")
        await hass.async_block_till_done()

        # Advance time past debounce
        future = dt_util.utcnow() + timedelta(seconds=5)
        with patch(
            "custom_components.smartmailbox.binary_sensor.dt_util.utcnow",
            return_value=future,
        ):
            hass.states.async_set("binary_sensor.flap", "on")
            await hass.async_block_till_done()

        assert state.counter == 2


# ---------------------------------------------------------------------------
# Notification tests
# ---------------------------------------------------------------------------


class TestNotifications:
    def _notify_entry(self, **overrides) -> MockConfigEntry:
        """Create a config entry with notifications enabled."""
        from pytest_homeassistant_custom_component.common import MockConfigEntry as MCE

        data = {
            CONF_FLAP_ENTITY: "binary_sensor.flap",
            CONF_DOOR_ENTITY: "binary_sensor.door",
            "name": "Test Mailbox",
            "debounce_seconds": 3,
            CONF_NOTIFY_ENABLED: True,
            CONF_NOTIFY_SERVICE: ["notify.test"],
            CONF_FLAP_TRIGGER_MODE: "binary",
            CONF_DOOR_TRIGGER_MODE: "binary",
        }
        data.update(overrides)
        return MCE(domain=DOMAIN, version=2, data=data, title="Test Mailbox")

    async def test_notification_sent_on_first_delivery(self, hass: HomeAssistant):
        entry = self._notify_entry()
        calls = []

        async def mock_notify(call):
            calls.append(call)

        hass.services.async_register("notify", "test", mock_notify)
        await setup_integration(hass, entry)

        hass.states.async_set("binary_sensor.flap", "on")
        await hass.async_block_till_done()

        assert len(calls) == 1

    async def test_notification_not_repeated_while_post_present(
        self, hass: HomeAssistant
    ):
        entry = self._notify_entry()
        calls = []

        async def mock_notify(call):
            calls.append(call)

        hass.services.async_register("notify", "test", mock_notify)
        await setup_integration(hass, entry)

        # First delivery
        hass.states.async_set("binary_sensor.flap", "on")
        await hass.async_block_till_done()

        hass.states.async_set("binary_sensor.flap", "off")
        await hass.async_block_till_done()

        # Second delivery (within same post period) — advance past debounce
        future = dt_util.utcnow() + timedelta(seconds=5)
        with patch(
            "custom_components.smartmailbox.binary_sensor.dt_util.utcnow",
            return_value=future,
        ):
            hass.states.async_set("binary_sensor.flap", "on")
            await hass.async_block_till_done()

        # Only 1 notification, not 2
        assert len(calls) == 1

    async def test_notification_resets_after_empty(self, hass: HomeAssistant):
        entry = self._notify_entry()
        calls = []

        async def mock_notify(call):
            calls.append(call)

        hass.services.async_register("notify", "test", mock_notify)
        await setup_integration(hass, entry)

        # First delivery
        hass.states.async_set("binary_sensor.flap", "on")
        await hass.async_block_till_done()
        assert len(calls) == 1

        hass.states.async_set("binary_sensor.flap", "off")
        await hass.async_block_till_done()

        # Empty mailbox
        hass.states.async_set("binary_sensor.door", "on")
        await hass.async_block_till_done()

        hass.states.async_set("binary_sensor.door", "off")
        await hass.async_block_till_done()

        # New delivery after emptying
        future = dt_util.utcnow() + timedelta(seconds=5)
        with patch(
            "custom_components.smartmailbox.binary_sensor.dt_util.utcnow",
            return_value=future,
        ):
            hass.states.async_set("binary_sensor.flap", "on")
            await hass.async_block_till_done()

        assert len(calls) == 2  # second notification sent

    async def test_door_notification_sent(self, hass: HomeAssistant):
        entry = self._notify_entry(
            **{
                CONF_NOTIFY_ENABLED: False,
                CONF_NOTIFY_SERVICE: [],
                CONF_DOOR_NOTIFY_ENABLED: True,
                CONF_DOOR_NOTIFY_SERVICE: ["notify.test"],
            }
        )
        calls = []

        async def mock_notify(call):
            calls.append(call)

        hass.services.async_register("notify", "test", mock_notify)
        await setup_integration(hass, entry)

        hass.states.async_set("binary_sensor.door", "on")
        await hass.async_block_till_done()

        assert len(calls) == 1


# ---------------------------------------------------------------------------
# Counter tests
# ---------------------------------------------------------------------------


class TestCounter:
    async def test_counter_resets_on_empty_when_configured(self, hass: HomeAssistant):
        from pytest_homeassistant_custom_component.common import MockConfigEntry as MCE

        entry = MCE(
            domain=DOMAIN,
            version=2,
            data={
                CONF_FLAP_ENTITY: "binary_sensor.flap",
                CONF_DOOR_ENTITY: "binary_sensor.door",
                "name": "Test Mailbox",
                "debounce_seconds": 3,
                CONF_NOTIFY_ENABLED: False,
                CONF_NOTIFY_SERVICE: [],
                CONF_FLAP_TRIGGER_MODE: "binary",
                CONF_DOOR_TRIGGER_MODE: "binary",
                CONF_RESET_ON_EMPTY: True,
            },
            title="Test Mailbox",
        )
        await setup_integration(hass, entry)
        state = hass.data[DOMAIN][entry.entry_id]["state"]

        # Deliver twice
        hass.states.async_set("binary_sensor.flap", "on")
        await hass.async_block_till_done()

        hass.states.async_set("binary_sensor.flap", "off")
        await hass.async_block_till_done()

        future = dt_util.utcnow() + timedelta(seconds=5)
        with patch(
            "custom_components.smartmailbox.binary_sensor.dt_util.utcnow",
            return_value=future,
        ):
            hass.states.async_set("binary_sensor.flap", "on")
            await hass.async_block_till_done()

        assert state.counter == 2

        hass.states.async_set("binary_sensor.flap", "off")
        await hass.async_block_till_done()

        # Empty
        later = dt_util.utcnow() + timedelta(seconds=10)
        with patch(
            "custom_components.smartmailbox.binary_sensor.dt_util.utcnow",
            return_value=later,
        ):
            hass.states.async_set("binary_sensor.door", "on")
            await hass.async_block_till_done()

        assert state.counter == 0

    async def test_counter_not_reset_when_not_configured(
        self, hass: HomeAssistant, mock_config_entry_binary
    ):
        # reset_on_empty defaults to False
        await setup_integration(hass, mock_config_entry_binary)
        state = hass.data[DOMAIN][mock_config_entry_binary.entry_id]["state"]

        hass.states.async_set("binary_sensor.flap", "on")
        await hass.async_block_till_done()
        assert state.counter == 1

        hass.states.async_set("binary_sensor.flap", "off")
        await hass.async_block_till_done()

        hass.states.async_set("binary_sensor.door", "on")
        await hass.async_block_till_done()

        assert state.counter == 1  # not reset
