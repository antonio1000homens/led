# Rail departures heap and prebuild experiments

Issue #241 starts with low frequency scene-build/first-refresh measurements,
board-local post-build collection, and ahead-of-train scene preparation. Both
new behaviors remain opt-in/default-off until actual board measurements show
that the retained scene fits safely alongside the train renderer.

## A/B setting

In the ignored board-local `settings_local.py`, set
`MATRIX_RAIL_POST_BUILD_GC_EXPERIMENT = True` for the post-build collection
run. Remove the setting or set it to `False` for the control run. The setting
does not change rotation, scene layout, row timing, or the steam-train slot.
It collects only after `_rail_scenes` owns all constructed display groups and
before the first rail refresh. The display root is not changed during build.

Capture serial output from one cold render and repeated warm cycles for each
payload size (4–5 services and the configured maximum). The relevant records
are `RAIL BUILD START/OK`, `RAIL POST BUILD GC`, `RAIL FIRST REFRESH`,
`HEAP TRACE`, `RAIL GC START/END`, `FRAME PACE`, `MATRIX STATS`, and
`SCREEN END`. Compare paired runs with the same payload, settings and board
uptime conditions.

| Run | Services | Build heap drop | GC reclaimed | Retained scene cost | Build to first present | Min free | GC time | Frame gaps >200 ms | Resets/errors |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Control, cold | | | n/a | n/a | | | n/a | | |
| Post-build GC, cold | | | | | | | | | |
| Control, warm | | | n/a | n/a | | | n/a | | |
| Post-build GC, warm | | | | | | | | | |

`heap_drop` is free bytes before build minus free bytes after build.
`reclaimed_bytes` is free bytes gained by the explicit collection.
`retained_heap_drop` is free bytes before build minus free bytes after that
collection. These are CircuitPython board measurements; host tests do not
provide representative heap numbers.

## Ahead-of-train scene preparation

Set `MATRIX_RAIL_PREBUILD_EXPERIMENT = True` in the ignored board-local
`settings_local.py` to enable preparation. The firmware searches the existing
rotation for the future adjacent `steam_train_intro` → `rail_combined` pair
during an already scheduled static maintenance window. It does not add time to
the train or put work between the train and departures. Preparation is skipped
for stale/empty payloads and unless free heap exceeds the configured estimated
scene cost plus the reserve (`MATRIX_RAIL_PREBUILD_MAX_SCENE_BYTES` and
`MATRIX_RAIL_PREBUILD_MIN_FREE_BYTES`). These are safety estimates, not measured
proof; keep the experiment off until low-water measurements support values for
the board and payload.

The prepared scene identity includes service data, title/stale/weather data,
preprocessed calling presentation, phase timings, scroll settings, row-scroll
mode, and train pause. A mismatch invalidates the hidden scene and uses the
existing on-demand path. Logs distinguish build duration/heap from
`scene_ready_to_present_ms`; a prepared scene is measured from the transition,
not from the earlier maintenance slot. `RAIL PREBUILD OK/SKIP/REUSE` records
explain the path selected.

| Run | Services | Train + prepared scene min free | Retained scene cost | Prebuild duration | Transition to present | Frame gaps >200 ms | Resets/errors |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Control, cold | | n/a | n/a | n/a | | | |
| Prebuild, cold | | | | | | | |
| Control, warm | | n/a | n/a | n/a | | | |
| Prebuild, warm | | | | | | | |

## Rail collection safety

The planned rail collection window now requires the calling marquee to be in
its end pause and the lower departure rows to be outside their slide/reset
movement. The clock/weather header currently switches while stationary. An
emergency low-heap collection remains available and its log marks
`heap_pressure_during_motion` when the planned safe window is unavailable.
Do not enable this experiment as the production default until repeated
physical runs show useful reclaimed memory without visible pauses or resets.

## Scope still requiring board evidence

No board measurements are checked in by this source change. Static-label
alternatives, row recycling, a complete rail-cycle summary, and all physical
acceptance measurements remain open; none should be claimed as accepted based
on host tests or simulated heap data.
