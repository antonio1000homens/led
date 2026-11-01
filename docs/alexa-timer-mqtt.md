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
the least remaining time. When one finishes, it holds `00:00` briefly and then
selects the next timer. A `clear` publication removes only that device's
snapshot. The separate Office Alexa is not supported.

Running timers require an offset-bearing `ends_at`. Supply
`duration_seconds` only when Alexa exposes the original duration. Paused timers
require `remaining_seconds`; a stale `ends_at` must not be included. A label is
optional and is limited to 40 characters. The board rejects expired running
timers, malformed fields, snapshots for a different device, and snapshots
whose `published_at` is not newer than the last accepted snapshot.

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
clock-anchor correction in progress captures the monotonic time at response
header receipt, before parsing the screen body, so download and parse time do
not make the timer clock lag. The board animates the car at the configured
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
