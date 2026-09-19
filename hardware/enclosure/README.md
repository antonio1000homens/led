# LED enclosure CAD

Tracked by issue #53.

## Current design: direct-mount backplane

The preferred enclosure is a four-module rear backplane. Each nominal 256 × 128 mm P4 HUB75 panel mounts directly to one printed module. Printed material stays behind the LED PCB; the full 1024 × 128 mm display face is a keep-clear area.

- `direct-mount/backplane_module.scad` — parametric source.
- `direct-mount/backplane_module.stl` — generated printable module; print 4.
- Two 1000 mm × 8 mm reinforcement bars run through the four modules.
- The current mounting cross-slots are provisional until the real panel hole pattern is measured.

## Legacy concept: side-loading

`legacy-side-loading/` preserves the earlier slide-in concept for reference. It is **not** the preferred enclosure after issue #53 switched to direct mounting.

The generated legacy STL set contains:
- frame module
- left/right end caps
- rod-retainer clip
- seam bridge/panel stop
- MatrixPortal controller tray
- power-distribution tray
- cable clip
- panel-thickness gauge
- joint-fit coupon
- assembly reference
- exploded assembly reference

## Regenerating STLs

Use the repository workflow **Generate enclosure STLs** or run OpenSCAD locally.

Do not print all four direct-mount modules until the physical AliExpress panel has been measured and the provisional mounting slots have been validated.
