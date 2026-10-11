# SL7 bus departures

The backend publisher polls Transitous/MOTIS directly and publishes two normal
HTTP screen records in `/api/screens`:

- `sl7-heathrow` — Heathrow Central Bus Station, `gb-great-britain_490008016S`
- `sl7-new-malden` — New Malden / Fountain Roundabout, Stop K, `gb-great-britain_490015206K`

Each screen uses `kind: bus_departures`, `route: SL7`, a whitelisted
`stop_key`, `observed_at`, and a bounded list of planned/estimated departures.
The firmware sorts by estimated then planned time, removes passed services,
and deduplicates `trip_id`.

The protected admin API exposes `sl7_bus` through the normal
`PATCH /api/control/v1/feeds/sl7_bus` optimistic-concurrency flow. It is off by
default. The controls are master enablement, per-stop pages, duration, row
count, and bounded stale/scroll settings.

The live Home Assistant configuration currently contains the westbound New
Malden entity `sensor.new_malden_fountain_roundabout_sl7_west_croydon`. It is
no longer used by the LED publisher. Home Assistant and MQTT are not
dependencies for these screens. Physical acceptance still requires both real
stops to be displayed on the 256x32 board.
