# LED enclosure CAD

Tracked by issue #53.

## Current design: direct-mount backplane

The enclosure is now **direct-mount only**. Four nominal 256 × 128 mm P4 HUB75 panels bolt directly to four printed rear backplane modules. Printed material stays behind the LED PCB so the full 1024 × 128 mm LED face remains unobstructed.

The superseded side-loading concept has been removed from the repository to avoid accidentally printing or maintaining the wrong parts.

See [`direct-mount/README.md`](direct-mount/README.md) for the printable parts list, hardware BOM, assembly order and validation notes.

## Source and generated STLs

- `direct-mount/direct_mount_enclosure.scad` — parametric source for all current parts.
- `direct-mount/01_backplane_module_PRINT_4.stl` — one rear backplane per LED panel.
- `direct-mount/02_module_joiner_PRINT_3.stl` — rear seam locks between neighbouring modules.
- `direct-mount/03_rod_end_plug_PRINT_4.stl` — retains the two 1 m × 8 mm reinforcement bars.
- `direct-mount/04_matrixportal_mount_PRINT_1.stl` — removable MatrixPortal S3 rear carrier.
- `direct-mount/05_power_distribution_mount_PRINT_1.stl` — removable fused 5 V distribution carrier.
- `direct-mount/06_cable_clip_PRINT_8.stl` — rear cable-management clips.
- `direct-mount/07_mounting_slot_coupon_PRINT_1.stl` — small fit test for mounting-slot/insert dimensions.

## Regenerating STLs

The repository workflow **Generate enclosure STLs** regenerates every checked-in STL from the OpenSCAD source.

The LED-panel mounting pattern is still provisional because the AliExpress order did not include a mechanical drawing. Print the slot coupon and one backplane first, measure the physical panel, then update the OpenSCAD dimensions before printing all four modules.
