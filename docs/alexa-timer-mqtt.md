# Alexa timer MQTT contract

The pinned timer scene uses a dedicated retained topic and does not join the
normal screen rotation.

- Topic: `led/timer/living-room-alexa`
- QoS: 1
- Retain: true
- Schema version: 1

Each `upsert` publication is a complete snapshot for that Alexa device. Use a
stable native Alexa timer ID. The board chooses the earliest running timer;
when none are running, it displays the paused timer with the least remaining
time. When one finishes, it holds `00:00` briefly and then selects the next
timer. A `clear` publication removes the device snapshot immediately.

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

The board anchors `ends_at` to its monotonic clock when the snapshot arrives and
animates the car at the configured board refresh cadence. If original duration is
absent, it uses the first observed remaining time as the race baseline. A
retained snapshot restores the timer after reconnect; no per-second MQTT
messages are needed. Refresh a still-active retained snapshot at least every
ten minutes; the board marks the timer `STALE` after ten minutes without an
accepted snapshot. Reminder flashes may cover the timer briefly, after which
the current timer state is rendered again. Timer snapshots are not yet enabled
by the Home Assistant producer. Live running, paused, and natural-completion
records have now been observed; deploy and read back this consumer before
enabling the HA publisher. Resume and cancellation transitions, MQTT delivery,
and physical panel acceptance remain unverified.
