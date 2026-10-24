"""Tests for sanitized AxeOS data models."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import replace

import pytest

from custom_components.nmaxe.exceptions import NMAxeDataError
from custom_components.nmaxe.models import (
    _as_compact_number,
    build_unique_id,
    format_compact_number,
    is_supported_model,
    parse_pool_config,
    parse_system_info,
)
from tests.fixtures import POOL_CONFIG_PAYLOAD, SYSTEM_INFO, SYSTEM_INFO_PAYLOAD


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("1.23M", 1_230_000),
        ("88.55T", 88_550_000_000_000),
        ("456.7K", 456_700),
        ("65536", 65_536),
        ("1,024", 1024),
        (123, 123),
        (1.5, 1.5),
        ("not a number", None),
        (None, None),
        (True, None),
    ],
)
def test_compact_number(raw: object, expected: float | None) -> None:
    """Parse firmware-formatted difficulty and hashrate values."""
    assert _as_compact_number(raw) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, None),
        (0, "0"),
        (999, "999"),
        (1000, "1 K"),
        (2500, "2.5 K"),
        (65_536, "65.54 K"),
        (999_999, "1 M"),
        (1_230_000, "1.23 M"),
        (88_550_000_000_000, "88.55 T"),
        (1.5, "1.5"),
        (-2500, "-2.5 K"),
        (float("nan"), None),
        (float("inf"), None),
    ],
)
def test_format_compact_number(value: float | None, expected: str | None) -> None:
    """Format large difficulty values with compact suffixes."""
    assert format_compact_number(value) == expected


@pytest.mark.parametrize("field", ["identity", "miner"])
def test_missing_required_objects(field: str) -> None:
    """Require the identity and miner objects."""
    payload = deepcopy(SYSTEM_INFO_PAYLOAD)
    payload.pop(field)
    with pytest.raises(NMAxeDataError):
        parse_system_info(payload)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("hwModel", ""),
        ("hostName", ""),
        ("hostName", None),
    ],
)
def test_missing_identity_values(field: str, value: object) -> None:
    """Require a model and hostname for a unique device identity."""
    payload = deepcopy(SYSTEM_INFO_PAYLOAD)
    payload["identity"][field] = value
    with pytest.raises(NMAxeDataError):
        parse_system_info(payload)


def test_paused_is_parsed() -> None:
    """Parse a paused miner and its reason."""
    payload = deepcopy(SYSTEM_INFO_PAYLOAD)
    payload["miner"]["paused"] = "true"
    payload["miner"]["pauseReason"] = "user"
    info = parse_system_info(payload)
    assert info.miner.paused is True
    assert info.miner.pause_reason == "user"


@pytest.mark.parametrize(
    ("model", "expected"),
    [
        ("NMAxe", True),
        ("NMAxeGamma", True),
        ("NMQAxe++", True),
        ("OtherMiner", False),
        ("", False),
    ],
)
def test_supported_models(model: str, expected: bool) -> None:
    """Accept the NMAxe and NMQAxe families only."""
    identity = replace(SYSTEM_INFO.identity, hw_model=model)
    assert is_supported_model(identity) is expected


def test_build_unique_id() -> None:
    """Build a stable unique ID from model and hostname."""
    assert build_unique_id(SYSTEM_INFO.identity) == "nmaxegamma-nmaxe-gamma-01"


def test_pool_config_without_secrets() -> None:
    """Drop every password field from pool settings."""
    pools = parse_pool_config(POOL_CONFIG_PAYLOAD)
    assert pools.used is not None
    assert pools.used.user == "bc1qexample.worker1"
    assert pools.primary is not None
    assert pools.fallback is not None
    assert "pwd" not in repr(pools)


def test_empty_pool_config() -> None:
    """Return empty pool slots when stratum settings are absent."""
    pools = parse_pool_config({})
    assert pools.used is None
    assert pools.primary is None
    assert pools.fallback is None
