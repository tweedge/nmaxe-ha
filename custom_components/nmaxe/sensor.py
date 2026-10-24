"""Sensor platform for the NMAxe integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from operator import attrgetter
from typing import TYPE_CHECKING

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    REVOLUTIONS_PER_MINUTE,
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfFrequency,
    UnitOfInformation,
    UnitOfPower,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.typing import StateType

from .entity import NMAxeEntity
from .models import NMAxeData

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import NMAxeCoordinator
    from .data import NMAxeConfigEntry

MINER_STATES = ("running", "pausing", "paused", "resuming", "error", "unknown")
POOL_SOURCES = ("primary", "fallback", "custom", "unknown")


@dataclass(frozen=True, kw_only=True)
class NMAxeSensorEntityDescription(SensorEntityDescription):
    """Describes a sensor and how to read its value."""

    value_fn: Callable[[NMAxeData], StateType]


def _scaled(value: float | None, divisor: float) -> float | None:
    return None if value is None else round(value / divisor, 3)


def _input_voltage(data: NMAxeData) -> float | None:
    return _scaled(data.info.power.voltage_mv, 1000)


def _input_current(data: NMAxeData) -> float | None:
    return _scaled(data.info.power.current_ma, 1000)


def _vcore_requested(data: NMAxeData) -> float | None:
    return _scaled(data.info.asic.vcore_requested_mv, 1000)


def _vcore_actual(data: NMAxeData) -> float | None:
    return _scaled(data.info.asic.vcore_actual_mv, 1000)


def _shares_submitted(data: NMAxeData) -> int | None:
    accepted = data.info.miner.shares_accepted
    rejected = data.info.miner.shares_rejected
    if accepted is None or rejected is None:
        return None
    return accepted + rejected


def _share_acceptance_rate(data: NMAxeData) -> float | None:
    submitted = _shares_submitted(data)
    accepted = data.info.miner.shares_accepted
    if not submitted or accepted is None:
        return None
    return round(accepted / submitted * 100, 1)


def _efficiency(data: NMAxeData) -> float | None:
    power = data.info.power.power_w
    hashrate = data.info.miner.hash_rate_ghs
    if power is None or hashrate is None or hashrate <= 0:
        return None
    return round(power / (hashrate / 1000), 2)


def _normalized_url(url: str | None) -> str | None:
    return url.strip().casefold() if url else None


def _active_pool_source(data: NMAxeData) -> str:
    active = _normalized_url(data.info.stratum.url)
    if active is None or data.pools is None:
        return "unknown"
    if data.pools.primary and _normalized_url(data.pools.primary.url) == active:
        return "primary"
    if data.pools.fallback and _normalized_url(data.pools.fallback.url) == active:
        return "fallback"
    return "custom"


def _primary_pool(data: NMAxeData) -> str | None:
    if data.pools is None or data.pools.primary is None:
        return None
    return data.pools.primary.url


def _fallback_pool(data: NMAxeData) -> str | None:
    if data.pools is None or data.pools.fallback is None:
        return None
    return data.pools.fallback.url


def _miner_state(data: NMAxeData) -> str:
    state = data.info.miner.state.strip().casefold()
    return state if state in MINER_STATES else "unknown"


def _fan_value(data: NMAxeData, fan_id: int, field: str) -> StateType:
    for fan in data.info.fans:
        if fan.id == fan_id:
            return getattr(fan, field)
    return None


SENSOR_DESCRIPTIONS: tuple[NMAxeSensorEntityDescription, ...] = (
    NMAxeSensorEntityDescription(
        key="hashrate",
        translation_key="hashrate",
        icon="mdi:speedometer",
        native_unit_of_measurement="GH/s",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=attrgetter("info.miner.hash_rate_ghs"),
    ),
    NMAxeSensorEntityDescription(
        key="power",
        translation_key="power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=attrgetter("info.power.power_w"),
    ),
    NMAxeSensorEntityDescription(
        key="input_voltage",
        translation_key="input_voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=3,
        value_fn=_input_voltage,
    ),
    NMAxeSensorEntityDescription(
        key="input_current",
        translation_key="input_current",
        device_class=SensorDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=_input_current,
    ),
    NMAxeSensorEntityDescription(
        key="asic_temperature",
        translation_key="asic_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=attrgetter("info.temps.asic_c"),
    ),
    NMAxeSensorEntityDescription(
        key="vcore_temperature",
        translation_key="vcore_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=attrgetter("info.temps.vcore_c"),
    ),
    NMAxeSensorEntityDescription(
        key="asic_frequency",
        translation_key="asic_frequency",
        device_class=SensorDeviceClass.FREQUENCY,
        icon="mdi:sine-wave",
        native_unit_of_measurement=UnitOfFrequency.MEGAHERTZ,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        value_fn=attrgetter("info.asic.frequency_mhz"),
    ),
    NMAxeSensorEntityDescription(
        key="vcore_requested",
        translation_key="vcore_requested",
        device_class=SensorDeviceClass.VOLTAGE,
        icon="mdi:chip",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=3,
        value_fn=_vcore_requested,
    ),
    NMAxeSensorEntityDescription(
        key="vcore_actual",
        translation_key="vcore_actual",
        device_class=SensorDeviceClass.VOLTAGE,
        icon="mdi:chip",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=3,
        value_fn=_vcore_actual,
    ),
    NMAxeSensorEntityDescription(
        key="asic_count",
        translation_key="asic_count",
        icon="mdi:chip",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=attrgetter("info.asic.count"),
    ),
    NMAxeSensorEntityDescription(
        key="asic_model",
        translation_key="asic_model",
        icon="mdi:chip",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=attrgetter("info.asic.model"),
    ),
    NMAxeSensorEntityDescription(
        key="best_difficulty_ever",
        translation_key="best_difficulty_ever",
        icon="mdi:trophy",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=attrgetter("info.miner.best_diff_ever"),
    ),
    NMAxeSensorEntityDescription(
        key="best_difficulty_session",
        translation_key="best_difficulty_session",
        icon="mdi:trophy-outline",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=attrgetter("info.miner.best_diff_session"),
    ),
    NMAxeSensorEntityDescription(
        key="network_difficulty",
        translation_key="network_difficulty",
        icon="mdi:earth",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=attrgetter("info.miner.network_diff"),
    ),
    NMAxeSensorEntityDescription(
        key="pool_difficulty",
        translation_key="pool_difficulty",
        icon="mdi:pool",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=attrgetter("info.miner.pool_diff"),
    ),
    NMAxeSensorEntityDescription(
        key="last_share_difficulty",
        translation_key="last_share_difficulty",
        icon="mdi:gauge",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=attrgetter("info.miner.last_diff"),
    ),
    NMAxeSensorEntityDescription(
        key="blocks_found",
        translation_key="blocks_found",
        icon="mdi:cube",
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=0,
        value_fn=attrgetter("info.miner.block_hits"),
    ),
    NMAxeSensorEntityDescription(
        key="shares_accepted",
        translation_key="shares_accepted",
        icon="mdi:check-circle",
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=0,
        value_fn=attrgetter("info.miner.shares_accepted"),
    ),
    NMAxeSensorEntityDescription(
        key="shares_rejected",
        translation_key="shares_rejected",
        icon="mdi:close-circle",
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=0,
        value_fn=attrgetter("info.miner.shares_rejected"),
    ),
    NMAxeSensorEntityDescription(
        key="shares_submitted",
        translation_key="shares_submitted",
        icon="mdi:send",
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=0,
        value_fn=_shares_submitted,
    ),
    NMAxeSensorEntityDescription(
        key="share_acceptance_rate",
        translation_key="share_acceptance_rate",
        icon="mdi:percent",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=_share_acceptance_rate,
    ),
    NMAxeSensorEntityDescription(
        key="efficiency",
        translation_key="efficiency",
        icon="mdi:lightning-bolt",
        native_unit_of_measurement="J/TH",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=_efficiency,
    ),
    NMAxeSensorEntityDescription(
        key="miner_state",
        translation_key="miner_state",
        device_class=SensorDeviceClass.ENUM,
        icon="mdi:state-machine",
        options=list(MINER_STATES),
        value_fn=_miner_state,
    ),
    NMAxeSensorEntityDescription(
        key="active_pool",
        translation_key="active_pool",
        icon="mdi:server-network",
        value_fn=attrgetter("info.stratum.url"),
    ),
    NMAxeSensorEntityDescription(
        key="pool_user",
        translation_key="pool_user",
        icon="mdi:key-variant",
        value_fn=attrgetter("info.stratum.user"),
    ),
    NMAxeSensorEntityDescription(
        key="primary_pool",
        translation_key="primary_pool",
        icon="mdi:server",
        value_fn=_primary_pool,
    ),
    NMAxeSensorEntityDescription(
        key="fallback_pool",
        translation_key="fallback_pool",
        icon="mdi:server-security",
        value_fn=_fallback_pool,
    ),
    NMAxeSensorEntityDescription(
        key="pool_source",
        translation_key="pool_source",
        device_class=SensorDeviceClass.ENUM,
        icon="mdi:source-branch",
        options=list(POOL_SOURCES),
        value_fn=_active_pool_source,
    ),
    NMAxeSensorEntityDescription(
        key="wifi_rssi",
        translation_key="wifi_rssi",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=attrgetter("info.identity.rssi"),
    ),
    NMAxeSensorEntityDescription(
        key="wifi_ssid",
        translation_key="wifi_ssid",
        icon="mdi:wifi",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=attrgetter("info.identity.ssid"),
    ),
    NMAxeSensorEntityDescription(
        key="free_heap",
        translation_key="free_heap",
        device_class=SensorDeviceClass.DATA_SIZE,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=attrgetter("info.miner.free_heap"),
    ),
    NMAxeSensorEntityDescription(
        key="min_free_heap",
        translation_key="min_free_heap",
        device_class=SensorDeviceClass.DATA_SIZE,
        native_unit_of_measurement=UnitOfInformation.BYTES,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=attrgetter("info.miner.min_free_heap"),
    ),
    NMAxeSensorEntityDescription(
        key="uptime",
        translation_key="uptime",
        device_class=SensorDeviceClass.DURATION,
        icon="mdi:timer-outline",
        native_unit_of_measurement=UnitOfTime.SECONDS,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=0,
        value_fn=attrgetter("info.miner.uptime_seconds"),
    ),
    NMAxeSensorEntityDescription(
        key="total_uptime",
        translation_key="total_uptime",
        device_class=SensorDeviceClass.DURATION,
        icon="mdi:timer-sand",
        native_unit_of_measurement=UnitOfTime.SECONDS,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=0,
        value_fn=attrgetter("info.miner.uptime_ever"),
    ),
    NMAxeSensorEntityDescription(
        key="firmware_version",
        translation_key="firmware_version",
        icon="mdi:package-up",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=attrgetter("info.identity.fw_version"),
    ),
    NMAxeSensorEntityDescription(
        key="app_sha256",
        translation_key="app_sha256",
        icon="mdi:fingerprint",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=attrgetter("info.identity.app_sha256"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: NMAxeConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up NMAxe sensors."""
    coordinator = entry.runtime_data.coordinator
    descriptions = list(SENSOR_DESCRIPTIONS)
    seen = {description.key for description in descriptions}

    for fan in coordinator.data.info.fans:
        for field, translation_key, unit, icon in (
            ("speed", "fan_speed", PERCENTAGE, "mdi:fan"),
            ("rpm", "fan_rpm", REVOLUTIONS_PER_MINUTE, "mdi:fan"),
        ):
            key = f"fan_{fan.id}_{field}"
            if key in seen:
                continue
            seen.add(key)
            descriptions.append(
                NMAxeSensorEntityDescription(
                    key=key,
                    translation_key=translation_key,
                    translation_placeholders={"fan": str(fan.id + 1)},
                    icon=icon,
                    native_unit_of_measurement=unit,
                    state_class=SensorStateClass.MEASUREMENT,
                    suggested_display_precision=0,
                    value_fn=lambda data, fan_id=fan.id, fan_field=field: _fan_value(
                        data,
                        fan_id,
                        fan_field,
                    ),
                )
            )

    async_add_entities(
        NMAxeSensor(coordinator, description) for description in descriptions
    )


class NMAxeSensor(NMAxeEntity, SensorEntity):
    """A sensor backed by the coordinator's latest miner data."""

    entity_description: NMAxeSensorEntityDescription

    def __init__(
        self,
        coordinator: NMAxeCoordinator,
        description: NMAxeSensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, description.key)
        self.entity_description = description
        if description.translation_placeholders:
            self._attr_translation_placeholders = dict(
                description.translation_placeholders
            )

    @property
    def native_value(self) -> StateType:
        """Return the current sensor value."""
        return self.entity_description.value_fn(self.coordinator.data)
