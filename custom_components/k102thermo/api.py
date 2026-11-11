"""Async client for the Klima102 cloud API (OAuth2 password flow)."""

from __future__ import annotations

import json
import time
from typing import Any

import aiohttp

from .const import API_BASE, REQUEST_TIMEOUT, TOKEN_URL


class K102Error(Exception):
    """Base error."""


class K102ConnectionError(K102Error):
    """Cloud unreachable."""


class K102AuthError(K102Error):
    """Invalid credentials."""


class K102Client:
    """Klima102 API client."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        username: str,
        password: str,
        client_id: str,
        client_secret: str,
    ) -> None:
        self._session = session
        self._username = username
        self._password = password
        self._client_params = {
            "client_id": client_id,
            "client_secret": client_secret,
        }
        self._token: str | None = None
        self._refresh: str | None = None
        self._expires_at = 0.0

    async def _token_request(self, data: dict[str, str]) -> None:
        try:
            async with self._session.post(
                TOKEN_URL,
                params=self._client_params,
                data=data,
                timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT),
            ) as resp:
                if resp.status in (400, 401):
                    raise K102AuthError("Invalid credentials")
                resp.raise_for_status()
                js = await resp.json()
        except (aiohttp.ClientError, TimeoutError) as err:
            raise K102ConnectionError(str(err)) from err
        self._token = js["access_token"]
        self._refresh = js.get("refresh_token")
        self._expires_at = time.monotonic() + int(js.get("expires_in", 300)) - 30

    async def async_login(self) -> None:
        """Obtain a token with the password grant."""
        await self._token_request(
            {
                "grant_type": "password",
                "username": self._username,
                "password": self._password,
            }
        )

    async def _ensure_token(self) -> None:
        if self._token and time.monotonic() < self._expires_at:
            return
        if self._refresh:
            try:
                await self._token_request(
                    {"grant_type": "refresh_token", "refresh_token": self._refresh}
                )
                return
            except K102AuthError:
                pass
        await self.async_login()

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        await self._ensure_token()
        try:
            async with self._session.request(
                method,
                f"{API_BASE}{path}",
                headers={"Authorization": f"Bearer {self._token}"},
                timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT),
                **kwargs,
            ) as resp:
                if resp.status in (401, 403):
                    self._token = None
                    raise K102AuthError("Unauthorized")
                resp.raise_for_status()
                if resp.status == 204:
                    return None
                text = await resp.text()
                return json.loads(text) if text.strip() else None
        except (aiohttp.ClientError, TimeoutError) as err:
            raise K102ConnectionError(str(err)) from err

    async def async_get_gateways(self) -> list[dict[str, Any]]:
        return await self._request("GET", "/v1/gateways")

    async def async_get_rooms(self, mac: str) -> dict[str, Any]:
        return await self._request("GET", f"/v1/gateways/{mac}/rooms")

    async def async_get_structure(self, mac: str) -> dict[str, Any]:
        """Full accessory list (valves, sensors) per room and control unit."""
        return await self._request("GET", f"/v1/housing-unit-structure/{mac}/full")

    async def async_get_devices(self, mac: str) -> list[dict[str, Any]]:
        """Battery powered sensor accessories per room."""
        return await self._request("GET", f"/v1/gateways/{mac}/rooms/devices")

    async def async_set_program(
        self, mac: str, room_id: str, program: str, temperature: int | None = None
    ) -> None:
        """Switch room program. Temperature is in tenths of a degree C."""
        body: dict[str, Any] = {"activeProgram": program}
        if temperature is not None:
            body["manualTemperature"] = temperature
        await self._request("POST", f"/v1/gateways/{mac}/rooms/{room_id}", json=body)
