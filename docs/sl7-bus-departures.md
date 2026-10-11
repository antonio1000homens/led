# SL7 bus departures on the LED board

The 256×32 MatrixPortal S3 already supports the two SL7 pages and the animated
bus intro. This work extends that existing feature rather than introducing a
second independent renderer.

## Sources and precedence

- **Backend fallback:** the LED publisher polls Transitous/MOTIS for
  Heathrow Central Bus Station (`gb-great-britain_490008016S`) and New Malden
  Fountain Roundabout, Stop K (`gb-great-britain_490015206K`). Responses are
  filtered to SL7 and, when a `place.stopId` is supplied, to the selected
  physical departure stop. This source works without Home Assistant.
- **Home Assistant override:** the `ha_departures` integration can publish
  bounded retained MQTT snapshots to `led/screens/sl7-heathrow` and
  `led/screens/sl7-new-malden` using the companion
  `homeassistant/packages/sl7_departures_led.yaml` package. At runtime the
  MatrixPortal prefers a valid, unexpired MQTT snapshot for the corresponding
  HTTP stop ID. There is never a duplicate stop page.

The companion HA package has two `input_text` selectors for the **actual
existing HA sensor entity IDs**; set these in Home Assistant after deploying
the package. The integration's entity IDs are held in HA's UI-managed
configuration entries, not in the repository. Do not infer stop identity from
the journey destination or assume the two ends have the same headsign.

## Normal-cycle MQTT contract

Use `schema_version: 1`, `event: upsert`, `published_at`, `expires_at`,
`source: homeassistant` with `screen` of kind `bus_departures`. The
screen must contain the matching `id`, exact `route: SL7`,
`stop_key: heathrow|new-malden`, readable `title` and `stop_name`,
`observed_at`, numeric `duration_seconds`, `status`, and at most 10
departures with ISO-aware `planned`, optional `estimated`, `trip_id`,
`destination`, `cancelled` and `alerts`. Optional `local_time` in
Europe/London and `due_text` are presentation helpers.

Snapshots expire within **five minutes** of publication. The board also
marks data older than `stale_after_seconds` as STALE and drops expired
slots. Invalid payloads do not replace a previously valid slot. A `clear`
message removes a slot when its HA source is decommissioned.

The board continues to display the independent HTTP fallback if the MQTT
snapshot is missing or expired. Admin settings are always delivered through
the existing `/api/screens.sl7_bus` non-secret policy, even though MQTT does
not have its own API status endpoint.

## Admin controls

Use **SL7 bus departures** in `/admin`:
- Master enable/disable (off by default)
- Heathrow and New Malden pages independently
- Screen and no-service durations
- Display every 1–6 rotations (intro stays paired with its bus screen)
- 1–3 upcoming buses (three legible rows fit in the 32px panel)
- Stale threshold and destination scroll-speed settings

The provider label indicates the fallback's Transitous source. Admin's
cloud-only health endpoint does not measure the local MQTT broker health.

## Rendering, testing and deployment

Each stop page shows a bright SL7 stop header, a clock, and up to three rows
with destination, local UK departure time, and countdown or cancellation.
Delayed rows are amber; cancelled rows are red. Expired services are removed
during refresh; the backend normalises UTC to Europe/London including DST.

Run `bash scripts/run-tests.sh` in the LED checkout. Check the browser
simulator with fixture SL7 screens, then perform on-device acceptance with
real SL7 departures in both directions. Confirm the Home Assistant entity
mapping for each real stop and verify time, cancellation, status, MQTT expiry
and fallback under broker disconnection.

The original HA sensor files are
[`sensor.py`](https://github.com/antonio1000homens/homeassistant/blob/master/custom_components/ha_departures/sensor.py)
and [`const.py`](https://github.com/antonio1000homens/homeassistant/blob/master/custom_components/ha_departures/const.py).
