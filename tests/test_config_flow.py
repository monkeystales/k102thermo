"""Config flow tests."""

from unittest.mock import AsyncMock, patch

from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.k102thermo.api import K102AuthError
from custom_components.k102thermo.const import DOMAIN

INPUT = {
    "username": "u@example.com",
    "password": "pw",
    "client_id": "cid",
    "client_secret": "sec",
}
LOGIN = "custom_components.k102thermo.config_flow.K102Client.async_login"


async def test_success(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    with patch(LOGIN, AsyncMock()), patch(
        "custom_components.k102thermo.async_setup_entry", return_value=True
    ):
        result = await hass.config_entries.flow.async_configure(result["flow_id"], INPUT)
    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_invalid_auth(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    with patch(LOGIN, AsyncMock(side_effect=K102AuthError)):
        result = await hass.config_entries.flow.async_configure(result["flow_id"], INPUT)
    assert result["errors"] == {"base": "invalid_auth"}
