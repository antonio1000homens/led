# LED enclosure CAD

Tracked by issue #53.

## Current design: direct-mount backplane

The enclosure is **direct-mount only**. Four nominal 256 × 128 mm P4 HUB75 panels bolt directly to three standard rear backplanes plus one dedicated right-end backplane. The physical rear moulding appears slightly smaller than the illuminated/front envelope, so each printed backplane is now centred at **255 × 127 mm** within the nominal 256 × 128 mm panel coordinate system. Printed material stays behind the LED PCB so the full 1024 × 128 mm LED face remains unobstructed.

The superseded side-loading concept has been removed.

See [`direct-mount/README.md`](direct-mount/README.md) for the expected mounting geometry, printable parts, hardware BOM and validation sequence.

## Current measured / physically corrected mounting geometry

The production mounting geometry no longer derives from the historical P2.5 reference model. A calibrated photograph and Kiri scan established a six-boss P4 layout. The first printed template moved the outer boss centres **2 mm inward**, and the next physical fit showed that correction was **0.5 mm too far inward**.

The current six boss centres are:

- x = **7.9, 128.0 and 248.1 mm**
- y = **7.9 and 120.1 mm**

The old P2.5-derived positions are retained only as separate moulded-locator clearance positions. The mounting coordinates remain referenced to the nominal 256 × 128 mm front-panel envelope even though the rear backplane itself is inset 0.5 mm on every edge. Print the revised low-material template and verify it physically before printing a structural backplane.

## Source and generated STLs

- `direct-mount/direct_mount_enclosure.scad` — parametric source for all current parts.
- `direct-mount/01_backplane_module_PRINT_3.stl` — three centred 255 × 127 mm rear backplanes with right-side alignment tongues, used on a 256 mm panel pitch.
- `direct-mount/01b_backplane_right_end_PRINT_1.stl` — rightmost 255 × 127 mm backplane without unused outer tongues/recesses.
- `direct-mount/02_module_joiner_PRINT_4.stl` — two recessed seam straps per STL/set, leaving a 16 mm-high rear flat-ribbon channel while a 4 mm front web keeps each backplane one piece.
- `direct-mount/03_rod_end_plug_PRINT_4.stl` — retains the two 1 m × 6 mm reinforcement bars.
- `direct-mount/04_matrixportal_mount_PRINT_1.stl` — removable MatrixPortal S3 rear carrier.
- `direct-mount/05_power_distribution_mount_PRINT_1.stl` — removable fused 5 V distribution carrier.
- `direct-mount/06_cable_clip_PRINT_8.stl` — rear cable-management clips.
- `direct-mount/07_mounting_slot_coupon_PRINT_1.stl` — slot test plus production-depth blind insert pocket.
- `direct-mount/08_mount_pattern_template_PRINT_1.stl` — full 256 × 128 mounting-pattern verification template.
- `direct-mount/09_centre_boss_desk_stand_PRINT_3.stl` — separately printed centre-boss desk stand with a 3 mm mounting plate and 15 mm forward anti-tip toe; print two for the complete display.
- `direct-mount/10_rear_lid_PRINT_4.stl` — open-sided snap-on rear cover; print four, preferably in PETG for repeated snap-fit use.

## Regenerating STLs

The repository workflow **Generate enclosure STLs** regenerates every checked-in STL from the OpenSCAD source. The seam geometry now provides a 16 mm-high × 12 mm-deep rear ribbon channel while retaining a 4 mm panel-facing structural web; CI also requires each backplane to be a single connected mesh. The rear lid uses dedicated snap sockets rather than the occupied reinforcement-bar bores.

The six-boss P4 pattern has now been refined by two physical fits, including a latest 0.5 mm outward correction. The revised template and one corrected backplane must still be physically verified before printing all four modules. The optional desk stand also requires a physical stability and screw-engagement check.
