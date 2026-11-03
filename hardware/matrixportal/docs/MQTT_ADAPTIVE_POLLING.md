# Adaptive MatrixPortal MQTT polling

The board uses a single MQTT connection. The LED admin **MatrixPortal & MQTT
timing** card edits the existing versioned `display` configuration:

- `mqtt_adaptive_enabled` (default `true`)
- `mqtt_idle_poll_seconds` (default `5`)
- `mqtt_live_poll_seconds` (default `1.5`)

Allowed intervals: 1.5, 2, 3, 5, 10, 15, or 30 seconds. If adaptive
polling is disabled, the idle interval applies in all states.

Any fresh MQTT football snapshot with `status="IN"` switches to the live
interval. Other teams remain independently tracked, so a `POST` from one
match does not revert the rate while another match is live. A missing
`POST` eventually reverts to idle because stale `IN` snapshots do
not count as live (10 minutes for TeamTracker; 4 hours for GoalAPI).
PRE, POST, BYE and absent snapshots all use the idle interval.

The publisher already sends `display` in `/api/screens`. The board
applies new values on its next successful HTTP feed fetch, without a reboot
or new MQTT connection. Invalid/incomplete payloads leave the prior
settings untouched; older firmware ignores the new fields.

MQTT connection keepalive remains 180 seconds and socket timeout 10 ms.
B8 presentation, bit depth, clocking and electrical HUB75 scan are unchanged.
Slower idle polling can delay timers, reminders and the first live score by
up to the idle interval; events can be received in batches.

Every 60 seconds the device emits `MQTT POLL STATS` with effective interval,
poll count, maximum service duration, message count and connect outcomes.
Policy transitions emit `MQTT POLL POLICY` once, not a per-poll log.

## Controlled physical test

1. Confirm B8 and RGB bit depth 2 are unchanged. With MQTT disabled, record
   a long static and animated baseline.
2. Re-enable MQTT, set both intervals to 1.5 seconds (control). Record
   flashes and compare serial aggregate metrics.
3. Enable adaptive polling (idle 5 s; live 1.5 s). Check PRE, IN and POST,
   including two simultaneous matches. Record when any flashes occur.
4. Check stale match expiry without POST, while leaving display and radio
   hardware unchanged.
5. Compare constant 5 s versus adaptive under comparable traffic, keeping
   the test windows and displayed scenes as similar as practical.

Reducing visible flashes is not proof of causal MQTT/HUB75 timing
interference. Python scheduling cannot guarantee that native Wi-Fi or DMA
activity avoids Protomatter scan operations. Inspect electrical waveforms
if flashes remain.
