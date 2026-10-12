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

To roll each saved capture into a comparable cycle table, run
`python3 scripts/summarize_rail_heap.py serial.log --label control` (replace
`control` with the A/B setting). It joins prebuild, build, GC, first-present,
frame-gap, and screen-end records. Missing fields are shown as `n/a`; do not
fill them with host-simulated heap values.

| Run | Services | Build heap drop | GC reclaimed | Retained scene cost | Build to first present | Min free | GC count/time | Frame gaps >200 ms | Max gap | Errors |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Control, cold | 6 | 168,848 B | n/a | n/a | 477 ms | 786,016 B | 3 / 0.237 s | 7 | 696 ms | 0 |
| Post-build GC, cold | 6 | 55,840 B | 27,504 B | 28,768 B | 620 ms | 786,000 B | 4 / 0.349 s | 6 | 773 ms | 0 |
| Control, warm | not captured | | n/a | n/a | | | n/a | | | |
| Post-build GC, warm | not captured | | | | | | | | | |

Board: MatrixPortal S3 UID `86EEF87F7005`, CircuitPython `10.3.0-dirty`; both
runs used the six-service live screen and B8 presentation preset. The exact
service contents may have changed between live fetches. These are single
cold-cycle captures, not repeated statistical samples. Post-build collection
reclaimed 27.5 KB, but the one run did not improve first-present latency or
minimum free heap; it is not a reason to enable the option by default.

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
not from the earlier maintenance slot. A valid prepared scene skips the
otherwise normal entry collection; its post-build collection already happened
during maintenance, and GC is disabled before animated presentation. A stale
or mismatched scene follows the existing on-demand entry path. `RAIL PREBUILD
OK/SKIP/REUSE` records explain the path selected.

| Run | Services | Train + prepared scene min free | Retained scene cost | Prebuild duration | Transition to present | Frame gaps >200 ms | Max gap | Errors |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Control, cold | 6 | n/a | n/a | n/a | 477 ms | 7 | 696 ms | 0 |
| Prebuild flag before adapter fix, cold (two on-demand cycles) | 6 | not prepared | n/a | n/a | 621 / 499 ms | 4 / 8 | 779 / 947 ms | 0 |
| Control, warm | not captured | n/a | n/a | n/a | | | | |
| Prebuild, warm | not captured | | | | | | | |

The prebuild flag was confirmed true in the running module. Two initial cold
cycles used the on-demand renderer. A follow-up diagnostic found that the
maintenance scheduler selected the future departures screen, but the
`QueueAwareDisplay` adapter did not forward `prepare_rail_scene` to the base
Matrix renderer (`reason=renderer_unavailable`). Forwarding and a host
regression test are now in the source; the successful physical handoff remains
to be measured. The production guard requires 2 MiB before building (1.5 MiB
reserve plus a 512 KiB scene estimate), above the board's approximately
1.67 MiB total free heap at startup. Any guarded physical trial must use an
explicit temporary test budget, then restore the defaults; keep the option
off until the train-plus-scene low-water result supports a production guard.

## Compact static service rows

Set `MATRIX_RAIL_STATIC_ROW_BITMAP_EXPERIMENT = True` in board-local
`settings_local.py` to render each static service row into a transparent,
single-bit bitmap. The row uses the existing font glyphs and the existing
column positions, and preserves the service-wide cancelled colour. It is an
isolated switch: keep post-build GC and prebuild off while measuring it. The
build log identifies the renderer (`static_row_renderer`) and number of
bitmaps (`static_row_bitmaps`); compare cold build heap drop and retained scene
cost with the normal labels at the same service count. The cache signature
includes this setting so a changed mode cannot reuse an incompatible scene.

| Run | Services | Static row renderer | Build heap drop | Retained scene cost | Build duration | First present | Min free | Frame gaps >200 ms | Max gap | Errors |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Labels, cold | 6 | labels | 168,848 B | n/a | 0.444 s | 477 ms | 786,016 B | 7 | 696 ms | 0 |
| Bitmap rows, cold | 6 | bitmap (6 bitmaps) | 80,624 B | n/a | 0.428 s | 449 ms | 785,408 B | 5 | 598 ms | 0 |
| Labels, warm | not captured | labels | | | | | | | | |
| Bitmap rows, warm | not captured | bitmap | | | | | | | | |

In this single six-service cold comparison, bitmap rows reduced the measured
build heap drop by 88,224 B (about 52%) and did not worsen measured first
presentation or minimum free heap. The user checked the physical display and
reported the rows looked fine, with no observed tearing, flashing, stalls, or
resets. Repeat with 4–5 services, the maximum configured payload, and warm
cycles before enabling the renderer by default; retained-scene cost was not
isolated in this bitmap run.

## Rail collection safety

The planned rail collection window now requires the calling marquee to be in
its end pause and the lower departure rows to be outside their slide/reset
movement. The clock/weather header currently switches while stationary. An
emergency low-heap collection remains available and its log marks
`heap_pressure_during_motion` when the planned safe window is unavailable.
Do not enable this experiment as the production default until repeated
physical runs show useful reclaimed memory without visible pauses or resets.

## Decision and remaining evidence

Keep post-build GC and prebuild disabled. The post-build run reclaimed
temporary allocations but had no one-run latency or low-water improvement.
Static bitmap rows are a promising, visually checked opt-in experiment, with a
measured six-service cold build reduction; retain default-off pending repeated
and larger-payload captures. Prebuild remains unmeasured because no preparation
record was produced, so do not lower its memory guard based on these captures.
Visible-row recycling is not justified by the current evidence.

Captures cover only six services and one cold rail cycle per control,
post-build-GC, and bitmap setting. The prebuild capture contains two
on-demand cycles. Four-to-five-service, maximum (up to ten) service, repeated
warm, and measured retained-cost comparisons remain open. The user observed
the bitmap rows once; this does not establish repeated physical acceptance.
Rollback is to leave the three `MATRIX_RAIL_*_EXPERIMENT` switches at their
default `False` values.
