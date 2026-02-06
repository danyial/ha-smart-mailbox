from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import (
    DOMAIN, PLATFORMS,
    SERVICE_RESET_COUNTER,
    SERVICE_MARK_EMPTY,
    SIGNAL_PREFIX,
    STORAGE_KEY_PREFIX, STORAGE_VERSION,
)

_LOGGER = logging.getLogger(__name__)

@dataclass
class MailboxState:
    post_present: bool = False
    last_delivery: datetime | None = None
    last_empty: datetime | None = None
    counter: int = 0
    notified_for_current_post: bool = False
    last_flap_trigger: datetime | None = None

def _dt_to_iso(dt: datetime | None) -> str | None:
    return dt.isoformat() if dt else None

def _iso_to_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        # parse_datetime handles timezone-aware and naive strings
        dt = dt_util.parse_datetime(value) or datetime.fromisoformat(value)
        if dt and dt.tzinfo is None:
            return dt.replace(tzinfo=dt_util.UTC)
        return dt
    except Exception:
        return None

async def _load_state(hass: HomeAssistant, entry: ConfigEntry) -> MailboxState:
    store = Store(hass, STORAGE_VERSION, f"{STORAGE_KEY_PREFIX}{entry.entry_id}")
    data = await store.async_load() or {}
    return MailboxState(
        post_present=bool(data.get("post_present", False)),
        last_delivery=_iso_to_dt(data.get("last_delivery")),
        last_empty=_iso_to_dt(data.get("last_empty")),
        counter=int(data.get("counter", 0)),
        notified_for_current_post=bool(data.get("notified_for_current_post", False)),
        last_flap_trigger=_iso_to_dt(data.get("last_flap_trigger")),
    )

async def _save_state(hass: HomeAssistant, entry: ConfigEntry, state: MailboxState) -> None:
    store = Store(hass, STORAGE_VERSION, f"{STORAGE_KEY_PREFIX}{entry.entry_id}")
    await store.async_save({
        "post_present": state.post_present,
        "last_delivery": _dt_to_iso(state.last_delivery),
        "last_empty": _dt_to_iso(state.last_empty),
        "counter": state.counter,
        "notified_for_current_post": state.notified_for_current_post,
        "last_flap_trigger": _dt_to_iso(state.last_flap_trigger),
    })

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})
    state = await _load_state(hass, entry)
    hass.data[DOMAIN][entry.entry_id] = {
        "state": state,
        "save": lambda: hass.async_create_task(_save_state(hass, entry, state)),
    }

    if not hass.data[DOMAIN].get("_service_registered"):
        async def handle_reset_counter(call: ServiceCall) -> None:
            target_entry_id = call.data.get("entry_id")
            for entry_id, data in list(hass.data[DOMAIN].items()):
                if entry_id.startswith("_"):
                    continue
                if target_entry_id and target_entry_id != entry_id:
                    continue
                data["state"].counter = 0
                data["save"]()
                async_dispatcher_send(hass, f"{SIGNAL_PREFIX}{entry_id}")

        async def handle_mark_empty(call: ServiceCall) -> None:
            target_entry_id = call.data.get("entry_id")
            for entry_id, data in list(hass.data[DOMAIN].items()):
                if entry_id.startswith("_"):
                    continue
                if target_entry_id and target_entry_id != entry_id:
                    continue
                data["state"].post_present = False
                data["state"].notified_for_current_post = False
                data["save"]()
                async_dispatcher_send(hass, f"{SIGNAL_PREFIX}{entry_id}")

        hass.services.async_register(
            DOMAIN,
            SERVICE_RESET_COUNTER,
            handle_reset_counter,
        )
        hass.services.async_register(
            DOMAIN,
            SERVICE_MARK_EMPTY,
            handle_mark_empty,
        )
        hass.data[DOMAIN]["_service_registered"] = True

    entry.async_on_unload(entry.add_update_listener(_update_listener))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def _update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    # Reload to apply option changes (enable/disable sensors, debounce, notify, etc.)
    await hass.config_entries.async_reload(entry.entry_id)

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id, None)
        if not [k for k in hass.data[DOMAIN].keys() if not k.startswith("_")]:
            hass.services.async_remove(DOMAIN, SERVICE_RESET_COUNTER)
            hass.services.async_remove(DOMAIN, SERVICE_MARK_EMPTY)
            hass.data[DOMAIN].pop("_service_registered", None)
    return unloaded
