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


## Backend-sourced PRE football fixtures (#275)

The publisher can read upcoming Sporting CP and Millwall FC fixtures from Google Calendar and insert one football_score / PRE screen per club into the normal public GET /api/screens payload. This is the independent football_fixtures feed, not the personal Todoist calendar feed.

### Private Google Calendar configuration

Create or select a dedicated calendar containing fixtures. Grant the OAuth client the Google Calendar events read-only scope (https://www.googleapis.com/auth/calendar.events.readonly), and authorize it to read the source calendars. Store the OAuth client ID, client secret, refresh token, and team calendar IDs in one encrypted SSM SecureString at /led/football/calendar. Its JSON shape is:

    {
      "client_id": "REDACTED",
      "client_secret": "REDACTED",
      "refresh_token": "REDACTED",
      "calendars": {
        "sporting_cp": ["sporting-fixtures@group.calendar.google.com"],
        "millwall": ["millwall-fixtures@group.calendar.google.com"]
      },
      "aliases": { "sporting_cp": ["Sporting"], "millwall": ["Millwall"] }
    }

The aliases map is optional; built-in aliases cover Sporting CP, Sporting Clube de Portugal, Millwall, and Millwall FC. A fixture can be matched by an anchored summary with a team on either side of v / vs / versus, or an away form such as Sporting CP @ Porto. Alternatively, set Google event extendedProperties.private.led_team_key to sporting_cp or millwall, and extendedProperties.private.led_opponent to the opponent name. Optional led_home_away accepts home, away or unknown. Arbitrary personal events are never parsed as fixtures.

All-day, floating-time, cancelled, invalid, past, and unrelated events are excluded. The backend queries a bounded future window and publishes only the next valid fixture per club. The public payload contains the sanitized team name, opponent, fixture display title, home/away, a Europe/London ISO kickoff with BST/GMT offset, and a non-reversible hash of calendar ID plus Google event ID. No raw description, summary, guests, location, OAuth data, or calendar ID is cached or published. Rescheduling retains match_id and updates kickoff. Each HTTP poll does not cause another Google request: the default TTL is 900 seconds.

### Rollout and rollback

Deploy the Lambda/provider and restricted publisher IAM permission first. Set LED_FOOTBALL_FIXTURE_SOURCE=google_calendar, LED_FOOTBALL_FIXTURE_PARAMETER_NAME=/led/football/calendar, LED_FOOTBALL_FIXTURE_CACHE_SECONDS=900, LED_FOOTBALL_FIXTURE_DURATION_SECONDS=20, and LED_FOOTBALL_FIXTURE_LOOKAHEAD_DAYS=45 as non-secret repository variables. The default source is off. After ensuring the SSM secret is readable, enable the football_fixtures feed in admin or the authenticated control API. On Google failure the last good state remains cached and marked stale; expired fixtures are never emitted.

Firmware integration with #272 and #273 is deliberately separate: the board must merge HTTP PRE with fresh MQTT IN per club, display PRE kickoff in UK local time, and avoid restarting the ball slide on unchanged HTTP polls. Until that firmware is deployed and verified, retain the HA PRE publisher. Only afterward deploy the HA #46/#48 IN-only producer plus one-time terminal clear. For rollback, restore the previous HA PRE producer until the dual-source firmware is operational. The backend alone cannot stop non-live MQTT traffic.

### HTTP PRE contract

    {
      "id": "football-sporting_cp",
      "kind": "football_score",
      "team_key": "sporting_cp",
      "team_name": "Sporting CP",
      "title": "Sporting CP",
      "status": "PRE",
      "opponent_long_name": "Benfica",
      "display_fixture": "Sporting CP vs Benfica",
      "home_away": "home",
      "kickoff": "2026-10-31T15:00:00+00:00",
      "match_id": "stable-calendar-hash",
      "source": "google_calendar",
      "stale": false,
      "duration_seconds": 20
    }

No score, clock, goal event, or changing countdown is embedded in the cached PRE contract.
