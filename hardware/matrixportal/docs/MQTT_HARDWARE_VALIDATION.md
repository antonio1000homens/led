# Issue #74 hardware validation gate

This is the test procedure for the MatrixPortal MQTT path. It is intentionally
not an activation instruction: the checked-in safety flags remain false until
Home Assistant issue #4 and the broker configuration are approved.

## Preconditions

- Home Assistant schedules the next Alexa reminder and publishes one
  `event: "due"` payload to `led/flash/reminder` at its due time with QoS 1 and
  `retain: false`.
- A stable broker hostname and uncommitted board credentials are available.
- `adafruit_minimqtt` has been installed into `CIRCUITPY/lib`.
- The board is running the current B8 production refresh profile.
- Record a disabled-MQTT baseline first; do not compare against memory or a
  different payload.

## Capture for each run

Use the existing serial diagnostics for a minimum of 60 seconds of Todoist
and departures activity. Record:

- `MATRIX PRESENTATION` profile and target cadence;
- `MATRIX STATS` refresh attempts, successes, failures and heap values;
- `FRAME PACE` tick rate, late frames and maximum late streak;
- fetch success/failure and reconnect messages;
- visible flashing, tearing, marquee jumps and page-slide behaviour.

Run the same payload in two states:

1. MQTT disabled (B8 baseline).
2. MQTT enabled but idle, with no published messages.

The idle run must retain bounded socket servicing and show no material change
in refresh failures, late-frame streaks, heap drift or visible rendering.

## Event checks

With the idle run stable, publish several test events and verify:

- the flash starts without waiting for the HTTP poll;
- the configured runtime duration is honoured;
- the underlying screen resumes at its prior phase;
- a duplicate ID is ignored;
- an expired event is ignored;
- a newer event replaces an active flash and restarts its duration;
- broker disconnect leaves HTTP screen rotation operating;
- reconnect restores the subscription.

Do not enable the production board path or close #74 until these observations
are recorded against the actual MatrixPortal and the Home Assistant publisher.

## Captured baseline

On 2026-09-21, the physically connected MatrixPortal S3 was synchronized with
the production bundle and measured with MQTT disabled (`MQTT_ENABLED = False`,
`MQTT_ENABLE_EXPERIMENTAL = False`) using the `B8` profile:

- presentation mode: `immediate`
- target animation rate: 8 FPS
- frame-pacing samples: 7.73 FPS at 40.2 seconds, 7.07 FPS at 82.7 seconds
- late frames: 6 and 9 respectively; maximum late streak: 1 and 2
- HUB75 refresh failures: 0 in each observed matrix statistics sample
- departures and calendar rendered, with successful HTTP refreshes during the capture
- observed render times: 1.070 seconds for departures and 0.526 seconds for calendar

The checked-in firmware remains gated by safe defaults. Local board-only MQTT
settings were enabled for the controlled tests recorded below; production
activation still depends on the live Home Assistant issue #4 contract and
broker approval.

## Fresh synchronized baseline

On 2026-09-21, after synchronizing the attached MatrixPortal with the merged
`master` runtime bundle, a 70-second disabled-MQTT capture was recorded with
both local MQTT gates false:

- target animation rate: 8 FPS;
- frame-pacing samples: 7.67 FPS at 60.2 seconds, 7.75 FPS at 80.2 seconds,
  7.78 FPS at 100.3 seconds and 7.79 FPS at 120.4 seconds;
- late frames: 10, 10, 13 and 15 respectively; maximum late streak: 2;
- HUB75 refresh failures: 0 in every sample;
- normal HTTP refreshes succeeded (`FETCH OK screens=2`);
- no MQTT connection or flash-event output appeared.

Use this synchronized capture as a historical disabled-MQTT reference. A
controlled but incomplete same-session comparison is recorded below.

## Manual due-event smoke test

With MQTT enabled only in the board's uncommitted `settings_local.py`, run from
the repository root:

```bash
./.venv/bin/python scripts/publish_mqtt_test_event.py --label "Manual MQTT test"
```

The publisher reads the private board settings without printing credentials,
connects to the configured broker, and publishes a unique `event: "due"`
message to `led/flash/reminder` with QoS 1 and `retain: false`. A successful
run reports PUBACK. On the physical board, confirm `FLASH START`, the supplied
label, the configured flash duration, `FLASH END`, and normal-screen recovery.
This is a board transport smoke test; it does not exercise Home Assistant's
Alexa schedule.

Focused parser/state checks can use explicit IDs and expiry values:

```bash
# Send this command twice; the second event must not start another flash.
./.venv/bin/python scripts/publish_mqtt_test_event.py --event-id duplicate-check

# Both messages must be ignored by the board.
./.venv/bin/python scripts/publish_mqtt_test_event.py --event scheduled --event-id scheduled-check
./.venv/bin/python scripts/publish_mqtt_test_event.py --expires-in-seconds -60 --event-id expired-check
```

For replacement, publish two different IDs and labels less than five seconds
apart. Expect `FLASH START` for A, then `FLASH START` for B before one `FLASH
END`; the underlying rotation should resume after B.

## Controlled MQTT-enabled comparison (2026-09-25)

The same attached MatrixPortal S3, B8 presentation profile and target cadence
were used. MQTT ran over authenticated raw MQTT/TCP to
`windsor-app2.internal.alf1000.uk:1883`; the board credentials remain only in
`CIRCUITPY/settings_local.py`. Adafruit MiniMQTT was present in
`CIRCUITPY/lib`. The local transport used a 10 ms socket timeout and a 2-second
poll interval. The checked-in safe defaults were not changed.

| State | Capture | Presented FPS | Max frame interval | HUB75 refresh failures | Heap at start/end | Todoist marquee ticks | HTTP |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| MQTT enabled, idle | 121.8 s | 7.23 | 4.4224 s | 0 | 1,959,296 / 1,747,392 | 1 | fetches succeeded |
| MQTT enabled, idle | 160.6 s | 7.00 | 5.1689 s | 0 | 1,959,264 / 1,623,424 | 234 | fetches succeeded |
| MQTT disabled | 60.4 s | 7.25 | 4.3364 s | 0 | 1,959,328 / 1,813,072 | 0 | fetch succeeded |
| MQTT disabled | 60.4 s | 7.03 | 4.4399 s | 0 | 1,959,248 / 1,804,400 | 0 | fetches succeeded |

Two nearby comparisons differ by 0.02 and 0.03 FPS, with zero HUB75 refresh
failures in every run. The enabled sample at 160.6 seconds also recorded 234
Todoist marquee ticks; its matching disabled run did not contain Todoist
marquee activity. All run lengths differ, so this does not prove a causal
performance gain from increasing the poll interval. It does show no consistent
idle regression from the 2-second poll. Frame intervals over four seconds and
the long scene renders/fetches dominate the worst stalls.

The enabled frame-pacing sample at telemetry elapsed 153.2 seconds recorded
94 late frames, a maximum late streak of 35, six fetches with no failures, and
four over-budget scene renders (average 0.842 seconds, maximum 1.625 seconds).
No equivalent `FRAME PACE` sample was captured in the disabled runs, so their
late-frame counts and streaks remain unverified.

The board subscribed at QoS 1 and stayed connected during the enabled-idle
capture. With MQTT enabled, the following controlled checks were observed:

- valid event: flash started and ended, then normal rendering continued;
- duplicate event ID: one flash start only;
- expired event: ignored;
- replacement A then B: both accepted, with B replacing the active flash;
- broker hostname path: a fresh valid event reached the board and logged both
  `FLASH START` and `FLASH END`;
- 2-second polling: one valid event was observed starting 1.339 seconds after
  the publisher received PUBACK.

CircuitPython prints `Code stopped by auto-reload` when files on the mounted
`CIRCUITPY` drive change. The observed reloads coincided with the deliberate
firmware/configuration writes during these tests. Keep all test settings
changes together and allow the board to finish reloading before measuring.

After this capture, the board was soft-restarted and logged a fresh Wi-Fi
connection, `MQTT subscribed topic=led/flash/reminder`, then a valid event's
`FLASH START` and `FLASH END`. Additional hardware checks confirmed one flash
for two identical IDs, no flash for a scheduled or expired event, and
replacement of event A by event B before the flash ended. After a parser fix,
a payload with fractional-second ISO 8601 timestamps also flashed and ended
normally. These focused runs verify event handling but are not matched
performance samples.

Local safety-gate toggle smoke test on 2026-09-25:

- With both local MQTT gates false for 100 seconds, the board continued to
  fetch and render HTTP screens; the observed matrix samples had zero HUB75
  refresh failures. No MQTT subscription was made. The workload had no active
  Todoist marquee content.
- After restoring both local MQTT gates to true, the board logged a new QoS 1
  subscription. A fresh due event received PUBACK and produced `FLASH START`
  and `FLASH END`; HTTP screen fetches continued during the flash.
- This verifies board-local bootstrap gating and re-subscription after a
  CircuitPython reload. It does not exercise the runtime flash controls from
  `/api/screens`, simulate a broker outage, or provide a matched performance
  comparison. The enabled run later included Todoist marquee activity, so its
  timing is not comparable to the disabled run.

Runtime flash-control hardware smoke test on 2026-09-25:

- Kept both board-local MQTT gates enabled and temporarily served a synthetic
  `/api/screens` response from the LAN with a one-screen test payload.
- With `flash.enabled=false` and `screen_duration_seconds=3`, the board fetched
  the response and stayed subscribed. A valid QoS 1 event received PUBACK but
  produced no `FLASH START` or `FLASH END` during the six-second observation.
- With `flash.enabled=true`, a fresh event produced `FLASH START` and the
  matching end log on the board. After changing
  `screen_duration_seconds` from 3 to 6 in the served response and waiting for
  the next fetch, another fresh event also produced the expected start/end
  transition.
- The serial output was not timestamped closely enough to claim a precise
  measured flash interval; this verifies runtime enable/disable and duration
  updates reached the hardware, while exact visual timing still merits direct
  inspection.
- Restored `SCREEN_API_URL=https://led.alf-broadcast.co.uk`; the board
  reloaded, resubscribed to `led/flash/reminder`, and fetched two public screens
  successfully. The temporary LAN server was stopped.

Broker outage/recovery hardware smoke test on 2026-09-25:

- To avoid interrupting the shared Home Assistant broker, ran a temporary
  authenticated MQTT broker on the laptop and changed only the board-local
  `MQTT_BROKER` host for this test. The normal public screen API remained in
  use.
- The board subscribed to `led/flash/reminder`. Stopping the temporary broker
  produced `MQTT unavailable`; HTTP screen fetches and rendering continued.
- After restarting that broker, the board resubscribed to the topic. A fresh
  QoS 1 test event received PUBACK and produced `FLASH START` followed by
  `FLASH END` on the board.
- Restored `MQTT_BROKER=windsor-app2.internal.alf1000.uk`; after reload the
  board subscribed again and fetched the public API. The temporary broker was
  stopped; the shared Home Assistant broker was never interrupted.

Supplemental idle observations on 2026-09-25 after the parser update:

- MQTT enabled, no reminder traffic: at telemetry elapsed 40 seconds, the
  frame-pacing sample recorded 9.32 tick FPS, 95 late frames, maximum late
  streak 27, 17 successful fetches, and six over-budget scene renders. At
  elapsed 448.8 seconds the matrix summary reported 7.58 presented FPS, a
  5.1504-second maximum interval, zero refresh failures, and heap
  1,959,184/1,609,600 bytes.
- MQTT disabled locally for comparison: after 82.4 seconds the matrix summary
  reported 7.09 presented FPS, a 4.3438-second maximum interval, zero refresh
  failures, and heap 1,959,232/1,807,088 bytes. HTTP fetches succeeded, but
  Todoist marquee ticks remained zero.

These captures are not workload-matched: the enabled run had Todoist marquee
activity, the disabled run did not, and both include different startup/fetch
conditions. They are recorded as supplemental evidence only and do not show a
causal performance difference.

Matched local-fixture comparison on 2026-09-25:

- The board fetched the same two-screen payload from a temporary LAN fixture
  server in both runs. MQTT gates were the only setting changed between runs.
- MQTT disabled: 120.4 seconds, 83 matrix refreshes, 0 refresh failures,
  0.69 presented FPS, 1.4146-second average refresh interval, and 6.1 ms
  average scene update time.
- MQTT enabled and idle: 121.7 seconds, 53 matrix refreshes, 0 refresh
  failures, 0.44 presented FPS, 2.1836-second average refresh interval, and
  4.1 ms average scene update time.
- The animation phase differed between captures, so refresh counts, interval,
  and update-time differences are not attributable to MQTT. The board logs do
  not measure whole-device CPU utilization; this comparison cannot establish
  a CPU saving from changing the two-second MQTT service interval to one
  minute. Both runs continued HTTP fetches without matrix refresh failures.
- The board was restored to `https://led.alf-broadcast.co.uk`, with both
  local MQTT gates enabled. It reloaded, subscribed to
  `led/flash/reminder`, and fetched the public API successfully. The temporary
  LAN fixture server was stopped.

Still outstanding: repeated workload-aligned captures that allow CPU use to
be measured directly, visual inspection for tearing, and the live Home
Assistant #4 Alexa recurrence and restart scenarios. Do not close #74 on these
partial measurements.
