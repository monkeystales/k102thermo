"""Verifica login e risposte dell'API Klima102 (senza Home Assistant).

Uso (PowerShell):
    $env:K102_USER="..."; $env:K102_PASS="..."
    $env:K102_CLIENT_ID="..."; $env:K102_CLIENT_SECRET="..."
    pip install aiohttp
    python scripts/probe.py

Stampa la struttura delle risposte; i valori sensibili (mac, id, nomi) sono mascherati.
"""

import asyncio
import importlib.util
import json
import os
import sys
import types
from pathlib import Path

import aiohttp

PKG = Path(__file__).resolve().parent.parent / "custom_components" / "k102thermo"


def load(name: str):
    """Carica const.py e api.py senza importare homeassistant."""
    pkg = sys.modules.setdefault("k102", types.ModuleType("k102"))
    pkg.__path__ = [str(PKG)]
    spec = importlib.util.spec_from_file_location(
        f"k102.{name}", PKG / f"{name}.py", submodule_search_locations=None
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules[f"k102.{name}"] = mod
    spec.loader.exec_module(mod)
    return mod


def mask(o):
    if isinstance(o, dict):
        return {
            k: ("***" if k in {"macAddress", "id", "name", "serialNumber", "ownerPrincipal", "accessoryHubId"} else mask(v))
            for k, v in o.items()
        }
    if isinstance(o, list):
        return [mask(i) for i in o]
    return o


async def main() -> None:
    load("const")
    api = load("api")
    async with aiohttp.ClientSession() as s:
        c = api.K102Client(
            s,
            os.environ["K102_USER"],
            os.environ["K102_PASS"],
            os.environ["K102_CLIENT_ID"],
            os.environ["K102_CLIENT_SECRET"],
        )
        await c.async_login()
        print("LOGIN OK")
        gws = await c.async_get_gateways()
        print("GATEWAYS:", json.dumps(mask(gws), indent=1))
        for gw in gws or []:
            rooms = await c.async_get_rooms(gw["macAddress"])
            print("ROOMS:", json.dumps(mask(rooms), indent=1))


asyncio.run(main())
