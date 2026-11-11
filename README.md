<p align="center">
  <img src="custom_components/k102thermo/brand/logo.png" alt="Klima102" width="320">
</p>

# K102 Thermo – integrazione Home Assistant (Klima102)

Integrazione non ufficiale, non affiliata a Klima102. Il logo appartiene ai rispettivi proprietari.

Integrazione custom (cloud polling) per i termostati Klima102, basata sulla
[Klima102 Services API](https://home.klima102.com/thermo-server/swagger-ui.html).
Login e lettura di gateway e stanze sono stati verificati su un impianto reale; la scrittura dei setpoint non è ancora stata provata.

## Funzioni (v0.1)
- Config flow: username, password e credenziali OAuth client dell'app (`client_id` / `client_secret`).
- Una `climate` per stanza:
  - temperatura e umidità correnti, setpoint del programma attivo;
  - menu preset con la sola voce **Auto** (e modo HVAC `auto`): riporta la stanza alla programmazione del dispositivo, annullando manuali e forzature;
  - `heat` o `cool` in base al modo inverno/estate del gateway, `off` se la stanza è disabilitata.
  - attributi `comfort_temperature`, `eco_temperature`, `standby_temperature` (visibili nella finestra dell'entità);
  - attributo `command_pending`: `true` finché il cloud non conferma l'ultimo comando. Nel frattempo viene mostrato lo stato richiesto e il polling passa a 5 s (max 90 s).
- Sensori temperatura e umidità per stanza.
- **Accessori** (valvole termostatiche, sensori, centralina, presa smart): un dispositivo per ciascuno. I nomi delle entità riportano il tipo (es. *Batteria valvola*, *Temperatura sensore*), nella lingua di Home Assistant. Ogni dispositivo ha
  - sensore **batteria** (solo per quelli a batteria) e **temperatura** misurata dall'accessorio;
  - sensore binario **connettività**;
  - sensore **ultimo contatto** (disattivato di default, abilitalo dalle entità).

  L'**attuatore caldaia** (`Switch1`, il relè che chiude il contatto in caldaia) è un dispositivo a sé: connettività, ultimo contatto e **Richiesta caldaia**. Quest'ultima è *derivata*: l'API non espone lo stato del relè, quindi risulta accesa quando almeno una stanza abilitata sta scaldando/raffrescando (`powering`); l'attributo `rooms_calling` elenca le stanze.

  Gli accessori vengono riletti ogni 5 minuti (`GET /v1/housing-unit-structure/{mac}/full`), non a ogni polling. Se ne aggiungi uno nuovo sull'impianto, ricarica l'integrazione.
- Polling di `GET /v1/gateways` e `GET /v1/gateways/{mac}/rooms`, ogni 60 s di default (configurabile, vedi sotto).

## Modalità del sistema (per gateway)
- **Modalità di lavoro** (`select`): *Normale* / *Vacanza (antigelo)*. Lettura e scrittura (`PUT /system/workingmode`).
- **Stagione** (`select`): *Inverno* / *Estate*. Lettura affidabile; la **scrittura è sperimentale**: l'API non ha un endpoint dedicato e l'integrazione invia `{"opMode": ...}` all'aggiornamento dei setpoint di ogni stanza (`PUT /v2/gateways/{mac}/rooms/{roomId}/setpoints`). Da verificare sul proprio impianto; se non ha effetto, lo stato torna a quello reale dopo circa 90 s.
- **Termoregolazione attiva** (`binary_sensor`): stato acceso/spento del sistema (`sysStatus`). **Sola lettura**: l'API documentata non permette di accendere o spegnere il sistema.
- Come per i comandi sulle stanze, la scelta compare subito e il cloud viene interrogato ogni 5 s (max 90 s) finché non conferma.

## Manuale: temporizzato o persistente
- **Manuale temporizzato** (`timedManual`): resta fino al prossimo cambio di fascia. È il default: ogni cambio di temperatura da Home Assistant (pulsanti − e +, `climate.set_temperature`) crea un manuale temporizzato.
- **Manuale persistente** (`manual`): resta finché non lo cambi.
- Per ogni stanza c'è un'entità **select "Tipo di manuale"** (Temporizzato / Persistente, il valore viene ricordato). Se la imposti su *Persistente*, i cambi di temperatura dalla card creano un manuale persistente.
- Servizio `k102thermo.set_manual` (temperatura 5–35 °C, `persistent: true|false`) per impostare un manuale preciso da automazioni e script:

```yaml
action: k102thermo.set_manual
target:
  entity_id: climate.cucina
data:
  temperature: 21.5
  persistent: true
```

- Le temperature manuali vanno a passi di 0,5 °C (anche i valori passati al servizio vengono arrotondati a 0,5).
- L'attributo `manual_type` (`timed` / `persistent`) indica il tipo attivo.
- Da verificare su impianto reale: che l'API accetti `timedManual` con `manualTemperature` e come riporti la fine della fascia.

## Configurazione
**Intervallo di aggiornamento**: Impostazioni → Dispositivi e servizi → K102 Thermo → *Configura*.
Valori ammessi 30–3600 secondi (default 60). Al salvataggio l'integrazione si ricarica da sola.
Dopo un comando l'integrazione aggiorna comunque ogni 5 s per un massimo di 90 s, finché il cloud non conferma il nuovo stato; è questo che imposta `command_pending`.
Ogni aggiornamento fa 1 richiesta per la lista dei gateway più 1 per ogni gateway.

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
- Gli ID entità possono risultare doppi (es. `climate.cucina_cucina`): Home Assistant antepone al nome del dispositivo anche il nome dell'area, e le stanze hanno area e dispositivo con lo stesso nome. Non dipende dall'integrazione: rinomina l'ID dell'entità o l'area.
- `auto` viene riconosciuto quando l'API riporta `activeProgram: auto` oppure quando `activeProgram` coincide con `scheduledProgram` (nessun override attivo). Se forzi un preset uguale a quello in programma, Home Assistant lo mostra quindi come `auto`. L'attributo `scheduled_program` indica il programma previsto dal dispositivo. Da verificare su un impianto reale.
- L'API non espone l'accensione/spegnimento di una stanza: da Home Assistant si può selezionare solo `auto`.
- Inverno/estate è un'impostazione del gateway e per ora è in sola lettura.

## API
- Intervallo, soglie e timeout sono nelle costanti di `const.py` e `climate.py`.
- Token: `POST https://home.klima102.com/uaa2/oauth/token` (OAuth2 *password grant*; `client_id` e `client_secret` come parametri di query, `username`/`password` nel body).
- Dati: `https://home.klima102.com/thermo-server/v1/...` con `Authorization: Bearer`.
- Temperature in **decimi di °C**.
- Impostazione programma: `POST /v1/gateways/{mac}/rooms/{roomId}` con `{"activeProgram", "manualTemperature"}`.

## Credenziali OAuth
`client_id` e `client_secret` non sono nello swagger e non sono inclusi in questo repository: sono quelli dell'app ufficiale Klima102 e vanno inseriti nel config flow.

## TODO
- [ ] Verificare la scrittura di setpoint e preset su un impianto reale.
- [ ] Entità `number` per modificare le temperature comfort/eco/standby (`PUT .../setpoints`).
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
