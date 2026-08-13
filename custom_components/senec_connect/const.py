"""Constants for the SENEC Connect integration."""

DOMAIN = "senec_connect"

API_BASE_URL = "https://apim-eds-gwc-prod.azure-api.net/senec-connect"

DEFAULT_POLLING_INTERVAL = 60  # seconds
MIN_POLLING_INTERVAL = 60  # seconds

REQUEST_TIMEOUT = 30  # seconds

INCLUDE_FULL = "battery,bessNameplate,meter,evse"
INCLUDE_VALIDATE = "bessNameplate"
