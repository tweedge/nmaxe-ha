"""The NMAxe integration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.const import Platform
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import NMAxeApiClient
from .const import (
    CONF_HOST,
    CONFIG_ENTRY_VERSION,
    DEFAULT_ENABLED_ENTITY_KEYS,
    LOGGER,
    REMOVED_ENTITY_KEYS,
)
from .coordinator import NMAxeCoordinator
from .data import NMAxeRuntimeData

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .data import NMAxeConfigEntry

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: NMAxeConfigEntry) -> bool:
    """Set up a miner from a config entry."""
    client = NMAxeApiClient(entry.data[CONF_HOST], async_get_clientsession(hass))
    coordinator = NMAxeCoordinator(hass, entry, client)
    entry.runtime_data = NMAxeRuntimeData(client=client, coordinator=coordinator)

    await coordinator.async_config_entry_first_refresh()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: NMAxeConfigEntry) -> bool:
    """Unload a miner config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_migrate_entry(hass: HomeAssistant, entry: NMAxeConfigEntry) -> bool:
    """Remove redundant entities and disable non-core entities."""
    if entry.version > CONFIG_ENTRY_VERSION:
        return False

    if entry.version < CONFIG_ENTRY_VERSION:
        old_version = entry.version
        registry = er.async_get(hass)
        prefix = f"{entry.entry_id}_"
        for entity in er.async_entries_for_config_entry(registry, entry.entry_id):
            key = entity.unique_id.removeprefix(prefix)
            if key in REMOVED_ENTITY_KEYS:
                registry.async_remove(entity.entity_id)
                continue
            if (
                old_version < 2
                and key not in DEFAULT_ENABLED_ENTITY_KEYS
                and entity.disabled_by is None
            ):
                registry.async_update_entity(
                    entity.entity_id,
                    disabled_by=er.RegistryEntryDisabler.INTEGRATION,
                )
        hass.config_entries.async_update_entry(
            entry,
            version=CONFIG_ENTRY_VERSION,
        )
    return True


async def _async_reload_entry(hass: HomeAssistant, entry: NMAxeConfigEntry) -> None:
    LOGGER.debug("Reloading %s after an options change", entry.title)
    await hass.config_entries.async_reload(entry.entry_id)
