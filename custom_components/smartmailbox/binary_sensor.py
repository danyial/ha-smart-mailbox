from __future__ import annotations

from datetime import timedelta

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    CONF_KLAPPE_ENTITY,
    CONF_TUER_ENTITY,
    CONF_DEBOUNCE_SECONDS,
    CONF_NOTIFY_ENABLED,
    CONF_NOTIFY_SERVICE,
    CONF_RESET_ON_EMPTY,
    SIGNAL_PREFIX,
)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    async_add_entities([BriefkastenPostSensor(hass, entry)])

class BriefkastenPostSensor(BinarySensorEntity):
    _attr_name = "Post"
    _attr_icon = "mdi:mailbox-outline"
    _attr_device_class = "occupancy"

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
        self.hass = hass
        self.entry = entry
        self._attr_unique_id = f"{entry.entry_id}_briefkasten_post"

        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "Briefkasten",
            "manufacturer": "Danny Smolinsky",
            "model": "Smart Mailbox",
        }

        self._state_ref = hass.data[DOMAIN][entry.entry_id]["state"]
        self._save = hass.data[DOMAIN][entry.entry_id]["save"]

        self._unsub = None

    async def async_added_to_hass(self) -> None:
        klappe = self.entry.options.get(CONF_KLAPPE_ENTITY, self.entry.data.get(CONF_KLAPPE_ENTITY))
        tuer = self.entry.options.get(CONF_TUER_ENTITY, self.entry.data.get(CONF_TUER_ENTITY))

        @callback
        def _changed(event):
            entity_id = event.data.get("entity_id")
            new_state = event.data.get("new_state")
            if new_state is None or new_state.state != "on":
                return

            now = dt_util.utcnow()
            debounce_s = self.entry.options.get(CONF_DEBOUNCE_SECONDS, self.entry.data.get(CONF_DEBOUNCE_SECONDS, 3))
            debounce = timedelta(seconds=int(debounce_s))

            # Klappe: Einwurf
            if entity_id == klappe:
                if self._state_ref.last_klappe_trigger and (now - self._state_ref.last_klappe_trigger) < debounce:
                    return

                self._state_ref.last_klappe_trigger = now
                self._state_ref.last_delivery = now
                self._state_ref.post_present = True

                # Push only once per "post_present period"
                if not self._state_ref.notified_for_current_post:
                    notify_enabled = self.entry.options.get(CONF_NOTIFY_ENABLED, self.entry.data.get(CONF_NOTIFY_ENABLED, False))
                    notify_service = self.entry.options.get(CONF_NOTIFY_SERVICE, self.entry.data.get(CONF_NOTIFY_SERVICE, "notify.notify"))
                    if notify_enabled:
                        domain, service = notify_service.split(".", 1) if "." in notify_service else ("notify", notify_service)
                        self.hass.services.call(domain, service, {"message": "📬 Neue Post im Briefkasten!"}, blocking=False)
                    self._state_ref.notified_for_current_post = True

                # Counter increments on every accepted klappe event
                self._state_ref.counter += 1

            # Tür: Leerung
            elif entity_id == tuer:
                self._state_ref.last_empty = now
                self._state_ref.post_present = False
                self._state_ref.notified_for_current_post = False

                if self.entry.options.get(CONF_RESET_ON_EMPTY, self.entry.data.get(CONF_RESET_ON_EMPTY, False)):
                    self._state_ref.counter = 0

            else:
                return

            self._save()
            async_dispatcher_send(self.hass, f"{SIGNAL_PREFIX}{self.entry.entry_id}")
            self.async_write_ha_state()

        self._unsub = async_track_state_change_event(self.hass, [klappe, tuer], _changed)

    async def async_will_remove_from_hass(self) -> None:
        if self._unsub:
            self._unsub()
            self._unsub = None

    @property
    def is_on(self) -> bool:
        return bool(self._state_ref.post_present)
