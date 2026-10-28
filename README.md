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


MQTT carries two independent display paths. Retained snapshots on
`led/screens/+` add expiring screens to the normal rotation; reminder events on
`led/flash/reminder` and `led/flash/assistant-response` remain interrupting
overlays that pause and resume that rotation. Assistant replies use the
version 1 `assistant_response` contract, render with an `ASSISTANT` heading,
show the complete message in compact quote-style pages of up to three lines,
and never modify reminder snapshot state. The flash extends as needed to show every page; the event still
expires if it arrives more than 120 seconds after publication. Reminders take
priority over assistant replies. See [LED issue #251](https://github.com/antonio1000homens/led/issues/251)
and the [Home Assistant publisher issue #41](https://github.com/antonio1000homens/homeassistant/issues/41).
Retained football snapshots on `led/football/sporting_cp` and
`led/football/millwall` trigger a coalesced, prompt match presentation: the
football slides in from the right and remains pinned at the left of the match
text. PRE fixtures show only the teams and Europe/London kick-off time. Flash
reminders keep priority, and football snapshots also remain in the normal
rotation. See [football MQTT behavior](docs/football-mqtt.md).
The first cycle-screen producer is the [Home Assistant next-recycling
screen](https://github.com/antonio1000homens/homeassistant/issues/7). The board
uses one MQTT connection, and broker credentials remain in board-local
settings.

To exercise the assistant-response path on a configured board before the Home
Assistant publisher is available, run
`python3 scripts/publish_mqtt_test_event.py --type assistant_response --label "The next collection is recycling tomorrow."`
and pass `--settings` if `settings_local.py` is not at the script's default
mounted-board path. The test event uses the production topic and QoS, is
non-retained, and expires after 120 seconds.

SL7 bus departures are polled by the backend from Transitous and arrive in the
same HTTP `/api/screens` payload as the other feeds; they do not use Home
Assistant or MQTT. SL7 MQTT slots are ignored so a retained local message
cannot replace either HTTPS-backed page. The MatrixPortal does not hold National Rail, Todoist,
Transitous, Queue-Times or weather-provider credentials. It only needs Wi-Fi
access to the backend. Feed authentication, polling, caching and stale handling
remain server-side.

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

## Remote model slicing

This repository owns the CAD sources and geometry validation. The reusable
Windsor Slicer service prepares this repository at an immutable commit,
generates the model declared in `.windsor-slicer.yaml`, validates it, and
returns a sliced 3MF. It does not submit jobs to a printer.

See [Windsor Slicer](https://github.com/antonio1000homens/windsor-slicer) for
the manifest contract and service details. The public MCP endpoint is
`https://slicer.alf-broadcast.co.uk/mcp`.
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

Production can append a `calendar_agenda` screen sourced from the Todoist API v1 `GET /api/v1/tasks/filter` endpoint. The publisher follows Todoist cursor pagination, normalizes scheduled items into Europe/London time, retains active overdue tasks, sorts them chronologically, removes only undated tasks, and publishes at most six events. Overdue rows are labelled `OVERDUE` on the board.

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
LED_TODOIST_FILTER_QUERY=due before: tomorrow | due after: yesterday
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

### Current weather overlay and dedicated Weather screens

The backend uses one Open-Meteo request and one atomic Weather cache for all Weather output: the compact current-weather overlay, the seven-day daily forecast, the rolling next-24-hour forecast, and today's sunrise/sunset. The request includes current temperature/WMO weather code, hourly temperature/weather code, and daily max/min/weather code/sunrise/sunset with `timezone=auto`. The free non-commercial endpoint needs no API key. Weather is cached for 600 seconds by default, so MatrixPortal/browser polls never create separate upstream polling paths for the three dedicated screens.

The default coordinates are New Malden railway station, matching the default `NEM` departure board:

```text
LED_WEATHER_SOURCE=open_meteo
LED_WEATHER_CACHE_SECONDS=600
LED_WEATHER_LATITUDE=51.4039
LED_WEATHER_LONGITUDE=-0.256
```

Set `LED_WEATHER_SOURCE=off` to stop Weather polling and remove all Weather output, or change latitude/longitude for another location. When Weather is enabled, the dedicated screens appear in this order when their individual controls are enabled:

1. `weather_sun` — today's local sunrise and sunset times, default 6 seconds.
2. `weather_today` — six rolling four-hour snapshots covering the next 24 hours, default 8 seconds. The first column is labelled `Now` and uses current conditions; the remaining columns are labelled at four-hour intervals and may cross midnight. The weather icon and temperature remain prominent.
3. `weather_weekly` — the seven-day overview, default 8 seconds. It preserves the max-only layout introduced with #195: weekday, enlarged weather icon and maximum temperature.

The enabled weather screens form one contiguous block during each rotation, even when static feeds are shuffled. The non-animated next-24-hour and seven-day screens can host explicit garbage collection, scheduled fetches and task preparation; the animated sunrise/sunset screen cannot.

Weather forecasts and the standalone Today screen use the palette-indexed 14×14 sprites in `hardware/matrixportal/firmware/weather_sprites.py`; the sunrise/sunset animation uses its 21×21 sun and moon sprites. The shared header keeps the clock visible and does not rotate in a compact weather icon.

The firmware and browser simulator add a local `christmas_tracker_intro` followed immediately by `christmas_tracker`; these screens need no API feed or provider configuration. The 8-second intro slides a 52-pixel Santa sleigh in from the right beside `HO HO HO...`. The following 18-second screen shows the London-local days-until-Christmas count with falling snow from its first frame. They remain one rotation block. The MatrixPortal prepares both scenes before entry and collects after preparation. Automatic garbage collection stays enabled during animation so per-frame allocations cannot exhaust the board heap; it collects again after the tracker exits.

Every screen owner also has an optional **Cron schedule** in the admin page's
Advanced section. Leave it blank to include that screen on every rotation.
Schedules use five numeric cron fields (`minute hour day-of-month month
day-of-week`) in `Europe/London`, with `*`, lists, ranges and `/step` values.
For example, `0 8 * * 1-5` includes the screen at 08:00 on weekdays. The
MatrixPortal evaluates the schedule when it selects the next screen, so a
screen already animating finishes its normal duration before a newly inactive
screen is skipped. A newly active screen is eligible at the next screen
boundary. If all scheduled screens are inactive, the display shows a short
local status page and checks again as the clock advances. Weather pages share
one schedule, as do all SL7 pages; Queue Times is one combined screen. The
steam-train and bus introductions remain paired with their matching departure
screen. MQTT recycling screens use the same rotation schedule; transient flash
events use the schedule configured on Flash events.

The protected admin/control plane provides independent enable and duration controls for the overview, next-24-hour and sunrise/sunset screens. The master Weather `enabled` switch still owns provider polling. If all three dedicated screens are disabled while Weather remains enabled, polling/cache refresh continues and the current-weather overlay can still appear on unrelated screens.

The backend maps Open-Meteo WMO weather codes into a renderer-neutral icon set (`clear_day`, `clear_night`, `partly_cloudy_*`, `cloudy`, `fog`, `rain`, `snow`, `storm`). All three dedicated Weather screens use the full 256×32 canvas and suppress the normal clock/current-weather/STALE header chrome; the browser simulator mirrors the same screen sequence and supports forced-stale preview.

If a Weather refresh fails after at least one successful response, the complete last-good current + weekly + rolling next-24-hour + solar payload remains available with `stale: true` and the dedicated renderers use their muted treatment. On a cold Weather failure, unrelated feeds remain available; the seven-day overview may show its existing unavailable state when enabled, while empty next-24-hour and sunrise/sunset screens are not emitted. Browser attribution links to Open-Meteo are included as required by the provider's licence.

### Screen contract

`GET /api/screens` is the renderer-neutral contract. A response contains `fetched_at`, an optional shared `weather` object, and one or more screens. Weather is sent once at the top level instead of being copied into each screen; the board and browser simulator attach that same object to screens locally for the shared header carousel. Weather also contributes one dedicated `weather_weekly` screen with a `days` array:

The authenticated admin page includes **Board preview → Live screen preview**. It embeds the same renderer as the public simulator, reads `/api/screens`, and cycles through the fetched screens; Previous, Next, and Pause let you inspect individual entries. The preview loads only while that admin section is open. It does not include retained MQTT events, which the MatrixPortal receives on a separate connection.

```json
{
  "fetched_at": "2026-09-13T11:45:30Z",
  "weather": {
    "source": "open_meteo",
    "temperature_c": 17.4,
    "weather_code": 2,
    "icon": "partly_cloudy_day",
    "stale": false
  },
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

The board can also receive MQTT cycle screens independently from HTTP. Publish
retained JSON snapshots to `led/screens/<screen.id>` at QoS 1. Each snapshot
uses `schema_version: 1`, `event: "upsert"`, ISO-8601 `published_at` and
`expires_at`, a `source`, and a renderer payload under `screen`. A later
`published_at` replaces that slot; an older one is ignored. Send
`event: "clear"` with a fresh `published_at` to remove a slot. Expiry is checked
against the synchronized board clock locally, so an expired retained value
does not reappear after reconnect. HTTP screens remain in backend order, then
active MQTT screens are appended in stable ID order.

The topic suffix must exactly equal `screen.id`. The board accepts only
schema version 1 and `upsert` or `clear` events, and ignores malformed,
unknown-kind, mismatched, older and already-expired snapshots. A clear retains
its publication timestamp for ordering. Reconnect delivers the broker's
retained active snapshot again.

```json
{
  "schema_version": 1,
  "event": "upsert",
  "published_at": "2026-10-07T19:00:05+01:00",
  "expires_at": "2026-10-14T00:00:00+01:00",
  "source": "homeassistant",
  "screen": {
    "id": "homeassistant-next-bin",
    "kind": "bin_collection",
    "title": "NEXT COLLECTION",
    "duration_seconds": 8,
    "slide_speed": 20,
    "collection_date": "2026-10-13",
    "collections": [{"id": "mixed", "label": "Mixed recycling"}],
    "source": "homeassistant",
    "stale": false
  }
}
```

Clear a slot by publishing a retained `event: "clear"` snapshot with a newer
`published_at` to that same topic. It has no `screen` or `expires_at` field.

The Recycling admin card controls whether a valid MQTT `bin_collection` screen is
eligible on the MatrixPortal, its on-device screen duration and label speed,
and the number of Europe/London calendar days preceding the collection date
(defaults: enabled, 20 seconds, 15 pixels/second, two days). The LED publisher
exposes this *presentation policy* under `mqtt.recycling` in `/api/screens`;
firmware also accepts the former root-level `recycling` field during staggered
rollouts. The publisher does not ingest collection dates or MQTT events. Home
Assistant retains responsibility for the dates and retained MQTT snapshots.
The board uses its synchronized local date and keeps snapshots untouched until
the original MQTT expiration or clear. Live MQTT status and next collection
dates cannot be seen by the cloud admin, so its Recycling health shows
unavailable instead of a fabricated healthy status. The browser simulator's
Preview recycling screen button is an explicit fixture preview and ignores
the enabled/date gate.

**Deployment order:** update the LED board firmware before deploying the Home
Assistant package change that publishes collections outside the former two-day
window. See [LED issue #244](https://github.com/antonio1000homens/led/issues/244).

The first MQTT renderer is `bin_collection`: provide `title`, ISO
`collection_date`, one or two `{id, label}` collection entries,
`duration_seconds`, and `slide_speed`. The supplied labels are shown together
on one screen, with long labels scrolling at the supplied pixel rate. Preview
it in the browser simulator with **Preview recycling screen**. The initial
producer work is tracked in [Home Assistant issue #7](https://github.com/antonio1000homens/homeassistant/issues/7).

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
WIFI_STARTUP_DELAY_SECONDS = 10
WIFI_TX_POWER_DBM = 8
```

The physical API application keeps Wi-Fi off for 10 seconds, then enables it
with an 8 dBm transmit-power limit before connecting. The bare-board test
restarted on the wall USB supply at its original transmit power, but remained
reachable at 8 dBm; the full application also answered pings on that supply.
Stability with powered panels still requires a physical check. Lower transmit
power reduces range and does not establish that the supply is electrically sound.

Use custom `WIFI_SSID` and `WIFI_PASSWORD` keys in board-local `settings.toml`,
or the Python settings above. Remove the reserved `CIRCUITPY_WIFI_SSID` and
`CIRCUITPY_WIFI_PASSWORD` keys: those cause an automatic connection before the
application can apply its transmit limit. Automatic browser maintenance is
disabled with this configuration; install over USB and power-cycle afterward
so the staged `boot.py` runs. Existing credentials remain board-local.

For local development instead, copy `hardware/matrixportal/firmware/settings_local.py.example` to the ignored root `settings_local.py` and point `SCREEN_API_URL` at the LAN machine running `scripts/run-server.sh`, for example `http://192.168.1.123:8000`.

The MatrixPortal does not need provider credentials or direct upstream API clients. It makes only the same `/api/screens` request regardless of which server-side feeds are enabled.

For a physical board to reach a local backend, start the grouped backend on an address reachable from the LAN rather than its safe `127.0.0.1` default. For example, on a trusted home network:

```sh
LED_SERVER_HOST=0.0.0.0 bash scripts/run-server.sh
```

Do not expose the local development server directly to the public Internet.
