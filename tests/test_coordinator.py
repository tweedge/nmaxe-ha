"""Tests for coordinator polling and pool-setting caching."""

from __future__ import annotations

import time
from datetime import timedelta
from unittest.mock import AsyncMock, Mock

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.nmaxe.const import (
    CONF_HOST,
    CONF_POOL_REFRESH_INTERVAL,
    CONF_SCAN_INTERVAL,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
)
from custom_components.nmaxe.coordinator import NMAxeCoordinator
from tests.fixtures import HOST, POOL_CONFIG, SYSTEM_INFO, UNIQUE_ID


def _client() -> Mock:
    client = Mock()
    client.host = HOST
    client.async_get_system_info = AsyncMock(return_value=SYSTEM_INFO)
    client.async_get_pool_config = AsyncMock(return_value=POOL_CONFIG)
    return client


def _entry(options: dict[str, int]) -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: HOST},
        unique_id=UNIQUE_ID,
        options=options,
    )


async def test_pool_settings_are_cached(hass: HomeAssistant) -> None:
    """Read pool settings once per configured refresh interval."""
    entry = _entry({CONF_POOL_REFRESH_INTERVAL: 600})
    entry.add_to_hass(hass)
    client = _client()
    coordinator = NMAxeCoordinator(hass, entry, client)

    await coordinator.async_refresh()
    await coordinator.async_refresh()
    assert client.async_get_pool_config.await_count == 1

    coordinator._pool_last_attempt = time.monotonic() - 601
    await coordinator.async_refresh()

    assert coordinator.last_update_success
    assert coordinator.data.info is SYSTEM_INFO
    assert coordinator.data.pools is POOL_CONFIG
    assert client.async_get_pool_config.await_count == 2


async def test_pool_settings_can_be_disabled(hass: HomeAssistant) -> None:
    """Do not read the sensitive pool settings endpoint when disabled."""
    entry = _entry({CONF_POOL_REFRESH_INTERVAL: 0})
    entry.add_to_hass(hass)
    client = _client()
    coordinator = NMAxeCoordinator(hass, entry, client)

    await coordinator.async_refresh()
    await coordinator.async_refresh()

    assert coordinator.data.pools is None
    client.async_get_pool_config.assert_not_awaited()


async def test_scan_interval_is_bounded(hass: HomeAssistant) -> None:
    """Clamp malformed or out-of-range scan intervals."""
    low = _entry({CONF_SCAN_INTERVAL: 1})
    low.add_to_hass(hass)
    high = _entry({CONF_SCAN_INTERVAL: 999999})
    high.add_to_hass(hass)

    low_coordinator = NMAxeCoordinator(hass, low, _client())
    high_coordinator = NMAxeCoordinator(hass, high, _client())

    assert low_coordinator.update_interval == timedelta(seconds=MIN_SCAN_INTERVAL)
    assert high_coordinator.update_interval == timedelta(seconds=MAX_SCAN_INTERVAL)
