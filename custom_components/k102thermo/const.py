"""Constants for the K102 Thermo (Klima102) integration."""

DOMAIN = "k102thermo"

API_BASE = "https://home.klima102.com/thermo-server"
TOKEN_URL = "https://home.klima102.com/uaa2/oauth/token"

CONF_CLIENT_ID = "client_id"
CONF_CLIENT_SECRET = "client_secret"

CONF_SCAN_INTERVAL = "scan_interval"
DEFAULT_SCAN_INTERVAL = 60  # seconds
MIN_SCAN_INTERVAL = 30
MAX_SCAN_INTERVAL = 3600
REQUEST_TIMEOUT = 15
