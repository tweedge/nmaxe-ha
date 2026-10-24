"""Constants for the NMAxe integration."""

from __future__ import annotations

from logging import Logger, getLogger

DOMAIN = "nmaxe"
LOGGER: Logger = getLogger(__package__)

CONFIG_ENTRY_VERSION = 3
REMOVED_ENTITY_KEYS = frozenset({"mining", "paused"})
DEFAULT_ENABLED_ENTITY_KEYS = frozenset(
    {
        "blocks_found",
        "efficiency",
        "hashrate",
        "miner_state",
        "pool_connected",
        "power",
        "share_acceptance_rate",
    }
)

MANUFACTURER = "NMTech"
SUPPORTED_MODEL_PREFIXES = ("nmaxe", "nmqaxe")

CONF_HOST = "host"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_POOL_REFRESH_INTERVAL = "pool_refresh_interval"

DEFAULT_SCAN_INTERVAL = 60
MIN_SCAN_INTERVAL = 15
MAX_SCAN_INTERVAL = 3600

DEFAULT_POOL_REFRESH_INTERVAL = 600
MIN_POOL_REFRESH_INTERVAL = 60
MAX_POOL_REFRESH_INTERVAL = 86400

REQUEST_TIMEOUT = 10
MAX_RESPONSE_BYTES = 64 * 1024

API_SYSTEM_INFO = "/api/system/info"
API_POOL_SETTINGS = "/api/setting/mining"
