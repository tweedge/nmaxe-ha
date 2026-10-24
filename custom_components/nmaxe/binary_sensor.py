"""Binary sensor platform for the NMAxe integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.helpers.entity import EntityCategory

from .entity import NMAxeEntity
from .models import NMAxeData

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import NMAxeCoordinator
    from .data import NMAxeConfigEntry


@dataclass(frozen=True, kw_only=True)
class NMAxeBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Describes a binary sensor and how to read its value."""

    value_fn: Callable[[NMAxeData], bool]


def _is_mining(data: NMAxeData) -> bool:
    return (
        data.info.miner.state.strip().casefold() == "running"
        and not data.info.miner.paused
    )


def _pool_connected(data: NMAxeData) -> bool:
    return bool(data.info.stratum.url) and _is_mining(data)


def _is_paused(data: NMAxeData) -> bool:
    return data.info.miner.paused


def _benchmark_mode(data: NMAxeData) -> bool:
    return data.info.miner.benchmark_mode == 1


BINARY_SENSOR_DESCRIPTIONS: tuple[NMAxeBinarySensorEntityDescription, ...] = (
    NMAxeBinarySensorEntityDescription(
        key="mining",
        translation_key="mining",
        device_class=BinarySensorDeviceClass.RUNNING,
        icon="mdi:pickaxe",
        value_fn=_is_mining,
    ),
    NMAxeBinarySensorEntityDescription(
        key="pool_connected",
        translation_key="pool_connected",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        icon="mdi:lan-connect",
        value_fn=_pool_connected,
    ),
    NMAxeBinarySensorEntityDescription(
        key="paused",
        translation_key="paused",
        icon="mdi:pause-circle",
        value_fn=_is_paused,
    ),
    NMAxeBinarySensorEntityDescription(
        key="benchmark_mode",
        translation_key="benchmark_mode",
        icon="mdi:chart-timeline-variant",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=_benchmark_mode,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: NMAxeConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up NMAxe binary sensors."""
    coordinator = entry.runtime_data.coordinator
    async_add_entities(
        NMAxeBinarySensor(coordinator, description)
        for description in BINARY_SENSOR_DESCRIPTIONS
    )


class NMAxeBinarySensor(NMAxeEntity, BinarySensorEntity):
    """A binary sensor backed by the coordinator's latest miner data."""

    entity_description: NMAxeBinarySensorEntityDescription

    def __init__(
        self,
        coordinator: NMAxeCoordinator,
        description: NMAxeBinarySensorEntityDescription,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool:
        """Return whether the binary sensor is on."""
        return self.entity_description.value_fn(self.coordinator.data)
