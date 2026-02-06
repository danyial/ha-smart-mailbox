from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import DOMAIN, SIGNAL_PREFIX


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    """Set up button entities."""
    state_ref = hass.data[DOMAIN][entry.entry_id]["state"]
    save_fn = hass.data[DOMAIN][entry.entry_id]["save"]

    async_add_entities([
        ResetCounterButton(hass, entry, state_ref, save_fn),
        MarkEmptyButton(hass, entry, state_ref, save_fn),
    ])


class _MailboxButtonBase(ButtonEntity):
    """Base class for mailbox buttons."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, state_ref, save_fn):
        self.hass = hass
        self.entry = entry
        self._state_ref = state_ref
        self._save = save_fn

        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "Smart Mailbox",
            "manufacturer": "Danny Smolinsky",
            "model": "Smart Mailbox",
        }

    def _notify_update(self):
        """Save state and notify listeners."""
        self._save()
        async_dispatcher_send(self.hass, f"{SIGNAL_PREFIX}{self.entry.entry_id}")


class ResetCounterButton(_MailboxButtonBase):
    """Button to reset the delivery counter."""

    _attr_translation_key = "reset_counter"
    _attr_icon = "mdi:counter"

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, state_ref, save_fn):
        super().__init__(hass, entry, state_ref, save_fn)
        self._attr_unique_id = f"{entry.entry_id}_reset_counter_button"

    async def async_press(self) -> None:
        """Handle button press."""
        self._state_ref.counter = 0
        self._notify_update()


class MarkEmptyButton(_MailboxButtonBase):
    """Button to mark mailbox as empty."""

    _attr_translation_key = "mark_empty"
    _attr_icon = "mdi:mailbox-open-outline"

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, state_ref, save_fn):
        super().__init__(hass, entry, state_ref, save_fn)
        self._attr_unique_id = f"{entry.entry_id}_mark_empty_button"

    async def async_press(self) -> None:
        """Handle button press."""
        self._state_ref.post_present = False
        self._state_ref.notified_for_current_post = False
        self._notify_update()
