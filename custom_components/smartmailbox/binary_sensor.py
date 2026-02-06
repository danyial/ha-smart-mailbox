from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send, async_dispatcher_connect
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.util import dt as dt_util

_LOGGER = logging.getLogger(__name__)

from homeassistant.helpers.translation import async_get_translations

from .const import (
    DOMAIN,
    CONF_FLAP_ENTITY,
    CONF_DOOR_ENTITY,
    CONF_DEBOUNCE_SECONDS,
    CONF_NOTIFY_ENABLED,
    CONF_NOTIFY_SERVICE,
    CONF_NOTIFY_MESSAGE,
    CONF_RESET_ON_EMPTY,
    TRANSLATION_KEY_DEFAULT_NOTIFY,
    SIGNAL_PREFIX,
)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    async_add_entities([MailboxPostSensor(hass, entry)])

class MailboxPostSensor(BinarySensorEntity):
    _attr_has_entity_name = True
    _attr_translation_key = "post"
    _attr_icon = "mdi:mailbox-outline"
    _attr_device_class = "occupancy"

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
        self.hass = hass
        self.entry = entry
        self._attr_unique_id = f"{entry.entry_id}_mailbox_post"

        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "Smart Mailbox",
            "manufacturer": "Danny Smolinsky",
            "model": "Smart Mailbox",
        }

        self._state_ref = hass.data[DOMAIN][entry.entry_id]["state"]
        self._save = hass.data[DOMAIN][entry.entry_id]["save"]

        self._unsub = None
        self._unsub_dispatcher = None
        self._default_notify_message = ""

    async def async_added_to_hass(self) -> None:
        translations = await async_get_translations(
            self.hass, self.hass.config.language, "options", {DOMAIN}
        )
        self._default_notify_message = translations.get(
            TRANSLATION_KEY_DEFAULT_NOTIFY, ""
        )

        self._unsub_dispatcher = async_dispatcher_connect(
            self.hass,
            f"{SIGNAL_PREFIX}{self.entry.entry_id}",
            self._handle_dispatcher_update,
        )

        flap = self.entry.options.get(CONF_FLAP_ENTITY, self.entry.data.get(CONF_FLAP_ENTITY))
        door = self.entry.options.get(CONF_DOOR_ENTITY, self.entry.data.get(CONF_DOOR_ENTITY))

        @callback
        def _changed(event):
            entity_id = event.data.get("entity_id")
            new_state = event.data.get("new_state")
            if new_state is None or new_state.state != "on":
                return

            now = dt_util.utcnow()
            debounce_s = self.entry.options.get(CONF_DEBOUNCE_SECONDS, self.entry.data.get(CONF_DEBOUNCE_SECONDS, 3))
            debounce = timedelta(seconds=int(debounce_s))

            # Flap: delivery
            if entity_id == flap:
                if self._state_ref.last_flap_trigger and (now - self._state_ref.last_flap_trigger) < debounce:
                    return

                self._state_ref.last_flap_trigger = now
                self._state_ref.last_delivery = now
                self._state_ref.post_present = True

                # Push only once per "post_present period"
                if not self._state_ref.notified_for_current_post:
                    notify_enabled = self.entry.options.get(CONF_NOTIFY_ENABLED, self.entry.data.get(CONF_NOTIFY_ENABLED, False))
                    notify_services = self.entry.options.get(CONF_NOTIFY_SERVICE, self.entry.data.get(CONF_NOTIFY_SERVICE, "notify.notify"))
                    if notify_enabled and notify_services:
                        message = self.entry.options.get(
                            CONF_NOTIFY_MESSAGE,
                            self.entry.data.get(CONF_NOTIFY_MESSAGE, self._default_notify_message),
                        )
                        self._send_notifications(notify_services, message)
                    self._state_ref.notified_for_current_post = True

                # Counter increments on every accepted flap event
                self._state_ref.counter += 1

            # Door: emptying
            elif entity_id == door:
                self._state_ref.last_empty = now
                self._state_ref.post_present = False
                self._state_ref.notified_for_current_post = False

                if self.entry.options.get(CONF_RESET_ON_EMPTY, self.entry.data.get(CONF_RESET_ON_EMPTY, False)):
                    self._state_ref.counter = 0

            else:
                return

            self._save()
            async_dispatcher_send(self.hass, f"{SIGNAL_PREFIX}{self.entry.entry_id}")
            self.schedule_update_ha_state()

        self._unsub = async_track_state_change_event(self.hass, [flap, door], _changed)

    async def async_will_remove_from_hass(self) -> None:
        if self._unsub:
            self._unsub()
            self._unsub = None
        if self._unsub_dispatcher:
            self._unsub_dispatcher()
            self._unsub_dispatcher = None

    @callback
    def _handle_dispatcher_update(self) -> None:
        self.schedule_update_ha_state()

    @callback
    def _send_notifications(self, notify_services: str, message: str) -> None:
        """Send notifications to configured services."""
        for notify_service in [s.strip() for s in notify_services.split(",") if s.strip()]:
            try:
                if "." in notify_service:
                    domain, service = notify_service.split(".", 1)
                else:
                    domain, service = "notify", notify_service
                _LOGGER.debug("Sending notification via %s.%s", domain, service)
                self.hass.async_create_task(
                    self.hass.services.async_call(
                        domain, service,
                        {"message": message},
                        blocking=False,
                    )
                )
            except Exception as err:
                _LOGGER.error("Failed to send notification via %s: %s", notify_service, err)

    @property
    def is_on(self) -> bool:
        return bool(self._state_ref.post_present)
