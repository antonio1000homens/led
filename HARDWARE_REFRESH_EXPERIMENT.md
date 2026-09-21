# MatrixPortal refresh experiment — issue #70

This branch is intended to be copied directly to the physical MatrixPortal S3.

The retained Todoist scene is identical across the primary test modes. Only the presentation strategy and animation cadence change.

## What the local board agent needs to do

For each run:

1. Edit **one line** in `matrix_config.py`:

   ```python
   MATRIX_EXPERIMENT_PRESET = "A7"
   ```

2. Upload/synchronise this branch to CIRCUITPY using the same process used for the current production board.
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

Run these nine presets:

| Preset | Presentation mode | Animation / target FPS | Todoist marquee |
| --- | --- | ---: | ---: |
| A7 | current `refresh(target_frames_per_second=N)` | 7 | 7 px/s |
| A8 | current `refresh(target_frames_per_second=N)` | 8 | 8 px/s |
| A10 | current `refresh(target_frames_per_second=N)` | 10 | 10 px/s |
| B7 | immediate `refresh(None)` + app pacing | 7 | 7 px/s |
| B8 | immediate `refresh(None)` + app pacing | 8 | 8 px/s |
| B10 | immediate `refresh(None)` + app pacing | 10 | 10 px/s |
| C7 | CircuitPython `auto_refresh=True` | 7 update ticks/s | 7 px/s |
| C8 | CircuitPython `auto_refresh=True` | 8 update ticks/s | 8 px/s |
| C10 | CircuitPython `auto_refresh=True` | 10 update ticks/s | 10 px/s |

For C presets, the number is the **application animation-update cadence**. CircuitPython owns framebuffer refresh timing.

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
| C7 | | | | | n/a | | | | |
| C8 | | | | | n/a | | | | |
| C10 | | | | | n/a | | | | |

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
