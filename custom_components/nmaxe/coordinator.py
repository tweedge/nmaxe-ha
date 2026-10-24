"""Data update coordinator for the NMAxe integration."""

from __future__ import annotations

import time
from datetime import timedelta
from typing import TYPE_CHECKING

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_POOL_REFRESH_INTERVAL,
    CONF_SCAN_INTERVAL,
    DEFAULT_POOL_REFRESH_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    LOGGER,
    MAX_POOL_REFRESH_INTERVAL,
    MAX_SCAN_INTERVAL,
    MIN_POOL_REFRESH_INTERVAL,
    MIN_SCAN_INTERVAL,
)
from .exceptions import NMAxeError
from .models import NMAxeData, PoolConfig

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .api import NMAxeApiClient
    from .data import NMAxeConfigEntry


def _as_seconds(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _clamped_seconds(
    value: object,
    default: int,
    minimum: int,
    maximum: int,
) -> int:
    seconds = _as_seconds(value)
    if seconds is None:
        return default
    return max(minimum, min(maximum, seconds))


def _pool_refresh_seconds(value: object) -> int:
    seconds = _as_seconds(value)
    if seconds is None:
        return DEFAULT_POOL_REFRESH_INTERVAL
    if seconds == 0:
        return 0
    return max(MIN_POOL_REFRESH_INTERVAL, min(MAX_POOL_REFRESH_INTERVAL, seconds))


class NMAxeCoordinator(DataUpdateCoordinator[NMAxeData]):
    """Poll a miner slowly and cache its less volatile pool settings."""

    config_entry: NMAxeConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: NMAxeConfigEntry,
        client: NMAxeApiClient,
    ) -> None:
        """Initialize the coordinator from config entry options."""
        scan_seconds = _clamped_seconds(
            entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
            DEFAULT_SCAN_INTERVAL,
            MIN_SCAN_INTERVAL,
            MAX_SCAN_INTERVAL,
        )
        super().__init__(
            hass,
            LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_seconds),
            always_update=False,
        )
        self.client = client
        self._pool_refresh_seconds = _pool_refresh_seconds(
            entry.options.get(
                CONF_POOL_REFRESH_INTERVAL,
                DEFAULT_POOL_REFRESH_INTERVAL,
            )
        )
        self._pool_config: PoolConfig | None = None
        self._pool_last_attempt: float | None = None

    async def _async_update_data(self) -> NMAxeData:
        try:
            info = await self.client.async_get_system_info()
        except NMAxeError as err:
            msg = f"Unable to read system information from {self.client.host}: {err}"
            raise UpdateFailed(msg) from err

        await self._async_refresh_pools()
        return NMAxeData(info=info, pools=self._pool_config)

    async def _async_refresh_pools(self) -> None:
        if self._pool_refresh_seconds == 0:
            return

        now = time.monotonic()
        if (
            self._pool_last_attempt is not None
            and now - self._pool_last_attempt < self._pool_refresh_seconds
        ):
            return

        self._pool_last_attempt = now
        try:
            self._pool_config = await self.client.async_get_pool_config()
        except NMAxeError as err:
            LOGGER.debug(
                "Unable to refresh pool settings from %s: %s",
                self.client.host,
                err,
            )
