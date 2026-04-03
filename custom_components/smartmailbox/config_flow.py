from __future__ import annotations

from homeassistant import config_entries
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)
from homeassistant.helpers.translation import async_get_translations
import voluptuous as vol

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
    CONF_ENABLE_COUNTER,
    CONF_ENABLE_AGE,
    CONF_AGE_UNIT,
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
    THRESHOLD_DIRECTION_BELOW,
    DEFAULT_DEBOUNCE_SECONDS,
    DEFAULT_NOTIFY_ENABLED,
    DEFAULT_DOOR_NOTIFY_ENABLED,
    DEFAULT_TRIGGER_MODE,
    DEFAULT_THRESHOLD,
    DEFAULT_THRESHOLD_DIRECTION,
    TRANSLATION_KEY_DEFAULT_NOTIFY,
    TRANSLATION_KEY_DEFAULT_DOOR_NOTIFY,
    DEFAULT_ENABLE_COUNTER,
    DEFAULT_ENABLE_AGE,
    DEFAULT_AGE_UNIT,
    DEFAULT_RESET_ON_EMPTY,
)

# Accept both binary_sensor and sensor domains
_ENTITY_SELECTOR = EntitySelector(
    EntitySelectorConfig(domain=["binary_sensor", "sensor"])
)

_THRESHOLD_SELECTOR = NumberSelector(
    NumberSelectorConfig(min=-1000, max=1000, step=0.1, mode=NumberSelectorMode.BOX)
)

_DIRECTION_SELECTOR = SelectSelector(
    SelectSelectorConfig(
        options=[
            {"value": THRESHOLD_DIRECTION_ABOVE, "label": THRESHOLD_DIRECTION_ABOVE},
            {"value": THRESHOLD_DIRECTION_BELOW, "label": THRESHOLD_DIRECTION_BELOW},
        ],
        mode=SelectSelectorMode.DROPDOWN,
    )
)


def _notify_selector(hass) -> SelectSelector:
    """Build a multi-select dropdown from registered notify services."""
    services = hass.services.async_services().get("notify", {})
    options = [
        {"value": f"notify.{name}", "label": f"notify.{name}"}
        for name in sorted(services)
        if name != "persistent_notification"
    ]
    return SelectSelector(
        SelectSelectorConfig(
            options=options, multiple=True, mode=SelectSelectorMode.DROPDOWN
        )
    )


def _is_non_binary(hass, entity_id: str) -> bool:
    """Check if an entity is NOT a binary_sensor."""
    if not entity_id:
        return False
    return not entity_id.startswith("binary_sensor.")


def _user_schema(hass) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_NAME, default="Smart Mailbox"): str,
            vol.Required(CONF_FLAP_ENTITY): _ENTITY_SELECTOR,
            vol.Required(CONF_DOOR_ENTITY): _ENTITY_SELECTOR,
            vol.Required(
                CONF_DEBOUNCE_SECONDS, default=DEFAULT_DEBOUNCE_SECONDS
            ): vol.Coerce(int),
            vol.Required(CONF_NOTIFY_ENABLED, default=DEFAULT_NOTIFY_ENABLED): bool,
            vol.Required(CONF_NOTIFY_SERVICE, default=[]): _notify_selector(hass),
        }
    )


def _triggers_schema(
    flap_needs_threshold: bool, door_needs_threshold: bool
) -> vol.Schema:
    """Build schema for threshold configuration (step 2)."""
    fields = {}
    if flap_needs_threshold:
        fields[vol.Required(CONF_FLAP_THRESHOLD, default=DEFAULT_THRESHOLD)] = (
            _THRESHOLD_SELECTOR
        )
        fields[
            vol.Required(
                CONF_FLAP_THRESHOLD_DIRECTION, default=DEFAULT_THRESHOLD_DIRECTION
            )
        ] = _DIRECTION_SELECTOR
    if door_needs_threshold:
        fields[vol.Required(CONF_DOOR_THRESHOLD, default=DEFAULT_THRESHOLD)] = (
            _THRESHOLD_SELECTOR
        )
        fields[
            vol.Required(
                CONF_DOOR_THRESHOLD_DIRECTION, default=DEFAULT_THRESHOLD_DIRECTION
            )
        ] = _DIRECTION_SELECTOR
    return vol.Schema(fields)


def _options_schema(options: dict, hass) -> vol.Schema:
    notify_sel = _notify_selector(hass)

    fields = {
        vol.Optional(
            CONF_ENABLE_COUNTER,
            default=options.get(CONF_ENABLE_COUNTER, DEFAULT_ENABLE_COUNTER),
        ): bool,
        vol.Optional(
            CONF_ENABLE_AGE, default=options.get(CONF_ENABLE_AGE, DEFAULT_ENABLE_AGE)
        ): bool,
        vol.Optional(
            CONF_AGE_UNIT, default=options.get(CONF_AGE_UNIT, DEFAULT_AGE_UNIT)
        ): vol.In(["hours", "days"]),
        vol.Optional(
            CONF_RESET_ON_EMPTY,
            default=options.get(CONF_RESET_ON_EMPTY, DEFAULT_RESET_ON_EMPTY),
        ): bool,
        vol.Optional(
            CONF_DEBOUNCE_SECONDS,
            default=options.get(CONF_DEBOUNCE_SECONDS, DEFAULT_DEBOUNCE_SECONDS),
        ): vol.Coerce(int),
        vol.Optional(
            CONF_NOTIFY_ENABLED,
            default=options.get(CONF_NOTIFY_ENABLED, DEFAULT_NOTIFY_ENABLED),
        ): bool,
        vol.Optional(
            CONF_NOTIFY_SERVICE, default=options.get(CONF_NOTIFY_SERVICE, [])
        ): notify_sel,
        vol.Optional(
            CONF_NOTIFY_MESSAGE, default=options.get(CONF_NOTIFY_MESSAGE, "")
        ): str,
        vol.Optional(
            CONF_DOOR_NOTIFY_ENABLED,
            default=options.get(CONF_DOOR_NOTIFY_ENABLED, DEFAULT_DOOR_NOTIFY_ENABLED),
        ): bool,
        vol.Optional(
            CONF_DOOR_NOTIFY_SERVICE, default=options.get(CONF_DOOR_NOTIFY_SERVICE, [])
        ): notify_sel,
        vol.Optional(
            CONF_DOOR_NOTIFY_MESSAGE, default=options.get(CONF_DOOR_NOTIFY_MESSAGE, "")
        ): str,
        vol.Optional(
            CONF_FLAP_ENTITY, default=options.get(CONF_FLAP_ENTITY, "")
        ): _ENTITY_SELECTOR,
        vol.Optional(
            CONF_DOOR_ENTITY, default=options.get(CONF_DOOR_ENTITY, "")
        ): _ENTITY_SELECTOR,
    }

    # Show threshold fields if flap sensor is non-binary
    flap_entity = options.get(CONF_FLAP_ENTITY, "")
    if _is_non_binary(hass, flap_entity):
        fields[
            vol.Optional(
                CONF_FLAP_THRESHOLD,
                default=options.get(CONF_FLAP_THRESHOLD, DEFAULT_THRESHOLD),
            )
        ] = _THRESHOLD_SELECTOR
        fields[
            vol.Optional(
                CONF_FLAP_THRESHOLD_DIRECTION,
                default=options.get(
                    CONF_FLAP_THRESHOLD_DIRECTION, DEFAULT_THRESHOLD_DIRECTION
                ),
            )
        ] = _DIRECTION_SELECTOR

    # Show threshold fields if door sensor is non-binary
    door_entity = options.get(CONF_DOOR_ENTITY, "")
    if _is_non_binary(hass, door_entity):
        fields[
            vol.Optional(
                CONF_DOOR_THRESHOLD,
                default=options.get(CONF_DOOR_THRESHOLD, DEFAULT_THRESHOLD),
            )
        ] = _THRESHOLD_SELECTOR
        fields[
            vol.Optional(
                CONF_DOOR_THRESHOLD_DIRECTION,
                default=options.get(
                    CONF_DOOR_THRESHOLD_DIRECTION, DEFAULT_THRESHOLD_DIRECTION
                ),
            )
        ] = _DIRECTION_SELECTOR

    return vol.Schema(fields)


class MailboxConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 2

    def __init__(self):
        self._user_input: dict = {}

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            self._user_input = user_input

            flap = user_input[CONF_FLAP_ENTITY]
            door = user_input[CONF_DOOR_ENTITY]
            flap_needs = _is_non_binary(self.hass, flap)
            door_needs = _is_non_binary(self.hass, door)

            if flap_needs or door_needs:
                # Need threshold configuration — go to step 2
                self._user_input[CONF_FLAP_TRIGGER_MODE] = (
                    TRIGGER_MODE_THRESHOLD if flap_needs else TRIGGER_MODE_BINARY
                )
                self._user_input[CONF_DOOR_TRIGGER_MODE] = (
                    TRIGGER_MODE_THRESHOLD if door_needs else TRIGGER_MODE_BINARY
                )
                return await self.async_step_triggers(
                    flap_needs_threshold=flap_needs,
                    door_needs_threshold=door_needs,
                )
            else:
                # Both binary — set defaults and create entry
                self._user_input[CONF_FLAP_TRIGGER_MODE] = TRIGGER_MODE_BINARY
                self._user_input[CONF_DOOR_TRIGGER_MODE] = TRIGGER_MODE_BINARY
                return await self._create_entry()

        return self.async_show_form(step_id="user", data_schema=_user_schema(self.hass))

    async def async_step_triggers(
        self, user_input=None, flap_needs_threshold=None, door_needs_threshold=None
    ):
        if user_input is not None:
            self._user_input.update(user_input)
            return await self._create_entry()

        # Determine which sensors need threshold config
        if flap_needs_threshold is None:
            flap_needs_threshold = (
                self._user_input.get(CONF_FLAP_TRIGGER_MODE) == TRIGGER_MODE_THRESHOLD
            )
        if door_needs_threshold is None:
            door_needs_threshold = (
                self._user_input.get(CONF_DOOR_TRIGGER_MODE) == TRIGGER_MODE_THRESHOLD
            )

        schema = _triggers_schema(flap_needs_threshold, door_needs_threshold)
        return self.async_show_form(step_id="triggers", data_schema=schema)

    async def _create_entry(self):
        data = self._user_input
        unique = f"{data[CONF_FLAP_ENTITY]}_{data[CONF_DOOR_ENTITY]}"
        await self.async_set_unique_id(unique)
        self._abort_if_unique_id_configured()
        return self.async_create_entry(title=data[CONF_NAME], data=data)

    @staticmethod
    def async_get_options_flow(config_entry):
        return MailboxOptionsFlow(config_entry)


class MailboxOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, entry: config_entries.ConfigEntry):
        self.entry = entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            # Derive trigger modes from selected entities
            flap = user_input.get(CONF_FLAP_ENTITY, "")
            door = user_input.get(CONF_DOOR_ENTITY, "")
            user_input[CONF_FLAP_TRIGGER_MODE] = (
                TRIGGER_MODE_THRESHOLD
                if _is_non_binary(self.hass, flap)
                else TRIGGER_MODE_BINARY
            )
            user_input[CONF_DOOR_TRIGGER_MODE] = (
                TRIGGER_MODE_THRESHOLD
                if _is_non_binary(self.hass, door)
                else TRIGGER_MODE_BINARY
            )
            return self.async_create_entry(title="", data=user_input)

        merged = {**self.entry.data, **self.entry.options}
        if not merged.get(CONF_NOTIFY_MESSAGE) or not merged.get(
            CONF_DOOR_NOTIFY_MESSAGE
        ):
            translations = await async_get_translations(
                self.hass, self.hass.config.language, "options", {DOMAIN}
            )
            if not merged.get(CONF_NOTIFY_MESSAGE):
                merged[CONF_NOTIFY_MESSAGE] = translations.get(
                    TRANSLATION_KEY_DEFAULT_NOTIFY, ""
                )
            if not merged.get(CONF_DOOR_NOTIFY_MESSAGE):
                merged[CONF_DOOR_NOTIFY_MESSAGE] = translations.get(
                    TRANSLATION_KEY_DEFAULT_DOOR_NOTIFY, ""
                )
        return self.async_show_form(
            step_id="init", data_schema=_options_schema(merged, self.hass)
        )
