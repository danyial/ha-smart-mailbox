from __future__ import annotations

DOMAIN = "smartmailbox"
PLATFORMS = ["binary_sensor", "sensor", "button"]

# Config / options keys
CONF_NAME = "name"
CONF_FLAP_ENTITY = "flap_entity"
CONF_DOOR_ENTITY = "door_entity"
CONF_DEBOUNCE_SECONDS = "debounce_seconds"
CONF_NOTIFY_ENABLED = "notify"
CONF_NOTIFY_SERVICE = "notify_service"
CONF_NOTIFY_MESSAGE = "notify_message"
CONF_DOOR_NOTIFY_ENABLED = "door_notify"
CONF_DOOR_NOTIFY_SERVICE = "door_notify_service"
CONF_DOOR_NOTIFY_MESSAGE = "door_notify_message"

CONF_ENABLE_COUNTER = "enable_counter"
CONF_ENABLE_AGE = "enable_age"
CONF_AGE_UNIT = "age_unit"  # "hours" or "days"
CONF_RESET_ON_EMPTY = "reset_on_empty"

# Trigger mode (per sensor)
CONF_FLAP_TRIGGER_MODE = "flap_trigger_mode"
CONF_FLAP_THRESHOLD = "flap_threshold"
CONF_FLAP_THRESHOLD_DIRECTION = "flap_threshold_direction"
CONF_DOOR_TRIGGER_MODE = "door_trigger_mode"
CONF_DOOR_THRESHOLD = "door_threshold"
CONF_DOOR_THRESHOLD_DIRECTION = "door_threshold_direction"

TRIGGER_MODE_BINARY = "binary"
TRIGGER_MODE_THRESHOLD = "threshold"

THRESHOLD_DIRECTION_ABOVE = "above"
THRESHOLD_DIRECTION_BELOW = "below"

DEFAULT_DEBOUNCE_SECONDS = 3
DEFAULT_TRIGGER_MODE = TRIGGER_MODE_BINARY
DEFAULT_THRESHOLD = 30.0
DEFAULT_THRESHOLD_DIRECTION = THRESHOLD_DIRECTION_ABOVE
DEFAULT_NOTIFY_ENABLED = False
DEFAULT_DOOR_NOTIFY_ENABLED = False
TRANSLATION_KEY_DEFAULT_NOTIFY = (
    f"component.{DOMAIN}.options.step.init.data_description.{CONF_NOTIFY_MESSAGE}"
)
TRANSLATION_KEY_DEFAULT_DOOR_NOTIFY = (
    f"component.{DOMAIN}.options.step.init.data_description.{CONF_DOOR_NOTIFY_MESSAGE}"
)
DEFAULT_ENABLE_COUNTER = True
DEFAULT_ENABLE_AGE = True
DEFAULT_AGE_UNIT = "hours"
DEFAULT_RESET_ON_EMPTY = False

SERVICE_RESET_COUNTER = "reset_counter"
SERVICE_MARK_EMPTY = "mark_empty"

# Dispatcher signal prefix
SIGNAL_PREFIX = "smartmailbox_update_"

# Storage
STORAGE_VERSION = 1
STORAGE_KEY_PREFIX = "smartmailbox_state_"
