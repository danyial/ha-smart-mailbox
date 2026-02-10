from __future__ import annotations

from homeassistant import config_entries
from homeassistant.helpers.selector import EntitySelector, EntitySelectorConfig
from homeassistant.helpers.translation import async_get_translations
import voluptuous as vol

from .const import (
    DOMAIN,
    CONF_FLAP_ENTITY,
    CONF_DOOR_ENTITY,
    CONF_DEBOUNCE_SECONDS,
    CONF_NOTIFY_ENABLED,
    CONF_NOTIFY_SERVICE,
    CONF_NOTIFY_MESSAGE,
    CONF_DOOR_NOTIFY_ENABLED,
    CONF_DOOR_NOTIFY_SERVICE,
    CONF_DOOR_NOTIFY_MESSAGE,
    CONF_ENABLE_COUNTER,
    CONF_ENABLE_AGE,
    CONF_AGE_UNIT,
    CONF_RESET_ON_EMPTY,
    DEFAULT_DEBOUNCE_SECONDS,
    DEFAULT_NOTIFY_ENABLED,
    DEFAULT_NOTIFY_SERVICE,
    DEFAULT_DOOR_NOTIFY_ENABLED,
    DEFAULT_DOOR_NOTIFY_SERVICE,
    TRANSLATION_KEY_DEFAULT_NOTIFY,
    TRANSLATION_KEY_DEFAULT_DOOR_NOTIFY,
    DEFAULT_ENABLE_COUNTER,
    DEFAULT_ENABLE_AGE,
    DEFAULT_AGE_UNIT,
    DEFAULT_RESET_ON_EMPTY,
)

_ENTITY_SELECTOR = EntitySelector(EntitySelectorConfig(domain="binary_sensor"))

USER_SCHEMA = vol.Schema({
    vol.Required(CONF_FLAP_ENTITY): _ENTITY_SELECTOR,
    vol.Required(CONF_DOOR_ENTITY): _ENTITY_SELECTOR,
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
        vol.Optional(CONF_NOTIFY_MESSAGE, default=options.get(CONF_NOTIFY_MESSAGE, "")): str,
        vol.Optional(CONF_DOOR_NOTIFY_ENABLED, default=options.get(CONF_DOOR_NOTIFY_ENABLED, DEFAULT_DOOR_NOTIFY_ENABLED)): bool,
        vol.Optional(CONF_DOOR_NOTIFY_SERVICE, default=options.get(CONF_DOOR_NOTIFY_SERVICE, DEFAULT_DOOR_NOTIFY_SERVICE)): str,
        vol.Optional(CONF_DOOR_NOTIFY_MESSAGE, default=options.get(CONF_DOOR_NOTIFY_MESSAGE, "")): str,
        vol.Optional(CONF_FLAP_ENTITY, default=options.get(CONF_FLAP_ENTITY, "")): _ENTITY_SELECTOR,
        vol.Optional(CONF_DOOR_ENTITY, default=options.get(CONF_DOOR_ENTITY, "")): _ENTITY_SELECTOR,
    })

class MailboxConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            # prevent multiple instances
            await self.async_set_unique_id(DOMAIN)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title="Smart Mailbox", data=user_input)

        return self.async_show_form(step_id="user", data_schema=USER_SCHEMA)

    @staticmethod
    def async_get_options_flow(config_entry):
        return MailboxOptionsFlow(config_entry)

class MailboxOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, entry: config_entries.ConfigEntry):
        self.entry = entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        merged = {**self.entry.data, **self.entry.options}
        if not merged.get(CONF_NOTIFY_MESSAGE) or not merged.get(CONF_DOOR_NOTIFY_MESSAGE):
            translations = await async_get_translations(
                self.hass, self.hass.config.language, "options", {DOMAIN}
            )
            if not merged.get(CONF_NOTIFY_MESSAGE):
                merged[CONF_NOTIFY_MESSAGE] = translations.get(TRANSLATION_KEY_DEFAULT_NOTIFY, "")
            if not merged.get(CONF_DOOR_NOTIFY_MESSAGE):
                merged[CONF_DOOR_NOTIFY_MESSAGE] = translations.get(TRANSLATION_KEY_DEFAULT_DOOR_NOTIFY, "")
        return self.async_show_form(step_id="init", data_schema=_options_schema(merged))
