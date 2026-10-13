# Rail departures heap and prebuild experiments

Issue #241 measures rail scene build/first-refresh cost, post-build collection,
and ahead-of-train preparation. Static service rows use the physically
accepted compact bitmap renderer by default. Repeated maximum-service captures
support guarded ahead-of-train preparation by default with a 1 MiB reserve and
512 KiB scene estimate. Post-build collection remains off.

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

`MATRIX_RAIL_PREBUILD_EXPERIMENT` now defaults to `True`; set it to `False` in
the ignored board-local `settings_local.py` to return to on-demand builds. The
firmware searches the existing
rotation for the future adjacent `steam_train_intro` → `rail_combined` pair
during an already scheduled static maintenance window. It does not add time to
the train or put work between the train and departures. Preparation is skipped
for stale/empty payloads and unless free heap exceeds the configured estimated
scene cost plus the reserve (`MATRIX_RAIL_PREBUILD_MAX_SCENE_BYTES` and
`MATRIX_RAIL_PREBUILD_MIN_FREE_BYTES`). The current guard requires more than
1.5 MiB free before building: a 1 MiB reserve plus a 512 KiB scene estimate.

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
| Ten-service bitmap, changed-content prebuild and handoff | 10 | 1,562,640 B at train exit | 9,552 B | 0.449 s | 0.823 s | 5 | 484 ms | 0 |
| Ten-service bitmap, repeated changed-content prebuild and handoff | 10 | 1,552,304 B at train exit | 9,552 B | 0.449 s | 0.824 s | 3 | 481 ms | 0 |
| Ten-service bitmap, candidate 1.5 MiB guard and handoff | 10 | 1,562,192 B at train exit | 9,552 B | 0.452 s | 0.826 s | 5 | 485 ms | 0 |
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

A maximum-payload bitmap capture started with fixture SHA-256
`39071c94a55483008bee981c1543bf07a3b50d603f5f7674aeb551c4fe131f7a` and then
changed one destination; the board request log confirmed the replacement
payload SHA-256 `e396f1a492fa0367f04e1100c6151fe8008d6e781504c56e229f42a341e07b64`.
The board logged `RAIL SCENE DISCARD reason=payload_or_settings_changed`, built
ten row bitmaps in 449 ms (333,152 B transient build drop), then completed
prebuild and collection in 823 ms total. The collection took 331 ms, reclaimed
324,064 B, and left a measured 9,552 B retained drop. The prepared scene was
reused in maintenance and across the adjacent train; first departures refresh
followed 28 ms after train exit, with 1,562,640 B free at train exit. This
confirms one physical changed-content invalidation and maximum-service prepared
handoff under a temporary 512 KiB reserve plus 512 KiB scene estimate. A repeat
using the same two payload hashes built the changed scene in 449 ms, completed
prebuild in 824 ms, retained 9,552 B, and presented 26 ms after train exit with
1,552,304 B free. A third capture used the candidate's 1 MiB reserve plus 512
KiB scene estimate. It built in 452 ms, completed prebuild in 826 ms, retained
9,552 B, and presented 28 ms after train exit with 1,562,192 B free. This
validates the candidate guard in one maximum-payload physical handoff.

Across the three prepared-handoff cycles, five/three/five frame gaps exceeded
200 ms, with maxima of 484/481/485 ms. The candidate-guard capture also had a
separate heap-pressure collection during rail movement that took 306 ms and
caused a 485 ms gap at 785,808 B free. Its rail low-water was 786,288 B. All
three captures had zero errors and serial reconnects. Each had three GC events
(prebuild, emergency, later planned), totaling 0.953/0.941/0.951 s. The
preceding cold on-demand entry had a 2,005 ms gap.

That faster entry did not remove later heap-pressure pauses. In the earlier
six-service run, two collections during departures took about 0.7 s each, with
frame gaps of 894 ms and 923 ms. The maximum-service captures also triggered
an emergency collection during animation, lasting about 306–307 ms at around
786 KiB free. Prebuild reduces transition latency; it does not prevent
animation-time heap-pressure collections.

The first two handoff captures used a temporary 512 KiB reserve plus a
512 KiB scene estimate. The third capture used the candidate's 1 MiB reserve
plus 512 KiB estimate. It passed with 1,750,624 B before preparation, 1,741,072
B after prebuild collection, and 1,562,192 B at train exit. After the trial,
the original production `settings_local.py` was restored and read back. The
full candidate upload verified all 23 staged files with `code.py` last. Remote
SHA-256 readback matched the candidate `matrix_config.py` and `code.py`, and
`settings_local.py` matched the saved production file. The candidate config has
bitmap rows and guarded prebuild on, with post-build GC off.

## Compact static service rows

With `MATRIX_RAIL_STATIC_ROW_BITMAP_EXPERIMENT = True` (the default), each
static service row is rendered into a transparent, single-bit bitmap. Set it
to `False` in board-local `settings_local.py` to restore the legacy label
renderer for comparison or rollback. The row uses the existing font glyphs and
column positions, and preserves the service-wide cancelled colour. Keep
post-build GC and prebuild off when comparing renderers. The
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
| Labels, maximum, first cycle | 10 | labels | 201,216 B | n/a | 0.623 s | 658 ms | 818,848 B | 84 | 889 ms | 0 |
| Labels, maximum, next cycle | 10 | labels | 202,928 B | n/a | 0.581 s | 633 ms | 788,592 B | 98 | 1,102 ms | 0 |
| Fixed 10-service payload, labels, cold | 10 | labels | 90,800 B | n/a | 6.037 s | 6,063 ms | 895,232 B | 63 | 6,339 ms | 0 |
| Fixed 10-service payload, bitmap, cold | 10 | bitmap (10 bitmaps) | 227,184 B | n/a | 0.687 s | 708 ms | 847,904 B | 3 | 956 ms | 0 |
| Fixed payload, labels, post-build GC | 10 | labels | 82,144 B | 65,408 B | 1.897 s | 1,988 ms | 900,688 B | 66 | 2,262 ms | 0 |
| Fixed payload, bitmap, post-build GC | 10 | bitmap (10 bitmaps) | 218,464 B | 5,840 B | 1.762 s | 2,031 ms | 940,048 B | 1 | 2,279 ms | 0 |
| Fixed payload, labels, warm cache | 10 | labels | n/a | n/a | n/a | n/a | 786,736 B | 73 | 363 ms | 0 |
| Fixed payload, bitmap, warm cache | 10 | bitmap (10 bitmaps) | n/a | n/a | n/a | n/a | 786,688 B | 4 | 467 ms | 0 |
| Same 3,482-byte payload, labels + post-build GC cold A | 10 | labels | -99,024 B | -115,264 B | 10.047 s | 10,541 ms | 1,113,936 B | 62 | 10,711 ms | 0 |
| Same 3,482-byte payload, labels + post-build GC cold B | 10 | labels | -98,864 B | -115,104 B | 10.111 s | 10,607 ms | 1,113,888 B | 60 | 10,780 ms | 0 |

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
cycles. The second build in each five-service pair followed a scene discard,
so neither is a warm cache hit. Payload equivalence has not been established;
the current five-service results do not show a bitmap heap saving.
Retained-scene cost for those live-feed runs remains unmeasured. The
ten-service label cycles dropped
201,216/202,928 B and first-presented in 658/633 ms, with 84/98 frame gaps
over 200 ms and maxima of 889/1,102 ms. These large gaps include screen entry
and emergency collection; no capture errors or serial reconnects were
recorded. Their current payloads were not verified byte-identical to the
bitmap pair, so this is not a strict A/B result. The user visually checked
the synthetic ten-service label screen and reported “looks fine”; no visual
defects were reported.

A deterministic ten-service screen payload then replaced the live feed for
matched label/bitmap runs. The board fetched the same 3,477-byte API response
with SHA-256 `3cddccfeaa73b4067ce6bc8b5c8382c65f4829c9164f7a7bdf178c18ca24580f`
throughout both runs. With post-build GC off and equal 1,589,248 B before-build
free heap, bitmap rows used 136,384 B more build heap but reached first present
5,355 ms sooner (708 ms versus 6,063 ms). Their first-cycle low-water was
47,328 B lower than labels. With post-build GC enabled for both renderers, the
bitmap retained-scene drop was 5,840 B versus 65,408 B for labels, a 59,568 B
(91%) reduction. Bitmap construction used 136,320 B more temporary heap and
its explicit collection took 235 ms versus 51 ms; first present was 2,031 ms
versus 1,988 ms. These results show a real retained-memory reduction with a
collection-time cost; they do not justify enabling both switches by default.
The exact payload was fetched unchanged before warm re-entry in both runs, and
no second `RAIL BUILD START` occurred, confirming that the cached scene was
reused after the intervening screens. The warm cycles had no capture errors.

To repeat the maximum-service post-build-GC label result, the board fetched the
same 3,482-byte fixture (SHA-256
`e396f1a492fa0367f04e1100c6151fe8008d6e781504c56e229f42a341e07b64`) on two
separate cold starts. The label builds took 10.047 and 10.111 s, with first
presentation at 10,541 and 10,607 ms. Both runs reclaimed 16,672 B in the
explicit post-build GC; the net retained-heap drops were -115,264 and
-115,104 B because automatic GC during construction had already increased
free heap by about 99 KB. This is a net free-heap change, not a claim that the
live scene occupies negative memory. Each cold entry had a frame gap above ten
seconds; the runs recorded 62/60 gaps above 200 ms, with maxima of
10,711/10,780 ms. Minimum free heap was 1,113,936/1,113,888 B, with no capture
errors or serial reconnects. Warm cached cycles did not rebuild the scene, but
still showed many frame gaps above 200 ms.

## Rail collection safety

The planned rail collection window now requires the calling marquee to be in
its end pause and the lower departure rows to be outside their slide/reset
movement. The clock/weather header currently switches while stationary. An
emergency low-heap collection remains available and its log marks
`heap_pressure_during_motion` when the planned safe window is unavailable.
Do not enable this experiment as the production default until repeated
physical runs show useful reclaimed memory without visible pauses or resets.

## Decision and remaining evidence

Keep post-build GC disabled. The post-build run reclaimed
temporary allocations but had no one-run latency or low-water improvement.
Static bitmap rows have a controlled ten-service retained-memory result: after
matched post-build collection they retained 59,568 B less than labels, while
using more temporary build heap and taking 184 ms longer to collect. The user
visually accepted the ten-service bitmap rows. Two exact-payload cold label
runs also reproduced first-presentation delays above 10.5 s. The compact
bitmap renderer is therefore the default; set its switch False to roll back to
labels. Two ten-service changed-content prebuild captures succeeded with the
measured 1.5 MiB guard and kept more than 1.55 MiB free through train exit.
Later animation still triggers an emergency collection around 786 KiB, so
prebuild does not remove the separate animation-time heap-pressure pause.
Visible-row recycling is not justified by the current evidence.

Captures cover six services for control, post-build-GC, bitmap, and corrected
prebuild; five services for two label and two bitmap cycles; and ten services
for two label and two bitmap live-feed cycles plus matched fixed-payload runs.
The unchanged fixture hash and absence of another `RAIL BUILD START` confirm
warm scene reuse across intervening screens. Three ten-service physical runs
demonstrated changed-content invalidation and completed prepared handoffs with
the same payload pair; the third validated the candidate guard. Repeated cold
post-GC label captures also exist for the same payload. Overall rotation
heap reached 129,680 B on non-rail
screens during the maximum bitmap run; the rail-only low-water stayed near
786 KB. The user visually accepted both the six-service and maximum bitmap
rows. The corrected prebuild run
reached the paired handoff after two earlier on-demand cycles.
Rollback the static row renderer by setting
`MATRIX_RAIL_STATIC_ROW_BITMAP_EXPERIMENT = False` in `settings_local.py`.
Keep `MATRIX_RAIL_POST_BUILD_GC_EXPERIMENT = False` to preserve normal GC
behavior. Set `MATRIX_RAIL_PREBUILD_EXPERIMENT = False` to restore on-demand
scene builds.
