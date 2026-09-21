# LED enclosure CAD

Tracked by issue #53.

## Current design: direct-mount backplane

The enclosure is **direct-mount only**. Four nominal 256 × 128 mm P4 HUB75 panels bolt directly to three standard rear backplanes plus one dedicated right-end backplane. Printed material stays behind the LED PCB so the full 1024 × 128 mm LED face remains unobstructed.

The superseded side-loading concept has been removed.

See [`direct-mount/README.md`](direct-mount/README.md) for the expected mounting geometry, printable parts, hardware BOM and validation sequence.

## Current expected mounting geometry

The supplied 160 × 80 mm P2.5 reference STL has four symmetric mounting centres at 16.69 / 143.31 mm horizontally and 7.50 / 72.50 mm vertically. Scaling by 1.6 to the 256 × 128 mm P4 envelope gives expected centres at:

- x = **26.704 mm** and **229.296 mm**
- y = **12.0 mm** and **116.0 mm**

The direct-mount CAD now uses those values. A low-material full-pattern test template is included so the pattern can be verified against one real P4 panel before the four structural backplanes are printed.

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

## Regenerating STLs

The repository workflow **Generate enclosure STLs** regenerates every checked-in STL from the OpenSCAD source.

The P4 mounting pattern is still an expected/scaled reference rather than a vendor mechanical drawing. Verify the pattern template and one backplane against the physical panel before printing all four modules.
