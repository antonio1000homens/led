# MatrixPortal performance and refresh architecture

This document records the current MatrixPortal S3 rendering and animation
decisions for the four-panel 256×32 HUB75 display.

It consolidates the physical-board work from:

- #70 — framebuffer presentation strategy / refresh experiments;
- #91 — adaptive partial-scene animation cadence;
- #92 — dirty-region / native RGBMatrix partial-conversion investigation;
- #94 — follow-up experiment for selective 15–20 Hz short transitions.

The issue threads remain the evidence trail. This document is the durable
summary of what the repository should assume going forward.

## Current production baseline

The stable presentation foundation is:

- Adafruit MatrixPortal S3;
- four chained 64×32 HUB75 panels presented as one 256×32 framebuffer;
- `bit_depth=1`;
- `doublebuffer=True`;
- `FramebufferDisplay(auto_refresh=False)`;
- Mode B / immediate manual presentation;
- changed frames use `display.refresh(target_frames_per_second=None)`;
- application-owned scheduling;
- persistent `displayio` scene graphs for animated screens;
- B8/baseline remains the source default; the physical board is being tested
  with its board-local adaptive profile after correcting animation pacing.

The preset/application FPS number is **not** the HUB75 electrical scan rate.
The RGBMatrix/Protomatter driver continuously scans the complete panel chain at
a much higher rate. The application cadence only determines how often Python
calculates and presents a new visible state.

## Findings from #70: presentation strategy

Issue #70 compared several presentation strategies and application cadences.

The important outcome is that Mode B — immediate manual refresh with
application-owned pacing — is the reliable basis for further work.

The historical A modes used
`refresh(target_frames_per_second=N)`. They could discard changed frames when
the refresh deadline was missed and are retained only as historical controls.

Mode C used CircuitPython `auto_refresh=True`. It remained useful as an
experiment but did not replace Mode B.

B8 was retained as the production control because it combined reliable
presentation with conservative application workload. Higher B-mode cadences
showed the board could execute more updates, but execution alone did not prove
a visible benefit.

See #70 and `HARDWARE_REFRESH_EXPERIMENT.md` for the detailed historical test
procedure and raw observations.

## Findings from #91: persistent scenes and change-driven scheduling

Issue #91 separated animation speed from animation update cadence and removed
the assumption that every animated screen should run continuously at one
global rate.

The implementation established these rules:

1. Keep the scene graph alive. Todoist and departures reuse the same
   `displayio` groups/labels rather than rebuilding the whole frame for every
   animation step.
2. Mutate only the objects that move, such as a cached group `x`/`y`
   position or text field.
3. Present only when the resulting visible integer-pixel/text state changed.
4. Let settled/static content sleep until the earliest meaningful boundary:
   animation transition, header transition, screen rotation or network poll.
5. Rebase absolute deadlines when cadence changes or a blocking operation
   makes the loop late. Do not replay stale animation frames.
6. Keep a reproducible fixed-B8 scheduling control and an explicit adaptive
   experiment profile.

Matched physical runs demonstrated the workload benefit. On the available
Todoist payload:

| Profile | Animation ticks | Refresh result |
| --- | ---: | --- |
| Fixed B8 scheduling baseline | 1,147 | 355/355 successful |
| Adaptive/change-driven | 163 | 165/165 successful |

The adaptive path therefore removed most unnecessary Python/displayio update
work while retaining successful presentation and stable heap behaviour.

This was an architecture success, but #91 did **not** promote adaptive cadence
as the production default because the original acceptance criterion also
required clear visual superiority. Live departures repeatedly returned
`No Services`, so the calling-at path could not be visually accepted on
hardware during that experiment.

## Isolated steam-train motion test

### Long-uptime clock precision

The October 11 physical investigation found that the 3.45-day-old board's
`time.monotonic()` returned only four distinct timestamps in 400 samples
spaced roughly a millisecond apart. Its reported steps included 31.25 ms and
156.25 ms, while the largest consecutive integer-nanosecond sample interval
was 3.12 ms. The same coarse float clock had driven both motion and telemetry,
making apparent 8 Hz loop stability insufficient to establish even movement.
Saving board-local settings also auto-reloaded the application, changing the
animation's timing alignment; improvement after the radio experiment alone
therefore did not establish Wi-Fi as the cause.

Animation timing now uses `time.monotonic_ns()` converted to integer
milliseconds. Frame waits and measurements subtract integer timestamps before
converting the short difference to seconds. `ScreenRotation` accepts integer
millisecond timestamps in the firmware, retains integer anchors across
rotation, refresh and resume, and returns short phases in seconds to the
renderers. Long-uptime tests cover one-pixel train steps and pause/resume.
Integer frame deadlines include telemetry/bookkeeping overhead in the cadence
budget and rebase any overdue deadline rather than issuing catch-up bursts.
The display cadence, bit depth and panel geometry are unchanged by this fix.

On October 11 the user confirmed the telemetry-off train was smooth throughout
each crossing, then confirmed it remained smooth after software reload. The
measured reload preserved aged hardware uptime (299545338 ms before,
299549570 ms at startup afterward). Readback retained the same train-only
C8 configuration at 8 FPS / 8 pixels per second, bit depth 1 and 20 ms sleep
slices, with Wi-Fi on. The firmware hash matched the deployed integer-pacing
stage. These observations establish a smooth physical train baseline and one
measured reload check, not a multi-day soak or standard-screen acceptance.
The full test record and remaining train-only reliability checks are in
[issue #225](https://github.com/antonio1000homens/led/issues/225).

To distinguish pixel stepping from stalls elsewhere in the application, the
firmware has an opt-in `STEAM_TRAIN_TEST` mode for the physical board. Set it
to `True` in the ignored board-local `settings_local.py`; the mode then uses a
single local train screen that repeats after each full crossing and skips API,
MQTT, and button polling.
It leaves the presentation preset and bit depth untouched. Configure
`STEAM_TRAIN_TEST_SPEED` in pixels per second and
`STEAM_TRAIN_TEST_FPS` from 1 to 30 independently. The startup banner records
both values and the fixed presentation settings. `FRAME PACE` and
`MATRIX STATS` report timing gaps and train update/refresh costs every 20
seconds.

Begin at 8 pixels/second and 8 FPS, then compare 12/12 and (if timing remains
even) 24/24. Matching speed to cadence targets one-pixel steps. Keep the board
on each setting long enough to observe repeated 20-second telemetry windows.
Afterward set `STEAM_TRAIN_TEST` back to `False` and restart to restore normal
screen selection. Smooth timing data does not replace visual confirmation on
the physical panel.

To compare the instrumentation itself, set
`MATRIX_TELEMETRY_ENABLED = False` in board-local `settings_local.py` and
restart. This bypasses per-frame timing/counter collection and aggregate
serial summaries while keeping the same animation scheduler and presentation
mode. Judge that run visually; it intentionally provides no timing report.
The checked-in default remains enabled.

For an 8 Hz timer-wake experiment, set
`STEAM_TRAIN_TEST_SLEEP_SLICE_MS = 20` with telemetry enabled. The test loop
then breaks each frame's idle wait into short sleeps; compare its `sleep_max`,
`gap_over_200ms`, and visible motion against the default single-sleep path.
This option is isolated to train-test mode and defaults to zero.

To test whether Wi-Fi activity contributes to visible stalls, the isolated
train test also supports a one-shot radio-off window. Set
`STEAM_TRAIN_TEST_WIFI_OFF_AFTER_SECONDS` to a positive delay and
`STEAM_TRAIN_TEST_WIFI_OFF_DURATION_SECONDS` to the desired window. The radio
is re-enabled afterward and CircuitPython's native reconnection is allowed to
run without a blocking application-level connect call. Keep this disabled
(delay zero) outside a deliberate physical A/B test; Wi-Fi/Web Workflow is
unavailable while the radio is off.

## What "partial refresh" means in this project

There are several different layers that are easy to conflate.

### 1. Partial scene update

The application changes only the relevant persistent `displayio` objects.

Example: move one Todoist title group by one pixel rather than rebuilding all
labels and rows.

This is already implemented and should be preserved.

### 2. Dirty-region displayio composition

CircuitPython `FramebufferDisplay` asks the current `displayio` tree for
refresh areas and composites only those dirty rectangles into the RGB565
framebuffer.

This already happens inside CircuitPython.

### 3. RGBMatrix / Protomatter conversion

`FramebufferDisplay` also builds a dirty-row bitmap and passes it through the
framebuffer protocol. In the current CircuitPython RGBMatrix adapter that
bitmap is discarded before the normal RGBMatrix refresh path, which invokes
the Protomatter RGB565 conversion and buffer swap.

Therefore a smaller application/displayio dirty region does not mean that the
HUB75 hardware scans only that region. The complete matrix continues to be
physically scanned.

## Findings from #92: dirty-region benchmark

Issue #92 measured the current stack directly on the four-panel MatrixPortal
S3. The standalone benchmark used:

- 256×32 display;
- `bit_depth=1`;
- double buffering;
- `auto_refresh=False`;
- immediate manual refresh;
- no Wi-Fi, HTTP, MQTT, fonts or application workload;
- 12 warm-up iterations;
- 80 samples per scenario;
- three rounds with alternating scenario order.

Measured average refresh durations were:

| Dirty scope | Average refresh |
| --- | ---: |
| Full 256×32 | ~12.67 ms |
| 256×8 band | ~4.03 ms |
| 32×8 band | ~4.03 ms |
| 32×8 moved by 1 px | ~4.05 ms |

The full frame was roughly 3.1× slower than the partial scopes, saving about
8.6 ms when only a band/small persistent scene changed.

The 256×8 and 32×8 cases were effectively identical. That is consistent with
the lower-level path having a common row-oriented/full-width conversion cost
once those rows are dirty. The benchmark demonstrates the cost behaviour; the
CircuitPython source explains why a dirty-row-aware native optimisation might
be possible.

## Why native RGBMatrix partial conversion was rejected

The ~4 ms partial-scene presentation cost is small relative to the application
budgets:

| Application cadence | Frame budget | ~4 ms partial refresh |
| --- | ---: | ---: |
| 8 Hz | 125 ms | ~3.2% |
| 12 Hz | 83.3 ms | ~4.8% |
| 15 Hz | 66.7 ms | ~6.0% |
| 20 Hz | 50 ms | ~8.0% |

A custom CircuitPython/Protomatter fork could at best recover only part of that
remaining ~4 ms, while adding significant maintenance and hardware-regression
risk.

Issue #92 therefore concluded that native dirty-row/row-pair conversion is not
justified for the current display. The issue was closed after the production
firmware was restored and verified with successful refreshes and no serial
exception.

The optimisation priority remains:

1. avoid unnecessary application wake-ups;
2. avoid unnecessary scene mutations;
3. avoid duplicate presentations;
4. keep scenes persistent;
5. only then consider higher cadence where it produces a visible benefit.

## What #92 tells us about earlier slow renders

The dirty-region benchmark also helps interpret earlier first-render timings
that were hundreds of milliseconds or more.

A complete 256×32 framebuffer presentation is only about 12.7 ms in the
isolated benchmark. Therefore large first-render times are predominantly
Python/`displayio` scene construction, label/font/allocation work and other
application processing — not the HUB75 framebuffer swap itself.

That is another reason persistent scenes are important.

## Follow-up: #94 selective higher cadence

Issue #94 tests the next distinct question: whether short page/header
transitions look better at 15–20 Hz now that settled content no longer consumes
continuous animation work.

The experiment deliberately does **not** return to a global 15/20 Hz loop.

Planned comparison:

| Animation | Control / current | Candidate |
| --- | ---: | ---: |
| Todoist horizontal marquee | 8 Hz / 8 px/s | keep 8 Hz |
| Todoist page slide | 12 Hz | test 15 Hz, then 20 Hz |
| Clock/weather header slide | 12 Hz | test 15 Hz, then 20 Hz |
| Departures calling-at | 12 Hz while actually moving | keep 12 Hz initially |
| Settled/static content | boundary-driven | keep boundary-driven |

Higher cadence should be temporary and only active while the relevant
transition is moving. Integer-state suppression, persistent groups, absolute
deadline rebasing and earliest-boundary arbitration must remain in place.

See #94 for the implementation and physical acceptance plan.

## Design rules for future changes

When changing MatrixPortal rendering or timing, preserve these rules unless a
new measured experiment supersedes them:

- Do not equate application FPS with physical HUB75 refresh rate.
- Do not rebuild an entire animated screen when coordinate/text mutation of a
  persistent scene is sufficient.
- Do not call `refresh()` for unchanged integer-pixel state.
- Do not run a continuous animation loop while the scene is settled.
- Do not use higher cadence to compensate for a scheduler or blocking-I/O
  problem.
- Keep animation travel speed separate from update cadence.
- Rebase after stalls rather than replaying missed frames.
- Keep `bit_depth=1` unless colour requirements materially change.
- Keep double buffering enabled.
- Prefer physical-board measurements over assumptions about what a higher FPS
  should look like.
- Treat a custom CircuitPython/Protomatter build as a last resort, not a normal
  application optimisation.

## Evidence / references

- #70 — presentation mode and B8/B10/B12/C-mode hardware experiments.
- #91 — adaptive persistent-scene/change-driven scheduler and telemetry.
- #92 — physical dirty-region benchmark and decision not to fork
  CircuitPython/Protomatter.
- PR #93 — standalone dirty-region benchmark implementation.
- #94 — selective 15–20 Hz transition experiment.
- `HARDWARE_REFRESH_EXPERIMENT.md` — historical #70 experiment instructions.
- `hardware/matrixportal/partial_refresh_benchmark.py` — #92 benchmark source.
