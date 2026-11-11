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
            k: ("***" if k in {"macAddress", "id", "name", "serialNumber", "ownerPrincipal", "accessoryHubId", "hubId", "description", "deviceAddress", "deviceUID", "eventId", "roomName"} else mask(v))
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
        events_only = len(sys.argv) > 1 and sys.argv[1] == "events"
        if not events_only:
            print("GATEWAYS:", json.dumps(mask(gws), indent=1))
        for gw in gws or []:
            mac = gw["macAddress"]
            structure = None
            if not events_only:
                rooms = await c.async_get_rooms(mac)
                print("ROOMS:", json.dumps(mask(rooms), indent=1))
                for label, call in (
                    ("STRUCTURE", c.async_get_structure),
                    ("DEVICES", c.async_get_devices),
                    ("SYSTEM", c.async_get_system),
                ):
                    try:
                        data = await call(mac)
                        if label == "STRUCTURE":
                            structure = data
                        print(f"{label}:", json.dumps(mask(data), indent=1))
                    except Exception as err:  # noqa: BLE001
                        print(f"{label}: ERROR {err}")
            else:
                structure = await c.async_get_structure(mac)
            candidates = [
                ("structure.hubId", (structure or {}).get("hubId")),
                ("gateway.accessoryHubId", gw.get("accessoryHubId")),
                ("structure.id", (structure or {}).get("id")),
                ("gateway.macAddress", gw.get("macAddress")),
                ("gateway.serialNumber", gw.get("serialNumber")),
                ("gateway.id", gw.get("id")),
            ]
            print("HUB ID CANDIDATES present:", [n for n, v in candidates if v])
            for name, value in candidates:
                if not value:
                    continue
                try:
                    events = await c.async_get_event_log(str(value), 30)
                except Exception as err:  # noqa: BLE001
                    print(f"EVENT-LOG with {name}: ERROR {err}")
                    continue
                print(f"EVENT-LOG with {name}:", json.dumps(mask(events), indent=1)[:8000])
                content = events.get("content") if isinstance(events, dict) else events
                if content:
                    break


asyncio.run(main())
