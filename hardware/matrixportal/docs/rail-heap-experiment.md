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
| Guarded prebuild before readiness-forwarding fix | 6 | 466,144 B observed during train | 42,832 B | 1.259 s | 501 ms, on-demand fallback | incomplete | 949 ms observed | 0 |
| Guarded prebuild after adapter fix, cold | 6 | 1,295,568 B train low-water | 42,448 B | 2.041 s | 30 ms | 7 | 923 ms | 0 |
| Control, warm | not captured | n/a | n/a | n/a | | | | |
| Prebuild, warm | not captured | | | | | | | |

The prebuild flag was confirmed true in the running module. The diagnostic
found that `QueueAwareDisplay` did not forward `prepare_rail_scene`; a
temporary 256 KiB reserve plus 256 KiB scene estimate then allowed a six
service build. It took 1.259 s, reclaimed 126,864 B, and retained 42,832 B;
the scene was reused in later maintenance windows. It remained allocated while
the train ran, with 466,144 B free at one sampled point. At the paired rail
boundary, however, `rail_scene_ready` and `rail_scene_prebuilt` were also
hidden by the adapter. The caller treated the scene as cold, discarded it,
and rebuilt on demand (501 ms to first present). All four adapter methods now
forward to the base display and have a host regression test. The corrected
physical run retained the six-service scene through the train intro and
presented departures in 30 ms. The user's visual check of the bitmap rows was
“looks fine”; no visual report for this corrected prebuild handoff was recorded
at the time of capture.

That faster entry did not remove later heap-pressure pauses. While departures
animated, the run forced two collections of about 0.7 s each, with frame gaps
of 894 ms and 923 ms. The full capture's minimum free heap was 318,880 B outside
the train/rail pair; its sampled train low-water was 1,295,568 B and the rail
capture's sampled minimum was 786,272 B. These are one cold six-service run,
not repeated or warm A/B measurements. Treat prebuild as an entry-latency
improvement only; leave it disabled until the independent animation-time heap
pressure and production guard are addressed and repeated payload runs are
recorded.

The production guard requires 2 MiB before building (1.5 MiB reserve plus a
512 KiB scene estimate), above the board's approximately 1.67 MiB total free
heap at startup. The guarded trial used an explicit temporary test budget.
The board's active `matrix_config.py` was restored to the staged default-off
file and its SHA-256 readback matched. A full staged upload then verified all
23 application files with `code.py` last, triggering the normal firmware
reload. The uploader refused to remove a pre-existing `boot.py` whose contents
did not match its temporary-workaround signature; no `boot.py` change was made.
Fresh serial startup logs after this reload were not captured.

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
| Labels, cold | 5 | labels | 160,960 B | n/a | 0.441 s | 464 ms | 788,096 B | 6 | 693 ms | 0 |
| Labels, next cycle | 5 | labels | 134,976 B | n/a | 0.388 s | 437 ms | 787,520 B | 6 | 886 ms | 0 |
| Bitmap rows, cold | 5 | bitmap (5 bitmaps) | 180,640 B | n/a | 0.324 s | 354 ms | 785,712 B | 5 | 564 ms | 0 |
| Bitmap rows, next cycle | 5 | bitmap (5 bitmaps) | 241,456 B | n/a | 0.339 s | 370 ms | 785,312 B | 6 | 629 ms | 0 |
| Bitmap rows, maximum, first cycle | 10 | bitmap (10 bitmaps) | 129,360 B | n/a | 0.524 s | 556 ms | 785,776 B | 5 | 767 ms | 0 |
| Bitmap rows, maximum, next cycle | 10 | bitmap (10 bitmaps) | 359,664 B | n/a | 0.533 s | 583 ms | 786,032 B | 5 | 1,039 ms | 0 |
| Labels, warm | not captured | labels | | | | | | | | |
| Bitmap rows, warm | not captured | bitmap | | | | | | | | |

In the single six-service cold comparison, bitmap rows reduced the measured
build heap drop by 88,224 B (about 52%) and did not worsen measured first
presentation or minimum free heap. The user checked those rows and reported
“looks fine”, with no observed tearing, flashing, stalls, or resets. The maximum
setting returned ten services from the live feed. The user visually checked
the maximum bitmap screen and reported “looks fine.” Two bitmap cycles measured
different build drops (129,360 B and 359,664 B) and first presentation at
556/583 ms; their current payloads were not byte-identical, so the difference
does not isolate cache or renderer cost. The two five-service label builds
dropped 160,960 B and 134,976 B and presented in 464/437 ms. The five-service
bitmap cycles dropped 180,640 B and 241,456 B and presented in 354/370 ms. The
bitmap runs had five/six frame gaps over 200 ms and a 785 KB rail low-water;
the label runs had six gaps and a 788 KB low-water. Emergency collections
during movement took 75/74 ms in the bitmap cycles and 76/84 ms in the label
cycles. The second build in each pair followed a scene discard, so neither is
a warm cache hit. Payload equivalence has not been established; the current
five-service results do not show a bitmap heap saving. Retained-scene cost
remains unmeasured for the bitmap renderer.

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
and larger-payload captures. Prebuild now has a successful six-service physical
handoff measurement, but later animation still forces long GC pauses and the
measured test budget is below the production guard. Keep it disabled pending
repeated and larger-payload captures. Visible-row recycling is not justified
by the current evidence.

Captures cover six services for control, post-build-GC, bitmap, and corrected
prebuild; five services for two label and two bitmap cycles; and ten services
for two bitmap cycles. Exact payloads differed across runs. Maximum-payload
labels, repeated warm/cache-identity checks, and retained-cost measurements
remain open. Overall rotation heap reached 129,680 B on non-rail
screens during the maximum bitmap run; the rail-only low-water stayed near
786 KB. The user visually accepted both the six-service and maximum bitmap
rows. The corrected prebuild run
reached the paired handoff after two earlier on-demand cycles.
Rollback is to leave the three `MATRIX_RAIL_*_EXPERIMENT` switches at their
default `False` values.
