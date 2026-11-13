# Football screens over MQTT

The board subscribes to non-retained Home Assistant Team Tracker snapshots at

- `led/football/sporting_cp`
- `led/football/millwall`
- `led/football/portugal`
- `led/football/england`

The producer contract, field meanings, and upstream freshness behavior are
documented in the [Home Assistant football LED contract](https://github.com/antonio1000homens/homeassistant/blob/master/docs/football-led-mqtt.md).
The board accepts schema version 1 snapshots from either Home Assistant
Team Tracker (`source: homeassistant`, `provider: teamtracker`) or Node-RED
Goal API (`source: nrwindsor`, `provider: goalapi`). Both producers publish
tracked clubs to the same club topic. The topic's final segment must match
`team_key`. `fixture_key=<team_key>|<UTC match date>|<normalized opponent>`
is diagnostic metadata. The board keeps one current match session per team and
reconciles provider updates by that team; fixture keys and provider match IDs
are not cross-provider join requirements. Kick-off/date, opponent, and source
time identify session rollovers and reject delayed updates from an older match,
including separate same-day fixtures. Ambiguous session changes fail closed.
MQTT does not replay snapshots on boot or reconnect; malformed or older events
leave the current state untouched.

## Goal API to Node-RED MQTT

The checked-in Node-RED function maps a Goal API event to each followed team in
the match. It publishes `led/football/<team_key>` and a shared
`fixture_key=<team_key>|<UTC match date>|<normalized opponent>`, while retaining Goal API's fixture
ID in `match_id`/`provider_match_id`. It preserves the webhook event `id`,
`event`, `createdAt`, `previousScore`, and processing time separately. This
keeps Goal API retries idempotent while matching Team Tracker snapshots on the
same topic. If both teams are followed, Node-RED emits one snapshot per team.
Unknown teams or events without fixture ID/date are discarded.

The [Node-RED producer notes](https://github.com/antonio1000homens/nrwindsor/blob/main/docs/football-led-mqtt.md)
describe the payload, mapping and focused validation command. Goal API defines
`goal.scored` as a score increase and `score.changed` as a correction; the
[official webhook reference](https://goal-api.com/documentation) lists both.

## Screen behavior

New fixtures, status changes, and score changes can request a football prompt.
Duplicate payloads and clock-only refreshes update state without requesting a
new prompt. A fresh `IN` match takes over the board and stays visible until its
status changes or its source snapshot becomes stale. MQTT clock and score
updates refresh the existing scene without restarting its animation phase.
When the same team match session is already visible, score and clock changes update that
scene directly. Deferred updates for the same team are coalesced. A transition
to POST starts a 20-second full-time card. POST is an event-only presentation:
once accepted and queued, the board does not keep the final in its per-team
state or recurring rotation. `post_expires_at` prevents an already expired
event from being shown.
Stale IN snapshots cancel the live presentation and resume the normal rotation.
PRE
fixtures supplied by the calendar continue to appear in the ordinary screen
rotation and animate
the 16×16 football with visible rotation from the right to the left over 3.2
seconds. The complete fixture and local kickoff time move with the ball. The
fixture is taller and uses more of the available width; the teams and `VS`
remain on one line, with only one space after `VS`. The ball freezes at x=2
when the scene arrives. If another PRE fixture immediately follows, the
incoming scene pushes the complete outgoing fixture/ball/countdown off the
left, with no blank interstitial frame. IN and POST screens appear in their
settled position immediately and do not slide or roll. The ball stays at the
left; both opponent names appear together in large type beside it, with the
live match clock (IN) or `FULL TIME` (POST) at the top right and the live or
final score at the bottom right. Both names use the same sweeping colour
gradient as the Today screen. The tracked team is not repeated as a screen
title. Live clocks and scores update when fresh snapshots arrive, including
when the providers use different fixture IDs or opponent slugs. A Goal API
`goal.scored` event applies its absolute score and flashes it once. A lower
Team Tracker snapshot cannot roll that score back after 120 seconds or at any
later point; the board continues to merge the newer clock. A matching score
confirms the Goal API score, while a newer Team Tracker score increase can
represent the next goal and is accepted. Goal API `score.changed` applies an
ordered correction without a goal flash, including legitimate decreases;
late or duplicate Goal API events cannot undo a newer accepted score. The
accepted score source and reconciliation decision are included in serial
diagnostics. Team Tracker-only score increases retain the existing single-point
highlight heuristic. POST never replays a goal highlight. Prompts
deferred behind a flash reminder are shown in arrival order after the flash
finishes. The already connected MQTT client continues polling
during active animations every 1.5 seconds with a 10 ms socket timeout.
Connection handshakes normally wait for an idle window. If MQTT stays
disconnected for 30 seconds, the firmware permits a reconnect attempt during
an animation so a continuous live football presentation cannot suppress
recovery indefinitely. If the outage reaches 120 seconds, cached `IN`
snapshots and queued live prompts are discarded and the board returns to its
normal rotation; queued `POST` results are kept. A successful reconnect resets
the outage timers, and newly received live snapshots can enter rotation again.
Non-football rotation rebuilds continue to wait for an idle window. Home
Assistant republishes POST during the finish-day window; each
accepted publication is a new one-shot presentation. If a flash reminder
delays a POST card, the firmware keeps at most the newest queued snapshot for
that team and match, and drops it if `post_expires_at` has passed. MQTT messages
are non-retained, so reconnect recovery depends on Home Assistant publishing
the current snapshot.
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
physical board soak test. Fresh IN snapshots are recurring screens in the
ordinary rotation; new fixtures, status changes, and score changes can also
request a one-shot prompt. A flash reminder keeps priority; football updates
received during it are queued and shown afterward. Pending POSTs are deduplicated
per team/match and expire locally. POST snapshots are not kept in per-team
state after acceptance and never enter the normal rotation. Live IN state remains
available for score/clock refresh and stale-live handling. Since messages are
non-retained, reconnect recovery depends on the publisher sending a fresh
snapshot after the board reconnects. Set `MQTT_FOOTBALL_ENABLED = False` in board-local
`settings_local.py` to hide both football screens; the MQTT connection and its
other subscriptions continue to work.

The display uses `display_fixture` when supplied. For PRE fixtures without it,
the board builds the home-versus-away order from team names and the Team
Tracker home/away fields. PRE shows the fixture and `DAY DD MON HH:MM` (without `KO:`) on the left,
in Europe/London local time, including automatic GMT/BST conversion. Invalid
or missing kickoff shows `TIME TBC`. After the ball stops, a right-aligned
`KICK-OFF` heading appears beside the local kickoff time and the compact
remaining countdown appears below.
The `VS` separator has a tighter gap after the left team, and the right team
starts after one space following `VS`.
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

IN and POST screens use the same fixed ball, one-line home-versus-away fixture
with the Today-style colour gradient, and score layout; POST replaces the clock
with `FULL TIME`, positioned 2 pixels lower and farther right. Longer fixtures
are horizontally condensed to fit the left column without overlapping the clock
or score. Scores retain home/away ordering.
BYE, NOT_FOUND, UNKNOWN, and UNAVAILABLE each have a distinct safe label. A
live snapshot whose `source_updated_at` is missing or more than ten minutes
old is shown as UNAVAILABLE and its score and clock are hidden.

Goal API score events are deduplicated by event ID and ordered by original
event time. The latest accepted Goal API score remains protected for the active
match session until a later Goal API event explicitly changes it or a newer
Team Tracker score confirms or advances it. There is no time-based score
rollback. Score provenance is tracked separately from the latest clock and
freshness timestamps. Team Tracker-only feeds use a conservative same-session,
newer-source-time, single-point-increase highlight heuristic because they do
not carry an explicit goal event type. Team Tracker live data is stale after
ten minutes; Goal API live data is stale after four hours. A session rollover
clears the previous match's score protection and event IDs.

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
and the publisher requests the next fixture at the first run at or after
kickoff, without waiting for the normal polling interval. If that request
fails, expired fixtures remain hidden and retries follow the normal interval.
The publisher and board polling schedules can delay the visible rollover;
the calendar kickoff, rather than live match status, determines it. Last-good
fetches are kept and marked stale after failures. Public Google Calendar ICS caching upstream
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
