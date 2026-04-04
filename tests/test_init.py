"""Tests for __init__.py (setup, migration, services, storage)."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.smartmailbox import (
    MailboxState,
    _dt_to_iso,
    _iso_to_dt,
    async_migrate_entry,
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
    TRIGGER_MODE_BINARY,
    TRIGGER_MODE_THRESHOLD,
    SERVICE_RESET_COUNTER,
    SERVICE_MARK_EMPTY,
    SIGNAL_PREFIX,
    STORAGE_KEY_PREFIX,
)

from .conftest import setup_integration


# ---------------------------------------------------------------------------
# Helper function tests
# ---------------------------------------------------------------------------


class TestDtToIso:
    def test_with_datetime(self):
        dt = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        result = _dt_to_iso(dt)
        assert result == "2025-01-01T12:00:00+00:00"

    def test_with_none(self):
        assert _dt_to_iso(None) is None


class TestIsoToDt:
    def test_with_valid_iso(self):
        result = _iso_to_dt("2025-01-01T12:00:00+00:00")
        assert result is not None
        assert result.year == 2025
        assert result.tzinfo is not None

    def test_with_naive_datetime(self):
        result = _iso_to_dt("2025-01-01T12:00:00")
        assert result is not None
        assert result.tzinfo is not None  # should get UTC

    def test_with_none(self):
        assert _iso_to_dt(None) is None

    def test_with_empty_string(self):
        assert _iso_to_dt("") is None

    def test_with_garbage(self):
        assert _iso_to_dt("not-a-date") is None

    def test_roundtrip(self):
        original = dt_util.utcnow()
        iso = _dt_to_iso(original)
        restored = _iso_to_dt(iso)
        assert restored is not None
        # Allow small difference due to microsecond precision
        assert abs((original - restored).total_seconds()) < 1


# ---------------------------------------------------------------------------
# Migration tests
# ---------------------------------------------------------------------------


class TestMigration:
    async def test_migrate_v1_to_v2_binary_sensors(
        self, hass: HomeAssistant, mock_config_entry_v1
    ):
        mock_config_entry_v1.add_to_hass(hass)
        result = await async_migrate_entry(hass, mock_config_entry_v1)

        assert result is True
        assert mock_config_entry_v1.version == 2
        assert mock_config_entry_v1.data[CONF_FLAP_TRIGGER_MODE] == TRIGGER_MODE_BINARY
        assert mock_config_entry_v1.data[CONF_DOOR_TRIGGER_MODE] == TRIGGER_MODE_BINARY

    async def test_migrate_v1_to_v2_numeric_flap(self, hass: HomeAssistant):
        entry = MockConfigEntry(
            domain=DOMAIN,
            version=1,
            data={
                CONF_NAME: "Test",
                CONF_FLAP_ENTITY: "sensor.flap_angle",
                CONF_DOOR_ENTITY: "binary_sensor.door",
                CONF_DEBOUNCE_SECONDS: 3,
                CONF_NOTIFY_ENABLED: False,
                CONF_NOTIFY_SERVICE: [],
            },
            title="Test",
        )
        entry.add_to_hass(hass)
        result = await async_migrate_entry(hass, entry)

        assert result is True
        assert entry.data[CONF_FLAP_TRIGGER_MODE] == TRIGGER_MODE_THRESHOLD
        assert entry.data[CONF_DOOR_TRIGGER_MODE] == TRIGGER_MODE_BINARY

    async def test_migrate_v1_to_v2_empty_entity(self, hass: HomeAssistant):
        entry = MockConfigEntry(
            domain=DOMAIN,
            version=1,
            data={
                CONF_NAME: "Test",
                CONF_FLAP_ENTITY: "",
                CONF_DOOR_ENTITY: "",
                CONF_DEBOUNCE_SECONDS: 3,
                CONF_NOTIFY_ENABLED: False,
                CONF_NOTIFY_SERVICE: [],
            },
            title="Test",
        )
        entry.add_to_hass(hass)
        result = await async_migrate_entry(hass, entry)

        assert result is True
        # Empty string → defaults to binary
        assert entry.data[CONF_FLAP_TRIGGER_MODE] == TRIGGER_MODE_BINARY
        assert entry.data[CONF_DOOR_TRIGGER_MODE] == TRIGGER_MODE_BINARY


# ---------------------------------------------------------------------------
# Setup tests
# ---------------------------------------------------------------------------


class TestSetup:
    async def test_setup_entry_creates_state(
        self, hass: HomeAssistant, mock_config_entry_binary
    ):
        await setup_integration(hass, mock_config_entry_binary)

        entry_data = hass.data[DOMAIN][mock_config_entry_binary.entry_id]
        assert "state" in entry_data
        assert "save" in entry_data
        assert isinstance(entry_data["state"], MailboxState)

    async def test_setup_entry_default_state(
        self, hass: HomeAssistant, mock_config_entry_binary
    ):
        await setup_integration(hass, mock_config_entry_binary)
        state = hass.data[DOMAIN][mock_config_entry_binary.entry_id]["state"]

        assert state.post_present is False
        assert state.last_delivery is None
        assert state.last_empty is None
        assert state.counter == 0
        assert state.notified_for_current_post is False
        assert state.last_flap_trigger is None

    async def test_setup_entry_loads_persisted_state(
        self, hass: HomeAssistant, hass_storage, mock_config_entry_binary
    ):
        storage_key = f"{STORAGE_KEY_PREFIX}{mock_config_entry_binary.entry_id}"
        hass_storage[storage_key] = {
            "version": 1,
            "data": {
                "post_present": True,
                "last_delivery": "2025-01-01T12:00:00+00:00",
                "last_empty": None,
                "counter": 5,
                "notified_for_current_post": True,
                "last_flap_trigger": "2025-01-01T12:00:00+00:00",
            },
        }

        await setup_integration(hass, mock_config_entry_binary)
        state = hass.data[DOMAIN][mock_config_entry_binary.entry_id]["state"]

        assert state.post_present is True
        assert state.counter == 5
        assert state.last_delivery is not None
        assert state.notified_for_current_post is True


# ---------------------------------------------------------------------------
# Service tests
# ---------------------------------------------------------------------------


class TestServices:
    async def test_reset_counter_service(
        self, hass: HomeAssistant, mock_config_entry_binary
    ):
        await setup_integration(hass, mock_config_entry_binary)
        state = hass.data[DOMAIN][mock_config_entry_binary.entry_id]["state"]
        state.counter = 10

        await hass.services.async_call(DOMAIN, SERVICE_RESET_COUNTER, {}, blocking=True)
        await hass.async_block_till_done()

        assert state.counter == 0

    async def test_reset_counter_targets_specific_entry(self, hass: HomeAssistant):
        entry1 = MockConfigEntry(
            domain=DOMAIN,
            version=2,
            data={
                CONF_NAME: "Mailbox 1",
                CONF_FLAP_ENTITY: "binary_sensor.flap1",
                CONF_DOOR_ENTITY: "binary_sensor.door1",
                CONF_DEBOUNCE_SECONDS: 3,
                CONF_NOTIFY_ENABLED: False,
                CONF_NOTIFY_SERVICE: [],
                CONF_FLAP_TRIGGER_MODE: "binary",
                CONF_DOOR_TRIGGER_MODE: "binary",
            },
            title="Mailbox 1",
        )
        entry2 = MockConfigEntry(
            domain=DOMAIN,
            version=2,
            data={
                CONF_NAME: "Mailbox 2",
                CONF_FLAP_ENTITY: "binary_sensor.flap2",
                CONF_DOOR_ENTITY: "binary_sensor.door2",
                CONF_DEBOUNCE_SECONDS: 3,
                CONF_NOTIFY_ENABLED: False,
                CONF_NOTIFY_SERVICE: [],
                CONF_FLAP_TRIGGER_MODE: "binary",
                CONF_DOOR_TRIGGER_MODE: "binary",
            },
            title="Mailbox 2",
        )

        # Set initial states
        for eid in [
            "binary_sensor.flap1",
            "binary_sensor.door1",
            "binary_sensor.flap2",
            "binary_sensor.door2",
        ]:
            hass.states.async_set(eid, "off")

        entry1.add_to_hass(hass)
        await hass.config_entries.async_setup(entry1.entry_id)
        entry2.add_to_hass(hass)
        await hass.config_entries.async_setup(entry2.entry_id)
        await hass.async_block_till_done()

        state1 = hass.data[DOMAIN][entry1.entry_id]["state"]
        state2 = hass.data[DOMAIN][entry2.entry_id]["state"]
        state1.counter = 10
        state2.counter = 20

        # Reset only entry1
        await hass.services.async_call(
            DOMAIN,
            SERVICE_RESET_COUNTER,
            {"entry_id": entry1.entry_id},
            blocking=True,
        )
        await hass.async_block_till_done()

        assert state1.counter == 0
        assert state2.counter == 20  # untouched

    async def test_mark_empty_service(
        self, hass: HomeAssistant, mock_config_entry_binary
    ):
        await setup_integration(hass, mock_config_entry_binary)
        state = hass.data[DOMAIN][mock_config_entry_binary.entry_id]["state"]
        state.post_present = True
        state.notified_for_current_post = True

        await hass.services.async_call(DOMAIN, SERVICE_MARK_EMPTY, {}, blocking=True)
        await hass.async_block_till_done()

        assert state.post_present is False
        assert state.notified_for_current_post is False


# ---------------------------------------------------------------------------
# Unload tests
# ---------------------------------------------------------------------------


class TestUnload:
    async def test_unload_removes_data(
        self, hass: HomeAssistant, mock_config_entry_binary
    ):
        await setup_integration(hass, mock_config_entry_binary)
        assert mock_config_entry_binary.entry_id in hass.data[DOMAIN]

        await hass.config_entries.async_unload(mock_config_entry_binary.entry_id)
        await hass.async_block_till_done()

        assert mock_config_entry_binary.entry_id not in hass.data[DOMAIN]

    async def test_unload_last_entry_removes_services(
        self, hass: HomeAssistant, mock_config_entry_binary
    ):
        await setup_integration(hass, mock_config_entry_binary)
        assert hass.services.has_service(DOMAIN, SERVICE_RESET_COUNTER)

        await hass.config_entries.async_unload(mock_config_entry_binary.entry_id)
        await hass.async_block_till_done()

        assert not hass.services.has_service(DOMAIN, SERVICE_RESET_COUNTER)
        assert not hass.services.has_service(DOMAIN, SERVICE_MARK_EMPTY)
