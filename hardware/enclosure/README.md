# LED enclosure CAD

Tracked by issue #53.

## Current design: direct-mount backplane

The enclosure is **direct-mount only**. Four nominal 256 × 128 mm P4 HUB75 panels bolt directly to three standard rear backplanes plus one dedicated right-end backplane. Printed material stays behind the LED PCB so the full 1024 × 128 mm LED face remains unobstructed.

The superseded side-loading concept has been removed.

See [`direct-mount/README.md`](direct-mount/README.md) for the expected mounting geometry, printable parts, hardware BOM and validation sequence.

## Current measured / physically corrected mounting geometry

The production mounting geometry no longer derives from the historical P2.5 reference model. A calibrated photograph and Kiri scan established a six-boss P4 layout, and the **first printed 1:1 template** then showed the outer boss centres needed to move **2 mm inward from every panel edge**.

The corrected six boss centres are:

- x = **8.4, 128.0 and 247.6 mm**
- y = **8.4 and 119.6 mm**

The old P2.5-derived positions are retained only as separate moulded-locator clearance positions. Print the revised low-material template and verify it physically before printing a structural backplane.

## Source and generated STLs

- `direct-mount/direct_mount_enclosure.scad` — parametric source for all current parts.
- `direct-mount/01_backplane_module_PRINT_3.stl` — three standard rear backplanes with right-side alignment tongues.
- `direct-mount/01b_backplane_right_end_PRINT_1.stl` — rightmost backplane without unused outer tongues/recesses.
- `direct-mount/02_module_joiner_PRINT_3.stl` — recessed rear seam locks with flush countersunk M3 fasteners.
- `direct-mount/03_rod_end_plug_PRINT_4.stl` — retains the two 1 m × 8 mm reinforcement bars.
- `direct-mount/04_matrixportal_mount_PRINT_1.stl` — removable MatrixPortal S3 rear carrier.
- `direct-mount/05_power_distribution_mount_PRINT_1.stl` — removable fused 5 V distribution carrier.
- `direct-mount/06_cable_clip_PRINT_8.stl` — rear cable-management clips.
- `direct-mount/07_mounting_slot_coupon_PRINT_1.stl` — slot test plus production-depth blind insert pocket.
- `direct-mount/08_mount_pattern_template_PRINT_1.stl` — full 256 × 128 mounting-pattern verification template.
- `direct-mount/09_centre_boss_desk_stand_PRINT_3.stl` — separately printed centre-boss desk stand with a 3 mm mounting plate and 15 mm forward anti-tip toe; print two for the complete display.

## Regenerating STLs

The repository workflow **Generate enclosure STLs** regenerates every checked-in STL from the OpenSCAD source.

The six-boss P4 pattern has been corrected from the first physical template fit, but the revised template and one corrected backplane must still be physically verified before printing all four modules. The optional desk stand also requires a physical stability and screw-engagement check.
