"""Validated data models for the AxeOS API."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Final

from .const import SUPPORTED_MODEL_PREFIXES
from .exceptions import NMAxeDataError

_NUMBER_RE: Final = re.compile(
    r"^\s*([-+]?(?:\d+(?:\.\d*)?|\.\d+))\s*([KMGTPEZY]?)\s*$",
    re.IGNORECASE,
)
_SUFFIX_MULTIPLIERS: Final = {
    "": 1.0,
    "K": 1e3,
    "M": 1e6,
    "G": 1e9,
    "T": 1e12,
    "P": 1e15,
    "E": 1e18,
    "Z": 1e21,
    "Y": 1e24,
}


@dataclass(frozen=True, slots=True)
class PowerData:
    """Power and input electrical measurements."""

    power_w: float | None
    voltage_mv: int | None
    current_ma: int | None


@dataclass(frozen=True, slots=True)
class TemperatureData:
    """ASIC and voltage regulator temperatures."""

    asic_c: float | None
    vcore_c: float | None


@dataclass(frozen=True, slots=True)
class AsicData:
    """ASIC identification and configuration."""

    count: int | None
    model: str | None
    vcore_requested_mv: int | None
    vcore_actual_mv: int | None
    frequency_mhz: int | None
    small_core_count: int | None


@dataclass(frozen=True, slots=True)
class MinerData:
    """Mining runtime statistics."""

    state: str
    paused: bool
    pause_reason: str | None
    hash_rate_ghs: float | None
    best_diff_ever: float | None
    best_diff_session: float | None
    network_diff: float | None
    pool_diff: float | None
    last_diff: float | None
    block_hits: int | None
    shares_accepted: int | None
    shares_rejected: int | None
    uptime_seconds: int | None
    uptime_ever: int | None
    free_heap: int | None
    min_free_heap: int | None
    benchmark_mode: int | None


@dataclass(frozen=True, slots=True)
class IdentityData:
    """Board identity and network information."""

    fw_version: str | None
    hw_model: str
    display_name: str
    host_name: str
    ssid: str | None
    rssi: int | None
    app_sha256: str | None


@dataclass(frozen=True, slots=True)
class StratumData:
    """The active stratum connection, without its password."""

    url: str | None
    user: str | None


@dataclass(frozen=True, slots=True)
class FanData:
    """A single fan's reported state."""

    id: int
    speed: int | None
    rpm: int | None


@dataclass(frozen=True, slots=True)
class SystemInfo:
    """Parsed and sanitized /api/system/info data."""

    power: PowerData
    temps: TemperatureData
    asic: AsicData
    miner: MinerData
    identity: IdentityData
    stratum: StratumData
    fans: tuple[FanData, ...]


@dataclass(frozen=True, slots=True)
class PoolInfo:
    """A configured stratum pool, without its password."""

    url: str | None
    user: str | None


@dataclass(frozen=True, slots=True)
class PoolConfig:
    """The miner's active, primary, and fallback pool configuration."""

    used: PoolInfo | None
    primary: PoolInfo | None
    fallback: PoolInfo | None


@dataclass(frozen=True, slots=True)
class NMAxeData:
    """All data fetched during one coordinator update."""

    info: SystemInfo
    pools: PoolConfig | None


def _as_mapping(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        msg = f"Expected {field} to be a JSON object"
        raise NMAxeDataError(msg)
    return value


def _optional_mapping(value: Any, field: str) -> dict[str, Any]:
    if value is None:
        return {}
    return _as_mapping(value, field)


def _as_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_int(value: Any) -> int | None:
    number = _as_float(value)
    if value is None or isinstance(value, bool):
        return None
    return int(number) if number is not None else None


def _as_str(value: Any) -> str | None:
    return value if isinstance(value, str) else None


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    if isinstance(value, str):
        return value.strip().casefold() in {"1", "true", "yes", "on"}
    return False


def _as_compact_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    if not isinstance(value, str):
        return None
    match = _NUMBER_RE.fullmatch(value.replace(",", ""))
    if match is None:
        return None
    number = float(match.group(1))
    multiplier = _SUFFIX_MULTIPLIERS[match.group(2).upper()]
    return number * multiplier


def _parse_fans(value: Any) -> tuple[FanData, ...]:
    if not isinstance(value, list):
        return ()
    fans: list[FanData] = []
    for index, raw_fan in enumerate(value):
        if not isinstance(raw_fan, dict):
            continue
        fan_id = _as_int(raw_fan.get("id"))
        fans.append(
            FanData(
                id=fan_id if fan_id is not None else index,
                speed=_as_int(raw_fan.get("speed")),
                rpm=_as_int(raw_fan.get("rpm")),
            )
        )
    return tuple(fans)


def _parse_pool(value: Any) -> PoolInfo | None:
    if not isinstance(value, dict):
        return None
    return PoolInfo(url=_as_str(value.get("url")), user=_as_str(value.get("user")))


def parse_system_info(payload: dict[str, Any]) -> SystemInfo:
    """Parse and sanitize a /api/system/info response."""
    identity_raw = _as_mapping(payload.get("identity"), "identity")
    miner_raw = _as_mapping(payload.get("miner"), "miner")
    power_raw = _optional_mapping(payload.get("power"), "power")
    temps_raw = _optional_mapping(payload.get("temps"), "temps")
    asic_raw = _optional_mapping(payload.get("asic"), "asic")
    stratum_raw = _optional_mapping(payload.get("stratum"), "stratum")

    hw_model = _as_str(identity_raw.get("hwModel")) or ""
    host_name = _as_str(identity_raw.get("hostName")) or ""
    if not hw_model or not host_name:
        msg = "The miner did not report its model and hostname"
        raise NMAxeDataError(msg)

    identity = IdentityData(
        fw_version=_as_str(identity_raw.get("fwVersion")),
        hw_model=hw_model,
        display_name=_as_str(identity_raw.get("displayName")) or hw_model,
        host_name=host_name,
        ssid=_as_str(identity_raw.get("ssid")),
        rssi=_as_int(identity_raw.get("rssi")),
        app_sha256=_as_str(identity_raw.get("appSha256")),
    )

    miner = MinerData(
        state=_as_str(miner_raw.get("state")) or "unknown",
        paused=_as_bool(miner_raw.get("paused")),
        pause_reason=_as_str(miner_raw.get("pauseReason")),
        hash_rate_ghs=_as_float(miner_raw.get("hashRate")),
        best_diff_ever=_as_compact_number(miner_raw.get("bestDiffEver")),
        best_diff_session=_as_compact_number(miner_raw.get("bestDiffSession")),
        network_diff=_as_compact_number(miner_raw.get("networkDiff")),
        pool_diff=_as_compact_number(miner_raw.get("poolDiff")),
        last_diff=_as_compact_number(miner_raw.get("lastDiff")),
        block_hits=_as_int(miner_raw.get("blkhits")),
        shares_accepted=_as_int(miner_raw.get("sAccepted")),
        shares_rejected=_as_int(miner_raw.get("sRejected")),
        uptime_seconds=_as_int(miner_raw.get("uptimeSeconds")),
        uptime_ever=_as_int(miner_raw.get("uptimeEver")),
        free_heap=_as_int(miner_raw.get("freeHeap")),
        min_free_heap=_as_int(miner_raw.get("minFreeHeap")),
        benchmark_mode=_as_int(miner_raw.get("bmMode")),
    )

    return SystemInfo(
        power=PowerData(
            power_w=_as_float(power_raw.get("power")),
            voltage_mv=_as_int(power_raw.get("vbus")),
            current_ma=_as_int(power_raw.get("ibus")),
        ),
        temps=TemperatureData(
            asic_c=_as_float(temps_raw.get("asic")),
            vcore_c=_as_float(temps_raw.get("vcore")),
        ),
        asic=AsicData(
            count=_as_int(asic_raw.get("count")),
            model=_as_str(asic_raw.get("model")),
            vcore_requested_mv=_as_int(asic_raw.get("vcoreReq")),
            vcore_actual_mv=_as_int(asic_raw.get("vcoreReal")),
            frequency_mhz=_as_int(asic_raw.get("freqReq")),
            small_core_count=_as_int(asic_raw.get("smallCoreCnt")),
        ),
        miner=miner,
        identity=identity,
        stratum=StratumData(
            url=_as_str(stratum_raw.get("url")),
            user=_as_str(stratum_raw.get("user")),
        ),
        fans=_parse_fans(payload.get("fans")),
    )


def parse_pool_config(payload: dict[str, Any]) -> PoolConfig:
    """Parse a /api/setting/mining response without retaining passwords."""
    stratum_raw = _optional_mapping(payload.get("stratum"), "stratum")
    return PoolConfig(
        used=_parse_pool(stratum_raw.get("used")),
        primary=_parse_pool(stratum_raw.get("primary")),
        fallback=_parse_pool(stratum_raw.get("fallback")),
    )


def is_supported_model(identity: IdentityData) -> bool:
    """Return whether the reported board model is supported."""
    return identity.hw_model.strip().casefold().startswith(SUPPORTED_MODEL_PREFIXES)


def build_unique_id(identity: IdentityData) -> str:
    """Build a stable config-entry unique ID from board identity."""
    model = identity.hw_model.strip().casefold()
    host = identity.host_name.strip().casefold()
    return f"{model}-{host}"
