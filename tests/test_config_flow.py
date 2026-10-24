"""Tests for the NMAxe config and options flows."""

from __future__ import annotations

from dataclasses import replace
from unittest.mock import patch

import pytest
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.nmaxe.api import NMAxeApiClient
from custom_components.nmaxe.const import (
    CONF_HOST,
    CONF_POOL_REFRESH_INTERVAL,
    CONF_SCAN_INTERVAL,
    CONFIG_ENTRY_VERSION,
    DOMAIN,
)
from custom_components.nmaxe.exceptions import (
    NMAxeConnectionError,
    NMAxeDataError,
    NMAxeResponseError,
)
from tests.fixtures import HOST, POOL_CONFIG, SYSTEM_INFO, UNIQUE_ID


async def _start_user_flow(hass: HomeAssistant) -> dict:
    return await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )


async def test_user_flow_success(hass: HomeAssistant) -> None:
    """Create an entry after validating the miner."""
    result = await _start_user_flow(hass)
    assert result["type"] is FlowResultType.FORM

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
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_HOST: f"http://{HOST}/"},
        )
        await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "NMAxeGamma (nmaxe-gamma-01)"
    assert result["data"] == {CONF_HOST: HOST}
    assert result["result"].unique_id == UNIQUE_ID
    assert result["result"].version == CONFIG_ENTRY_VERSION


@pytest.mark.parametrize(
    ("exception", "error"),
    [
        (NMAxeConnectionError("down"), "cannot_connect"),
        (NMAxeDataError("bad data"), "invalid_device"),
        (NMAxeResponseError("bad response"), "unknown"),
    ],
)
async def test_user_flow_errors(
    hass: HomeAssistant,
    exception: Exception,
    error: str,
) -> None:
    """Report API failures in the form."""
    result = await _start_user_flow(hass)
    with patch.object(
        NMAxeApiClient,
        "async_get_system_info",
        side_effect=exception,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_HOST: HOST},
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": error}


async def test_user_flow_invalid_host(hass: HomeAssistant) -> None:
    """Reject URLs with a scheme, path, or credentials."""
    result = await _start_user_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_HOST: f"https://{HOST}/status"},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_host"}


async def test_user_flow_unsupported_model(hass: HomeAssistant) -> None:
    """Reject non-NMAxe devices."""
    unsupported = replace(
        SYSTEM_INFO,
        identity=replace(SYSTEM_INFO.identity, hw_model="OtherMiner"),
    )
    result = await _start_user_flow(hass)
    with patch.object(
        NMAxeApiClient,
        "async_get_system_info",
        return_value=unsupported,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_HOST: HOST},
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "unsupported_device"}


async def test_user_flow_duplicate_aborts(hass: HomeAssistant) -> None:
    """Abort when the same miner is already configured."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: "192.168.1.50"},
        unique_id=UNIQUE_ID,
    )
    entry.add_to_hass(hass)

    result = await _start_user_flow(hass)
    with patch.object(
        NMAxeApiClient,
        "async_get_system_info",
        return_value=SYSTEM_INFO,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_HOST: HOST},
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
    assert entry.data[CONF_HOST] == HOST


async def test_reconfigure_updates_host(hass: HomeAssistant) -> None:
    """Update the host while keeping the same miner identity."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: "192.168.1.50"},
        unique_id=UNIQUE_ID,
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={
            "source": config_entries.SOURCE_RECONFIGURE,
            "entry_id": entry.entry_id,
        },
    )
    assert result["type"] is FlowResultType.FORM

    with (
        patch.object(
            NMAxeApiClient,
            "async_get_system_info",
            return_value=SYSTEM_INFO,
        ),
        patch.object(
            NMAxeApiClient,
            "async_get_pool_config",
            return_value=None,
        ),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_HOST: HOST},
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert entry.data[CONF_HOST] == HOST


async def test_reconfigure_wrong_device(hass: HomeAssistant) -> None:
    """Refuse to point an entry at a different miner."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: HOST},
        unique_id=UNIQUE_ID,
    )
    entry.add_to_hass(hass)
    other = replace(
        SYSTEM_INFO,
        identity=replace(SYSTEM_INFO.identity, host_name="other-miner"),
    )

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={
            "source": config_entries.SOURCE_RECONFIGURE,
            "entry_id": entry.entry_id,
        },
    )
    with patch.object(
        NMAxeApiClient,
        "async_get_system_info",
        return_value=other,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_HOST: HOST},
        )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "unique_id_mismatch"


async def test_options_flow(hass: HomeAssistant) -> None:
    """Store polling intervals in entry options."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: HOST},
        unique_id=UNIQUE_ID,
        options={},
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_SCAN_INTERVAL: 120,
            CONF_POOL_REFRESH_INTERVAL: 0,
        },
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options == {
        CONF_SCAN_INTERVAL: 120,
        CONF_POOL_REFRESH_INTERVAL: 0,
    }
