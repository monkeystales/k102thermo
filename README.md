<p align="center">
  <img src="custom_components/k102thermo/brand/logo.png" alt="Klima102" width="320">
</p>

# K102 Thermo – integrazione Home Assistant (Klima102)

Integrazione non ufficiale, non affiliata a Klima102 / Giacomini. Il logo appartiene ai rispettivi proprietari.

Integrazione custom (cloud polling) per i termostati Klima102 / Giacomini, basata sulla
[Klima102 Services API](https://home.klima102.com/thermo-server/swagger-ui.html).
Login e lettura di gateway e stanze sono stati verificati su un impianto reale; la scrittura dei setpoint non è ancora stata provata.

## Funzioni (v0.1)
- Config flow: username, password e credenziali OAuth client dell'app (`client_id` / `client_secret`).
- Una `climate` per stanza:
  - temperatura e umidità correnti, setpoint del programma attivo;
  - preset `comfort` / `eco` / `standby`, e modo `auto` (segue la programmazione);
  - `heat` o `cool` in base al modo inverno/estate del gateway, `off` se la stanza è disabilitata.
  - attributi `comfort_temperature`, `eco_temperature`, `standby_temperature` (visibili nella finestra dell'entità);
  - attributo `command_pending`: `true` finché il cloud non conferma l'ultimo comando. Nel frattempo viene mostrato lo stato richiesto e il polling passa a 5 s (max 90 s).
- Sensori temperatura e umidità per stanza.
- Polling ogni 60 s di `GET /v1/gateways` e `GET /v1/gateways/{mac}/rooms`.

## Esempio di card
La card termostato standard non mostra umidità né lo stato "in attesa". Una tile card sì:

```yaml
type: tile
entity: climate.cucina_cucina
state_content:
  - hvac_action
  - current_temperature
  - current_humidity
  - command_pending
features:
  - type: target-temperature
```

## Limiti noti
- Se `activeProgram` coincide sempre con `scheduledProgram`, il modo `auto` potrebbe non essere distinguibile dai preset (da verificare su un impianto reale).
- L'API non espone l'accensione/spegnimento di una stanza: da Home Assistant si può selezionare solo `auto`.
- Inverno/estate è un'impostazione del gateway e per ora è in sola lettura.

## API
- Token: `POST https://home.klima102.com/uaa2/oauth/token` (OAuth2 *password grant*; `client_id` e `client_secret` come parametri di query, `username`/`password` nel body).
- Dati: `https://home.klima102.com/thermo-server/v1/...` con `Authorization: Bearer`.
- Temperature in **decimi di °C**.
- Impostazione programma: `POST /v1/gateways/{mac}/rooms/{roomId}` con `{"activeProgram", "manualTemperature"}`.

## Credenziali OAuth
`client_id` e `client_secret` non sono nello swagger e non sono inclusi in questo repository: sono quelli dell'app ufficiale Klima102 e vanno inseriti nel config flow.

## TODO
- [ ] Verificare la scrittura di setpoint e preset su un impianto reale.
- [ ] Entità `number` per modificare le temperature comfort/eco/standby (`PUT .../setpoints`).
- [ ] Nome entità duplicato (`climate.cucina_cucina`).
- [ ] Cambio winter/summer e working mode (`PUT .../system/workingmode`).
- [ ] Sensore temperatura esterna, batteria accessori, finestre aperte.

## Installazione

**HACS (repository personalizzato)**
1. HACS → menu ⋮ → *Repository personalizzati* → aggiungi `https://github.com/monkeystales/k102thermo`, categoria *Integrazione*.
2. Cerca *K102 Thermo*, scarica e riavvia Home Assistant.
3. Impostazioni → Dispositivi e servizi → Aggiungi integrazione → *K102 Thermo*.

**Manuale**: copia `custom_components/k102thermo` in `<config>/custom_components/` e riavvia.

## Sviluppo
Per verificare login e risposte dell'API senza Home Assistant, imposta `K102_USER`, `K102_PASS`, `K102_CLIENT_ID`, `K102_CLIENT_SECRET` ed esegui `python scripts/probe.py` (dopo `pip install aiohttp`).

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements_test.txt
pytest
```
