# Direct-mount enclosure alignment audit

This audit tracks the mechanical files referenced by issue #76 and later enclosure follow-ups.

The distinction is important:

- **CAD-aligned** means the mating coordinates are derived from the same source or explicitly checked in CI.
- **Physically validated** requires a real printed part / real LED panel / real MatrixPortal fit test.

## Part/interface audit

| Part | Interface checked | CAD status | Physical status |
| --- | --- | --- | --- |
| `../stl/01_backplane_module_PRINT_3.stl` | P4 bosses, locator clearances, seam tongues, joiner inserts, accessory inserts, lid sockets | Aligned to current source | One real backplane still required |
| `../stl/01b_backplane_right_end_PRINT_1.stl` | Same as standard backplane, without unused outer seam features | Aligned to current source | One real fit still required |
| `../stl/02_module_joiner_PRINT_4.stl` | Four M3 holes vs neighbouring backplane inserts | **Corrected in this audit**: local y=9/51 at installed y=34 gives global y=43/85 | Print/assemble one seam |
| `../stl/03_rod_end_plug_PRINT_4.stl` | 7.2 mm reinforcement bore | Concentric/sized from common source | Retention fit remains physical |
| `../stl/04_matrixportal_mount_PRINT_1.stl` | Carrier M3 holes vs Panel 1 accessory inserts; MatrixPortal four-hole pattern | Carrier holes align exactly. Board orientation corrected to landscape | Fit real MatrixPortal |
| `../stl/05_power_distribution_mount_PRINT_1.stl` | Carrier M3 holes vs Panel 2 accessory inserts | Aligns exactly | Fit selected power hardware |
| `../stl/06_cable_clip_PRINT_8.stl` | Independent screw-down accessory | No fixed panel coordinate required | Fit cable bundle |
| `../stl/07_mounting_slot_coupon_PRINT_1.stl` | Heat-set insert pilot/depth | Reproduces production insert geometry | Print first for insert fit |
| `../stl/08_mount_pattern_template_PRINT_1.stl` | Six panel bosses + four locator clearances | Uses the same source coordinates as structural backplanes | Current physical template test remains source of truth |
| `../stl/09_centre_boss_desk_stand_PRINT_3.stl` | Lower-centre panel boss | Local stand screw maps to x=128, y=7.9 | Stability/screw length still physical |
| `../stl/10_rear_lid_PRINT_4.stl` | Four snap pegs vs four backplane sockets | **Corrected in this audit**: same XY coordinate system and exact centres | Print one PETG lid |

## Key coordinate checks

### Panel mounting

Current physical-fit-corrected panel boss centres:

- x = 7.9 / 128.0 / 248.1 mm
- y = 7.9 / 120.1 mm

The mounting template and both structural backplanes use these same source variables.

### Seam joiner

For each PRINT_4 joiner set:

- installed joiner origin y = 34 mm
- local screw rows y = 9 / 51 mm
- installed screw rows y = **43 / 85 mm**

These now match the backplane joiner heat-set insert rows exactly.

### MatrixPortal carrier-to-backplane

Carrier-local M3 holes:

- x = 6 / 238 mm
- y = 6 / 66 mm

Panel 1 carrier translation:

- x = +6 mm
- y = +28 mm

Installed carrier holes therefore become:

- x = **12 / 244 mm**
- y = **34 / 94 mm**

These exactly match the Panel 1 backplane accessory inserts. The power carrier uses the same local interface on Panel 2.

### MatrixPortal board direction

The MatrixPortal S3 is represented as:

- **63.50 mm long dimension along X**
- **44.45 mm short dimension along Y**
- the **short USB/button edge** faces the outside/left edge of Panel 1
- approximately 10 mm of board overhang is reserved for access

The previous portrait representation exposed the long edge and was not consistent with the physical controller orientation.

### Rear lid

Backplane socket centres:

- x = 64 / 192 mm
- y = 8 / 120 mm

Lid snap-peg centres are now exactly the same values. The lid also uses the same 255 × 127 mm rear footprint coordinate system, removing the former hidden +2 mm placement offset.

See `../schematics/10_rear_lid_alignment_ASSEMBLY.scad`.

## CI coverage

`../scripts/assembly_validation.json` now includes point-level checks for:

- all three seam-joiner screw patterns;
- MatrixPortal carrier M3 holes vs Panel 1 accessory inserts;
- power carrier M3 holes vs Panel 2 accessory inserts;
- lid peg centres vs socket centres;
- desk-stand lower-centre boss alignment.

Collision/interference and connected-component checks still run in addition to these coordinate checks.
