# LED information board

CircuitPython prototype for four 64×32 HUB75 RGB panels arranged as one 256×32 board. The intended physical controller is an Adafruit MatrixPortal S3. The board is now a generic renderer: external feeds are normalized by the CPython backend into `/api/screens`, and both the browser simulator and physical MatrixPortal consume the same screen contract.

## Architecture

```text
National Rail ───┐
Queue-Times ─────┤
Todoist ─────────┼──> publisher/server ──> GET /api/screens ──> MatrixPortal S3
Open-Meteo ──────┤                              │                    │
Future feeds ────┘                              └──> browser          └──> 256×32 HUB75
```

## Repository layout

Application Python is grouped by runtime rather than kept flat at the repository root:

```text
code.py       CircuitPython/Wokwi entrypoint
hardware/matrixportal/firmware/  MatrixPortal implementation
backend/      local CPython server and Lambda implementation
shared/       renderer/fixture modules used by both runtimes
scripts/      build, test, deployment and maintenance tooling
tests/        host-side regression tests
docs/         cross-cutting architecture/deployment documentation
```

The root `code.py` is intentional because Wokwi/CircuitPython uses that
entrypoint. Use `scripts/stage-firmware.sh` to create the flat filesystem
expected by a physical board, or `scripts/install-firmware.sh` to copy it to
a mounted `CIRCUITPY` volume.


Transient flash events are designed as a separate path: Home Assistant will
publish normalized reminder events to MQTT, and the MatrixPortal will briefly
show them before resuming the paused normal rotation. The MQTT path is
implemented but deliberately disabled in the checked-in firmware while Home
Assistant issue #4 and the broker safety review are incomplete. No broker
credentials are committed and no DHCP reservation is required.

The MatrixPortal does not hold National Rail, Todoist, Queue-Times or weather-provider credentials. It only needs Wi-Fi access to the backend. Feed authentication, polling, caching and stale handling remain server-side.

The checked-in defaults run a deterministic fixture mode for Wokwi, with no credentials or LAN backend required. Screens rotate using each screen's `duration_seconds`. The top-right `HH:MM` clock and bottom-right weather status are renderer-level overlays and therefore remain visible on every screen.

## Production AWS deployment

Production does **not** run `backend/server.py` as an always-on webserver. EventBridge Scheduler invokes `led-publisher` once per minute; the Lambda refreshes only feeds whose independent TTL has elapsed, persists the last successful feed state to private S3, and atomically publishes the existing `/api/screens` contract as an S3 object. CloudFront serves the simulator and screen snapshot through a private S3 Origin Access Control (OAC).

The production endpoint is:

```text
https://led.alf-broadcast.co.uk
https://led.alf-broadcast.co.uk/api/screens
```

Cloudflare remains the authoritative DNS provider and points the DNS-only `led.alf-broadcast.co.uk` CNAME at CloudFront. The S3 `state/*` prefix is not exposed through CloudFront.

GitHub Actions uses AWS OIDC and stores only non-secret deployment configuration. The National Rail and Windsor Cloudflare deployment secrets are Standard `SecureString` parameters under `/led/deploy/*`; the workflow assumes `GitHubActionsLedDeployRole` first, then decrypts and masks those two values. Todoist is separate because its OAuth refresh token rotates at runtime: its client credentials plus access/refresh tokens remain in `/led/todoist/oauth`, which only the publisher runtime can read and update.

See [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) for first-time AWS bootstrap, the Bitwarden-to-SSM migration helper, deployment-secret rotation, Todoist OAuth bootstrap, GitHub variables, ACM/Cloudflare setup, manual deployment and runtime details.

## Hardware notes

For the current MatrixPortal refresh/pacing architecture, measured performance
results, and the decisions from issues #70, #91, #92 and #94, see
[`hardware/matrixportal/docs/matrixportal-performance.md`](hardware/matrixportal/docs/matrixportal-performance.md).

The four panels must have an appropriate HUB75 data chain and a separate, correctly sized 5 V power supply. Do not attempt to power four panels from the MatrixPortal or USB alone. Confirm the panel scan/pin wiring against the actual panel before purchase; the software assumes the MatrixPortal S3 `MTX_*` pin definitions and 1/32-scan 64×32 panels.

Wokwi uses four chained WS2812 matrix parts as a visual surrogate because its documented CircuitPython target and built-in matrix part do not reproduce a MatrixPortal S3 HUB75 panel. It also prints the active screen to the serial monitor.

## Run tests

```sh
bash scripts/run-tests.sh
```

## Backend

For rapid look-and-feel work without a MatrixPortal, run the local server:

```sh
bash scripts/run-server.sh
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

The process requires an authenticated `bws` CLI, normally through `BWS_ACCESS_TOKEN`. It resolves the token at startup and never sends it to the MatrixPortal or browser. This is a local-development path only; the production GitHub deployment no longer depends on a Bitwarden machine account.

### Thorpe Park queue times

The backend can append a Thorpe Park screen sourced from Queue-Times.com park ID `2`. No Queue-Times credential is required. The default cache is 300 seconds to match the source's approximate refresh cadence.

Enable it in `.env`:

```text
LED_THORPE_PARK_SOURCE=queue_times
LED_THORPE_PARK_CACHE_SECONDS=300
LED_THORPE_PARK_RIDES=Hyperia,Stealth,The Swarm,SAW - The Ride,Nemesis Inferno,Colossus,Ghost Train,Rush,Detonator,Tidal Wave
```

Configured rides are matched case-insensitively and kept in a stable order. The heading remains fixed while a three-row viewport cycles down the configured list: rows hold briefly, slide upward together, then settle on the next ride. When more rides are configured the Thorpe Park screen duration grows so the additional rows can be shown before the board rotates to the next screen. A failed refresh keeps the last successful data and marks only the Thorpe Park screen stale; a cold Queue-Times failure produces an unavailable Thorpe screen without removing rail departures.

Queue data is displayed with `Powered by Queue-Times.com` attribution.

### Todoist upcoming events

Production can append a `calendar_agenda` screen sourced from the Todoist API v1 `GET /api/v1/tasks/filter` endpoint. The publisher follows Todoist cursor pagination, normalizes scheduled items into Europe/London time, sorts them chronologically, removes undated and already-past timed tasks, and publishes at most the next six events.

The display uses a departure-board-style two-column row:

```text
13/09 18:30 Event one
14/09 ALL   All-day event
14/09 09:00 Event three
```

Three rows are visible at once. With four to six events the first three remain visible for five seconds, then the rows slide upward together and events 4–6 settle into the same viewport. The heading, clock and weather overlay remain fixed. With three or fewer events no paging occurs.

Default production settings are:

```text
LED_CALENDAR_SOURCE=off
LED_TODOIST_CACHE_SECONDS=300
LED_TODOIST_MAX_EVENTS=6
LED_TODOIST_FILTER_QUERY=date after: yesterday
LED_TODOIST_TIMEZONE=Europe/London
LED_CALENDAR_DURATION_SECONDS=10
LED_CALENDAR_PAGE_SECONDS=5
```

The feed is intentionally **off by default**. The current production `/api/screens` object is publicly retrievable through CloudFront, so enabling a personal Todoist feed makes the selected task names and dates/times publicly retrievable as part of that JSON response. Use a deliberately narrow Todoist filter/project/label if this exposure is acceptable, or protect/personalize the screen endpoint before enabling private task data.

#### Todoist OAuth bootstrap

Use the Client ID and Client Secret from the Todoist integration rather than a personal API token. OAuth state is stored in SSM Parameter Store at `/led/todoist/oauth` as a **Standard `SecureString`**. The value contains the client credentials plus the current access and refresh tokens. The Lambda reads it with decryption, refreshes expiring access tokens itself, and immediately overwrites the parameter with Todoist's replacement refresh token.

For a newly-created Todoist integration, add this OAuth redirect URL in Todoist App Management unless you choose another URI:

```text
http://127.0.0.1:8765/callback
```

For a fresh authorization, run the bootstrap script from a machine with AWS CLI access to the LED account:

```sh
TODOIST_CLIENT_ID='<client-id>' \
AWS_PROFILE='<aws-profile>' \
python3 scripts/bootstrap-todoist-oauth.py
```

The script prompts securely for the Client Secret, requests only the `data:read` Todoist scope, opens the authorization page in your browser, validates the OAuth `state`, receives the localhost callback, exchanges the authorization code, and writes the credentials/tokens to the Standard `SecureString`. To use a different registered redirect URI, set `TODOIST_REDIRECT_URI`; `--manual` is also available when a localhost callback is unsuitable.

If you already bootstrapped the previous Secrets Manager implementation, migrate the existing OAuth JSON without authorizing Todoist again:

```sh
AWS_PROFILE='<aws-profile>' \
python3 scripts/bootstrap-todoist-oauth.py \
  --migrate-secret-id '<existing-secrets-manager-arn>'
```

After deploying the SSM-backed stack and verifying Todoist, schedule the old Secrets Manager secret for deletion so it is no longer billed:

```sh
AWS_PROFILE='<aws-profile>' aws secretsmanager delete-secret \
  --region eu-west-2 \
  --secret-id '<existing-secrets-manager-arn>' \
  --recovery-window-in-days 7
```

Do not pass the Client Secret on a shell command line. For unattended fresh authorization the script also accepts `TODOIST_CLIENT_SECRET` from the environment, but an interactive prompt is preferred.

Once OAuth is present in SSM, set the GitHub repository variable:

```text
LED_CALENDAR_SOURCE=todoist
```

and run the deployment workflow. There is no `BW_TODOIST_TOKEN` or Todoist token CloudFormation parameter; runtime token rotation is contained in the SSM `SecureString`.

A failed Todoist refresh preserves the last successful events and marks only the calendar screen stale. A cold Todoist failure publishes `Calendar unavailable` without affecting rail, queue or weather data. A successful response containing no qualifying tasks renders `No upcoming events` and is not stale.

For credential-free visual testing, the local fixture contains six normalized events and exercises both agenda pages:

```sh
bash scripts/run-server.sh --calendar-source fixture
```

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
  "fetched_at": "2026-09-13T11:45:30Z",
  "screens": [
    {
      "id": "departures",
      "kind": "rail_combined",
      "duration_seconds": 8,
      "title": "NEM departures",
      "source": "national_rail",
      "stale": false,
      "services": []
    },
    {
      "id": "calendar",
      "kind": "calendar_agenda",
      "duration_seconds": 10,
      "title": "UPCOMING",
      "source": "todoist",
      "stale": false,
      "viewport_size": 3,
      "page_seconds": 5,
      "events": [
        {"start": "2026-09-13T18:30:00+01:00", "all_day": false, "date_text": "13/09", "time_text": "18:30", "title": "Event one"}
      ]
    }
  ]
}
```

The MatrixPortal rotates these screens locally and does not reset the active screen every time fresh data is polled. If the backend becomes temporarily unreachable it keeps the last screens, marks the active screen stale, and dims the retained weather value.

The board clock is derived from the backend's UTC `fetched_at` timestamp and advanced locally between polls. The CircuitPython client converts UTC to Europe/London time itself, including the GMT/BST transitions, so no separate NTP or clock API is needed.

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

For local development instead, copy `hardware/matrixportal/firmware/settings_local.py.example` to the ignored root `settings_local.py` and point `SCREEN_API_URL` at the LAN machine running `scripts/run-server.sh`, for example `http://192.168.1.123:8000`.

The MatrixPortal does not need provider credentials or direct upstream API clients. It makes only the same `/api/screens` request regardless of which server-side feeds are enabled.

For a physical board to reach a local backend, start the grouped backend on an address reachable from the LAN rather than its safe `127.0.0.1` default. For example, on a trusted home network:

```sh
LED_SERVER_HOST=0.0.0.0 bash scripts/run-server.sh
```

Do not expose the local development server directly to the public Internet.
