# Issue #74 hardware validation gate

This is the test procedure for the MatrixPortal MQTT path. It is intentionally
not an activation instruction: the checked-in safety flags remain false until
Home Assistant issue #3 and the broker configuration are approved.

## Preconditions

- Home Assistant publishes the documented `led/flash/reminder` contract with
  QoS 1 and `retain: false`.
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

The MQTT-enabled-but-idle comparison and event checks remain gated on the
Home Assistant issue #3 contract and approved broker configuration.

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

Use this synchronized capture as the disabled-MQTT reference for the eventual
approved MQTT-enabled-idle comparison.
