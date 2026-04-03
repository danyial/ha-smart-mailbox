from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import (
    async_dispatcher_send,
    async_dispatcher_connect,
)
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.util import dt as dt_util

_LOGGER = logging.getLogger(__name__)

from homeassistant.helpers.translation import async_get_translations

from .const import (
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
    CONF_RESET_ON_EMPTY,
    CONF_FLAP_TRIGGER_MODE,
    CONF_FLAP_THRESHOLD,
    CONF_FLAP_THRESHOLD_DIRECTION,
    CONF_DOOR_TRIGGER_MODE,
    CONF_DOOR_THRESHOLD,
    CONF_DOOR_THRESHOLD_DIRECTION,
    TRIGGER_MODE_BINARY,
    TRIGGER_MODE_THRESHOLD,
    THRESHOLD_DIRECTION_ABOVE,
    DEFAULT_TRIGGER_MODE,
    DEFAULT_THRESHOLD,
    DEFAULT_THRESHOLD_DIRECTION,
    TRANSLATION_KEY_DEFAULT_NOTIFY,
    TRANSLATION_KEY_DEFAULT_DOOR_NOTIFY,
    SIGNAL_PREFIX,
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
):
    async_add_entities([MailboxPostSensor(hass, entry)])


def _get_option(entry: ConfigEntry, key: str, default=None):
    """Get a config value from options first, then data, then default."""
    return entry.options.get(key, entry.data.get(key, default))


def _is_triggered_threshold(
    new_state_val: float, old_state_val: float | None, threshold: float, direction: str
) -> bool:
    """Check if a threshold crossing occurred (edge detection).

    Returns True only if the new value crosses the threshold while the old value
    did not meet the condition — preventing repeated triggers at a constant value.
    """
    if direction == THRESHOLD_DIRECTION_ABOVE:
        new_meets = new_state_val >= threshold
        old_meets = old_state_val is not None and old_state_val >= threshold
    else:  # below
        new_meets = new_state_val <= threshold
        old_meets = old_state_val is not None and old_state_val <= threshold

    return new_meets and not old_meets


def _parse_float(state_str: str) -> float | None:
    """Safely parse a state string to float."""
    try:
        return float(state_str)
    except (ValueError, TypeError):
        return None


class MailboxPostSensor(BinarySensorEntity):
    _attr_has_entity_name = True
    _attr_translation_key = "post"
    _attr_icon = "mdi:mailbox-outline"
    _attr_device_class = "occupancy"

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
        self.hass = hass
        self.entry = entry
        self._attr_unique_id = f"{entry.entry_id}_mailbox_post"

        device_name = entry.data.get(CONF_NAME, "Smart Mailbox")
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": device_name,
            "manufacturer": "Danny Smolinsky",
            "model": "Smart Mailbox",
        }

        self._state_ref = hass.data[DOMAIN][entry.entry_id]["state"]
        self._save = hass.data[DOMAIN][entry.entry_id]["save"]

        self._unsub = None
        self._unsub_dispatcher = None
        self._default_notify_message = ""
        self._default_door_notify_message = ""

    async def async_added_to_hass(self) -> None:
        translations = await async_get_translations(
            self.hass, self.hass.config.language, "options", {DOMAIN}
        )
        self._default_notify_message = translations.get(
            TRANSLATION_KEY_DEFAULT_NOTIFY, ""
        )
        self._default_door_notify_message = translations.get(
            TRANSLATION_KEY_DEFAULT_DOOR_NOTIFY, ""
        )

        self._unsub_dispatcher = async_dispatcher_connect(
            self.hass,
            f"{SIGNAL_PREFIX}{self.entry.entry_id}",
            self._handle_dispatcher_update,
        )

        flap = _get_option(self.entry, CONF_FLAP_ENTITY)
        door = _get_option(self.entry, CONF_DOOR_ENTITY)

        # Load trigger configuration
        flap_mode = _get_option(
            self.entry, CONF_FLAP_TRIGGER_MODE, DEFAULT_TRIGGER_MODE
        )
        flap_threshold = float(
            _get_option(self.entry, CONF_FLAP_THRESHOLD, DEFAULT_THRESHOLD)
        )
        flap_direction = _get_option(
            self.entry, CONF_FLAP_THRESHOLD_DIRECTION, DEFAULT_THRESHOLD_DIRECTION
        )

        door_mode = _get_option(
            self.entry, CONF_DOOR_TRIGGER_MODE, DEFAULT_TRIGGER_MODE
        )
        door_threshold = float(
            _get_option(self.entry, CONF_DOOR_THRESHOLD, DEFAULT_THRESHOLD)
        )
        door_direction = _get_option(
            self.entry, CONF_DOOR_THRESHOLD_DIRECTION, DEFAULT_THRESHOLD_DIRECTION
        )

        @callback
        def _changed(event):
            entity_id = event.data.get("entity_id")
            new_state = event.data.get("new_state")
            old_state = event.data.get("old_state")
            if new_state is None:
                return

            # Ignore state transitions during startup (unavailable/unknown → any)
            if old_state is None or old_state.state in ("unavailable", "unknown"):
                return
            # Ignore transitions TO unavailable/unknown
            if new_state.state in ("unavailable", "unknown"):
                return

            # Determine which sensor fired and check trigger condition
            if entity_id == flap:
                triggered = self._check_trigger(
                    flap_mode, new_state, old_state, flap_threshold, flap_direction
                )
            elif entity_id == door:
                triggered = self._check_trigger(
                    door_mode, new_state, old_state, door_threshold, door_direction
                )
            else:
                return

            if not triggered:
                return

            now = dt_util.utcnow()
            debounce_s = _get_option(self.entry, CONF_DEBOUNCE_SECONDS, 3)
            debounce = timedelta(seconds=int(debounce_s))

            # Flap: delivery
            if entity_id == flap:
                if (
                    self._state_ref.last_flap_trigger
                    and (now - self._state_ref.last_flap_trigger) < debounce
                ):
                    return

                self._state_ref.last_flap_trigger = now
                self._state_ref.last_delivery = now
                self._state_ref.post_present = True

                # Push only once per "post_present period"
                if not self._state_ref.notified_for_current_post:
                    notify_enabled = _get_option(self.entry, CONF_NOTIFY_ENABLED, False)
                    notify_services = _get_option(self.entry, CONF_NOTIFY_SERVICE, [])
                    if notify_enabled and notify_services:
                        message = _get_option(
                            self.entry,
                            CONF_NOTIFY_MESSAGE,
                            self._default_notify_message,
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

                if _get_option(self.entry, CONF_RESET_ON_EMPTY, False):
                    self._state_ref.counter = 0

                door_notify_enabled = _get_option(
                    self.entry, CONF_DOOR_NOTIFY_ENABLED, False
                )
                door_notify_services = _get_option(
                    self.entry, CONF_DOOR_NOTIFY_SERVICE, []
                )
                if door_notify_enabled and door_notify_services:
                    door_message = _get_option(
                        self.entry,
                        CONF_DOOR_NOTIFY_MESSAGE,
                        self._default_door_notify_message,
                    )
                    self._send_notifications(door_notify_services, door_message)

            self._save()
            async_dispatcher_send(self.hass, f"{SIGNAL_PREFIX}{self.entry.entry_id}")
            self.schedule_update_ha_state()

        self._unsub = async_track_state_change_event(self.hass, [flap, door], _changed)

    @staticmethod
    def _check_trigger(
        mode: str, new_state, old_state, threshold: float, direction: str
    ) -> bool:
        """Check if a state change constitutes a trigger event."""
        if mode == TRIGGER_MODE_BINARY:
            return new_state.state == "on"

        if mode == TRIGGER_MODE_THRESHOLD:
            new_val = _parse_float(new_state.state)
            if new_val is None:
                return False
            old_val = _parse_float(old_state.state) if old_state else None
            return _is_triggered_threshold(new_val, old_val, threshold, direction)

        return False

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
    def _send_notifications(self, notify_services: list | str, message: str) -> None:
        """Send notifications to configured services."""
        # Support both list (EntitySelector) and comma-separated string (legacy)
        if isinstance(notify_services, str):
            services = [s.strip() for s in notify_services.split(",") if s.strip()]
        else:
            services = notify_services

        for notify_service in services:
            try:
                if "." in notify_service:
                    domain, service = notify_service.split(".", 1)
                else:
                    domain, service = "notify", notify_service
                _LOGGER.debug("Sending notification via %s.%s", domain, service)
                self.hass.async_create_task(
                    self.hass.services.async_call(
                        domain,
                        service,
                        {"message": message},
                        blocking=False,
                    )
                )
            except Exception as err:
                _LOGGER.error(
                    "Failed to send notification via %s: %s", notify_service, err
                )

    @property
    def is_on(self) -> bool:
        return bool(self._state_ref.post_present)
