from __future__ import annotations

DOMAIN = "briefkasten"
PLATFORMS = ["binary_sensor", "sensor"]

# Default source entities (can be changed via config/options flow)
DEFAULT_KLAPPE_ENTITY = "binary_sensor.briefkasten_klappe_offnung"
DEFAULT_TUER_ENTITY = "binary_sensor.briefkasten_tur_offnung"

# Config / options keys
CONF_KLAPPE_ENTITY = "klappe_entity"
CONF_TUER_ENTITY = "tuer_entity"
CONF_DEBOUNCE_SECONDS = "debounce_seconds"
CONF_NOTIFY_ENABLED = "notify"
CONF_NOTIFY_SERVICE = "notify_service"

CONF_ENABLE_COUNTER = "enable_counter"
CONF_ENABLE_AGE = "enable_age"
CONF_AGE_UNIT = "age_unit"          # "hours" or "days"
CONF_RESET_ON_EMPTY = "reset_on_empty"

DEFAULT_DEBOUNCE_SECONDS = 3
DEFAULT_NOTIFY_ENABLED = False
DEFAULT_NOTIFY_SERVICE = "notify.notify"
DEFAULT_ENABLE_COUNTER = True
DEFAULT_ENABLE_AGE = True
DEFAULT_AGE_UNIT = "hours"
DEFAULT_RESET_ON_EMPTY = False

SERVICE_RESET_COUNTER = "reset_counter"

# Dispatcher signal prefix
SIGNAL_PREFIX = "briefkasten_update_"

# Storage
STORAGE_VERSION = 1
STORAGE_KEY_PREFIX = "briefkasten_state_"
