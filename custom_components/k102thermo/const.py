"""Constants for the K102 Thermo (Klima102) integration."""

from datetime import timedelta

DOMAIN = "k102thermo"

API_BASE = "https://home.klima102.com/thermo-server"
TOKEN_URL = "https://home.klima102.com/uaa2/oauth/token"

CONF_CLIENT_ID = "client_id"
CONF_CLIENT_SECRET = "client_secret"

DEFAULT_SCAN_INTERVAL = timedelta(seconds=60)
REQUEST_TIMEOUT = 15
