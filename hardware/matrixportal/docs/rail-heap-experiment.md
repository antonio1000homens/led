# Rail departures heap experiment

Issue #241 starts with two controls: low frequency scene-build/first-refresh
measurements and a board-local, opt-in collection after the persistent rail
scene has been built. Both remain opt-in/default-off for new GC behavior.

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

## Rail collection safety

The planned rail collection window now requires the calling marquee to be in
its end pause and the lower departure rows to be outside their slide/reset
movement. The clock/weather header currently switches while stationary. An
emergency low-heap collection remains available and its log marks
`heap_pressure_during_motion` when the planned safe window is unavailable.
Do not enable this experiment as the production default until repeated
physical runs show useful reclaimed memory without visible pauses or resets.

## Scope still requiring board evidence

No board measurements are checked in by this source change. Ahead-of-train
scene preparation, static-label alternatives, row recycling, and a complete
rail-cycle summary remain separate experiments; none should be claimed as
accepted based on host tests or simulated heap data.
