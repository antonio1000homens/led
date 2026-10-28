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

Every accepted, newer snapshot immediately queues that club's match screen for
presentation. Its palette-indexed football enters from the right, settles at
the left edge, and stays there beside the match information for the 20-second
presentation. The same cached bitmap and display group are reused; the slide
is paced by the MatrixPortal refresh loop. After the prompt presentation,
football screens remain in the ordinary rotation as a fallback. A flash
reminder keeps priority; football updates wait behind it. Pending updates are
coalesced to one item per club so bursts cannot build an unbounded queue.
Duplicate or out-of-order snapshots are rejected before they can request a
slide. The first valid retained snapshot after boot hydrates that team and
requests one presentation. Set `MQTT_FOOTBALL_ENABLED = False` in board-local
`settings_local.py` to hide both football screens; the MQTT connection and its
other subscriptions continue to work.

The display uses `display_fixture` when supplied. For PRE fixtures without it,
the board builds the home-versus-away order from team names and the Team
Tracker home/away fields. PRE shows only the fixture and `KO: DAY DD MON HH:MM`
in Europe/London local time, including automatic GMT/BST conversion. Invalid
or missing kick-off data shows `KO: TBC`. Long lines are clipped to the area
beside the ball. No status, competition, countdown or score is shown for PRE.

IN and POST screens show normalized home/away scores when both are present.
BYE, NOT_FOUND, UNKNOWN, and UNAVAILABLE each have a distinct safe label. A
live snapshot whose `source_updated_at` is missing or more than ten minutes
old is shown as UNAVAILABLE and its score and clock are hidden.

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

The board checks source timestamps and formats kick-off locally; it does not
poll Home Assistant or make additional network requests for a countdown.
