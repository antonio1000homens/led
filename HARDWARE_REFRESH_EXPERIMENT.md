# MatrixPortal refresh experiment — issue #70

This branch is intended to be copied directly to the physical MatrixPortal S3.

## Current decision

Mode A is retired as a production candidate. Its targeted refresh deadline
discarded a large proportion of changed frames in the physical runs. Further
testing is limited to Mode B (immediate refresh with application pacing) and
Mode C (CircuitPython auto-refresh).

B8 remains the production baseline because it combines the strongest tested
manual-refresh reliability with the lower 8-update/s cadence.

The merged source retains a focused post-#72 **B12** experiment. B12 keeps Mode B's
immediate refresh strategy but raises the application animation cadence to
12 updates/s while deliberately keeping the Todoist marquee speed at 8 px/s.
This isolates update smoothness from text travel speed.

The retained Todoist scene is identical across the primary test modes. Only the presentation strategy and animation cadence change.

## What the local board agent needs to do

For each run:

1. Edit **one line** in `firmware/matrix_config.py`:

   ```python
   MATRIX_EXPERIMENT_PRESET = "A7"
   ```

2. Upload/synchronise this branch with `bash scripts/install-firmware.sh /Volumes/CIRCUITPY`.
3. Allow the board to boot, fetch the live payload, and enter the Todoist screen.
4. Observe at least 30 seconds and preferably multiple complete six-task page cycles.
5. Capture the serial lines beginning with:
   - `MATRIX PRESENTATION`
   - `MATRIX STATS`
   - `FRAME PACE`
   - `FETCH START` / `FETCH OK`
   - any `DISPLAY REFRESH DEADLINE MISSED`
6. Record direct visual observations:
   - horizontal flashing
   - tearing / partial rows
   - title-scroll smoothness
   - skipped-pixel jumps
   - page-slide smoothness
   - readability
7. Reboot/reset the board between presets so counters start cleanly.
8. Post the results table to issue #70.

## Presets

The historical comparison presets remain available, plus the focused B12 follow-up:

| Preset | Presentation mode | Animation / target FPS | Todoist marquee |
| --- | --- | ---: | ---: |
| A7 | current `refresh(target_frames_per_second=N)` | 7 | 7 px/s |
| A8 | current `refresh(target_frames_per_second=N)` | 8 | 8 px/s |
| A10 | current `refresh(target_frames_per_second=N)` | 10 | 10 px/s |
| B7 | immediate `refresh(None)` + app pacing | 7 | 7 px/s |
| B8 | immediate `refresh(None)` + app pacing | 8 | 8 px/s |
| B10 | immediate `refresh(None)` + app pacing | 10 | 10 px/s |
| **B12** | immediate `refresh(None)` + app pacing | **12** | **8 px/s** |
| C7 | CircuitPython `auto_refresh=True` | 7 update ticks/s | 7 px/s |
| C8 | CircuitPython `auto_refresh=True` | 8 update ticks/s | 8 px/s |
| C10 | CircuitPython `auto_refresh=True` | 10 update ticks/s | 10 px/s |

The A7/A8/A10 presets remain in the code only as historical controls and are
not part of the remaining test plan.

For B and C presets, the number is the **application animation-update cadence**.
It is not the physical HUB75 scan rate.

B12 intentionally breaks the older "FPS equals marquee speed" pattern: it is
**12 animation updates/s with an 8 px/s Todoist marquee**. This lets the hardware
test answer whether more frequent coordinate updates improve smoothness without
making the text move faster.

For C presets, CircuitPython owns framebuffer refresh timing.

## What each mode does

### A — current control

- `FramebufferDisplay(auto_refresh=False)`
- changed scenes call `refresh(target_frames_per_second=N)`
- current relative outer sleep is retained
- late refresh calls may return `False`

### B — immediate manual refresh

- `FramebufferDisplay(auto_refresh=False)`
- changed scenes call `refresh(target_frames_per_second=None)`
- application uses an absolute animation deadline
- a long fetch/transition rebases instead of spinning through stale animation ticks

### C — CircuitPython auto-refresh

- `FramebufferDisplay(auto_refresh=True)`
- normal animation does **not** call `refresh()`
- application only mutates persistent group coordinates/state
- CircuitPython controls framebuffer presentation

## Serial metrics

Example startup:

```text
MATRIX PRESENTATION preset=B8 mode=immediate target_fps=8 marquee_px_s=8.0 auto_refresh=False
```

Manual modes periodically emit:

```text
MATRIX STATS mode=immediate target_fps=8 elapsed=... changes=... refresh_attempts=... refresh_successes=... refresh_failures=... presented_fps=... interval_min=... interval_max=... interval_avg=... heap_start=... heap_end=...
```

All Todoist runs periodically emit:

```text
FRAME PACE mode=immediate target_fps=8 elapsed=... animation_ticks=... tick_fps=... late_frames=... max_late_streak=...
```

In auto-refresh mode, `refresh_attempts`, `refresh_successes`, and `presented_fps` are intentionally not treated as observable physical-refresh metrics. Use `FRAME PACE`, heap data, and direct visual observation.

## Suggested result table

| Preset | Visual flashing | Tearing | Marquee | Page slide | Refresh failures | Late frames | Max late streak | Heap drift | Notes |
| --- | --- | --- | --- | --- | ---: | ---: | ---: | --- | --- |
| A7 | | | | | | | | | |
| A8 | | | | | | | | | |
| A10 | | | | | | | | | |
| B7 | | | | | | | | | |
| B8 | | | | | | | | | |
| B10 | | | | | | | | | |
| **B12 (12 updates/s, 8 px/s)** | | | | | | | | | |
| C7 | | | | | n/a | | | | |
| C8 | | | | | n/a | | | | |
| C10 | | | | | n/a | | | | |

### Current serial evidence

| Preset | Window | Refresh result | Application pacing | Network / reset |
| --- | ---: | --- | --- | --- |
| B8 | 60.9 s | 409/409 successful, 0 failures | 7.43 ticks/s; 4 late, max streak 3 | fetches succeeded; no reset observed |
| C8 | 20.1 s | n/a; auto-refresh owns presentation | 7.61 ticks/s; 10 late, max streak 2 | fetch succeeded; reload occurred after capture |
| B10 | 102.4 s | 706/706 successful, 0 failures | 10.44 ticks/s; 5 late, max streak 2 | fetches succeeded; no reset observed |
| C10 | 20.1 s | n/a; auto-refresh owns presentation | 10.06 ticks/s; 116 late, max streak 4 | fetch succeeded; reload occurred after capture |

These serial results do not establish flashing, tearing, or visual smoothness.

## Focused B12 check

Use this branch only after the #72 layout/timing changes have been loaded on the
physical board.

Compare B12 directly against the B8 production baseline using the same payload.
Do not change marquee speed between those two runs.

Record:

- horizontal flashing / tearing;
- Todoist marquee smoothness;
- Todoist page-slide smoothness;
- departures calling-at smoothness;
- visible pixel-step/jump behaviour;
- achieved animation tick rate;
- late frames and maximum late streak;
- refresh attempts/successes/failures;
- one live fetch during movement;
- DOWN/UP responsiveness.

If B12 is not visibly smoother than B8, or produces materially more lateness,
keep B8. Do not increase cadence further merely because the board can execute
more ticks.

If B12 is clearly smoother and remains stable, record that evidence on #70
before changing the production preset.

### B12 serial result

The connected-board run after PR #73 booted, fetched the live two-screen
payload, and completed all measured immediate refreshes successfully. At the
12-update/s cadence it reached 11.31 animation ticks/s in the first 20.1 s,
with 12 late frames and a maximum late streak of 3. The 40.2 s summary still
showed 135/135 successful refreshes and no refresh failures. No direct visual
observation was available, so B8 remains the production profile.

## Stress check for the best candidate

After the nine short comparisons, run the best candidate for several minutes and verify:

- six Todoist tasks / page transition
- several long titles
- live network fetch during movement
- DOWN manual screen change
- UP diagnostic mode and return
- no reset/reconnect failure
- no progressive heap loss
- root group remains stable during normal Todoist animation

Do not change `MATRIX_BIT_DEPTH` during this experiment.
