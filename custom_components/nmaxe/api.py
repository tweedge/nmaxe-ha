"""HTTP client for the AxeOS API."""

from __future__ import annotations

import asyncio
import json
import re
from http import HTTPStatus
from typing import Any
from urllib.parse import urlsplit

import aiohttp

from .const import (
    API_POOL_SETTINGS,
    API_SYSTEM_INFO,
    MAX_RESPONSE_BYTES,
    REQUEST_TIMEOUT,
)
from .exceptions import NMAxeConnectionError, NMAxeResponseError
from .models import PoolConfig, SystemInfo, parse_pool_config, parse_system_info

_ALLOWED_HOST = re.compile(r"[A-Za-z0-9._:%-]+")


def _with_scheme(value: str) -> str:
    candidate = value.strip()
    if not candidate:
        msg = "A device IP address or hostname is required"
        raise ValueError(msg)
    if "://" not in candidate:
        return f"http://{candidate}"
    return candidate


def _validated_host(candidate: str) -> tuple[str, int | None]:
    parsed = urlsplit(candidate)
    if parsed.scheme != "http":
        msg = "Only plain HTTP is supported"
        raise ValueError(msg)
    if parsed.username is not None or parsed.password is not None:
        msg = "Credentials are not allowed in the host"
        raise ValueError(msg)
    if parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
        msg = "The host must not contain a path, query, or fragment"
        raise ValueError(msg)
    if parsed.hostname is None:
        msg = "The device IP address or hostname is invalid"
        raise ValueError(msg)

    host = parsed.hostname
    if not _ALLOWED_HOST.fullmatch(host):
        msg = "The device IP address or hostname contains invalid characters"
        raise ValueError(msg)

    try:
        port = parsed.port
    except ValueError as err:
        msg = "The device port is invalid"
        raise ValueError(msg) from err

    if port is not None and not 1 <= port <= 65535:
        msg = "The device port must be between 1 and 65535"
        raise ValueError(msg)
    return host, port


def normalize_host(value: str) -> str:
    """Normalize a user-supplied host into a safe host[:port] value."""
    host, port = _validated_host(_with_scheme(value))
    if ":" in host:
        host = f"[{host}]"
    if port is not None:
        return f"{host}:{port}"
    return host


class NMAxeApiClient:
    """Read-only client for a single AxeOS miner."""

    def __init__(self, host: str, session: aiohttp.ClientSession) -> None:
        """Initialize the client for a normalized host."""
        self.host = normalize_host(host)
        self._session = session

    async def async_get_system_info(self) -> SystemInfo:
        """Fetch and parse /api/system/info."""
        payload = await self._async_get_json(API_SYSTEM_INFO)
        return parse_system_info(payload)

    async def async_get_pool_config(self) -> PoolConfig:
        """Fetch and sanitize /api/setting/mining."""
        payload = await self._async_get_json(API_POOL_SETTINGS)
        return parse_pool_config(payload)

    async def _async_get_json(self, path: str) -> dict[str, Any]:
        url = f"http://{self.host}{path}"
        try:
            async with asyncio.timeout(REQUEST_TIMEOUT):
                async with self._session.get(
                    url,
                    allow_redirects=False,
                    headers={
                        "Accept": "application/json",
                        "Cache-Control": "no-cache",
                    },
                ) as response:
                    if response.status != HTTPStatus.OK:
                        msg = f"{self.host} returned HTTP {response.status}"
                        raise NMAxeResponseError(msg)

                    content_length = response.headers.get("Content-Length")
                    if content_length is not None:
                        try:
                            length = int(content_length)
                        except ValueError:
                            length = None
                        if length is not None and length > MAX_RESPONSE_BYTES:
                            msg = f"{self.host} returned an oversized response"
                            raise NMAxeResponseError(msg)

                    body = await response.content.read(MAX_RESPONSE_BYTES + 1)
        except TimeoutError as err:
            msg = f"Timed out connecting to {self.host}"
            raise NMAxeConnectionError(msg) from err
        except (aiohttp.ClientError, OSError) as err:
            msg = f"Unable to connect to {self.host}: {err}"
            raise NMAxeConnectionError(msg) from err

        if len(body) > MAX_RESPONSE_BYTES:
            msg = f"{self.host} returned an oversized response"
            raise NMAxeResponseError(msg)

        try:
            payload = json.loads(body)
        except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as err:
            msg = f"{self.host} returned invalid JSON"
            raise NMAxeResponseError(msg) from err

        if not isinstance(payload, dict):
            msg = f"{self.host} returned an unexpected JSON payload"
            raise NMAxeResponseError(msg)
        return payload
