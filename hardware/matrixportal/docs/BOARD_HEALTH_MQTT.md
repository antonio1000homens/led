# MatrixPortal board health MQTT contract

The display loop publishes a retained QoS 0 JSON snapshot to
`led/board/health`. It keeps the older retained `led/board/screen` topic
available for existing consumers. Home Assistant subscribes to the health
topic and exports metrics from the original board report timestamp.

The payload uses `schema_version: 1`. Sequence increases within a random boot
session. `board_id` is stable across restarts; `session_id` changes at boot.
Uptime fields use seconds since boot. Epoch fields are Unix seconds and remain
null until the board clock is synchronized. A retained replay must not be
treated as a new report; consumers compare `reported_at_epoch` and session /
sequence values, rather than MQTT receipt time.

Each JSON object is bounded and contains:

- Board, firmware revision, session, sequence, report epoch, uptime and clock
  synchronization state.
- Current attempted screen ID/kind/source and stage, with stage start uptime.
- Last completed screen ID/kind/source, screen start and last-render uptime,
  expected duration, rotation cycle, brightness and root-group state.
- Free heap and observed low-water heap.
- Aggregate fetch attempt/success uptimes, duration and failure count, plus a
  bounded error class. Exception messages and screen content are excluded.
- Up to eight per-source stale flags derived from the received screen payload.

Stage checkpoints are published when the attempt context changes before
fetch, scene preparation or render work. Completion heartbeats are generated
after display-loop work returns and are due every 30 seconds. MQTT disconnection
keeps only the newest pending snapshot; it does not stop rendering. Payloads
are compact (below 2 KiB in unit validation), and no per-frame publish occurs.

The screen ID and source are retained as Home Assistant attributes. The custom
Prometheus adapter maps IDs, kinds, sources and stages through fixed allowlists
before using them as labels. Unknown values map to `unknown` to keep
cardinality bounded.

Firmware tests cover payload size, heartbeat cadence, clock synchronization,
attempt versus completion attribution, bounded feed summaries, and newest-only
pending MQTT publication. A publish/serial check does not prove the physical
panel pixels are lit.
