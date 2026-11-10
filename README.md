<p align="center">
  <img src="custom_components/k102thermo/brand/logo.png" alt="Klima102" width="320">
</p>

# K102 Thermo – integrazione Home Assistant (Klima102)

Integrazione non ufficiale, non affiliata a Klima102 / Giacomini. Il logo appartiene ai rispettivi proprietari.

Integrazione custom (cloud polling) per i termostati Klima102 / Giacomini, basata sulla
[Klima102 Services API](https://home.klima102.com/thermo-server/swagger-ui.html).

## Funzioni (v0.1)
- Config flow: username, password e credenziali OAuth client dell'app (`client_id` / `client_secret`).
- Una `climate` per stanza: temperatura corrente, setpoint, preset `comfort` / `eco` / `standby`, modo `auto`.
- Sensori temperatura e umidità per stanza.
- Polling ogni 60 s di `GET /v1/gateways` e `GET /v1/gateways/{mac}/rooms`.

## API
- Token: `POST https://home.klima102.com/uaa2/oauth/token` (OAuth2 *password grant*; `client_id` e `client_secret` come parametri di query, `username`/`password` nel body).
- Dati: `https://home.klima102.com/thermo-server/v1/...` con `Authorization: Bearer`.
- Temperature in **decimi di °C**.
- Impostazione programma: `POST /v1/gateways/{mac}/rooms/{roomId}` con `{"activeProgram", "manualTemperature"}`.

## Da verificare / TODO
- [ ] `client_id` / `client_secret` non sono nello swagger: vanno ricavati dall'app ufficiale.
- [ ] Verificare lo schema reale delle risposte con un account vero.
- [ ] Cambio winter/summer e working mode (`PUT .../system/workingmode`).
- [ ] Sensore temperatura esterna, batteria accessori, finestre aperte.

## Installazione

**HACS (repository personalizzato)**
1. HACS → menu ⋮ → *Repository personalizzati* → aggiungi `https://github.com/monkeystales/k102thermo`, categoria *Integrazione*.
2. Cerca *K102 Thermo*, scarica e riavvia Home Assistant.
3. Impostazioni → Dispositivi e servizi → Aggiungi integrazione → *K102 Thermo*.

**Manuale**: copia `custom_components/k102thermo` in `<config>/custom_components/` e riavvia.

## Sviluppo
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements_test.txt
pytest
```
