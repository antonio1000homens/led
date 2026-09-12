# LED departures board

CircuitPython prototype for four 64×32 HUB75 RGB panels arranged as one 256×32 board. The intended physical controller is an Adafruit MatrixPortal S3. The default mode is an animated dummy feed for visual development; the live feed is National Rail LDBWS JSON for New Malden (`NEM`).

## Modes

The checked-in defaults run a deterministic animated fixture mode so the Wokwi project contains no credentials. Pages rotate every eight seconds, rows slide in, and cancelled services pulse. Copy `settings_local.py.example` to the ignored `settings_local.py`, add Wi-Fi and National Rail Basic Authentication values, and select the `matrix`/`national_rail` backends for hardware.

Wokwi uses four chained WS2812 matrix parts as a visual surrogate because its documented CircuitPython target and built-in matrix part do not reproduce a MatrixPortal S3 HUB75 panel. It also prints the board to the serial monitor. Open the project as a CircuitPython Wokwi project; this repository intentionally has no `wokwi.toml`, because that file is for compiled firmware simulations and requires a firmware path. The provider and formatter are hardware-independent, so the same departure handling is exercised in host tests.

## National Rail API

The client uses the current JSON endpoint:

`https://realtime.nationalrail.co.uk/LDBWS/api/20220120/GetDepartureBoard/{CRS}`

National Rail requires HTTP Basic Authentication. Credentials are read only from `settings_local.py`; never commit them or put them in `diagram.json`.

## Hardware notes

The four panels must have an appropriate HUB75 data chain and a separate, correctly sized 5 V power supply. Do not attempt to power four panels from the MatrixPortal or USB alone. Confirm the panel scan/pin wiring against the actual panel before purchase; the software assumes the MatrixPortal S3 `MTX_*` pin definitions and 1/32-scan 64×32 panels.

## Run tests

```sh
python3 -m unittest discover -s tests
```

## Local visual simulator

For rapid look-and-feel work without a MatrixPortal, run the local server. It
serves the browser preview and a normalized departures API from the same
origin. Fixture mode needs no packages or credentials:


```sh
python3 server.py
```

Then visit `http://127.0.0.1:8000`. The preview polls its screen API every 30
seconds. The rail screen combines the next departure, a scrolling `CALLING AT:`
station/time line, and only the following two departures. Slide-in transitions,
cancellation pulse, stale-data state, and four 64×32 panel boundaries remain
visible.

### Live National Rail data

The live provider talks directly to National Rail's Darwin LDBWS service. Home
Assistant is not part of the runtime path. Install the CPython-only dependency
in an isolated environment:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-server.txt
```

Copy `.env.example` to `.env` and set only the Bitwarden Secrets Manager UUID:

```text
LED_DATA_SOURCE=national_rail
BWS_NATIONAL_RAIL_TOKEN_SECRET_ID=<bitwarden-secret-uuid>
```

The process requires an authenticated `bws` CLI (normally through
`BWS_ACCESS_TOKEN`). It resolves the token at startup and never sends it to the
browser. Command-line options can override the environment, for example:

```sh
python server.py --source national_rail --station NEM
```

The server binds to `127.0.0.1:8000` by default. Do not bind it to a public
interface; a later CircuitPython LAN test should use an explicitly chosen host
and a trusted network.

### Screen rotation and future feeds

`GET /api/screens` is the simulator's renderer-neutral screen contract. By
default it returns one combined National Rail layout. The departure data remains available at
`/api/departures` for future CircuitPython use.

The server deliberately does not connect to a calendar yet: its provider,
authentication method, and privacy boundary need to be chosen first. A
credential-free calendar fixture exists solely to test the rotation seam:

```sh
python3 server.py --calendar-source fixture
```

That appends an `calendar_agenda` screen to `/api/screens`; it does not read a
real calendar. A real adapter should normalize to `start`, `title`, and
`location` fields and remain separate from the renderer.

### Departures API

`GET /api/departures` returns a stable, display-oriented response:

```json
{
  "station": "NEM",
  "source": "fixture",
  "fetched_at": "2026-09-12T12:00:00Z",
  "stale": false,
  "services": [
    {
      "time": "12:04",
      "destination": "Waterloo",
      "platform": "1",
      "status": "On time",
      "cancelled": false,
      "delay_reason": "",
      "stops": [
        {"station": "Clapham Junction", "crs": "CLJ", "time": "12:12", "status": "On time", "cancelled": false}
      ]
    }
  ]
}
```

Responses are cached for 60 seconds. If a refresh fails, the last successful
payload is returned with `stale: true`; without cached data the API returns a
safe `503 {"error":"departures_unavailable"}` response. This contract is kept
independent of the HTML so a future CircuitPython client can consume it.
