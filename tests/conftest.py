"""Shared fixtures for smartmailbox tests."""

from __future__ import annotations

import pytest
from homeassistant.core import HomeAssistant

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.smartmailbox.const import (
    DOMAIN,
    CONF_NAME,
    CONF_FLAP_ENTITY,
    CONF_DOOR_ENTITY,
    CONF_DEBOUNCE_SECONDS,
    CONF_NOTIFY_ENABLED,
    CONF_NOTIFY_SERVICE,
    CONF_NOTIFY_MESSAGE,
    CONF_DOOR_NOTIFY_ENABLED,
    CONF_DOOR_NOTIFY_SERVICE,
    CONF_DOOR_NOTIFY_MESSAGE,
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
    THRESHOLD_DIRECTION_BELOW,
)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Automatically enable custom integrations in all tests."""
    yield


def _base_binary_data() -> dict:
    """Return base config data for a binary-sensor-based mailbox."""
    return {
        CONF_NAME: "Test Mailbox",
        CONF_FLAP_ENTITY: "binary_sensor.flap",
        CONF_DOOR_ENTITY: "binary_sensor.door",
        CONF_DEBOUNCE_SECONDS: 3,
        CONF_NOTIFY_ENABLED: False,
        CONF_NOTIFY_SERVICE: [],
        CONF_FLAP_TRIGGER_MODE: TRIGGER_MODE_BINARY,
        CONF_DOOR_TRIGGER_MODE: TRIGGER_MODE_BINARY,
    }


@pytest.fixture
def mock_config_entry_binary() -> MockConfigEntry:
    """Config entry with both sensors as binary_sensor entities."""
    return MockConfigEntry(
        domain=DOMAIN,
        version=2,
        data=_base_binary_data(),
        title="Test Mailbox",
    )


@pytest.fixture
def mock_config_entry_threshold() -> MockConfigEntry:
    """Config entry with both sensors as numeric (threshold) entities."""
    return MockConfigEntry(
        domain=DOMAIN,
        version=2,
        data={
            CONF_NAME: "Test Mailbox Threshold",
            CONF_FLAP_ENTITY: "sensor.flap_angle",
            CONF_DOOR_ENTITY: "sensor.door_angle",
            CONF_DEBOUNCE_SECONDS: 3,
            CONF_NOTIFY_ENABLED: False,
            CONF_NOTIFY_SERVICE: [],
            CONF_FLAP_TRIGGER_MODE: TRIGGER_MODE_THRESHOLD,
            CONF_DOOR_TRIGGER_MODE: TRIGGER_MODE_THRESHOLD,
            CONF_FLAP_THRESHOLD: 30.0,
            CONF_FLAP_THRESHOLD_DIRECTION: THRESHOLD_DIRECTION_ABOVE,
            CONF_DOOR_THRESHOLD: 30.0,
            CONF_DOOR_THRESHOLD_DIRECTION: THRESHOLD_DIRECTION_ABOVE,
        },
        title="Test Mailbox Threshold",
    )


@pytest.fixture
def mock_config_entry_mixed() -> MockConfigEntry:
    """Config entry: binary flap + threshold door (the Issue #1 use case)."""
    return MockConfigEntry(
        domain=DOMAIN,
        version=2,
        data={
            CONF_NAME: "Test Mailbox Mixed",
            CONF_FLAP_ENTITY: "binary_sensor.flap",
            CONF_DOOR_ENTITY: "sensor.door_angle",
            CONF_DEBOUNCE_SECONDS: 3,
            CONF_NOTIFY_ENABLED: False,
            CONF_NOTIFY_SERVICE: [],
            CONF_FLAP_TRIGGER_MODE: TRIGGER_MODE_BINARY,
            CONF_DOOR_TRIGGER_MODE: TRIGGER_MODE_THRESHOLD,
            CONF_DOOR_THRESHOLD: 30.0,
            CONF_DOOR_THRESHOLD_DIRECTION: THRESHOLD_DIRECTION_ABOVE,
        },
        title="Test Mailbox Mixed",
    )


@pytest.fixture
def mock_config_entry_v1() -> MockConfigEntry:
    """Version 1 config entry for migration testing."""
    return MockConfigEntry(
        domain=DOMAIN,
        version=1,
        data={
            CONF_NAME: "Old Mailbox",
            CONF_FLAP_ENTITY: "binary_sensor.flap",
            CONF_DOOR_ENTITY: "binary_sensor.door",
            CONF_DEBOUNCE_SECONDS: 3,
            CONF_NOTIFY_ENABLED: False,
            CONF_NOTIFY_SERVICE: [],
        },
        title="Old Mailbox",
    )


async def setup_integration(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    """Set up the integration with initial entity states."""
    # Set initial states for the source entities so listeners work
    flap = entry.data.get(CONF_FLAP_ENTITY, "")
    door = entry.data.get(CONF_DOOR_ENTITY, "")

    if flap.startswith("binary_sensor."):
        hass.states.async_set(flap, "off")
    elif flap.startswith("sensor."):
        hass.states.async_set(flap, "0")

    if door.startswith("binary_sensor."):
        hass.states.async_set(door, "off")
    elif door.startswith("sensor."):
        hass.states.async_set(door, "0")

    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
