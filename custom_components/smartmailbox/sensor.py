from __future__ import annotations

from datetime import timedelta
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    CONF_ENABLE_COUNTER,
    CONF_ENABLE_AGE,
    CONF_AGE_UNIT,
    SIGNAL_PREFIX,
)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    state_ref = hass.data[DOMAIN][entry.entry_id]["state"]

    entities: list[SensorEntity] = [
        LetzterEinwurfSensor(hass, entry, state_ref, f"{entry.entry_id}_briefkasten_letzter_einwurf"),
        LetzteLeerungSensor(hass, entry, state_ref, f"{entry.entry_id}_briefkasten_letzte_leerung"),
    ]

    if entry.options.get(CONF_ENABLE_COUNTER, entry.data.get(CONF_ENABLE_COUNTER, True)):
        entities.append(EinwurfZaehlerSensor(hass, entry, state_ref, f"{entry.entry_id}_briefkasten_einwurf_zaehler"))

    if entry.options.get(CONF_ENABLE_AGE, entry.data.get(CONF_ENABLE_AGE, True)):
        entities.append(PostLiegtSeitSensor(hass, entry, state_ref, f"{entry.entry_id}_briefkasten_post_liegt_seit"))

    async_add_entities(entities)

class _BriefkastenBaseSensor(SensorEntity):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, state_ref, unique_id: str):
        self.hass = hass
        self.entry = entry
        self._state_ref = state_ref
        self._attr_unique_id = unique_id

        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "Briefkasten",
            "manufacturer": "Danny Smolinsky",
            "model": "Smart Mailbox",
        }

        self._unsub = None

    async def async_added_to_hass(self):
        self._unsub = async_dispatcher_connect(
            self.hass,
            f"{SIGNAL_PREFIX}{self.entry.entry_id}",
            self._handle_update,
        )

    async def async_will_remove_from_hass(self):
        if self._unsub:
            self._unsub()
            self._unsub = None

    @callback
    def _handle_update(self):
        self.async_write_ha_state()

class LetzterEinwurfSensor(_BriefkastenBaseSensor):
    _attr_name = "Letzter Einwurf"
    _attr_icon = "mdi:clock-outline"
    _attr_device_class = "timestamp"

    @property
    def native_value(self):
        return self._state_ref.last_delivery

class LetzteLeerungSensor(_BriefkastenBaseSensor):
    _attr_name = "Letzte Leerung"
    _attr_icon = "mdi:clock-outline"
    _attr_device_class = "timestamp"

    @property
    def native_value(self):
        return self._state_ref.last_empty

class EinwurfZaehlerSensor(_BriefkastenBaseSensor):
    _attr_name = "Einwurf Zähler"
    _attr_icon = "mdi:counter"

    @property
    def native_value(self):
        return int(self._state_ref.counter)

class PostLiegtSeitSensor(_BriefkastenBaseSensor):
    _attr_name = "Post liegt seit"
    _attr_icon = "mdi:clock-outline"

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, state_ref, unique_id: str):
        super().__init__(hass, entry, state_ref, unique_id)
        self._attr_native_unit_of_measurement = "h"
        self._unsub_time = None

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        self._unsub_time = async_track_time_interval(
            self.hass,
            self._handle_time_update,
            timedelta(minutes=1),
        )

    async def async_will_remove_from_hass(self):
        if self._unsub_time:
            self._unsub_time()
            self._unsub_time = None
        await super().async_will_remove_from_hass()

    @callback
    def _handle_time_update(self, now):
        self.async_write_ha_state()

    @property
    def native_value(self):
        if not self._state_ref.post_present or not self._state_ref.last_delivery:
            return None

        unit = self.entry.options.get(CONF_AGE_UNIT, self.entry.data.get(CONF_AGE_UNIT, "hours"))
        delta = dt_util.utcnow() - self._state_ref.last_delivery
        seconds = delta.total_seconds()

        if unit == "days":
            self._attr_native_unit_of_measurement = "d"
            return round(seconds / 86400, 2)

        self._attr_native_unit_of_measurement = "h"
        return round(seconds / 3600, 2)
