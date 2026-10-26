# Static feeds and maintenance windows

The admin's **Static feeds** section groups Dad jokes, Random facts and Today.
Each has independent enable/duration controls. Today shows London time/date,
current temperature and current weather, using the existing shared weather
cache/poll interval even when forecast screens are disabled. It is distinct
from Weather's **Next 24 hours** forecast. Existing saved configurations gain
Today disabled, so adding this feature does not silently enable another feed.

## Content selection

- The backend maintains up to five jokes and five facts. It grows each pool
  gradually, downloading at most two new items per feed per publisher run.
- The board chooses locally once per slot, not once per animation frame or
  HTTP poll. Items may repeat; the pool refreshes on its configured TTL, and
  exhausted/offline pools remain usable instead of leaving a blank screen.
- An API poll retains the currently displayed static text until that slot ends.
  Provider work is bounded by scheduled runs, a maximum pool size of five,
  at most two additions per run, and a minimum 60-second retry interval.

## Rotation and blocking work

Every enabled, available screen participates each cycle. Stored
`display_every_cycles` values are discarded on migration; new PATCH requests
using that retired field are rejected. Static-page positions are randomized
once per cycle while normal-screen ordering and train/departures adjacency are
preserved. An API poll retains the current selected text, phase and cycle order;
new screens join next cycle. The Weather screens are one contiguous normal block
in the order Sunrise/Sunset, Next 24 hours, then seven-day overview (omitting
disabled or unavailable pages); static pages cannot be inserted between them.

Explicit GC, screen fetching and detached Todoist scene construction run only
with a static screen already visible. A due refresh
waits for the next block boundary and brings forward an unused static page, or
inserts a repeated static slot. When no static feed is available, a local
clock/date/current-weather card is used. The train/departures pair is never
split. Extra maintenance slots do not increment the cycle counter.

Reading/page timing is frozen during blocking work and resumes afterwards.
There is no Upcoming/Loading tasks transition. Preparation failure restores
the previous complete task cache, uses it when valid, otherwise displays Tasks
unavailable; another preparation attempt waits at least 30 seconds and a static
window. New maintenance/fetch deadlines use integer milliseconds.

Automatic GC remains enabled as an allocation safety net. This schedules
explicit collection; it cannot guarantee that allocation-triggered collection,
Wi-Fi firmware work or hardware stalls never occur during animations.

## Validation and commissioning

Run the complete unittest suite with `PYTHONPATH=shared:backend:firmware:hardware/matrixportal/firmware`.
`tests/test_static_feeds.py` covers pools/replenishment/replay/failure, shared
weather, schema migration, local random choice, atomic normal blocks, aged
integer timing, stable polls, response closing, browser parsing/selection,
static scene caching and detached/failed task preparation.

Before live commissioning, deploy backend/admin before firmware. Stage firmware,
verify board identity and writable filesystem, upload non-code files first and
code.py last with SHA-256 readback. If paused at the serial REPL, explicitly
resume and verify actual startup/FETCH output; HTTP reachability alone does not
prove the display is running. Enable Today in Static feeds after deployment.

Physical acceptance still requires at least five full rotations, including a
due fetch, task change, multi-page fact and reminder interruption. Check that
each page retains its reading time, static content can repeat, train/queue/
CALLING AT motion does not freeze during maintenance, and no black/Loading
screen appears. This is separate from a multi-day uptime soak.
