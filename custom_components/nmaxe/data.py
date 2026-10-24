"""Runtime data types for the NMAxe integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from homeassistant.config_entries import ConfigEntry

if TYPE_CHECKING:
    from .api import NMAxeApiClient
    from .coordinator import NMAxeCoordinator

type NMAxeConfigEntry = ConfigEntry[NMAxeRuntimeData]


@dataclass
class NMAxeRuntimeData:
    """Objects shared by the integration platforms."""

    client: NMAxeApiClient
    coordinator: NMAxeCoordinator
