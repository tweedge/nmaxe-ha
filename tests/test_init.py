"""Tests for integration setup, entities, and unloading."""

from __future__ import annotations

from unittest.mock import patch

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity import EntityCategory
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.nmaxe import async_migrate_entry
from custom_components.nmaxe.api import NMAxeApiClient
from custom_components.nmaxe.const import (
    CONF_HOST,
    CONFIG_ENTRY_VERSION,
    DOMAIN,
)
from custom_components.nmaxe.exceptions import NMAxeConnectionError
from tests.fixtures import HOST, POOL_CONFIG, SECRET, SYSTEM_INFO, UNIQUE_ID


def _mock_entry() -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: HOST},
        unique_id=UNIQUE_ID,
    )


async def test_setup_creates_entities(hass: HomeAssistant) -> None:
    """Set up the integration and verify representative entities."""
    entry = _mock_entry()
    entry.add_to_hass(hass)

    with (
        patch.object(
            NMAxeApiClient,
            "async_get_system_info",
            return_value=SYSTEM_INFO,
        ),
        patch.object(
            NMAxeApiClient,
            "async_get_pool_config",
            return_value=POOL_CONFIG,
        ),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED

    registry = er.async_get(hass)
    entities = {
        entity.unique_id.removeprefix(f"{entry.entry_id}_"): entity
        for entity in er.async_entries_for_config_entry(registry, entry.entry_id)
    }

    expected = {
        "hashrate",
        "power",
        "input_voltage",
        "asic_temperature",
        "blocks_found",
        "shares_accepted",
        "shares_submitted",
        "share_acceptance_rate",
        "efficiency",
        "miner_state",
        "active_pool",
        "pool_user",
        "primary_pool",
        "fallback_pool",
        "pool_source",
        "fan_0_speed",
        "fan_0_rpm",
        "mining",
        "pool_connected",
        "paused",
    }
    assert expected <= entities.keys()

    core = {
        "blocks_found",
        "efficiency",
        "hashrate",
        "miner_state",
        "pool_connected",
        "power",
        "share_acceptance_rate",
    }
    for key in expected:
        entity = entities[key]
        if key in core:
            assert entity.disabled_by is None
            assert entity.entity_category is None
        else:
            assert entity.disabled_by is er.RegistryEntryDisabler.INTEGRATION

    diagnostic = {
        "asic_frequency",
        "asic_temperature",
        "fan_0_rpm",
        "fan_0_speed",
        "input_current",
        "input_voltage",
        "total_uptime",
        "uptime",
        "vcore_actual",
        "vcore_requested",
        "vcore_temperature",
    }
    for key in diagnostic:
        assert entities[key].entity_category is EntityCategory.DIAGNOSTIC

    def state_for(key: str):
        entity = entities[key]
        state = hass.states.get(entity.entity_id)
        assert state is not None
        return state

    assert state_for("hashrate").state == "1200.5"
    assert state_for("power").state == "25.4"
    assert state_for("blocks_found").state == "2"
    assert state_for("share_acceptance_rate").state == "99.7"
    assert state_for("efficiency").state == "21.16"
    assert state_for("miner_state").state == "running"
    assert state_for("pool_connected").state == "on"

    assert hass.states.get(entities["input_voltage"].entity_id) is None
    assert hass.states.get(entities["shares_submitted"].entity_id) is None
    assert hass.states.get(entities["pool_source"].entity_id) is None
    assert hass.states.get(entities["fan_0_rpm"].entity_id) is None
    assert hass.states.get(entities["mining"].entity_id) is None
    assert hass.states.get(entities["paused"].entity_id) is None

    device = dr.async_get(hass).async_get_device_by_identifier(
        (DOMAIN, entry.entry_id),
        entry.entry_id,
    )
    assert device is not None
    assert device.manufacturer == "NMTech"
    assert device.model == "NMAxeGamma"
    assert device.sw_version == "v3.2.01"

    assert all(SECRET not in str(state.attributes) for state in hass.states.async_all())

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.NOT_LOADED


async def test_setup_retries_when_device_is_offline(hass: HomeAssistant) -> None:
    """Leave the entry in setup retry when the miner cannot be reached."""
    entry = _mock_entry()
    entry.add_to_hass(hass)

    with patch.object(
        NMAxeApiClient,
        "async_get_system_info",
        side_effect=NMAxeConnectionError("down"),
    ):
        assert not await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_migration_disables_non_core_entities(hass: HomeAssistant) -> None:
    """Disable enabled non-core entities when upgrading an old entry."""
    entry = _mock_entry()
    entry.add_to_hass(hass)
    registry = er.async_get(hass)
    prefix = f"{entry.entry_id}_"

    core = registry.async_get_or_create(
        DOMAIN,
        "sensor",
        f"{prefix}hashrate",
        config_entry=entry,
        suggested_object_id="hashrate",
    )
    other = registry.async_get_or_create(
        DOMAIN,
        "sensor",
        f"{prefix}input_voltage",
        config_entry=entry,
        suggested_object_id="input_voltage",
    )
    user_disabled = registry.async_get_or_create(
        DOMAIN,
        "sensor",
        f"{prefix}asic_temperature",
        config_entry=entry,
        suggested_object_id="asic_temperature",
        disabled_by=er.RegistryEntryDisabler.USER,
    )

    assert await async_migrate_entry(hass, entry)

    assert entry.version == CONFIG_ENTRY_VERSION
    assert registry.async_get(core.entity_id).disabled_by is None
    assert (
        registry.async_get(other.entity_id).disabled_by
        is er.RegistryEntryDisabler.INTEGRATION
    )
    assert (
        registry.async_get(user_disabled.entity_id).disabled_by
        is er.RegistryEntryDisabler.USER
    )
