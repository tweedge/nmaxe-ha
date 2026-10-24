"""Tests for diagnostics redaction."""

from __future__ import annotations

import json
from unittest.mock import patch

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.nmaxe.api import NMAxeApiClient
from custom_components.nmaxe.const import CONF_HOST, DOMAIN
from custom_components.nmaxe.diagnostics import (
    _redact,
    async_get_config_entry_diagnostics,
)
from tests.fixtures import HOST, POOL_CONFIG, SECRET, SYSTEM_INFO, UNIQUE_ID


def test_redact_nested_secrets() -> None:
    """Redact secret keys recursively."""
    redacted = _redact(
        {
            "password": SECRET,
            "nested": [{"pwd": SECRET, "safe": "value"}],
            "safe": "value",
        }
    )
    assert redacted["password"] == "**REDACTED**"
    assert redacted["nested"][0]["pwd"] == "**REDACTED**"
    assert redacted["nested"][0]["safe"] == "value"
    assert redacted["safe"] == "value"


async def test_diagnostics_contain_no_secret(hass: HomeAssistant) -> None:
    """Never expose pool passwords in diagnostics."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_HOST: HOST},
        unique_id=UNIQUE_ID,
    )
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

    diagnostics = await async_get_config_entry_diagnostics(hass, entry)
    serialized = json.dumps(diagnostics)

    assert SECRET not in serialized
    assert "pwd" not in serialized.casefold()
    assert diagnostics["entry"]["host"] == HOST
    assert diagnostics["data"]["pools"]["primary"]["url"] == (
        "stratum+tcp://pool.example.com:3333"
    )
