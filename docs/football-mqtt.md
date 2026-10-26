# Football screens over MQTT

The board subscribes to the retained Home Assistant Team Tracker snapshots at

- `led/football/sporting_cp`
- `led/football/millwall`

The producer contract, field meanings, and upstream freshness behavior are
documented in the [Home Assistant football LED contract](https://github.com/antonio1000homens/homeassistant/blob/master/docs/football-led-mqtt.md).
The board accepts schema version 1 snapshots with `source: homeassistant`,
`provider: teamtracker`, matching `team_key`, a supported lifecycle status, and
valid ISO-8601 timestamps. Each topic has independent state. A retained
snapshot is accepted at boot or reconnect; malformed and out-of-order
snapshots leave the last accepted screen untouched.

## Screen behavior

Football screens enter the same normal rotation as HTTP screens and
`led/screens/+` screens as soon as a valid snapshot for that club arrives.
Each screen lasts 20 seconds and is inserted into the existing mixed rotation;
it does not interrupt an active flash event. Set `MQTT_FOOTBALL_ENABLED = False`
in board-local `settings_local.py` to hide both football screens. The MQTT
connection and other subscriptions continue to work.

The display uses `display_fixture` when supplied, otherwise it builds the
fixture line from team and opponent names. PRE screens calculate their
countdown locally from the timezone-aware `kickoff`; after kickoff they show
“AWAITING LIVE UPDATE” until Team Tracker changes state. IN and POST screens
show normalized home/away scores when both are present. BYE, NOT_FOUND, UNKNOWN,
and UNAVAILABLE each have a distinct safe label. A live snapshot whose
`source_updated_at` is missing or more than ten minutes old is shown as
UNAVAILABLE and its score and clock are hidden.

Score changes are considered for a short goal highlight only when both
snapshots are IN for the same non-empty `match_id`, both prior and current
scores are numeric, `source_updated_at` advances, and exactly one side's score
increases by one while the other stays unchanged. Fixture changes, startup
score initialization, null scores, decreases, and multi-point corrections do
not trigger the highlight. The MQTT contract has no explicit goal event, so a
single-point upward correction is indistinguishable from a goal in the data;
the highlight is a conservative score-delta heuristic, not a verified goal
notification.

## Board settings

Defaults are set in `hardware/matrixportal/firmware/settings.py` and mirrored
in `settings_local.py.example`:

```python
MQTT_FOOTBALL_TOPIC = "led/football/+"
MQTT_FOOTBALL_ENABLED = True
```

The board checks the source timestamps locally; it does not poll Home Assistant
or make additional network requests for a countdown.
