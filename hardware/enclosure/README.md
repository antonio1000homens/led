# LED enclosure CAD

Tracked by issues #53 and #76.

## Current design: direct-mount backplane

The enclosure is **direct-mount only**. Four nominal 256 × 128 mm P4 HUB75 panels bolt directly to four printed rear backplane modules. Printed material stays behind the LED PCB so the full 1024 × 128 mm LED face remains unobstructed.

The superseded side-loading concept has been removed.

See [`direct-mount/README.md`](direct-mount/README.md) for the expected mounting geometry, printable parts, hardware BOM and validation sequence.

## Current provisional physical mounting geometry

The purchased panel is treated as a 256 × 128 mm PCB. Issue #76 replaces the superseded P2.5 scaling assumption with the following six-point pattern derived from the physical panel/template photograph:

| Point | x (mm) | y (mm) |
| --- | ---: | ---: |
| bottom-left | 6 | 6 |
| bottom-centre | 128 | 6 |
| bottom-right | 250 | 6 |
| top-left | 6 | 122 |
| top-centre | 128 | 122 |
| top-right | 250 | 122 |

The CAD now uses explicit `panel_w`, `panel_h`, and `panel_mount_points` parameters. The nominal 6 mm edge offset is photo-derived and still requires one direct ruler/caliper verification before structural printing. The low-material full-pattern template is the first validation part.

## Source and generated STLs

- `direct-mount/direct_mount_enclosure.scad` — parametric source for all current parts.
- `direct-mount/01_backplane_module_PRINT_4.stl` — one rear backplane per LED panel.
- `direct-mount/02_module_joiner_PRINT_3.stl` — rear seam locks between neighbouring modules.
- `direct-mount/03_rod_end_plug_PRINT_4.stl` — retains the two 1 m × 8 mm reinforcement bars.
- `direct-mount/04_matrixportal_mount_PRINT_1.stl` — removable MatrixPortal S3 rear carrier.
- `direct-mount/04_matrixportal_mount_ASSEMBLY.svg` — documentation-only 1:1 carrier/PCB/backplane mounting overlay.
- `direct-mount/05_power_distribution_mount_PRINT_1.stl` — removable fused 5 V distribution carrier.
- `direct-mount/06_cable_clip_PRINT_8.stl` — rear cable-management clips.
- `direct-mount/07_mounting_slot_coupon_PRINT_1.stl` — small slot/insert test.
- `direct-mount/08_mount_pattern_template_PRINT_1.stl` — full 256 × 128 mounting-pattern verification template.

## Regenerating STLs

The repository workflow **Generate enclosure STLs** regenerates every checked-in STL from the OpenSCAD source.

The P4 mounting pattern is now an explicit six-point physical-panel hypothesis, not a scaled P2.5 reference. Verify the pattern template and one backplane against the physical panel before printing all four modules.

## MatrixPortal S3 carrier reference

The carrier uses the official [Adafruit MatrixPortal S3 CAD](https://github.com/adafruit/Adafruit_CAD_Parts/blob/main/5778%20Matrix%20Portal%20S3/5778%20Matrix%20Portal%20S3.stl) as its mechanical reference. The PCB is centred in the 244 × 72 mm carrier at 44.45 × 63.50 mm, portrait orientation: HUB75 at the top and USB-C at the bottom.

The four PCB mounting centres are explicit carrier-local coordinates:

| x (mm) | y (mm) |
| ---: | ---: |
| 115.650 | 19.490 |
| 135.335 | 19.490 |
| 115.650 | 60.130 |
| 135.335 | 60.130 |

The holes are round 2.8 mm M2.5-clearance holes on 19.685 × 40.640 mm spacing. The 5V/GND terminal screws are electrical terminals only, not mounting points. Carrier-to-backplane M3 points are carrier-local `(8,6)`, `(236,6)`, `(8,66)`, `(236,66)`, corresponding to backplane `(14,34)`, `(242,34)`, `(14,94)`, `(242,94)`.

The carrier is one connected printable solid: 2 mm-high side and 6 mm-wide cross-ribs join the four 8 mm posts at both MatrixPortal mounting rows while preserving the large central clearance opening. The posts start at z=2 mm and finish at the 10 mm PCB mounting surface. Captive M2.5 nut pockets open at the carrier bottom and connect to the round through-holes.
