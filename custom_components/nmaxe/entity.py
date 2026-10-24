"""Shared entity definitions for the NMAxe integration."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import NMAxeCoordinator


class NMAxeEntity(CoordinatorEntity[NMAxeCoordinator]):
    """Base entity attached to a single miner."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: NMAxeCoordinator, unique_key: str) -> None:
        """Initialize the entity and its device registry entry."""
        super().__init__(coordinator)
        info = coordinator.data.info
        identity = info.identity
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{unique_key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.config_entry.entry_id)},
            name=f"{identity.display_name} ({identity.host_name})",
            manufacturer=MANUFACTURER,
            model=identity.display_name,
            model_id=identity.hw_model,
            sw_version=identity.fw_version,
            configuration_url=f"http://{coordinator.client.host}",
        )
