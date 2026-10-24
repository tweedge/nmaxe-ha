"""Tests for the AxeOS HTTP client and host normalization."""

from __future__ import annotations

import aiohttp
import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from pytest_homeassistant_custom_component.test_util.aiohttp import (
    AiohttpClientMocker,
)

from custom_components.nmaxe.api import NMAxeApiClient, normalize_host
from custom_components.nmaxe.const import MAX_RESPONSE_BYTES
from custom_components.nmaxe.exceptions import (
    NMAxeConnectionError,
    NMAxeResponseError,
)
from tests.fixtures import (
    ENTITY_URL,
    HOST,
    POOL_CONFIG_PAYLOAD,
    SECRET,
    SYSTEM_INFO_PAYLOAD,
)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("192.168.1.100", "192.168.1.100"),
        ("http://192.168.1.100/", "192.168.1.100"),
        ("miner.local", "miner.local"),
        ("miner.local:8080", "miner.local:8080"),
        ("[fe80::1]", "[fe80::1]"),
    ],
)
def test_normalize_host(value: str, expected: str) -> None:
    """Normalize supported host forms."""
    assert normalize_host(value) == expected


@pytest.mark.parametrize(
    "value",
    [
        "",
        "https://192.168.1.100",
        "http://192.168.1.100/status",
        "http://user:pass@192.168.1.100",
        "http://192.168.1.100:0",
        "http://192.168.1.100?query=1",
        "http://bad host",
    ],
)
def test_normalize_host_rejects_unsafe_values(value: str) -> None:
    """Reject schemes, paths, credentials, and malformed ports."""
    with pytest.raises(ValueError):
        normalize_host(value)


async def test_get_system_info(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """Fetch and sanitize system information."""
    aioclient_mock.get(f"{ENTITY_URL}/api/system/info", json=SYSTEM_INFO_PAYLOAD)
    info = await NMAxeApiClient(
        HOST,
        async_get_clientsession(hass),
    ).async_get_system_info()

    assert info.miner.hash_rate_ghs == 1200.5
    assert info.miner.best_diff_ever == 1_230_000
    assert info.identity.hw_model == "NMAxeGamma"
    assert info.stratum.url == "stratum+tcp://pool.example.com:3333"
    assert info.stratum.user == "bc1qexample.worker1"
    assert info.fans[0].rpm == 2800
    assert not hasattr(info.stratum, "pwd")
    assert SECRET not in repr(info)


async def test_get_pool_config_without_passwords(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """Fetch pool configuration without retaining passwords."""
    aioclient_mock.get(
        f"{ENTITY_URL}/api/setting/mining",
        json=POOL_CONFIG_PAYLOAD,
    )
    pools = await NMAxeApiClient(
        HOST,
        async_get_clientsession(hass),
    ).async_get_pool_config()

    assert pools.primary is not None
    assert pools.primary.url == "stratum+tcp://pool.example.com:3333"
    assert pools.fallback is not None
    assert pools.fallback.url == "stratum+tcp://fallback.example.com:3333"
    assert SECRET not in repr(pools)


async def test_connection_error(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """Surface transport failures as connection errors."""
    aioclient_mock.get(
        f"{ENTITY_URL}/api/system/info",
        exc=aiohttp.ClientError("boom"),
    )
    with pytest.raises(NMAxeConnectionError):
        await NMAxeApiClient(
            HOST,
            async_get_clientsession(hass),
        ).async_get_system_info()


async def test_invalid_json(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """Reject malformed JSON."""
    aioclient_mock.get(f"{ENTITY_URL}/api/system/info", text="{broken")
    with pytest.raises(NMAxeResponseError):
        await NMAxeApiClient(
            HOST,
            async_get_clientsession(hass),
        ).async_get_system_info()


async def test_non_object_json(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """Reject non-object JSON payloads."""
    aioclient_mock.get(
        f"{ENTITY_URL}/api/system/info",
        json=["not", "an", "object"],
    )
    with pytest.raises(NMAxeResponseError):
        await NMAxeApiClient(
            HOST,
            async_get_clientsession(hass),
        ).async_get_system_info()


async def test_oversized_response(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """Reject responses larger than the configured cap."""
    aioclient_mock.get(
        f"{ENTITY_URL}/api/system/info",
        text="x" * (MAX_RESPONSE_BYTES + 1),
    )
    with pytest.raises(NMAxeResponseError):
        await NMAxeApiClient(
            HOST,
            async_get_clientsession(hass),
        ).async_get_system_info()


async def test_http_error(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """Reject non-success HTTP statuses."""
    aioclient_mock.get(f"{ENTITY_URL}/api/system/info", status=500)
    with pytest.raises(NMAxeResponseError):
        await NMAxeApiClient(
            HOST,
            async_get_clientsession(hass),
        ).async_get_system_info()


async def test_redirect_not_followed(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """Do not follow redirects from the miner."""
    aioclient_mock.get(
        f"{ENTITY_URL}/api/system/info",
        status=302,
        headers={"Location": "http://example.invalid/"},
    )
    with pytest.raises(NMAxeResponseError):
        await NMAxeApiClient(
            HOST,
            async_get_clientsession(hass),
        ).async_get_system_info()
