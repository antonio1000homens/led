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
  HTTP poll. It avoids its five most recently completed items where possible.
  Exhausted/offline pools remain usable; repeats are preferable to a blank board.
- Completing or manually advancing a joke/fact marks that exact content version
  for refresh. Pending acknowledgements are sent only in a static maintenance
  window. Failed acknowledgements retry later, with renewed URLs on API polls.
- The acknowledgement is an expiring S3 write-only capability for a fixed-size
  marker, not an admin credential. The publisher reads markers on its scheduled
  run and replenishes consumed entries, retaining cached content on failure.
  Replayed markers cannot consume different/newer content. Markers expire after
  one day. Public screen payload readers can also acknowledge that content;
  this is not proof of a particular device's identity. Provider work is bounded
  by scheduled runs and a minimum 60-second retry interval.
- The browser simulator selects from the same pools but deliberately does not
  acknowledge consumption: previews must not consume production board content.

## Rotation and blocking work

Every enabled, available screen participates each cycle. Stored
`display_every_cycles` values are discarded on migration; new PATCH requests
using that retired field are rejected. Static-page positions are randomized
once per cycle while normal-screen ordering and train/departures adjacency are
preserved. An API poll retains the current selected text, phase and cycle order;
new screens join next cycle. The Weather screens are one contiguous normal block
in the order Sunrise/Sunset, Next 24 hours, then seven-day overview (omitting
disabled or unavailable pages); static pages cannot be inserted between them.

Explicit GC, screen fetching, content acknowledgements and detached Todoist
scene construction run only with a static screen already visible. A due refresh
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

Before live commissioning, validate the CloudFormation acknowledgement
permissions/lifecycle and deploy backend/admin before firmware. Stage firmware,
verify board identity and writable filesystem, upload non-code files first and
code.py last with SHA-256 readback. If paused at the serial REPL, explicitly
resume and verify actual startup/FETCH output; HTTP reachability alone does not
prove the display is running. Enable Today in Static feeds after deployment.

Physical acceptance still requires at least five full rotations, including a
due fetch, task change, multi-page fact and reminder interruption. Check that
each page retains its reading time, consumed content is replaced, train/queue/
CALLING AT motion does not freeze during maintenance, and no black/Loading
screen appears. This is separate from a multi-day uptime soak.
