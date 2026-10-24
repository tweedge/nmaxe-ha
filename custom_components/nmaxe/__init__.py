"""The NMAxe integration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.const import Platform
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import NMAxeApiClient
from .const import CONF_HOST, LOGGER
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


async def _async_reload_entry(hass: HomeAssistant, entry: NMAxeConfigEntry) -> None:
    LOGGER.debug("Reloading %s after an options change", entry.title)
    await hass.config_entries.async_reload(entry.entry_id)
