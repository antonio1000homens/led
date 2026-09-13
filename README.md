# LED information board

CircuitPython prototype for four 64×32 HUB75 RGB panels arranged as one 256×32 board. The intended physical controller is an Adafruit MatrixPortal S3. The board is now a generic renderer: external feeds are normalized by the CPython backend into `/api/screens`, and both the browser simulator and physical MatrixPortal consume the same screen contract.

## Architecture

```text
National Rail ───┐
Queue-Times ─────┼──> server.py ──> GET /api/screens ──> MatrixPortal S3
Open-Meteo ──────┤                         │                    │
Future feeds ────┘                         └──> browser          └──> 256×32 HUB75
```

The MatrixPortal does not hold National Rail, Queue-Times or weather-provider credentials. It only needs Wi-Fi access to the backend. Feed authentication, polling, caching and stale handling remain server-side.

The checked-in defaults run a deterministic fixture mode for Wokwi, with no credentials or LAN backend required. Screens rotate using each screen's `duration_seconds`. The top-right `HH:MM` clock and bottom-right weather status are renderer-level overlays and therefore remain visible on every screen.

## Production AWS deployment

Production does **not** run `server.py` as an always-on webserver. EventBridge Scheduler invokes `led-publisher` once per minute; the Lambda refreshes only feeds whose independent TTL has elapsed, persists the last successful feed state to private S3, and atomically publishes the existing `/api/screens` contract as an S3 object. CloudFront serves the simulator and screen snapshot through a private S3 Origin Access Control (OAC).

The production endpoint is:

```text
https://led.alf-broadcast.co.uk
https://led.alf-broadcast.co.uk/api/screens
```

Cloudflare remains the authoritative DNS provider and points the DNS-only `led.alf-broadcast.co.uk` CNAME at CloudFront. The S3 `state/*` prefix is not exposed through CloudFront.

Deployment follows the same operational model as the private Scouts repository: GitHub Actions uses AWS OIDC, `BW_ACCESS_TOKEN` is the Bitwarden machine-account GitHub secret, and GitHub variables hold non-secret configuration or Bitwarden secret UIDs only. The National Rail token is resolved at deployment and passed through a `NoEcho` CloudFormation parameter; the Cloudflare API token remains CI-only.

See [`DEPLOYMENT.md`](DEPLOYMENT.md) for first-time AWS bootstrap, Bitwarden/GitHub variables, ACM/Cloudflare setup, manual deployment and runtime details.

## Hardware notes

The four panels must have an appropriate HUB75 data chain and a separate, correctly sized 5 V power supply. Do not attempt to power four panels from the MatrixPortal or USB alone. Confirm the panel scan/pin wiring against the actual panel before purchase; the software assumes the MatrixPortal S3 `MTX_*` pin definitions and 1/32-scan 64×32 panels.

Wokwi uses four chained WS2812 matrix parts as a visual surrogate because its documented CircuitPython target and built-in matrix part do not reproduce a MatrixPortal S3 HUB75 panel. It also prints the active screen to the serial monitor.

## Run tests

```sh
python3 -m unittest discover -s tests -v
```

## Backend

For rapid look-and-feel work without a MatrixPortal, run the local server:

```sh
python3 server.py
```

Then visit `http://127.0.0.1:8000`. The browser polls `/api/screens` every 30 seconds and renders the same normalized screen kinds used by the physical board.

### Live National Rail data

The backend talks to National Rail Darwin LDBWS and keeps the credential server-side. Install the CPython-only dependency in an isolated environment:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-server.txt
```

Copy `.env.example` to `.env` and set the Bitwarden Secrets Manager UUID:

```text
LED_DATA_SOURCE=national_rail
BWS_NATIONAL_RAIL_TOKEN_SECRET_ID=<bitwarden-secret-uuid>
```

The process requires an authenticated `bws` CLI, normally through `BWS_ACCESS_TOKEN`. It resolves the token at startup and never sends it to the MatrixPortal or browser.

### Thorpe Park queue times

The backend can append a Thorpe Park screen sourced from Queue-Times.com park ID `2`. No Queue-Times credential is required. The default cache is 300 seconds to match the source's approximate refresh cadence.

Enable it in `.env`:

```text
LED_THORPE_PARK_SOURCE=queue_times
LED_THORPE_PARK_CACHE_SECONDS=300
LED_THORPE_PARK_RIDES=Hyperia,Stealth,The Swarm
```

Configured rides are matched case-insensitively and kept in a stable order. A failed refresh keeps the last successful data and marks only the Thorpe Park screen stale; a cold Queue-Times failure produces an unavailable Thorpe screen without removing rail departures.

Queue data is displayed with `Powered by Queue-Times.com` attribution.

### Current weather overlay

The backend uses Open-Meteo for current temperature plus the WMO weather code. The free non-commercial endpoint needs no API key. Weather is cached independently for 600 seconds, so multiple MatrixPortal/browser polls do not multiply upstream weather requests.

The default coordinates are New Malden railway station, matching the default `NEM` departure board:

```text
LED_WEATHER_SOURCE=open_meteo
LED_WEATHER_CACHE_SECONDS=600
LED_WEATHER_LATITUDE=51.4039
LED_WEATHER_LONGITUDE=-0.256
```

Set `LED_WEATHER_SOURCE=off` to remove the overlay, or change latitude/longitude for another location.

The backend maps Open-Meteo WMO weather codes into a small renderer-neutral icon set (`clear_day`, `clear_night`, `partly_cloudy_*`, `cloudy`, `fog`, `rain`, `snow`, `storm`). Both the browser and MatrixPortal draw compact 7×7 pixel icons, with the rounded Celsius temperature beside the icon on the bottom-right row. The physical display uses `17C`-style ASCII text because the built-in CircuitPython terminal font does not provide a reliable degree glyph.

If a weather refresh fails after at least one successful response, the previous value remains visible and is dimmed as stale. A cold weather failure shows an unavailable weather marker without affecting departures, queues or calendar screens. Browser attribution links to Open-Meteo are included as required by the provider's licence.

### Screen contract

`GET /api/screens` is the renderer-neutral contract. A response contains `fetched_at` plus one or more screens. Weather is attached to every screen so it remains available as a fixed overlay while the board rotates:

```json
{
  "fetched_at": "2026-09-12T19:45:30Z",
  "screens": [
    {
      "id": "departures",
      "kind": "rail_combined",
      "duration_seconds": 8,
      "title": "NEM departures",
      "source": "national_rail",
      "stale": false,
      "weather": {
        "source": "open_meteo",
        "stale": false,
        "temperature_c": 17.4,
        "weather_code": 2,
        "icon": "partly_cloudy_day",
        "is_day": true,
        "attribution": "Weather data by Open-Meteo.com",
        "attribution_url": "https://open-meteo.com/"
      },
      "services": []
    },
    {
      "id": "thorpe-park",
      "kind": "theme_park_queues",
      "duration_seconds": 8,
      "title": "THORPE PARK · Powered by Queue-Times.com",
      "source": "queue_times",
      "stale": false,
      "weather": {
        "source": "open_meteo",
        "stale": false,
        "temperature_c": 17.4,
        "weather_code": 2,
        "icon": "partly_cloudy_day",
        "is_day": true
      },
      "rides": []
    }
  ]
}
```

The MatrixPortal rotates these screens locally and does not reset the active screen every time fresh data is polled. If the backend becomes temporarily unreachable it keeps the last screens, marks the active screen stale, and dims the retained weather value.

The board clock is derived from the backend's UTC `fetched_at` timestamp and advanced locally between polls. The CircuitPython client converts UTC to Europe/London time itself, including the GMT/BST transitions, so no separate NTP or clock API is needed.

A credential-free `calendar_agenda` fixture is also available for testing the generic rotation seam:

```sh
python3 server.py --calendar-source fixture
```

## Physical MatrixPortal configuration

For the deployed service, configure the board to use the CloudFront/custom-domain endpoint:

```python
DISPLAY_BACKEND = "matrix"
SCREEN_SOURCE = "api"
SCREEN_API_URL = "https://led.alf-broadcast.co.uk"
POLL_SECONDS = 30
ANIMATE = True
FRAME_SECONDS = 0.2

WIFI_SSID = "your-wifi-name"
WIFI_PASSWORD = "your-wifi-password"
```

For local development instead, copy `settings_local.py.example` to the ignored `settings_local.py` and point `SCREEN_API_URL` at the LAN machine running `server.py`, for example `http://192.168.1.123:8000`.

The MatrixPortal no longer needs National Rail credentials or a direct National Rail client. Weather also remains server-side, so the MatrixPortal makes only the same `/api/screens` request it already used.

For a physical board to reach a local backend, `server.py` must listen on an address reachable from the LAN rather than its safe `127.0.0.1` default. For example, on a trusted home network:

```text
LED_SERVER_HOST=0.0.0.0
```

Do not expose the local development server directly to the public Internet.

## Legacy departures endpoint

`GET /api/departures` remains available from the local development server for diagnostics and compatibility. It returns the normalized departure feed independently of the renderer-neutral `/api/screens` contract. New display functionality should be added through `/api/screens` rather than by adding upstream API clients to CircuitPython.
