"""Config and options flows for the NMAxe integration."""

from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import NMAxeApiClient, normalize_host
from .const import (
    CONF_HOST,
    CONF_POOL_REFRESH_INTERVAL,
    CONF_SCAN_INTERVAL,
    CONFIG_ENTRY_VERSION,
    DEFAULT_POOL_REFRESH_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MAX_POOL_REFRESH_INTERVAL,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
)
from .exceptions import NMAxeConnectionError, NMAxeDataError, NMAxeError
from .models import IdentityData, SystemInfo, build_unique_id, is_supported_model


def _entry_title(identity: IdentityData) -> str:
    return f"{identity.display_name} ({identity.host_name})"


def _host_schema(default_host: str) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_HOST, default=default_host): selector.TextSelector(
                selector.TextSelectorConfig(
                    type=selector.TextSelectorType.TEXT,
                )
            )
        }
    )


class NMAxeConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle installation and reconfiguration of a miner."""

    VERSION = CONFIG_ENTRY_VERSION

    async def async_step_user(
        self,
        user_input: dict[str, object] | None = None,
    ) -> ConfigFlowResult:
        """Ask for the miner's IP address or hostname."""
        errors: dict[str, str] = {}

        if user_input is not None:
            raw_host = str(user_input.get(CONF_HOST, ""))
            try:
                host, info = await self._async_resolve(raw_host)
            except ValueError:
                errors["base"] = "invalid_host"
            except NMAxeConnectionError:
                errors["base"] = "cannot_connect"
            except NMAxeDataError:
                errors["base"] = "invalid_device"
            except NMAxeError:
                errors["base"] = "unknown"
            else:
                if not is_supported_model(info.identity):
                    errors["base"] = "unsupported_device"
                else:
                    await self.async_set_unique_id(build_unique_id(info.identity))
                    self._abort_if_unique_id_configured(updates={CONF_HOST: host})
                    return self.async_create_entry(
                        title=_entry_title(info.identity),
                        data={CONF_HOST: host},
                    )

        return self.async_show_form(
            step_id="user",
            data_schema=_host_schema(str((user_input or {}).get(CONF_HOST, ""))),
            errors=errors,
        )

    async def async_step_reconfigure(
        self,
        user_input: dict[str, object] | None = None,
    ) -> ConfigFlowResult:
        """Change the IP address of an existing miner."""
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}

        if user_input is not None:
            raw_host = str(user_input.get(CONF_HOST, ""))
            try:
                host, info = await self._async_resolve(raw_host)
            except ValueError:
                errors["base"] = "invalid_host"
            except NMAxeConnectionError:
                errors["base"] = "cannot_connect"
            except NMAxeDataError:
                errors["base"] = "invalid_device"
            except NMAxeError:
                errors["base"] = "unknown"
            else:
                if not is_supported_model(info.identity):
                    errors["base"] = "unsupported_device"
                else:
                    await self.async_set_unique_id(build_unique_id(info.identity))
                    self._abort_if_unique_id_mismatch()
                    return self.async_update_reload_and_abort(
                        entry,
                        data_updates={CONF_HOST: host},
                    )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=_host_schema(
                str((user_input or {}).get(CONF_HOST, entry.data[CONF_HOST]))
            ),
            errors=errors,
            description_placeholders={"name": entry.title},
        )

    async def _async_resolve(self, raw_host: str) -> tuple[str, SystemInfo]:
        host = normalize_host(raw_host)
        client = NMAxeApiClient(host, async_get_clientsession(self.hass))
        return host, await client.async_get_system_info()

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> NMAxeOptionsFlow:
        """Return the options flow for this config entry."""
        return NMAxeOptionsFlow()


class NMAxeOptionsFlow(config_entries.OptionsFlow):
    """Configure polling behavior."""

    async def async_step_init(
        self,
        user_input: dict[str, object] | None = None,
    ) -> ConfigFlowResult:
        """Change the status and pool polling intervals."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options = self.config_entry.options
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SCAN_INTERVAL,
                        default=options.get(
                            CONF_SCAN_INTERVAL,
                            DEFAULT_SCAN_INTERVAL,
                        ),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=MIN_SCAN_INTERVAL,
                            max=MAX_SCAN_INTERVAL,
                            step=1,
                            mode=selector.NumberSelectorMode.BOX,
                            unit_of_measurement="s",
                        )
                    ),
                    vol.Required(
                        CONF_POOL_REFRESH_INTERVAL,
                        default=options.get(
                            CONF_POOL_REFRESH_INTERVAL,
                            DEFAULT_POOL_REFRESH_INTERVAL,
                        ),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=0,
                            max=MAX_POOL_REFRESH_INTERVAL,
                            step=1,
                            mode=selector.NumberSelectorMode.BOX,
                            unit_of_measurement="s",
                        )
                    ),
                }
            ),
        )
