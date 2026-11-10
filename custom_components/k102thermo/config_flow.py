"""Config flow for K102 Thermo."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import K102AuthError, K102Client, K102Error
from .const import CONF_CLIENT_ID, CONF_CLIENT_SECRET, DOMAIN

SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Required(CONF_CLIENT_ID): str,
        vol.Required(CONF_CLIENT_SECRET): str,
    }
)


class K102ConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for K102 Thermo."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_USERNAME].lower())
            self._abort_if_unique_id_configured()
            client = K102Client(
                async_get_clientsession(self.hass),
                user_input[CONF_USERNAME],
                user_input[CONF_PASSWORD],
                user_input[CONF_CLIENT_ID],
                user_input[CONF_CLIENT_SECRET],
            )
            try:
                await client.async_login()
            except K102AuthError:
                errors["base"] = "invalid_auth"
            except K102Error:
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(
                    title=user_input[CONF_USERNAME], data=user_input
                )
        return self.async_show_form(step_id="user", data_schema=SCHEMA, errors=errors)
