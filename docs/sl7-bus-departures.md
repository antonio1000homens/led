# SL7 bus departures on the LED board

## Data path: Transitous over HTTPS only

The LED backend polls the Transitous/MOTIS HTTPS API for the two SL7 stops:

- Heathrow Central Bus Station (`gb-great-britain_490008016S`)
- New Malden Fountain Roundabout, Stop K (`gb-great-britain_490015206K`)

The backend filters responses to SL7 and the selected physical stop, normalises departures, caches its results and publishes two `bus_departures` pages (with their bus introductions) through the existing HTTP `/api/screens` payload. The MatrixPortal polls that same HTTP endpoint used by other backend feeds.

**SL7 does not subscribe to, publish to or require MQTT.** It does not use Home Assistant sensors or the Home Assistant `ha_departures` integration. The board rejects any `led/screens/sl7-*` MQTT slot (including retained messages from older integrations), and MQTT cycle screens cannot override an HTTP SL7 page. MQTT remains available for unrelated functionality such as recycling screens and reminder notifications.

## Admin controls

The protected `/admin` card is **SL7 bus departures**, with provider **Transitous / MOTIS · HTTPS API**. The normal backend health and refresh timestamps apply.

Available controls:

- Master enable/disable (off by default)
- Heathrow and New Malden page switches
- Optional animated blue bus that enters from the right immediately before each enabled SL7 stop page. Default trailing text: `Beep! Beep!...`
- Bus intro enable/disable, animation speed (8–80 pixels/second), and printable ASCII trailing text (up to 80 characters)
- Screen duration and no-service duration
- Display frequency every 1–6 rotations (intro and departure page remain paired)
- Number of upcoming buses (1–3)
- Advanced stale threshold and destination scroll speed

The intro is paired with each corresponding stop and inherits the SL7 display frequency. Disabling the intro does not disable departures or the separate rail steam-train animation. Existing saved SL7 settings are automatically given safe default intro settings.

Changes to `sl7_bus` via the normal authenticated control API affect the backend-published HTTP pages on the next refresh; no HA entity IDs, MQTT broker or board-local bus policy are needed.

## Rendering and validation

Each stop page has the bright SL7 header, UK-local clock and up to three destination rows with local departure time and countdown/cancellation indication. Delayed rows are amber, cancelled rows are red; stale and unavailable states are marked separately. The backend handles Europe/London daylight saving time and removes already-departed services.

Run `bash scripts/run-tests.sh` in the LED checkout, preview both SL7 fixture pages in the browser simulator and validate both real stops on the 256×32 MatrixPortal. Confirm timestamps, headsigns, empty/unavailable handling, update frequency and the admin toggles. No Home Assistant or broker setup is part of SL7 acceptance.
