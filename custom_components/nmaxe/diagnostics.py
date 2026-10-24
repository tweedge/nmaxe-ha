"""Diagnostics support for the NMAxe integration."""

from __future__ import annotations

from dataclasses import asdict
from typing import TYPE_CHECKING, Any

from .const import CONF_HOST

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .data import NMAxeConfigEntry

_SECRET_KEYS = frozenset(
    {
        "api_key",
        "pass",
        "password",
        "passwd",
        "pwd",
        "secret",
        "token",
        "wifi_pass",
        "wifipass",
    }
)


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: (
                "**REDACTED**" if str(key).casefold() in _SECRET_KEYS else _redact(item)
            )
            for key, item in value.items()
        }
    if isinstance(value, list | tuple):
        return [_redact(item) for item in value]
    return value


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: NMAxeConfigEntry,
) -> dict[str, Any]:
    """Return config entry diagnostics with secret-like keys removed."""
    coordinator = entry.runtime_data.coordinator
    payload: dict[str, Any] = {
        "entry": {
            "host": entry.data.get(CONF_HOST),
            "options": dict(entry.options),
        },
        "last_update_success": coordinator.last_update_success,
        "update_interval_seconds": (
            coordinator.update_interval.total_seconds()
            if coordinator.update_interval
            else None
        ),
        "data": asdict(coordinator.data) if coordinator.data else None,
    }
    return _redact(payload)
