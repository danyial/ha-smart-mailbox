"""Tests for button entities."""

from __future__ import annotations

import pytest
from homeassistant.core import HomeAssistant

from custom_components.smartmailbox.const import DOMAIN

from .conftest import setup_integration


class TestResetCounterButton:
    async def test_press_resets_counter(
        self, hass: HomeAssistant, mock_config_entry_binary
    ):
        await setup_integration(hass, mock_config_entry_binary)
        state_ref = hass.data[DOMAIN][mock_config_entry_binary.entry_id]["state"]
        state_ref.counter = 10

        await hass.services.async_call(
            "button",
            "press",
            {"entity_id": f"button.test_mailbox_reset_counter"},
            blocking=True,
        )
        await hass.async_block_till_done()

        assert state_ref.counter == 0

    async def test_unique_id(self, hass: HomeAssistant, mock_config_entry_binary):
        await setup_integration(hass, mock_config_entry_binary)

        entity = hass.states.get("button.test_mailbox_reset_counter")
        assert entity is not None


class TestMarkEmptyButton:
    async def test_press_marks_empty(
        self, hass: HomeAssistant, mock_config_entry_binary
    ):
        await setup_integration(hass, mock_config_entry_binary)
        state_ref = hass.data[DOMAIN][mock_config_entry_binary.entry_id]["state"]
        state_ref.post_present = True
        state_ref.notified_for_current_post = True

        await hass.services.async_call(
            "button",
            "press",
            {"entity_id": f"button.test_mailbox_mark_as_empty"},
            blocking=True,
        )
        await hass.async_block_till_done()

        assert state_ref.post_present is False
        assert state_ref.notified_for_current_post is False

    async def test_unique_id(self, hass: HomeAssistant, mock_config_entry_binary):
        await setup_integration(hass, mock_config_entry_binary)

        entity = hass.states.get("button.test_mailbox_mark_as_empty")
        assert entity is not None


class TestBothButtonsCreated:
    async def test_both_buttons_exist(
        self, hass: HomeAssistant, mock_config_entry_binary
    ):
        await setup_integration(hass, mock_config_entry_binary)

        reset = hass.states.get("button.test_mailbox_reset_counter")
        mark_empty = hass.states.get("button.test_mailbox_mark_as_empty")

        assert reset is not None
        assert mark_empty is not None
