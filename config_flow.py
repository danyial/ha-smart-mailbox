from __future__ import annotations

from homeassistant import config_entries
import voluptuous as vol

from .const import (
    DOMAIN,
    DEFAULT_KLAPPE_ENTITY,
    DEFAULT_TUER_ENTITY,
    CONF_KLAPPE_ENTITY,
    CONF_TUER_ENTITY,
    CONF_DEBOUNCE_SECONDS,
    CONF_NOTIFY_ENABLED,
    CONF_NOTIFY_SERVICE,
    CONF_ENABLE_COUNTER,
    CONF_ENABLE_AGE,
    CONF_AGE_UNIT,
    CONF_RESET_ON_EMPTY,
    DEFAULT_DEBOUNCE_SECONDS,
    DEFAULT_NOTIFY_ENABLED,
    DEFAULT_NOTIFY_SERVICE,
    DEFAULT_ENABLE_COUNTER,
    DEFAULT_ENABLE_AGE,
    DEFAULT_AGE_UNIT,
    DEFAULT_RESET_ON_EMPTY,
)

USER_SCHEMA = vol.Schema({
    vol.Required(CONF_KLAPPE_ENTITY, default=DEFAULT_KLAPPE_ENTITY): str,
    vol.Required(CONF_TUER_ENTITY, default=DEFAULT_TUER_ENTITY): str,
    vol.Required(CONF_DEBOUNCE_SECONDS, default=DEFAULT_DEBOUNCE_SECONDS): vol.Coerce(int),
    vol.Required(CONF_NOTIFY_ENABLED, default=DEFAULT_NOTIFY_ENABLED): bool,
    vol.Required(CONF_NOTIFY_SERVICE, default=DEFAULT_NOTIFY_SERVICE): str,
})

def _options_schema(options: dict) -> vol.Schema:
    return vol.Schema({
        vol.Optional(CONF_ENABLE_COUNTER, default=options.get(CONF_ENABLE_COUNTER, DEFAULT_ENABLE_COUNTER)): bool,
        vol.Optional(CONF_ENABLE_AGE, default=options.get(CONF_ENABLE_AGE, DEFAULT_ENABLE_AGE)): bool,
        vol.Optional(CONF_AGE_UNIT, default=options.get(CONF_AGE_UNIT, DEFAULT_AGE_UNIT)): vol.In(["hours", "days"]),
        vol.Optional(CONF_RESET_ON_EMPTY, default=options.get(CONF_RESET_ON_EMPTY, DEFAULT_RESET_ON_EMPTY)): bool,
        vol.Optional(CONF_DEBOUNCE_SECONDS, default=options.get(CONF_DEBOUNCE_SECONDS, DEFAULT_DEBOUNCE_SECONDS)): vol.Coerce(int),
        vol.Optional(CONF_NOTIFY_ENABLED, default=options.get(CONF_NOTIFY_ENABLED, DEFAULT_NOTIFY_ENABLED)): bool,
        vol.Optional(CONF_NOTIFY_SERVICE, default=options.get(CONF_NOTIFY_SERVICE, DEFAULT_NOTIFY_SERVICE)): str,
        vol.Optional(CONF_KLAPPE_ENTITY, default=options.get(CONF_KLAPPE_ENTITY, DEFAULT_KLAPPE_ENTITY)): str,
        vol.Optional(CONF_TUER_ENTITY, default=options.get(CONF_TUER_ENTITY, DEFAULT_TUER_ENTITY)): str,
    })

class BriefkastenConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            # prevent multiple instances
            await self.async_set_unique_id(DOMAIN)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title="Briefkasten", data=user_input)

        return self.async_show_form(step_id="user", data_schema=USER_SCHEMA)

    @staticmethod
    def async_get_options_flow(config_entry):
        return BriefkastenOptionsFlow(config_entry)

class BriefkastenOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, entry: config_entries.ConfigEntry):
        self.entry = entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        merged = {**self.entry.data, **self.entry.options}
        return self.async_show_form(step_id="init", data_schema=_options_schema(merged))
