# Enclosure schematics and assembly views

These OpenSCAD files are **non-printing direct-mount detail views/references**. Printable part entrypoints remain one directory above and generated meshes live in `../stl/`. The full four-panel assembly and projection views are intentionally kept in `../../complete_enclosure/` by PR #102.

Key files:

- `00_complete_enclosure_ASSEMBLY.scad` — complete four-panel rear assembly.
- `00_complete_enclosure_*_VIEW_SVG.scad` — front/back/side/top/bottom 2D projection wrappers.
- `04_matrixportal_side_access_ASSEMBLY.scad` — Panel 1 MatrixPortal carrier attachment and controller orientation.
- `10_rear_lid_alignment_ASSEMBLY.scad` — rear-lid peg/socket overlay.
- `matrixportal_s3_REFERENCE.scad` — simplified MatrixPortal S3 mechanical reference used by assembly views.

## MatrixPortal orientation

The controller reference is modelled **63.50 × 44.45 mm in landscape orientation**.

The **44.45 mm short edge** containing USB-C and Reset/Up/Down/Boot faces the outside/left edge of Panel 1. The board overhangs that edge by approximately 10 mm so the controls remain accessible.

## Rear lid alignment

The lid and backplane share the same nominal XY coordinate system. Lid pegs and backplane sockets are centred at:

- x = 64 / 192 mm
- y = 8 / 120 mm

Open `10_rear_lid_alignment_ASSEMBLY.scad` to inspect the mating centres directly.
