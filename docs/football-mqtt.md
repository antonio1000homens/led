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

A new accepted fixture is eligible for a prompt presentation. Every football
screen entry (including calendar-sourced PRE in the ordinary screen rotation)
animates the 16×16 football with visible rotation from the right to the left
over 3.2 seconds. The fixture and local kickoff time slide **with** the ball,
not after it. The ball freezes at x=2 when the scene arrives. If another
football fixture immediately follows, the incoming scene pushes the complete
outgoing fixture/ball/countdown off the left, with no blank interstitial frame.
Two persistent displayio scenes share **eight precomputed 16×16 indexed
sprite poses** (around 512 bytes of bitmap pixels before object overhead);
the renderer changes only TileGrid bitmap references and Group positions while
moving. Fixture text and label objects remain cached when only the clock
changes. This avoids allocating/drawing the sprite bitmap per animation frame.
Ordinary API polls and 1 Hz clock updates do not restart the entry.

### Garbage collection

The firmware's rail departures scene has a special GC-suppressed animation
window. On leaving rail, the existing runtime restores automatic GC. Football
does **not** disable automatic GC. After each football screen settles and has
shown its first countdown frame, a one-shot `gc.collect()` is scheduled no
earlier than 3.7 seconds into the scene, while it is stationary. Collection is
never scheduled during the rolling/pushing motion or the live goal highlight.
The collect operation explicitly restores **automatic GC enabled** on success
or failure. Its completion key is `(screen id, rotation cycle)`, so a 1 Hz
countdown update or HTTP feed refresh cannot cause repeated GC pauses. The
existing startup/maintenance/rail GC paths remain unchanged. When heap
diagnostics are enabled, `FOOTBALL GC settled` reports collector duration
and free heap before/after; track those alongside `FRAME PACE` during the
physical board soak test. After the prompt presentation,
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
Tracker home/away fields. PRE shows the fixture and `DAY DD MON HH:MM` (without `KO:`) on the left,
in Europe/London local time, including automatic GMT/BST conversion. Invalid
or missing kickoff shows `TIME TBC`. After the ball stops, `KICK-OFF IN` appears
beside the local kickoff time and the compact remaining countdown appears below.
The `VS` separator starts at character column 15 for the tracked football
teams, so short and multiword names line up consistently.
Its units depend on the **total time until kickoff**:

| Time remaining | Display |
| --- | --- |
| At least 24 hours | `2 DAYS` (or `1 DAY`), whole days only |
| Over 60 minutes, below 24 hours | `05H 14M 09S` |
| Over 60 seconds, up to 60 minutes | `14M 09S` |
| 1–60 seconds | `UNDER 1 MIN` |
| At or past kickoff | `DUE NOW` |
| No kickoff / clock unsynchronised | `TBC` |

Values are calculated locally from the absolute timestamp (not via MQTT or
an API request per second). The display refreshes only the changed glyphs.
Days count complete 24-hour periods, so 2 days 5 hours shows `2 DAYS`.
At exactly 24 hours it shows `1 DAY`, then switches to `23H 59M 59S` one
second later without restarting the scene.
Long names are clipped before the right column; no competition/status/score
lines are added to the PRE view.

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


## Backend-sourced PRE football fixtures (#275)

This is a dedicated public-ICS `football_fixtures` feed, separate from the
personal Todoist `calendar` agenda and from live MQTT score updates. Google Calendar
has accessible events for all four calendars; public iCalendar (.ics) downloads
are supported directly without OAuth or API keys. The backend fetches only
enabled clubs and publishes *sanitized* `football_score` / `PRE` screens.

### Calendar subscriptions and default status

| Team | Public calendar URL | Initial board state |
| --- | --- | --- |
| Sporting CP | https://calendar.google.com/calendar/ical/fd67v39hov7a8uplrk8djd818c%40group.calendar.google.com/public/basic.ics | Enabled |
| Millwall FC | https://calendar.google.com/calendar/ical/rajefpgnm1ue0j6eae1ob9us1s%40group.calendar.google.com/public/basic.ics | Enabled |
| Portugal | https://calendar.google.com/calendar/ical/c88a0605u3b1m04j217pnqfkfs%40group.calendar.google.com/public/basic.ics | Disabled (test) |
| England | https://calendar.google.com/calendar/ical/ulqvlgdfg9ag1kuv4vlvjd1tuc%40group.calendar.google.com/public/basic.ics | Disabled (test) |

These public IDs are known exclusively to the backend. The fourth and fifth
screens (Portugal and England) are *not fetched or published* by default;
later enable each with the corresponding team flag in the admin feed settings.
The firmware's HTTP PRE/MQTT IN merge must support those extra team keys
before enabling them for display. The original Google Calendar subscription
links are equivalent references to the above public iCal calendar IDs.
Google's iCal endpoint requires the source calendar's **public event
visibility**; a mere shared/embedded calendar link does not guarantee the
unauthenticated .ics feed can be downloaded. Confirm the Public address in
iCal format in Google Calendar's Integrate calendar settings if the provider
reports unavailable.

The backend source selector is `LED_FOOTBALL_FIXTURE_SOURCE=public_ical`
(default remains `off`). The existing authenticated `google_calendar` option
remains supported for non-public sources. For that option only, the publisher
reads OAuth credentials and team ID mappings from an encrypted SSM
`SecureString` at `/led/football/calendar`, using Google's events
read-only scope; do not configure OAuth for the new public iCal provider.

### Fixture title parsing and privacy

These calendars use a home-away dash separator (for example `Casa Pia - Sporting Portugal`,
`Millwall FC - Derby County`, `Portugal - Denmark`,
`Shakhtar Donetsk - Sporting Portugal [CL]`). The parser
accepts only an **anchored complete club alias** on one side of a dash, an en
dash, an em dash, `v`, `vs`, `versus` or `@`. Built-in
aliases include Sporting CP, Sporting Portugal, Sporting Clube de Portugal,
Millwall FC, Millwall, Portugal and England. Optional trailing competition
labels such as `[CL]` are stripped from the display opponent.
Unrelated personal appointments, all-day/unscheduled kickoffs, cancelled
events, invalid fixture titles and past matches are rejected.

The source queries a bounded 45-day future window (admin adjustable to 180),
handles recurrence exceptions, and selects each club's next scheduled valid
match. The source event UID is hashed with the calendar ID to produce a
stable public `match_id` across reschedules; the kickoff timestamp is updated
independently and converted to Europe/London (BST/GMT). Only the cleaned team,
opponent, display title, home/away, timezone-aware kickoff, opaque match ID,
source and stale status enter the S3 cached result or public screen JSON.
No calendar IDs, raw descriptions, attendees, locations or token material are
published. Cached matches stop displaying when their kickoff has passed,
even if the calendar is temporarily unreachable; last-good fetches are kept
and marked stale after failures. Public Google Calendar ICS caching upstream
may add some additional delay beyond our 900-second polling interval.

### Enablement and staged rollout

1. Deploy the backend PR with `LED_FOOTBALL_FIXTURE_SOURCE=public_ical`,
   `LED_FOOTBALL_FIXTURE_CACHE_SECONDS=900`,
   `LED_FOOTBALL_FIXTURE_DURATION_SECONDS=20` and
   `LED_FOOTBALL_FIXTURE_LOOKAHEAD_DAYS=45`.
2. Enable `football_fixtures.enabled` in the existing admin/control
   plane; per-team defaults are `sporting_cp_enabled=true`,
   `millwall_enabled=true`, `portugal_enabled=false`,
   `england_enabled=false`.
3. Confirm both football PRE screens in public `/api/screens`, with
   correct British local kickoff and no private event content.
4. Deploy firmware #272/#273 for HTTP PRE/MQTT IN precedence and the
   introduction ball slide. **Only then** switch Home Assistant #46/#48
   to IN-only MQTT updates plus a terminal clear. Roll back by restoring
   HA's old PRE publishing until the dual-source board is working.

The backend cannot by itself stop non-live MQTT. The feature is not live
until the runtime feed is enabled, and its original secure OAuth mode is
retained as a fallback.

### Public PRE example

    {
      "id": "football-sporting_cp",
      "kind": "football_score",
      "team_key": "sporting_cp",
      "team_name": "Sporting CP",
      "title": "Sporting CP",
      "status": "PRE",
      "opponent_long_name": "Casa Pia",
      "display_fixture": "Sporting CP vs Casa Pia",
      "home_away": "away",
      "kickoff": "2026-10-30T20:15:00+00:00",
      "match_id": "opaque-calendar-event-hash",
      "source": "public_ical",
      "stale": false,
      "duration_seconds": 20
    }

No score, live clock, goal event or changing countdown is embedded in PRE.
