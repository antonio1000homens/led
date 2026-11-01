# Alexa timer MQTT contract

The pinned timer scene uses dedicated retained topics and does not join the
normal screen rotation. Home Assistant publishes one complete snapshot per
Alexa device:

- Living room: `led/timer/living-room-alexa` (`living-room-alexa` device)
- Hall: `led/timer/hall-alexa` (`hall-alexa` device)
- QoS: 1
- Retain: true
- Schema version: 1

Each `upsert` publication is a complete snapshot for that Alexa device. Use a
stable native Alexa timer ID. The board chooses the earliest running timer
across both devices; when none are running, it displays the paused timer with
the least remaining time. When one finishes, it holds `00:00` for five seconds
and then selects the next timer. A `clear` publication removes only that device's
snapshot. The separate Office Alexa is not supported.

Running timers require an offset-bearing `ends_at`. Supply
`duration_seconds` only when Alexa exposes the original duration. Paused timers
require `remaining_seconds`; a stale `ends_at` must not be included. A label is
optional and is limited to 40 characters. The board rejects expired running
timers, malformed fields, snapshots for a different device, and snapshots
whose `published_at` is not newer than the last accepted snapshot.

When a label is present, the LED uses its normalized value to choose a stable
animation theme. Labels exactly matching `caterpillar`, `race`, `rocket`, or
`stars` select that theme directly. Other labels consistently hash to a theme;
unnamed timers always use the racing-car theme, matching the original timer
display behavior regardless of their native Alexa ID. Add an exact lower-case
alias to `TIMER_LABEL_THEME_MAP` in `timer_visuals.py` when a specific named
timer should always use a chosen animation. The simulator follows the same
selection behavior.

Example running snapshot:

```json
{
  "schema_version": 1,
  "event": "upsert",
  "source": "homeassistant",
  "device": "living-room-alexa",
  "published_at": "2026-10-31T16:00:01+00:00",
  "timers": [
    {
      "timer_id": "stable-alexa-timer-id",
      "state": "running",
      "ends_at": "2026-10-31T16:05:00+00:00",
      "duration_seconds": 300,
      "label": "Pasta"
    }
  ]
}
```

Example pause and clear snapshots:

```json
{
  "schema_version": 1,
  "event": "upsert",
  "source": "homeassistant",
  "device": "living-room-alexa",
  "published_at": "2026-10-31T16:01:00+00:00",
  "timers": [
    {
      "timer_id": "stable-alexa-timer-id",
      "state": "paused",
      "remaining_seconds": 240,
      "duration_seconds": 300,
      "label": "Pasta"
    }
  ]
}
```

```json
{
  "schema_version": 1,
  "event": "clear",
  "source": "homeassistant",
  "device": "living-room-alexa",
  "published_at": "2026-10-31T16:05:01+00:00"
}
```

The board derives wall time from the screen API's HTTP `Date` header, then
anchors `ends_at` to its monotonic clock when a timer snapshot arrives. The
merged clock-anchor fix captures the monotonic time at response-header receipt,
before parsing the screen body, so download and parse time do not make the timer
clock lag. The board animates the car at the configured
refresh cadence. If original duration is absent, it uses the first observed
remaining time as the race baseline. A retained snapshot restores the timer
after reconnect; no per-second MQTT messages are needed. Refresh a still-active
retained snapshot at least every ten minutes; the board marks the timer `STALE`
after ten minutes without an accepted snapshot. Reminder flashes may cover the
timer briefly, after which the current timer state is rendered again.

## Deployment and live acceptance

The LED consumer is deployed and was verified on the physical MatrixPortal
with a retained synthetic 60-second timer: the user confirmed the countdown
and racing car appeared and updated; expiry cleared the retained message and
returned the board to normal rotation. This validates the consumer and display
path, but not Alexa-to-Home-Assistant delivery.

The Home Assistant publisher is enabled after the LED deployment gate. Its
package is deployed with the native-mapping payload-guard fix. On 2026-11-01,
a live Alexa timer created at 08:23:53.652 UTC produced a retained `upsert` at
08:24:09.332 UTC. The user confirmed that the physical MatrixPortal showed the
countdown and racing car, and that both updated. This verifies an Alexa
start-to-board path; the first physical frame was not timestamped independently.

Earlier lifecycle trials verified a same-ID pause snapshot with 75 seconds
remaining and a later pause snapshot with 175 seconds remaining. A separate
trial published `clear` while over two minutes remained, so it did not verify a
same-ID resume. Duration edit, concurrent timer handoff, and recovery behavior
remain unverified.

On 2026-11-01, the merged LED #324 firmware was deployed and all 35 staged files
passed SHA-256 readback. A fresh 90-second Alexa timer was published at
11:07:21.115 UTC with `started_at` 11:07:20.619 and `ends_at` 11:08:50.328; the
end matched `started_at + duration_seconds` within 0.3 seconds. The physical
board entered the timer scene at 11:07:23, remained in it for 96.1 seconds, and
returned to the normal `TODAY` screen at 11:09:00. HA published `clear` at
11:09:00.147. No render exception appeared in the serial capture. The user
observed Alexa's alarm while the board still appeared to count down its final
seconds; the exact displayed value at the alarm is not yet known. Since the
scene ended about 9.7 seconds after `ends_at`, the timer's final-second timing
still needs physical confirmation. LED #324 fixed the render crash, but this
run does not by itself prove exact-zero alignment or the visible completion
hold.

After HA PR #63 and LED PR #326 were merged, a live 60-second Living room
Alexa timer named `Stars` produced an `upsert` at 12:11:53.162 UTC with
`label: "Stars"`; the user confirmed that the physical display showed an
updating countdown animation. The deployed label map selects the `stars`
theme for this exact normalized label. HA later published a retained `clear`
and the timer topics read `clear`, but the exact-zero frame and return to
rotation were not observed in that run. The MQTT capture contained a `clear` at 12:12:08,
before the then-current `ends_at`, followed by a fresh `Stars` timer at
12:12:42; the cause of that early clear and second start is unknown. A later
`clear` followed the refreshed timer's `ends_at` by about 20.5 seconds. See
the HA repository's `docs/alexa-timer-led-mqtt.md` for the corresponding
producer timestamps. Pause/resume, duration edit, timer replacement, and a
live Hall Alexa timer remain unverified against current device selection.

On 2026-11-01, an unlabelled three-minute Living Room timer was published at
19:40:07.803 UTC. Serial recorded `TIMER START` and `SCREEN OK` for the pinned
timer scene at 19:40:09. The board's then-deployed timer-ID fallback selected
the race theme for this ID; the user confirmed that the unnamed timer used a
different theme from `Stars`. HA published `clear` at 19:43:13.200, and serial
recorded `TIMER END` and return to rotation at 19:43:14 after 185 seconds in
the timer scene. The user confirmed that the physical board showed `00:00`
with the car at the clock before rotation. This verifies natural completion,
the visible finish pose, and release back to rotation. The timer's retained
MQTT payload had no label, so this run does not verify named-label forwarding.
Pause/resume, duration edit, timer replacement, and a live Hall Alexa timer
remain unverified against current device selection.
