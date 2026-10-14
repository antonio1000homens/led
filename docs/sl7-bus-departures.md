# SL7 bus departures on the LED board

## Data path: Transitous over HTTPS only

The LED backend polls the Transitous/MOTIS HTTPS API for the two SL7 stops:

- Heathrow Central Bus Station, Stop 19 (`gb-great-britain_4900801619`)
- New Malden / Fountain Roundabout, Stop J (`gb-great-britain_490015206J`)

The backend filters responses to SL7 and the selected physical stop, normalises departures, caches its results and publishes one two-column `bus_departures_combined` page (with one optional bus introduction), or two legacy stop pages through the existing HTTP `/api/screens` payload. The configured IDs are the route-specific platform IDs returned by Transitous: Heathrow Central Stop 19 (`gb-great-britain_4900801619`) and New Malden Fountain Roundabout Stop J (`gb-great-britain_490015206J`). The MatrixPortal polls that same HTTP endpoint used by other backend feeds.

**SL7 does not subscribe to, publish to or require MQTT.** It does not use Home Assistant sensors or the Home Assistant `ha_departures` integration. The board rejects any `led/screens/sl7-*` MQTT slot (including retained messages from older integrations), and MQTT cycle screens cannot override an HTTP SL7 page. MQTT remains available for unrelated functionality such as recycling screens and reminder notifications.

## Admin controls

The protected `/admin` card is **SL7 bus departures**, with provider **Transitous / MOTIS · HTTPS API**. The normal backend health and refresh timestamps apply.

Available controls:

- Master enable/disable (off by default)
- Heathrow and New Malden direction switches
- **Layout mode** (default `split_columns`; optional `separate_stops` legacy pages), configured through the same versioned runtime admin API
- Split mode: 256×32 display divided into two 128px columns: **SL7 to Heathrow** (left, departures from New Malden) and **SL7 to New Malden** (right, departures from Heathrow). Four 8px lines per column (header and up to three rows with **`HH:MM` first**, followed by **`Due in 15m`** or **`Due in 0m`** for imminent buses), without the normal overlay clock
- Optional red double-decker bus, with two distinct rows of passenger windows, that enters from the right, stops fully visible at the left edge, and then gives way to each enabled SL7 stop page. Default trailing text: `Beep! Beep!...`
- Bus intro enable/disable, animation speed (8–80 pixels/second), and printable ASCII trailing text (up to 80 characters)
- Screen duration and no-service duration
- Display frequency every 1–6 rotations (one intro is paired with the combined page; separate mode pairs one intro per enabled stop)
- Number of upcoming buses (1–3 **per column**)
- Advanced stale threshold and destination scroll speed

In split mode there is one intro immediately before the combined page, inheriting its display frequency. In legacy separate mode the intro stays paired with each corresponding stop. Disabling the intro does not disable departures or the separate rail steam-train animation. Existing saved SL7 settings are automatically given safe default intro settings.

Changes to `sl7_bus` via the normal authenticated control API affect the backend-published HTTP pages on the next refresh; no HA entity IDs, MQTT broker or board-local bus policy are needed.

## Rendering and validation

The default combined page has two fixed-width side-by-side sections, each showing the upcoming 1–3 trips as Europe/London local departure time at the left, followed by an explicit `Due in` rolling countdown on the right. A cancelled row displays `CXL` in place of the countdown. The page deliberately suppresses the global clock/header overlay so neither directional title is obscured. When one direction is disabled or unavailable, the other continues showing live trips. Optional legacy stop pages preserve the prior full-width detail rows. Delayed rows are amber, cancelled rows are red; stale and unavailable states are marked separately. The backend handles Europe/London daylight saving time and removes already-departed services.

Run `bash scripts/run-tests.sh` in the LED checkout, preview both SL7 fixture pages in the browser simulator and validate both real stops on the 256×32 MatrixPortal. Confirm timestamps, headsigns, empty/unavailable handling, update frequency and the admin toggles. No Home Assistant or broker setup is part of SL7 acceptance.
